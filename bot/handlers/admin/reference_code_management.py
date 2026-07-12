from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from bot.database.methods import check_role
from bot.database.models.main import Permission
from bot.states.user_state import ReferenceCodeStates
from bot.keyboards import back, reference_code_admin_keyboard
from bot.keyboards.inline import InlineKeyboardBuilder
from bot.referrals import create_reference_code
from bot.i18n import localize
from bot.monitoring import get_metrics

router = Router()


@router.callback_query(F.data == "admin_refcode_management")
async def admin_refcode_menu(call: CallbackQuery, state: FSMContext):
    """
    Show reference code management menu (admin only)

    Args:
        call: Callback query
        state: FSM context
    """
    # Check admin permission
    user_role = check_role(call.from_user.id)
    if not (user_role & (Permission.SHOP_MANAGE | Permission.ADMINS_MANAGE)):
        await call.answer(localize("refcode.admin.access_denied"), show_alert=True)
        return

    await call.message.edit_text(
        localize("refcode.admin.menu"),
        reply_markup=reference_code_admin_keyboard(),
        parse_mode='HTML'
    )
    await state.clear()


@router.callback_query(F.data == "admin_create_refcode")
async def admin_create_refcode_start(call: CallbackQuery, state: FSMContext):
    """
    Start reference code creation process

    Args:
        call: Callback query
        state: FSM context
    """
    # Check admin permission
    user_role = check_role(call.from_user.id)
    if not (user_role & (Permission.SHOP_MANAGE | Permission.ADMINS_MANAGE)):
        await call.answer(localize("refcode.admin.access_denied"), show_alert=True)
        return

    await call.message.edit_text(
        localize("refcode.admin.create_prompt_expires"),
        reply_markup=back("admin_refcode_management"),
        parse_mode='HTML'
    )
    await state.set_state(ReferenceCodeStates.waiting_refcode_expires)


@router.message(ReferenceCodeStates.waiting_refcode_expires)
async def admin_create_refcode_expires(message: Message, state: FSMContext):
    """
    Process expiration hours input

    Args:
        message: Message with expiration hours
        state: FSM context
    """
    try:
        expires_hours = int(message.text)
        if expires_hours < 0:
            await message.answer(localize("refcode.admin.hours_positive"))
            return

        await state.update_data(expires_hours=expires_hours)

        await message.answer(
            localize("refcode.admin.create_prompt_max_uses"),
            reply_markup=back("admin_refcode_management"),
            parse_mode='HTML'
        )
        await state.set_state(ReferenceCodeStates.waiting_refcode_max_uses)

    except ValueError:
        await message.answer(localize("refcode.admin.enter_valid_number"))


@router.message(ReferenceCodeStates.waiting_refcode_max_uses)
async def admin_create_refcode_max_uses(message: Message, state: FSMContext):
    """
    Process max uses input

    Args:
        message: Message with max uses
        state: FSM context
    """
    try:
        max_uses = int(message.text)
        if max_uses < 0:
            await message.answer(localize("refcode.admin.max_uses_positive"))
            return

        await state.update_data(max_uses=max_uses)

        await message.answer(
            localize("refcode.admin.create_prompt_note"),
            reply_markup=back("admin_refcode_management"),
            parse_mode='HTML'
        )
        await state.set_state(ReferenceCodeStates.waiting_refcode_note)

    except ValueError:
        await message.answer(localize("refcode.admin.enter_valid_number"))


@router.message(ReferenceCodeStates.waiting_refcode_note)
async def admin_create_refcode_note(message: Message, state: FSMContext):
    """
    Process note and create the reference code

    Args:
        message: Message with note
        state: FSM context
    """
    note = None if message.text.lower() == 'skip' else message.text
    user_id = message.from_user.id
    username = message.from_user.username or f"admin_{user_id}"

    # Get stored data
    data = await state.get_data()
    expires_hours = data.get('expires_hours', 0)
    max_uses = data.get('max_uses', 0)

    try:
        code = create_reference_code(
            created_by=user_id,
            created_by_username=username,
            is_admin_code=True,
            expires_in_hours=expires_hours if expires_hours > 0 else None,
            max_uses=max_uses if max_uses > 0 else None,
            note=note
        )

        # Track admin referral code creation
        metrics = get_metrics()
        if metrics:
            metrics.track_event("admin_referral_code_created", user_id, {
                "code": code,
                "expires_hours": expires_hours,
                "max_uses": max_uses,
                "has_note": bool(note)
            })

        expires_text = localize("refcode.expires_hours", hours=expires_hours) if expires_hours > 0 else localize("refcode.never")
        max_uses_text = str(max_uses) if max_uses > 0 else localize("refcode.unlimited")

        await message.answer(
            localize(
                "refcode.admin.created",
                code=code, expires=expires_text,
                max_uses=max_uses_text, note=note or localize("refcode.none_note"),
            ),
            reply_markup=reference_code_admin_keyboard(),
            parse_mode='HTML'
        )
    except Exception as e:
        await message.answer(
            localize("refcode.admin.create_error", error=str(e)),
            reply_markup=reference_code_admin_keyboard()
        )

    await state.clear()


@router.callback_query(F.data == "admin_list_refcodes")
async def admin_list_refcodes(call: CallbackQuery, state: FSMContext):
    """
    List all reference codes

    Args:
        call: Callback query
        state: FSM context
    """
    # Check admin permission
    user_role = check_role(call.from_user.id)
    if not (user_role & (Permission.SHOP_MANAGE | Permission.ADMINS_MANAGE)):
        await call.answer(localize("refcode.admin.access_denied"), show_alert=True)
        return

    from bot.database.main import Database
    from bot.database.models.main import ReferenceCode

    with Database().session() as session:
        codes = session.query(ReferenceCode).order_by(
            ReferenceCode.created_at.desc()
        ).limit(20).all()

        if not codes:
            await call.message.edit_text(
                localize("refcode.admin.list_none"),
                reply_markup=back("admin_refcode_management")
            )
            return

        text = localize("refcode.admin.list_title")

        for code in codes:
            status = "✅" if code.is_active else "❌"
            code_type = localize("refcode.type_admin_emoji") if code.is_admin_code else localize("refcode.type_user_emoji")
            max_uses = str(code.max_uses) if code.max_uses else "∞"
            expires = code.expires_at.strftime('%Y-%m-%d %H:%M') if code.expires_at else localize("refcode.never")

            text += localize(
                "refcode.admin.list_entry",
                status=status, code=code.code, type=code_type,
                current=code.current_uses, max=max_uses, expires=expires,
            )
            if code.note:
                text += localize("refcode.admin.list_note", note=code.note)
            text += "\n"

        # Build keyboard with disable options
        kb = InlineKeyboardBuilder()
        kb.button(text=localize("btn.back"), callback_data="admin_refcode_management")
        kb.adjust(1)

        await call.message.edit_text(
            text,
            reply_markup=kb.as_markup(),
            parse_mode='HTML'
        )

    await state.clear()
