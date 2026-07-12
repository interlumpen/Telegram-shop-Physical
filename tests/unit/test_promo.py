"""
Tests for promo codes: validation, bindings, stacking on top of a sale, and
usage recording.
"""
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest

from bot.database.methods.promo import (
    create_promo_code, validate_promo_code, compute_promo_discount,
    record_promo_usage, set_promo_active,
)
from bot.database.models.main import PromoCode, PromoCodeUsage


def _cart(item_name, category_name, total):
    return [{"item_name": item_name, "category_name": category_name, "total": Decimal(str(total))}]


@pytest.mark.unit
@pytest.mark.database
class TestPromoValidation:
    def test_percent_discount(self, db_session):
        create_promo_code("SAVE10", "percent", Decimal("10"))
        ok, err, discount, promo = validate_promo_code("SAVE10", 1, _cart("X", "C", 200))
        assert ok, err
        assert discount == Decimal("20.00")

    def test_fixed_discount_capped_to_eligible(self, db_session):
        create_promo_code("BIG", "fixed", Decimal("1000"))
        ok, _, discount, _ = validate_promo_code("BIG", 1, _cart("X", "C", 50))
        assert ok
        assert discount == Decimal("50.00")  # never more than the eligible subtotal

    def test_invalid_code(self, db_session):
        ok, err, _, _ = validate_promo_code("NOPE", 1, _cart("X", "C", 100))
        assert not ok and err == "promo.error.invalid"

    def test_inactive_code(self, db_session):
        create_promo_code("OFF", "percent", Decimal("10"))
        set_promo_active("OFF", False)
        ok, err, _, _ = validate_promo_code("OFF", 1, _cart("X", "C", 100))
        assert not ok and err == "promo.error.invalid"

    def test_expired_code(self, db_session):
        create_promo_code("OLD", "percent", Decimal("10"),
                          expires_at=datetime.now(timezone.utc) - timedelta(hours=1))
        ok, err, _, _ = validate_promo_code("OLD", 1, _cart("X", "C", 100))
        assert not ok and err == "promo.error.expired"

    def test_category_binding_not_applicable(self, db_session):
        create_promo_code("CATONLY", "percent", Decimal("10"), category_name="Electronics")
        # cart item is in a different category -> not applicable
        ok, err, _, _ = validate_promo_code("CATONLY", 1, _cart("X", "Food", 100))
        assert not ok and err == "promo.error.not_applicable"

    def test_category_binding_applies_to_matching(self, db_session):
        create_promo_code("CAT2", "percent", Decimal("50"), category_name="Food")
        ok, _, discount, _ = validate_promo_code("CAT2", 1, _cart("X", "Food", 100))
        assert ok and discount == Decimal("50.00")

    def test_already_used_by_user(self, db_session, test_user):
        create_promo_code("ONCE", "percent", Decimal("10"))
        # record a usage for the existing user
        record_promo_usage("ONCE", test_user.telegram_id, None, Decimal("10"), db_session)
        db_session.commit()
        ok, err, _, _ = validate_promo_code("ONCE", test_user.telegram_id, _cart("X", "C", 100))
        assert not ok and err == "promo.error.already_used"
        # a different user can still use it
        ok2, _, _, _ = validate_promo_code("ONCE", 999, _cart("X", "C", 100))
        assert ok2

    def test_exhausted_max_uses(self, db_session, test_user):
        create_promo_code("LIMIT", "percent", Decimal("10"), max_uses=1)
        record_promo_usage("LIMIT", test_user.telegram_id, None, Decimal("10"), db_session)
        db_session.commit()
        ok, err, _, _ = validate_promo_code("LIMIT", 999, _cart("X", "C", 100))
        assert not ok and err == "promo.error.exhausted"


@pytest.mark.unit
class TestPromoStacksOnSale:
    def test_promo_computes_on_sale_price(self):
        # cart 'total' already reflects the sale (get_cart_items applies it), so a
        # 10% promo on an item that was 100 -> 80 (sale) discounts 8, not 10.
        promo = {"discount_type": "percent", "discount_value": Decimal("10"),
                 "category_name": None, "item_name": None}
        discount = compute_promo_discount(promo, _cart("X", "C", 80))
        assert discount == Decimal("8.00")


@pytest.mark.unit
@pytest.mark.database
class TestPromoUsageRecording:
    def test_record_usage_increments_and_inserts(self, db_session, test_user):
        create_promo_code("REC", "percent", Decimal("10"))
        ok = record_promo_usage("REC", test_user.telegram_id, None, Decimal("5"), db_session)
        db_session.commit()
        assert ok
        promo = db_session.query(PromoCode).filter_by(code="REC").first()
        assert promo.current_uses == 1
        usage = db_session.query(PromoCodeUsage).filter_by(code="REC", used_by=test_user.telegram_id).first()
        assert usage is not None and usage.discount_amount == Decimal("5.00")
