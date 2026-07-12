from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import datetime

from bot.database.methods import create_user
from bot.states.user_state import ReferenceCodeStates
from bot.referrals.codes import (
    validate_reference_code,
    use_reference_code,
    create_reference_code as create_ref_code
)
from bot.keyboards import back
from bot.config import EnvKeys
from bot.i18n import localize
from bot.monitoring import get_metrics

router = Router()


async def prompt_reference_code(message: Message, state: FSMContext):
    """
    Prompt user to enter a reference code

    Args:
        message: Message object
        state: FSM context
    """
    await message.answer(
        localize("refcode.user.prompt_enter"),
        reply_markup=back("cancel_start")
    )
    await state.set_state(ReferenceCodeStates.waiting_reference_code)


@router.message(ReferenceCodeStates.waiting_reference_code)
async def process_reference_code(message: Message, state: FSMContext):
    """
    Process entered reference code

    Args:
        message: Message with reference code
        state: FSM context
    """
    code = message.text.strip().upper()
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"

    # Validate the reference code
    is_valid, error_msg, creator_id = validate_reference_code(code, user_id)

    if not is_valid:
        await message.answer(
            localize("refcode.user.error_retry", error=error_msg),
            reply_markup=back("cancel_start")
        )
        return

    # Create user FIRST (required for foreign key constraint)
    from bot.database.methods import select_max_role_id
    owner_max_role = select_max_role_id()
    user_role = owner_max_role if user_id == EnvKeys.OWNER_ID else 1

    create_user(
        telegram_id=user_id,
        registration_date=datetime.datetime.now(),
        referral_id=creator_id,  # Track who referred this user
        role=user_role
    )

    # Now mark code as used (user must exist first due to FK constraint)
    success, error_msg, referrer_id = use_reference_code(code, user_id, username)

    if not success:
        await message.answer(
            localize("refcode.user.error_retry", error=error_msg),
            reply_markup=back("cancel_start")
        )
        return

    # Track referral code usage
    metrics = get_metrics()
    if metrics:
        metrics.track_event("referral_code_used", user_id, {
            "code": code,
            "referrer_id": referrer_id
        })
        metrics.track_conversion("referral_program", "code_used", user_id)

    # Clear state
    await state.clear()

    # Welcome message
    from bot.handlers.user.main import show_main_menu
    await message.answer(localize("refcode.user.welcome"))
    await show_main_menu(message, state)


@router.callback_query(F.data == "cancel_start")
async def cancel_start(call: CallbackQuery, state: FSMContext):
    """
    Cancel the start/registration process

    Args:
        call: Callback query
        state: FSM context
    """
    await state.clear()
    await call.message.edit_text(
        localize("refcode.user.registration_cancelled")
    )


@router.callback_query(F.data == "my_refcodes")
async def show_my_refcodes(call: CallbackQuery, state: FSMContext):
    """
    Show user's generated reference codes

    Args:
        call: Callback query
        state: FSM context
    """
    from bot.referrals.codes import get_user_reference_codes

    user_id = call.from_user.id
    codes = get_user_reference_codes(user_id, include_inactive=False)

    if not codes:
        await call.message.edit_text(
            localize("refcode.user.my_none"),
            reply_markup=back("referral_system")
        )
        return

    text = localize("refcode.user.my_title")

    for code_data in codes:
        code_type = localize("refcode.type_admin") if code_data['is_admin_code'] else localize("refcode.type_user")
        status = localize("refcode.status_active") if code_data['is_active'] else localize("refcode.status_inactive")
        max_uses = code_data['max_uses'] if code_data['max_uses'] else localize("refcode.unlimited")
        expires = code_data['expires_at'].strftime('%Y-%m-%d %H:%M') if code_data['expires_at'] else localize("refcode.never")

        text += localize(
            "refcode.user.my_entry",
            code=code_data['code'], type=code_type,
            current=code_data['current_uses'], max=max_uses,
            expires=expires, status=status,
        )

    await call.message.edit_text(text, reply_markup=back("referral_system"), parse_mode='HTML')
    await state.clear()


@router.callback_query(F.data == "create_my_refcode")
async def create_user_refcode(call: CallbackQuery, state: FSMContext):
    """
    Create a new user reference code (24h, 1 use)
    Users can only have ONE active code at a time

    Args:
        call: Callback query
        state: FSM context
    """
    user_id = call.from_user.id
    username = call.from_user.username or f"user_{user_id}"

    try:
        # Check if user already has an active code
        from bot.referrals.codes import get_user_reference_codes
        active_codes = get_user_reference_codes(user_id, include_inactive=False)

        # Filter to only user-created codes (not admin codes)
        active_user_codes = [c for c in active_codes if not c['is_admin_code']]

        if active_user_codes:
            # User already has an active code - show it
            existing_code = active_user_codes[0]
            expires_str = existing_code['expires_at'].strftime('%Y-%m-%d %H:%M') if existing_code['expires_at'] else 'Never'

            await call.message.edit_text(
                localize(
                    "refcode.user.create_existing",
                    code=existing_code['code'], expires=expires_str,
                    current=existing_code['current_uses'],
                    max=existing_code['max_uses'] or '∞',
                ),
                reply_markup=back("referral_system"),
                parse_mode='HTML'
            )
            return

        code = create_ref_code(
            created_by=user_id,
            created_by_username=username,
            is_admin_code=False  # This will auto-set 24h expiry and 1 use max
        )

        # Track referral code creation
        metrics = get_metrics()
        if metrics:
            metrics.track_event("referral_code_created", user_id, {
                "code": code,
                "is_admin": False
            })
            metrics.track_conversion("referral_program", "code_created", user_id)

        await call.message.edit_text(
            localize("refcode.user.create_success", code=code),
            reply_markup=back("referral_system"),
            parse_mode='HTML'
        )
    except Exception as e:
        await call.message.edit_text(
            localize("refcode.user.create_error", error=str(e)),
            reply_markup=back("referral_system")
        )

    await state.clear()
