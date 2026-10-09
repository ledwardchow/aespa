from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

import aespa.models  # noqa: F401
from aespa.config import get_settings
from alembic import context

# Alembic Config object, which provides access to values within alembic.ini
config = context.config

# Interpret the config file for Python logging
if config.config_file_name and config.attributes.get("configure_logging", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# Set database URL dynamically from runtime application settings
db_url = get_settings().database_url
config.set_main_option("sqlalchemy.url", db_url)

target_metadata = SQLModel.metadata

# These historical tables are read only during the Benchmark Lab extension's
# one-time import. Keep them on existing installations without treating their
# absence from core ORM metadata as an instruction to drop saved data.
_LEGACY_BENCHMARK_TABLES = {
    "benchmark_lab_config",
    "benchmark_dataset",
    "benchmark_evaluation",
    "benchmark_match",
    "benchmark_comparison",
    "benchmark_comparison_evaluation",
}


def _include_object(object, name, type_, reflected, compare_to):
    return not (type_ == "table" and name in _LEGACY_BENCHMARK_TABLES)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
        include_object=_include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
        include_object=_include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = config.attributes.get("connection", None)
    if connectable is None:
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
        with connectable.connect() as connection:
            _do_run_migrations(connection)
    else:
        if hasattr(connectable, "connect"):
            with connectable.connect() as connection:
                _do_run_migrations(connection)
        else:
            _do_run_migrations(connectable)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
