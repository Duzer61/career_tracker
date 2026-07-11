"""
Чистые вычислительные функции для статистики откликов.
Не содержит запросов к БД — только агрегация и расчёт метрик.
"""

from collections import defaultdict

from app.constants import FUNNEL_STATUSES, STATUS_LABELS
from app.db.models import ApplicationStatus
from app.schemas import StageDuration


def compute_time_to_stage(
    raw_rows: list[tuple[ApplicationStatus, float, float]],
) -> list[StageDuration]:
    """
    Принимает сырые строки из БД: (to_status, prev_timestamp_epoch, first_timestamp_epoch).
    Возвращает список StageDuration со статистиками по каждой паре статусов.

    Параметры:
        raw_rows: список кортежей, где каждый элемент — (to_status, prev_at_epoch, first_at_epoch).
    """
    # Пары последовательных статусов воронки: CREATED→HR, HR→TECH, TECH→OFFER
    status_pairs = list(zip(FUNNEL_STATUSES, FUNNEL_STATUSES[1:]))
    if not status_pairs:
        return []

    # Группируем дельты (часы) по парам переходов
    deltas: dict[tuple[ApplicationStatus, ApplicationStatus], list[float]] = defaultdict(list)
    for to_status, prev_at, first_at in raw_rows:
        delta_hours = (first_at - prev_at) / 3600
        if delta_hours >= 0:
            for from_s, to_s in status_pairs:
                if to_s == to_status:
                    deltas[(from_s, to_s)].append(delta_hours)
                    break

    # Считаем статистики по каждой паре: avg, median, min, max
    time_to_stage: list[StageDuration] = []
    for from_s, to_s in status_pairs:
        d = deltas.get((from_s, to_s), [])
        if not d:
            continue
        d_sorted = sorted(d)
        n = len(d_sorted)
        avg = round(sum(d_sorted) / n, 1)
        median = (
            round(d_sorted[n // 2], 1)
            if n % 2 == 1
            else round((d_sorted[n // 2 - 1] + d_sorted[n // 2]) / 2, 1)
        )
        time_to_stage.append(
            StageDuration(
                from_status=from_s,
                to_status=to_s,
                from_label=STATUS_LABELS[from_s],
                to_label=STATUS_LABELS[to_s],
                avg_hours=avg,
                median_hours=median,
                min_hours=round(d_sorted[0], 1),
                max_hours=round(d_sorted[-1], 1),
            )
        )
    return time_to_stage
