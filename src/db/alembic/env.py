"""
Alembic environment configuration for Rung database migrations.

Imports all models so autogenerate can detect schema changes.
Reads DATABASE_URL from environment, falling back to SQLite for development.
"""

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url from environment variable if set
database_url = os.getenv("DATABASE_URL")
if database_url:
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    config.set_main_option("sqlalchemy.url", database_url)

# Import Base and all models for autogenerate support
from src.models.base import Base  # noqa: E402
from src.models.therapist import Therapist  # noqa: E402, F401
from src.models.client import Client  # noqa: E402, F401
from src.models.session import Session  # noqa: E402, F401
from src.models.agent import Agent  # noqa: E402, F401
from src.models.clinical_brief import ClinicalBrief  # noqa: E402, F401
from src.models.client_guide import ClientGuide  # noqa: E402, F401
from src.models.development_plan import DevelopmentPlan  # noqa: E402, F401
from src.models.couple_link import CoupleLink  # noqa: E402, F401
from src.models.framework_merge import FrameworkMerge  # noqa: E402, F401
from src.models.audit_log import AuditLog  # noqa: E402, F401
from src.models.pipeline_run import PipelineRun  # noqa: E402, F401
from src.models.progress_metric import ProgressMetric  # noqa: E402, F401
from src.models.reading_item import ReadingItem  # noqa: E402, F401

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # Required for SQLite ALTER TABLE support
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Required for SQLite ALTER TABLE support
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
