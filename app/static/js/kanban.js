// Kanban board rendering and application loading

function renderKanbanBoard() {
    const board = document.getElementById('kanban-board');
    const statuses = Object.keys(STATUS_LABELS);

    // Filter applications by search query
    const filteredApplications = applications.filter(app => matchesSearch(app));

    // Update visible count
    document.getElementById('visible-count').textContent = filteredApplications.length;

    // Clear board
    board.innerHTML = '';

    // Create columns for each status (always render all columns)
    statuses.forEach(status => {
        const columnApps = filteredApplications.filter(app => app.status === status);

        const column = document.createElement('div');
        column.className = 'column';
        column.dataset.status = status;

        column.innerHTML = `
            <div class="column-header">
                <span class="column-title">${STATUS_LABELS[status]}</span>
                <span class="column-count">${columnApps.length}</span>
            </div>
            <div class="cards-container"></div>
        `;

        const cardsContainer = column.querySelector('.cards-container');

        columnApps.forEach(app => {
            const card = createCard(app);
            cardsContainer.appendChild(card);
        });

        board.appendChild(column);
    });
}

function createCard(app) {
    const card = document.createElement('div');
    card.className = 'card';
    card.draggable = true;
    card.dataset.applicationId = app.id;

    const daysClass = app.days_since_creation > 7 ? 'style="color: #e74c3c;"' : '';
    const commentsHtml = app.comments
        ? `<div class="card-field card-comments"><strong>Комментарий:</strong> ${escapeHtml(app.comments)}</div>`
        : '';

    card.innerHTML = `
        <div class="card-header">
            <span class="card-company">${escapeHtml(app.company_name)}</span>
            <div class="card-actions">
                <button class="card-btn view" title="Просмотр">👁️</button>
                <button class="card-btn edit" title="Редактировать">✏️</button>
                <button class="card-btn delete" title="Удалить">🗑️</button>
            </div>
        </div>
        <div class="card-body">
            <div class="card-field">${app.vacancy_url ? `<a href="${escapeHtml(app.vacancy_url)}" target="_blank" class="vacancy-link">${escapeHtml(app.vacancy_name || 'Not specified')}</a>` : `<strong>${escapeHtml(app.vacancy_name || 'Not specified')}</strong>`}</div>
            ${app.contacts ? `<div class="card-field"><strong>Контакты:</strong> ${escapeHtml(app.contacts)}</div>` : ''}
            ${commentsHtml}
        </div>
        <div class="card-footer">
            <span class="card-days" ${daysClass}>${app.days_since_creation} дн.</span>
            <span>${formatDate(app.created_at)}</span>
        </div>
    `;

    // Двойной клик для открытия просмотра
    card.addEventListener('dblclick', (e) => {
        // Игнорируем двойной клик по кнопкам действий
        if (e.target.closest('.card-btn')) return;
        openViewModal(app);
    });

    return card;
}

let loadingAppData = false;
async function loadApplications() {
    if (loadingAppData) return;
    loadingAppData = true;

    try {
        const query = buildFilterQuery();
        const response = await authenticatedFetch(`${API_BASE}/applications?${query}`);
        if (!response.ok) throw new Error('Failed to load');
        applications = await response.json();
        renderKanbanBoard();
    } catch (err) {
        // Silently fail — data will be stale
    } finally {
        loadingAppData = false;
    }
}

async function updateApplicationStatus(applicationId, newStatus) {
    try {
        const response = await authenticatedFetch(`${API_BASE}/applications/${applicationId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus })
        });

        if (!response.ok) throw new Error('Server error');

        // Reload to get fresh data
        await loadApplications();
    } catch (error) {
        alert('Не удалось обновить статус заявки');
    }
}