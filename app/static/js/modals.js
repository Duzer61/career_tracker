const FIELD_LABELS = {
    company_name: 'Компания',
    vacancy_name: 'Вакансия',
    contacts: 'Контакты',
    vacancy_url: 'Ссылка на вакансию',
    comments: 'Комментарии',
};

const MAX_LENGTHS = {
    company_name: 255,
    vacancy_name: 255,
    contacts: 500,
    vacancy_url: 500,
};

// Utility: extract user-friendly error message from API response
function extractErrorMessage(data) {
    if (typeof data.detail === 'string') {
        return data.detail;
    }
    if (Array.isArray(data.detail) && data.detail.length > 0) {
        const first = data.detail[0];
        const rawField = first.loc?.length > 1 ? first.loc[1] : '';
        const field = FIELD_LABELS[rawField] || rawField;
        const msg = first.msg || 'Ошибка валидации';
        return field ? `${field}: ${msg}` : msg;
    }
    return data.detail?.message || 'Ошибка сохранения';
}

// Modal logic and status history
// Modal references are initialized in app.js initDomRefs()

function openApplicationModal(app = null) {
    editingApplicationId = app ? app.id : null;
    const title = document.getElementById('modal-title');
    const form = document.getElementById('application-form');

    form.reset();
    document.getElementById('application-id').value = '';

    if (app) {
        title.textContent = 'Редактировать заявку';
        document.getElementById('application-id').value = app.id;
        document.getElementById('company-name').value = app.company_name || '';
        document.getElementById('vacancy-name').value = app.vacancy_name || '';
        document.getElementById('vacancy-url').value = app.vacancy_url || '';
        document.getElementById('contacts').value = app.contacts || '';
        document.getElementById('comments').value = app.comments || '';
        document.getElementById('status').value = app.status;
    } else {
        title.textContent = 'Новая заявка';
    }

    applicationModal.classList.remove('hidden');
}

function closeApplicationModal() {
    if (applicationModal) applicationModal.classList.add('hidden');
    editingApplicationId = null;
}

async function handleApplicationSubmit(e) {
    e.preventDefault();

    const id = document.getElementById('application-id').value;
    const companyName = document.getElementById('company-name').value.trim();
    const vacancyName = document.getElementById('vacancy-name').value.trim();
    const vacancyUrl = document.getElementById('vacancy-url').value.trim();
    const contacts = document.getElementById('contacts').value.trim();
    const comments = document.getElementById('comments').value.trim();
    const status = document.getElementById('status').value;
    if (companyName.length > MAX_LENGTHS.company_name) {
        alert(`${FIELD_LABELS.company_name}: длина не должна превышать ${MAX_LENGTHS.company_name} символов`);
        return;
    }
    if (vacancyName.length > MAX_LENGTHS.vacancy_name) {
        alert(`${FIELD_LABELS.vacancy_name}: длина не должна превышать ${MAX_LENGTHS.vacancy_name} символов`);
        return;
    }
    if (contacts && contacts.length > MAX_LENGTHS.contacts) {
        alert(`${FIELD_LABELS.contacts}: длина не должна превышать ${MAX_LENGTHS.contacts} символов`);
        return;
    }
    if (vacancyUrl && vacancyUrl.length > MAX_LENGTHS.vacancy_url) {
        alert(`${FIELD_LABELS.vacancy_url}: длина не должна превышать ${MAX_LENGTHS.vacancy_url} символов`);
        return;
    }

    const body = {
        company_name: companyName,
        vacancy_name: vacancyName,
        vacancy_url: vacancyUrl || null,
        contacts: contacts || null,
        comments: comments || null,
        status: status
    };

    try {
        let response;
        if (id) {
            response = await authenticatedFetch(`${API_BASE}/applications/${id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
        } else {
            response = await authenticatedFetch(`${API_BASE}/applications`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
        }

        if (response.ok) {
            closeApplicationModal();
            await loadApplications();
        } else {
            const data = await response.json();
            alert(extractErrorMessage(data));
        }
    } catch (err) {
        alert('Ошибка подключения');
    }
}

function openViewModal(application) {
    if (!application) return;

    document.getElementById('view-modal-title').textContent = escapeHtml(application.company_name) +
        (application.vacancy_name ? ` — ${escapeHtml(application.vacancy_name)}` : '');

    const statusLabel = STATUS_LABELS[application.status] || application.status;

    const daysWarning = application.days_since_creation > 7
        ? `<span style="color: #e74c3c;">${application.days_since_creation} дн.</span>`
        : `${application.days_since_creation} дн.`;

    document.getElementById('view-modal-body').innerHTML = `
        <div class="view-field-row">
            <div class="view-field">
                <div class="view-field-label">Компания</div>
                <div class="view-field-value">${escapeHtml(application.company_name)}</div>
            </div>
            <div class="view-field">
                <div class="view-field-label">Статус</div>
                <div class="view-field-value">
                    <span class="view-field-status status-${application.status}">${escapeHtml(statusLabel)}</span>
                </div>
            </div>
        </div>
        ${application.vacancy_url ? `
        <div class="view-field">
            <div class="view-field-label">Ссылка на вакансию</div>
            <div class="view-field-value view-field-url">
                <a href="${escapeHtml(application.vacancy_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(application.vacancy_url)}</a>
            </div>
        </div>
        ` : ''}
        ${application.contacts ? `
        <div class="view-field">
            <div class="view-field-label">Контакты</div>
            <div class="view-field-value">${escapeHtml(application.contacts)}</div>
        </div>
        ` : ''}
        ${application.comments ? `
        <div class="view-field">
            <div class="view-field-label">Комментарии</div>
            <div class="view-field-value view-field-comments">${escapeHtml(application.comments)}</div>
        </div>
        ` : ''}
        <div class="view-field-row">
            <div class="view-field">
                <div class="view-field-label">Дата создания</div>
                <div class="view-field-value">${formatDate(application.created_at)}</div>
            </div>
            <div class="view-field">
                <div class="view-field-label">Дней в работе</div>
                <div class="view-field-value">${daysWarning}</div>
            </div>
        </div>
        <!-- Status History Section -->
        <div class="history-section">
            <div class="history-title">История статусов</div>
            <div id="history-loading" style="font-size: 14px; color: #888;">Загрузка...</div>
            <ul class="history-list" id="history-list"></ul>
            <div class="history-error" id="history-error"></div>
        </div>
    `;

    viewModal.classList.remove('hidden');

    // Load status history
    loadStatusHistory(application.id);
}

function closeViewModal() {
    if (viewModal) viewModal.classList.add('hidden');
}

function showDeleteModal(applicationId) {
    currentDeleteApplicationId = applicationId;
    if (deleteModal) deleteModal.classList.remove('hidden');
}

function closeDeleteModal() {
    if (deleteModal) deleteModal.classList.add('hidden');
    currentDeleteApplicationId = null;
}

async function handleConfirmDelete() {
    if (!currentDeleteApplicationId) return;
    await deleteApplication(currentDeleteApplicationId);
    closeDeleteModal();
}

async function deleteApplication(applicationId) {
    try {
        const response = await authenticatedFetch(`${API_BASE}/applications/${applicationId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            applications = applications.filter(a => a.id !== applicationId);
            renderKanbanBoard();
        } else {
            const data = await response.json();
            alert(extractErrorMessage(data));
        }
    } catch (err) {
        alert('Ошибка подключения');
    }
}

// ====== Status History ======

async function loadStatusHistory(applicationId) {
    const listEl = document.getElementById('history-list');
    const loadingEl = document.getElementById('history-loading');
    const errorEl = document.getElementById('history-error');

    try {
        const response = await authenticatedFetch(`${API_BASE}/applications/${applicationId}/history`);
        if (!response.ok) throw new Error('Failed to load history');

        const history = await response.json();
        loadingEl.style.display = 'none';
        renderStatusHistory(history, applicationId);
    } catch (err) {
        loadingEl.style.display = 'none';
        errorEl.textContent = 'Ошибка загрузки истории статусов';
        errorEl.style.display = 'block';
    }
}

function canDeleteHistoryEntry(index, history) {
    // Первая запись — никогда нельзя удалять
    if (index === 0) return false;

    // Последняя запись
    if (index === history.length - 1) {
        if (history.length > 2) return false;               // записей > 2
        if (history.length === 2) {                          // ровно 2 записи
            return history[0].status === history[1].status;  // можно только если статусы совпадают
        }
        return false;
    }

    // Средняя запись (не первая и не последняя) — всегда можно
    return true;
}

function renderStatusHistory(history, applicationId) {
    const listEl = document.getElementById('history-list');
    listEl.innerHTML = '';

    history.forEach((entry, index) => {
        const isCurrent = index === history.length - 1;
        const li = document.createElement('li');
        li.className = 'history-entry' + (isCurrent ? ' is-current' : '');

        const date = formatDateTime(entry.changed_at);
        const showDelete = canDeleteHistoryEntry(index, history);

        li.innerHTML = `
            <span class="history-entry-date">${date}</span>
            <span class="history-entry-status">
                <span class="status-badge status-${entry.status}">${STATUS_LABELS[entry.status] || entry.status}</span>
                ${isCurrent ? '<span class="history-entry-current-label">текущий</span>' : ''}
            </span>
            ${showDelete ? '<button class="history-delete-btn" title="Удалить запись истории" data-history-id="' + entry.id + '">🗑️</button>' : ''}
        `;

        listEl.appendChild(li);
    });

    // Attach delete handlers only to existing delete buttons
    listEl.querySelectorAll('.history-delete-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const historyId = parseInt(btn.dataset.historyId);
            await deleteHistoryEntry(applicationId, historyId);
        });
    });
}

async function deleteHistoryEntry(applicationId, historyId) {
    if (!confirm('Удалить эту запись истории?')) return;

    const errorEl = document.getElementById('history-error');
    errorEl.style.display = 'none';

    try {
        const response = await authenticatedFetch(
            `${API_BASE}/applications/${applicationId}/history/${historyId}`,
            { method: 'DELETE' }
        );

        if (response.ok) {
            // Reload history
            await loadStatusHistory(applicationId);
        } else {
            const data = await response.json();
            errorEl.textContent = extractErrorMessage(data);
            errorEl.style.display = 'block';
        }
    } catch (err) {
        errorEl.textContent = 'Ошибка подключения';
        errorEl.style.display = 'block';
    }
}