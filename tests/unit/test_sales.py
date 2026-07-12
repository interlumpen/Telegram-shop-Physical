"""
Tests for time-limited sales: the effective_price helper and its application in
the cart, plus set_item_sale.
"""
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest

from bot.utils.money import effective_price, format_sale_percent


@pytest.mark.unit
class TestEffectivePrice:
    def test_no_sale(self):
        final, on_sale, original = effective_price(Decimal("100"))
        assert final == Decimal("100.00")
        assert on_sale is False
        assert original == Decimal("100.00")

    def test_active_sale(self):
        until = datetime.now(timezone.utc) + timedelta(days=1)
        final, on_sale, original = effective_price(100, 20, until)
        assert on_sale is True
        assert final == Decimal("80.00")
        assert original == Decimal("100.00")

    def test_expired_sale_ignored(self):
        until = datetime.now(timezone.utc) - timedelta(days=1)
        final, on_sale, _ = effective_price(100, 20, until)
        assert on_sale is False
        assert final == Decimal("100.00")

    def test_iso_string_until_from_cache(self):
        # Cached item dicts store sale_until as an ISO string and percent as str.
        until = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        final, on_sale, _ = effective_price(100, "25.00", until)
        assert on_sale is True
        assert final == Decimal("75.00")

    def test_percent_clamped_to_100(self):
        until = datetime.now(timezone.utc) + timedelta(days=1)
        final, on_sale, _ = effective_price(100, 150, until)
        assert on_sale is True
        assert final == Decimal("0.00")

    def test_zero_percent_is_not_a_sale(self):
        until = datetime.now(timezone.utc) + timedelta(days=1)
        _, on_sale, _ = effective_price(100, 0, until)
        assert on_sale is False

    def test_missing_until_is_not_a_sale(self):
        _, on_sale, _ = effective_price(100, 20, None)
        assert on_sale is False

    def test_format_sale_percent(self):
        assert format_sale_percent(Decimal("20.00")) == "20"
        assert format_sale_percent(Decimal("15.50")) == "15.5"
        assert format_sale_percent(5) == "5"


@pytest.mark.unit
@pytest.mark.database
class TestSaleInCart:
    async def test_get_cart_items_charges_sale_price(self, db_session, test_user, test_goods):
        from bot.database.methods.update import set_item_sale
        from bot.database.methods import get_cart_items
        from bot.database.models.main import ShoppingCart

        until = datetime.now(timezone.utc) + timedelta(days=1)
        ok, err = set_item_sale(test_goods.name, Decimal("50"), until)
        assert ok, err

        db_session.add(ShoppingCart(user_id=test_user.telegram_id, item_name=test_goods.name, quantity=2))
        db_session.commit()

        items = await get_cart_items(test_user.telegram_id)
        assert len(items) == 1
        row = items[0]
        assert row["on_sale"] is True
        # 50% off, quantity 2
        assert row["price"] == (row["original_price"] * Decimal("0.5")).quantize(Decimal("0.01"))
        assert row["total"] == row["price"] * 2

    async def test_remove_sale(self, db_session, test_goods):
        from bot.database.methods.update import set_item_sale
        from bot.database.methods import get_cart_items
        from bot.database.models.main import ShoppingCart, Goods

        until = datetime.now(timezone.utc) + timedelta(days=1)
        set_item_sale(test_goods.name, Decimal("50"), until)
        ok, _ = set_item_sale(test_goods.name, None, None)
        assert ok

        good = db_session.query(Goods).filter_by(name=test_goods.name).first()
        db_session.refresh(good)
        assert good.sale_percent is None
        assert good.sale_until is None
