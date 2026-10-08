// Utility functions

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Parse a server datetime. The server may return a naive UTC string (no
// timezone suffix, e.g. "2025-01-01T12:00:00") or a timezone-aware ISO string
// ("...+00:00" / "...Z"). Naive strings are treated as UTC by appending "Z".
function parseServerDate(dateString) {
    if (!dateString) return null;
    const hasTimezone = /(Z|[+-]\d{2}:?\d{2})$/.test(dateString);
    return new Date(hasTimezone ? dateString : dateString + 'Z');
}

function formatDate(dateString) {
    return parseServerDate(dateString).toLocaleDateString('ru-RU');
}

function formatDateTime(dateString) {
    return parseServerDate(dateString).toLocaleDateString('ru-RU', {
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
