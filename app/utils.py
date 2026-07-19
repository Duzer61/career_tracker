from datetime import datetime, timedelta, timezone

from fastapi import HTTPException


def utc_now() -> datetime:
    """Возвращает дату и время по UTC"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def start_of_day(dt: datetime) -> datetime:
    """Возвращает начало дня (00:00:00.000000)."""
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def end_of_day(dt: datetime) -> datetime:
    """Возвращает конец дня (23:59:59.999999) для включения всех записей за эту дату."""
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def validate_password_strength(v: str) -> str:
    """Validate password strength: min 8 chars, upper, lower, digit, ASCII only."""
    rules = [
        (len(v) >= 8, "Пароль должен содержать минимум 8 символов."),
        (any(c.islower() for c in v), "Пароль должен содержать хотя бы одну строчную букву."),
        (any(c.isupper() for c in v), "Пароль должен содержать хотя бы одну заглавную букву."),
        (any(c.isdigit() for c in v), "Пароль должен содержать хотя бы одну цифру."),
        (v.isascii(), "Пароль должен содержать только символы ASCII."),
    ]
    errors = [msg for is_valid, msg in rules if not is_valid]
    if errors:
        raise ValueError(" ".join(errors))
    return v


def parse_date_filters(
    period: str | None,
    date_from: str | None,
    date_to: str | None,
    now: datetime,
) -> tuple[datetime | None, datetime | None]:
    """
    Парсит и валидирует параметры фильтрации по дате.

    Поддерживает предустановленные периоды (today, week, month, old)
    и произвольный интервал (date_from / date_to в ISO-формате).

    Возвращает кортеж (date_from_dt, date_to_dt).
    """
    date_from_dt: datetime | None = None
    date_to_dt: datetime | None = None

    if period:
        period = period.strip().lower()
        if period == "today":
            date_from_dt = start_of_day(now)
        elif period == "yesterday":
            date_from_dt = start_of_day(now) - timedelta(days=1)
            date_to_dt = end_of_day(now - timedelta(days=1))
        elif period == "week":
            date_from_dt = start_of_day(now) - timedelta(days=7)
        elif period == "month":
            date_from_dt = start_of_day(now) - timedelta(days=30)
        elif period == "old":
            date_to_dt = start_of_day(now) - timedelta(days=30)
        else:
            raise HTTPException(
                status_code=422,
                detail=f"Неизвестный период: '{period}'. Допустимые: today, yesterday, week, month, old",
            )
    else:
        # Если нет period, пробуем распарсить date_from / date_to
        if date_from:
            try:
                date_from_dt = datetime.fromisoformat(date_from)
            except ValueError:
                raise HTTPException(
                    status_code=422,
                    detail=f"Неверный формат date_from: '{date_from}'. Используйте ISO-формат (напр. 2025-01-01)",
                )

        if date_to:
            try:
                date_to_dt = datetime.fromisoformat(date_to)
            except ValueError:
                raise HTTPException(
                    status_code=422,
                    detail=f"Неверный формат date_to: '{date_to}'. Используйте ISO-формат (напр. 2025-01-31)",
                )

        # Проверка года в разумном диапазоне (2000–2100)
        valid_range = "от 2000 до 2100"
        if date_from_dt and (date_from_dt.year < 2000 or date_from_dt.year > 2100):
            raise HTTPException(
                status_code=422,
                detail=f"Год в date_from должен быть {valid_range}, получено: {date_from_dt.year}",
            )
        if date_to_dt and (date_to_dt.year < 2000 or date_to_dt.year > 2100):
            raise HTTPException(
                status_code=422,
                detail=f"Год в date_to должен быть {valid_range}, получено: {date_to_dt.year}",
            )

        # Преобразуем date_to_dt в конец дня для включения всех записей за эту дату
        if date_to_dt:
            date_to_dt = end_of_day(date_to_dt)

    return date_from_dt, date_to_dt
