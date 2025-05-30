from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

import os
import sys
from dotenv import load_dotenv

project_root = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
dotenv_path = os.path.join(project_root, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print(f"Alembic env.py: Loaded .env file from {dotenv_path}")
else:
    print(f"Warning: Alembic env.py: .env file not found at {dotenv_path}. Relying on environment variables.")

sys.path.insert(0, project_root)

from app.core.database import Base
from app.database.postgres_models import device_models

from app.core.config import settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

if settings.DATABASE_URL:
    config.set_main_option('sqlalchemy.url', settings.DATABASE_URL)
    print(f"Alembic env.py: Using DATABASE_URL from settings: {settings.DATABASE_URL[:30]}...")
else:
    print(
        "Warning: Alembic env.py: DATABASE_URL not found in settings. Alembic might fail or use a default from alembic.ini if any.")

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# alembic/env.py (всередині run_migrations_online)

def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    configuration = config.get_section(config.config_ini_section)

    if settings.DATABASE_URL:
        configuration['sqlalchemy.url'] = settings.DATABASE_URL
    else:
        if 'sqlalchemy.url' not in configuration:
            print("ERROR: sqlalchemy.url is not set in alembic.ini and DATABASE_URL is not available from settings.")

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    print("Running migrations in offline mode...")
    run_migrations_offline()
else:
    print("Running migrations in online mode...")
    run_migrations_online()
