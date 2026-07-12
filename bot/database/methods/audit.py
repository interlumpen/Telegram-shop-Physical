import logging
from typing import Optional

from sqlalchemy.orm import Session

from bot.database.main import Database
from bot.database.models.main import AuditLog
from bot.logger_mesh import audit_logger

logger = logging.getLogger(__name__)

_VALID_LEVELS = {"INFO", "WARNING", "ERROR"}


def log_audit(
    action: str,
    level: str = "INFO",
    user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
    session: Optional[Session] = None,
) -> None:
    """Record an audit event to both the rotating audit.log file and audit_log table.

    Args:
        action: short action name, e.g. "order_confirmed", "user_banned".
        level: INFO / WARNING / ERROR.
        user_id: the actor (admin/user) or None for system actions.
        resource_type / resource_id: the affected entity, e.g. "Order" / "ABCDEF".
        details: free-form context.
        ip_address: for web/CLI actions where a client IP is known.
        session: if given, the DB row is added to that session (no commit — it
                 becomes part of the caller's transaction); otherwise a short
                 own-session write is committed immediately.
    """
    level = level.upper()
    if level not in _VALID_LEVELS:
        level = "INFO"

    # 1) File log (always attempted, cheap, never raises).
    parts = [f"action={action}"]
    if user_id is not None:
        parts.append(f"user={user_id}")
    if resource_type or resource_id:
        parts.append(f"resource={resource_type or ''}:{resource_id or ''}")
    if ip_address:
        parts.append(f"ip={ip_address}")
    if details:
        parts.append(f"details={details}")
    audit_logger.log(getattr(logging, level, logging.INFO), " ".join(parts))

    # 2) DB write (best-effort). Never propagate failures to the caller.
    entry = AuditLog(
        action=action,
        level=level,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=(str(resource_id) if resource_id is not None else None),
        details=details,
        ip_address=ip_address,
    )
    try:
        if session is not None:
            session.add(entry)
        else:
            with Database().session() as own:
                own.add(entry)
    except Exception as e:  # pragma: no cover - defensive
        logger.error(f"Failed to write audit_log DB entry for action '{action}': {e}")


def get_recent_audit_logs(limit: int = 50, action: Optional[str] = None,
                          user_id: Optional[int] = None) -> list[dict]:
    """Return the most recent audit entries (newest first) for CLI/reporting."""
    with Database().session() as s:
        query = s.query(AuditLog)
        if action:
            query = query.filter(AuditLog.action == action)
        if user_id is not None:
            query = query.filter(AuditLog.user_id == user_id)
        rows = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "created_at": r.created_at,
                "level": r.level,
                "action": r.action,
                "user_id": r.user_id,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "details": r.details,
                "ip_address": r.ip_address,
            }
            for r in rows
        ]
