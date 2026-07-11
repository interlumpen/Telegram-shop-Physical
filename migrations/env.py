from dotenv import load_dotenv

load_dotenv(encoding='utf-8')

from sqlalchemy import create_engine, pool

from alembic import context

# Import the app metadata and every model so autogenerate/create_all see them.
from bot.database.main import Database
import bot.database.models.main  # noqa: F401  (populates Database.BASE.metadata)
from bot.database.dsn import dsn

config = context.config

target_metadata = Database.BASE.metadata


def _get_url() -> str:
    return config.get_main_option("sqlalchemy.url") or dsn()


def run_migrations_offline() -> None:
    context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(_get_url(), poolclass=pool.NullPool)
    try:
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                # Batch mode makes ALTER TABLE work on SQLite (tests / smoke-check).
                render_as_batch=connection.dialect.name == "sqlite",
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
