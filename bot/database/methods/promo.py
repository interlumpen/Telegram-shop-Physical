from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from bot.database.main import Database
from bot.database.models.main import PromoCode, PromoCodeUsage
from bot.utils.money import as_datetime


def _q2(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _eligible_subtotal(promo: dict, cart_items: list) -> Decimal:
    """Sum of cart-item totals the promo applies to (respecting any binding)."""
    if promo.get("item_name"):
        rows = [i for i in cart_items if i["item_name"] == promo["item_name"]]
    elif promo.get("category_name"):
        rows = [i for i in cart_items if i.get("category_name") == promo["category_name"]]
    else:
        rows = cart_items
    return sum((Decimal(str(i["total"])) for i in rows), Decimal("0"))


def compute_promo_discount(promo: dict, cart_items: list) -> Decimal:
    """Discount amount for a promo against the given cart items (never negative)."""
    eligible = _eligible_subtotal(promo, cart_items)
    if eligible <= 0:
        return Decimal("0.00")

    if promo["discount_type"] == "percent":
        percent = min(Decimal(str(promo["discount_value"])), Decimal("100"))
        discount = eligible * percent / Decimal("100")
    else:  # fixed
        discount = Decimal(str(promo["discount_value"]))

    discount = min(discount, eligible)  # never discount more than the eligible amount
    if discount < 0:
        discount = Decimal("0")
    return _q2(discount)


def validate_promo_code(code: str, user_id: int, cart_items: list
                        ) -> Tuple[bool, Optional[str], Decimal, Optional[dict]]:
    """Validate a promo code for a user + cart.

    Returns (is_valid, error_i18n_key, discount, promo_dict).
    """
    code = (code or "").strip().upper()
    if not code:
        return False, "promo.error.invalid", Decimal("0"), None

    with Database().session() as s:
        promo = s.query(PromoCode).filter_by(code=code).first()
        if not promo or not promo.is_active:
            return False, "promo.error.invalid", Decimal("0"), None

        expires = as_datetime(promo.expires_at)
        if expires and expires <= datetime.now(timezone.utc):
            return False, "promo.error.expired", Decimal("0"), None

        if promo.max_uses is not None and (promo.current_uses or 0) >= promo.max_uses:
            return False, "promo.error.exhausted", Decimal("0"), None

        already = s.query(PromoCodeUsage).filter_by(code=code, used_by=user_id).first()
        if already:
            return False, "promo.error.already_used", Decimal("0"), None

        promo_dict = {
            "code": promo.code,
            "discount_type": promo.discount_type,
            "discount_value": promo.discount_value,
            "category_name": promo.category_name,
            "item_name": promo.item_name,
        }

    discount = compute_promo_discount(promo_dict, cart_items)
    if discount <= 0:
        return False, "promo.error.not_applicable", Decimal("0"), None

    return True, None, discount, promo_dict


def record_promo_usage(code: str, user_id: int, order_id: int, discount, session: Session) -> bool:
    """Record a promo usage inside the order transaction and bump current_uses.

    Locks the promo row to keep current_uses correct under concurrency. The
    unique (code, used_by) constraint is the final guard against double use.
    """
    promo = session.query(PromoCode).filter_by(code=code).with_for_update().first()
    if not promo:
        return False
    promo.current_uses = (promo.current_uses or 0) + 1
    session.add(PromoCodeUsage(
        code=code, used_by=user_id, discount_amount=_q2(discount), order_id=order_id
    ))
    return True


# ---- Admin management ----

def create_promo_code(code: str, discount_type: str, discount_value,
                      category_name: str = None, item_name: str = None,
                      max_uses: int = None, expires_at=None,
                      created_by: int = None) -> Tuple[bool, Optional[str]]:
    """Create a promo code. Returns (success, error_reason)."""
    code = (code or "").strip().upper()
    if not code:
        return False, "empty_code"
    if discount_type not in ("percent", "fixed"):
        return False, "bad_type"
    with Database().session() as s:
        if s.query(PromoCode).filter_by(code=code).first():
            return False, "exists"
        s.add(PromoCode(
            code=code, discount_type=discount_type, discount_value=discount_value,
            category_name=category_name or None, item_name=item_name or None,
            max_uses=max_uses, expires_at=expires_at, created_by=created_by,
        ))
    return True, None


def list_promo_codes(active_only: bool = False, limit: int = 50) -> list[dict]:
    with Database().session() as s:
        query = s.query(PromoCode)
        if active_only:
            query = query.filter(PromoCode.is_active.is_(True))
        rows = query.order_by(PromoCode.created_at.desc()).limit(limit).all()
        return [{
            "code": r.code,
            "discount_type": r.discount_type,
            "discount_value": r.discount_value,
            "category_name": r.category_name,
            "item_name": r.item_name,
            "max_uses": r.max_uses,
            "current_uses": r.current_uses,
            "expires_at": r.expires_at,
            "is_active": r.is_active,
        } for r in rows]


def set_promo_active(code: str, active: bool) -> bool:
    with Database().session() as s:
        promo = s.query(PromoCode).filter_by(code=(code or "").strip().upper()).first()
        if not promo:
            return False
        promo.is_active = active
        return True


def delete_promo_code(code: str) -> bool:
    with Database().session() as s:
        deleted = s.query(PromoCode).filter_by(
            code=(code or "").strip().upper()
        ).delete(synchronize_session=False)
        return bool(deleted)
