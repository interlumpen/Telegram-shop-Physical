"""
Tests for the audit-log dual-write (file + DB) helper.
"""
import pytest

from bot.database.methods.audit import log_audit, get_recent_audit_logs
from bot.database.models.main import AuditLog


@pytest.mark.unit
@pytest.mark.database
class TestAuditLog:
    def test_log_audit_writes_db_row(self, db_session):
        log_audit("unit_action", user_id=42, resource_type="Order",
                  resource_id="ABC123", details="did a thing")
        rows = get_recent_audit_logs(action="unit_action")
        assert len(rows) == 1
        row = rows[0]
        assert row["action"] == "unit_action"
        assert row["user_id"] == 42
        assert row["resource_type"] == "Order"
        assert row["resource_id"] == "ABC123"
        assert row["details"] == "did a thing"

    def test_log_audit_with_session_joins_caller_transaction(self, db_session):
        # With a session, the row is added but not committed by log_audit itself.
        log_audit("txn_action", user_id=7, session=db_session)
        pending = db_session.query(AuditLog).filter_by(action="txn_action").all()
        assert len(pending) == 1
        db_session.commit()

    def test_resource_id_coerced_to_string(self, db_session):
        # Numeric resource ids (e.g. telegram_id) must be stored as strings.
        log_audit("user_banned", level="WARNING", user_id=1, resource_type="User",
                  resource_id=123456789)
        row = get_recent_audit_logs(action="user_banned")[0]
        assert row["resource_id"] == "123456789"
        assert row["level"] == "WARNING"

    def test_invalid_level_defaults_to_info(self, db_session):
        log_audit("lvl_action", level="BOGUS")
        assert get_recent_audit_logs(action="lvl_action")[0]["level"] == "INFO"
