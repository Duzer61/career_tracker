// Constants
const API_BASE = '/api';

// Yandex SmartCaptcha site key (set from server-side template)
let SMARTCAPTCHA_SITE_KEY = '';

// Application statuses mapping
const STATUS_LABELS = {
    created: 'Отклик',
    hr_interview: 'HR собеседование',
    tech_interview: 'Тех. собеседование',
    offer: 'Оффер',
    auto_reject: 'Автоотказ',
    rejected: 'Отказ',
    ignored: 'Игнор'
};