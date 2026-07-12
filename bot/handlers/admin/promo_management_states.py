from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.i18n import localize
from bot.database.models import Permission
from bot.database.methods import (
    create_promo_code, list_promo_codes, set_promo_active, delete_promo_code,
)
from bot.database.methods.audit import log_audit
from bot.keyboards.inline import back, simple_buttons
from bot.filters import HasPermissionFilter
from bot.states import PromoFSM
from bot.utils.money import format_sale_percent, format_price, as_datetime

router = Router()

_PERM = Permission.SHOP_MANAGE


def _promo_menu_keyboard():
    return simple_buttons([
        (localize("admin.promo.create"), "promo_create"),
        (localize("admin.promo.list"), "promo_list"),
        (localize("btn.back"), "console"),
    ], per_row=1)


@router.callback_query(F.data == "admin_promo_management", HasPermissionFilter(permission=_PERM))
async def promo_menu(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(localize("admin.promo.menu"), reply_markup=_promo_menu_keyboard())
    await state.clear()


# ----- Create flow -----

@router.callback_query(F.data == "promo_create", HasPermissionFilter(permission=_PERM))
async def promo_create_start(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(localize("admin.promo.prompt.code"), reply_markup=back("admin_promo_management"))
    await state.set_state(PromoFSM.waiting_code)


@router.message(PromoFSM.waiting_code, F.text)
async def promo_create_code(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    if not code or len(code) > 32 or ' ' in code:
        await message.answer(localize("admin.promo.invalid_code"))
        return
    await state.update_data(promo_code=code)
    await message.answer(
        localize("admin.promo.prompt.type"),
        reply_markup=simple_buttons([
            (localize("admin.promo.type_percent"), "promo_type_percent"),
            (localize("admin.promo.type_fixed"), "promo_type_fixed"),
            (localize("btn.back"), "admin_promo_management"),
        ], per_row=1)
    )
    await state.set_state(PromoFSM.waiting_type)


@router.callback_query(F.data.startswith("promo_type_"), PromoFSM.waiting_type)
async def promo_create_type(call: CallbackQuery, state: FSMContext):
    discount_type = call.data.replace("promo_type_", "")  # percent | fixed
    await state.update_data(discount_type=discount_type)
    prompt = "admin.promo.prompt.value_percent" if discount_type == "percent" else "admin.promo.prompt.value_fixed"
    await call.message.edit_text(localize(prompt), reply_markup=back("admin_promo_management"))
    await state.set_state(PromoFSM.waiting_value)


@router.message(PromoFSM.waiting_value, F.text)
async def promo_create_value(message: Message, state: FSMContext):
    data = await state.get_data()
    discount_type = data.get("discount_type")
    try:
        value = Decimal((message.text or "").strip().replace(',', '.'))
    except (InvalidOperation, ValueError):
        await message.answer(localize("admin.promo.invalid_value"))
        return
    if value <= 0 or (discount_type == "percent" and value >= 100):
        await message.answer(localize("admin.promo.invalid_value"))
        return
    await state.update_data(discount_value=str(value))
    await message.answer(localize("admin.promo.prompt.max_uses"), reply_markup=back("admin_promo_management"))
    await state.set_state(PromoFSM.waiting_max_uses)


@router.message(PromoFSM.waiting_max_uses, F.text)
async def promo_create_max_uses(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer(localize("admin.promo.invalid_number"))
        return
    await state.update_data(max_uses=int(text))
    await message.answer(localize("admin.promo.prompt.expiry_hours"), reply_markup=back("admin_promo_management"))
    await state.set_state(PromoFSM.waiting_expiry_hours)


@router.message(PromoFSM.waiting_expiry_hours, F.text)
async def promo_create_finish(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer(localize("admin.promo.invalid_number"))
        return
    hours = int(text)

    data = await state.get_data()
    code = data["promo_code"]
    discount_type = data["discount_type"]
    discount_value = Decimal(data["discount_value"])
    max_uses = data["max_uses"] or None
    expires_at = datetime.now(timezone.utc) + timedelta(hours=hours) if hours > 0 else None

    ok, reason = create_promo_code(
        code=code, discount_type=discount_type, discount_value=discount_value,
        max_uses=max_uses, expires_at=expires_at, created_by=message.from_user.id,
    )
    if not ok:
        key = "admin.promo.exists" if reason == "exists" else "admin.promo.create_error"
        await message.answer(localize(key), reply_markup=back("admin_promo_management"))
        await state.clear()
        return

    log_audit("promo_created", user_id=message.from_user.id, resource_type="PromoCode",
              resource_id=code, details=f"{discount_type}={discount_value}; max_uses={max_uses}; hours={hours}")
    await message.answer(localize("admin.promo.created", code=code), reply_markup=back("admin_promo_management"))
    await state.clear()


# ----- List / toggle / delete -----

def _format_promo(p: dict) -> str:
    if p["discount_type"] == "percent":
        value = f"-{format_sale_percent(p['discount_value'])}%"
    else:
        value = f"-{format_price(p['discount_value'])}"
    status = "✅" if p["is_active"] else "❌"
    uses = f"{p['current_uses']}/{p['max_uses'] if p['max_uses'] is not None else '∞'}"
    exp = as_datetime(p["expires_at"])
    exp_str = exp.strftime('%Y-%m-%d %H:%M') if exp else localize("refcode.never")
    binding = p["item_name"] or p["category_name"] or "—"
    return localize("admin.promo.list_entry", status=status, code=p["code"], value=value,
                    uses=uses, expires=exp_str, binding=binding)


@router.callback_query(F.data == "promo_list", HasPermissionFilter(permission=_PERM))
async def promo_list(call: CallbackQuery, state: FSMContext):
    promos = list_promo_codes(limit=30)
    if not promos:
        await call.message.edit_text(localize("admin.promo.list_none"), reply_markup=back("admin_promo_management"))
        return

    text = localize("admin.promo.list_title") + "\n\n" + "\n".join(_format_promo(p) for p in promos)
    buttons = []
    for p in promos:
        toggle_label = localize("admin.promo.disable") if p["is_active"] else localize("admin.promo.enable")
        buttons.append((f"{toggle_label}: {p['code']}", f"promo_toggle_{p['code']}"))
        buttons.append((f"🗑 {p['code']}", f"promo_delete_{p['code']}"))
    buttons.append((localize("btn.back"), "admin_promo_management"))
    await call.message.edit_text(text, parse_mode='HTML', reply_markup=simple_buttons(buttons, per_row=1))
    await state.clear()


@router.callback_query(F.data.startswith("promo_toggle_"), HasPermissionFilter(permission=_PERM))
async def promo_toggle(call: CallbackQuery, state: FSMContext):
    code = call.data.replace("promo_toggle_", "")
    promos = {p["code"]: p for p in list_promo_codes(limit=1000)}
    current = promos.get(code)
    new_active = not current["is_active"] if current else True
    if set_promo_active(code, new_active):
        log_audit("promo_toggled", user_id=call.from_user.id, resource_type="PromoCode",
                  resource_id=code, details=f"active={new_active}")
    await promo_list(call, state)


@router.callback_query(F.data.startswith("promo_delete_"), HasPermissionFilter(permission=_PERM))
async def promo_delete(call: CallbackQuery, state: FSMContext):
    code = call.data.replace("promo_delete_", "")
    if delete_promo_code(code):
        log_audit("promo_deleted", level="WARNING", user_id=call.from_user.id,
                  resource_type="PromoCode", resource_id=code)
    await promo_list(call, state)
