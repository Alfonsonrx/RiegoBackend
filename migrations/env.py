from logging.config import fileConfig

from alembic import context

from app.database import engine  # connection settings from the environment (002 FR-3)
from app.models import Base

if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name, disable_existing_loggers=False)  # keep app/pytest loggers

if context.is_offline_mode():  # `--sql`: print the SQL instead of running it
    context.configure(url=engine.url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
