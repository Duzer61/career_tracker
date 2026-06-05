// Utility functions

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    const utcString = dateString.endsWith('Z') ? dateString : dateString + 'Z';
    const date = new Date(utcString);
    return date.toLocaleDateString('ru-RU');
}

function formatDateTime(dateString) {
    // Сервер отдаёт datetime без часового пояса (UTC, но без Z на конце)
    // Принудительно добавляем Z, чтобы new Date() трактовал время как UTC
    const utcString = dateString.endsWith('Z') ? dateString : dateString + 'Z';
    const date = new Date(utcString);
    return date.toLocaleDateString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function pluralizeRussian(n) {
    const mod100 = Math.abs(n) % 100;
    if (mod100 > 10 && mod100 < 20) return `${n} откликов перенесено`;
    switch (mod100 % 10) {
        case 1: return `${n} отклик перенесен`;
        case 2:
        case 3:
        case 4: return `${n} отклика перенесено`;
        default: return `${n} откликов перенесено`;
    }
}
