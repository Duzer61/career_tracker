from datetime import datetime, timezone


def utc_now() -> datetime:
    """Возвращает дату и время по UTC"""
    return datetime.now(timezone.utc).replace(tzinfo=None)
