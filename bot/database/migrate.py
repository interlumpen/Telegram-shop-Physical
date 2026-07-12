import logging
from pathlib import Path

from sqlalchemy import inspect
from alembic.config import Config
from alembic import command

from bot.database.main import Database

# bot/database/migrate.py -> project root
_PROJECT_ROOT = Path(__file__).resolve().parents[2]

BASELINE_REVISION = "0001_baseline"

# Presence of any of these tables means the schema predates Alembic (was built by
# the old create_all()) and should be stamped, not recreated.
_LEGACY_MARKER_TABLES = {"users", "goods", "orders"}


def get_alembic_config() -> Config:
    cfg = Config(str(_PROJECT_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_PROJECT_ROOT / "migrations"))
    return cfg


def run_migrations() -> None:
    """Bring the database schema up to head.

    - alembic_version present    -> upgrade head (already Alembic-managed)
    - legacy schema, no version  -> stamp baseline, then upgrade head
    - empty database             -> upgrade head (builds the full schema)
    """
    engine = Database().engine
    tables = set(inspect(engine).get_table_names())
    cfg = get_alembic_config()

    if "alembic_version" in tables:
        logging.info("Applying database migrations (upgrade -> head)...")
        command.upgrade(cfg, "head")
    elif tables & _LEGACY_MARKER_TABLES:
        logging.info(
            "Existing pre-Alembic schema detected; stamping baseline and upgrading to head..."
        )
        command.stamp(cfg, BASELINE_REVISION)
        command.upgrade(cfg, "head")
    else:
        logging.info("Empty database; building schema via migrations (upgrade -> head)...")
        command.upgrade(cfg, "head")

    logging.info("Database migrations applied.")
