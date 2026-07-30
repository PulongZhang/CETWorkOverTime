from functools import lru_cache
from urllib.parse import quote_plus

from sqlalchemy import Engine, create_engine

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    password = quote_plus(settings.db_password)
    url = (
        f"mysql+pymysql://{settings.db_user}:{password}"
        f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
        f"?charset={settings.db_charset}"
    )
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600)


def dispose_engine() -> None:
    if get_engine.cache_info().currsize:
        get_engine().dispose()
        get_engine.cache_clear()
