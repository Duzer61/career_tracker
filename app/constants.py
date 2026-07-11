"""Константы предметной области для приложения Career Tracker."""

from app.db.models import ApplicationStatus

# Маппинг статусов на человекочитаемые русские названия
STATUS_LABELS: dict[ApplicationStatus, str] = {
    ApplicationStatus.CREATED: "Создано",
    ApplicationStatus.HR_INTERVIEW: "HR-интервью",
    ApplicationStatus.TECH_INTERVIEW: "Техническое интервью",
    ApplicationStatus.OFFER: "Оффер",
    ApplicationStatus.AUTO_REJECT: "Автоотказ",
    ApplicationStatus.REJECTED: "Отказ",
    ApplicationStatus.IGNORED: "Игнорировано",
}

# Порядок статусов для воронки (позитивные, без терминальных)
FUNNEL_STATUSES: list[ApplicationStatus] = [
    ApplicationStatus.CREATED,
    ApplicationStatus.HR_INTERVIEW,
    ApplicationStatus.TECH_INTERVIEW,
    ApplicationStatus.OFFER,
]

# Терминальные статусы (завершающие)
TERMINAL_STATUSES: set[ApplicationStatus] = {
    ApplicationStatus.AUTO_REJECT,
    ApplicationStatus.REJECTED,
    ApplicationStatus.IGNORED,
}
