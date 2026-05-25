// API base URL
const API_BASE = '/api';

// Application statuses mapping
const STATUS_LABELS = {
    created: 'Отклик',
    hr_interview: 'HR собеседование',
    tech_interview: 'Техническое собеседование',
    offer: 'Оффер',
    auto_reject: 'Автоотказ',
    rejected: 'Отказ',
    ignored: 'Игнор'
};

// State
let currentUser = null;
let applications = [];
let editingApplicationId = null;
// Чтение сохранённого состояния сортировки из sessionStorage (живёт до закрытия вкладки)
const savedSort = sessionStorage.getItem('sortAscending');
let sortAscending = savedSort !== null ? savedSort === 'true' : false; // false = сначала новые (desc), true = сначала старые (asc)

// Filter state
let filterPeriod = ''; // '', today, week, month, old
let customDateFrom = '';
let customDateTo = '';

// Refresh token tracking
let refreshInProgress = false;

// Helper function to make authenticated requests with auto-refresh
async function authenticatedFetch(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        credentials: 'include'
    });

    // If token expired, try to refresh
    if (response.status === 401) {
        console.log('Token expired, attempting refresh...');
        
        // If refresh already in progress, wait for it
        if (refreshInProgress) {
            console.log('Waiting for refresh to complete...');
            await new Promise(resolve => {
                const checkInterval = setInterval(() => {
                    if (!refreshInProgress) {
                        clearInterval(checkInterval);
                        resolve();
                    }
                }, 100);
            });
            // Retry the original request with new token
            return fetch(url, {
                ...options,
                credentials: 'include'
            });
        }

        // Try to refresh token
        refreshInProgress = true;
        try {
            const refreshResponse = await fetch(`${API_BASE}/auth/refresh`, {
                method: 'POST',
                credentials: 'include'
            });

            if (refreshResponse.ok) {
                console.log('Token refreshed successfully');
                // Retry the original request
                return fetch(url, {
                    ...options,
                    credentials: 'include'
                });
            } else {
                console.log('Refresh failed, logging out');
                // Refresh failed - logout
                refreshInProgress = false;
                currentUser = null;
                showAuth();
                throw new Error('Session expired. Please login again.');
            }
        } catch (error) {
            refreshInProgress = false;
            currentUser = null;
            showAuth();
            throw error;
        } finally {
            refreshInProgress = false;
        }
    }

    return response;
}

// DOM Elements - will be initialized after DOM loads
let authContainer, appContainer, loginForm, registerForm, authMessage;
let usernameDisplay, logoutBtn, addApplicationBtn, kanbanBoard;
let applicationModal, applicationForm, modalTitle, closeModal, cancelBtn;
let logoutModal, confirmLogoutBtn, cancelLogoutBtn;
let deleteModal, confirmDeleteBtn, cancelDeleteBtn;
let viewModal, viewModalTitle, viewModalBody, closeViewBtn;
let currentDeleteApplicationId = null;

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    console.log('DOM loaded, initializing...');
    
    // Initialize DOM elements
    authContainer = document.getElementById('auth-container');
    appContainer = document.getElementById('app-container');
    loginForm = document.getElementById('login-form');
    registerForm = document.getElementById('register-form');
    authMessage = document.getElementById('auth-message');
    usernameDisplay = document.getElementById('username-display');
    logoutBtn = document.getElementById('logout-btn');
    addApplicationBtn = document.getElementById('add-application-btn');
    kanbanBoard = document.getElementById('kanban-board');
    applicationModal = document.getElementById('application-modal');
    applicationForm = document.getElementById('application-form');
    modalTitle = document.getElementById('modal-title');
    closeModal = document.querySelector('.close-modal');
    cancelBtn = document.getElementById('cancel-btn');
    logoutModal = document.getElementById('logout-modal');
    confirmLogoutBtn = document.getElementById('confirm-logout-btn');
    cancelLogoutBtn = document.getElementById('cancel-logout-btn');
    deleteModal = document.getElementById('delete-modal');
    confirmDeleteBtn = document.getElementById('confirm-delete-btn');
    cancelDeleteBtn = document.getElementById('cancel-delete-btn');
    viewModal = document.getElementById('view-modal');
    viewModalTitle = document.getElementById('view-modal-title');
    viewModalBody = document.getElementById('view-modal-body');
    closeViewBtn = document.getElementById('close-view-btn');
    
    console.log('Elements initialized:', {
        authContainer: !!authContainer,
        appContainer: !!appContainer,
        loginForm: !!loginForm,
        registerForm: !!registerForm
    });
    
    await checkAuth();
    setupEventListeners();
});

// Event Listeners
function setupEventListeners() {
    console.log('Setting up event listeners');
    
    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // Sort button
    const sortBtn = document.getElementById('sort-btn');
    if (sortBtn) {
        sortBtn.addEventListener('click', toggleSort);
    }

    // Auth forms
    console.log('Adding submit listeners to forms');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
        console.log('Login form listener added');
    } else {
        console.error('Login form not found!');
    }
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
        console.log('Register form listener added');
    } else {
        console.error('Register form not found!');
    }

    // Logout
    if (logoutBtn) {
        logoutBtn.addEventListener('click', showLogoutModal);
    }
    
    // Logout modal
    if (confirmLogoutBtn) {
        confirmLogoutBtn.addEventListener('click', handleLogout);
    }
    if (cancelLogoutBtn) {
        cancelLogoutBtn.addEventListener('click', closeLogoutModal);
    }
    // Close logout modal on clicking X
    const logoutCloseModal = logoutModal?.querySelector('.close-modal');
    if (logoutCloseModal) {
        logoutCloseModal.addEventListener('click', closeLogoutModal);
    }

    // Delete modal
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', handleConfirmDelete);
    }
    if (cancelDeleteBtn) {
        cancelDeleteBtn.addEventListener('click', closeDeleteModal);
    }
    const deleteCloseModal = deleteModal?.querySelector('.close-modal');
    if (deleteCloseModal) {
        deleteCloseModal.addEventListener('click', closeDeleteModal);
    }

    // Add application
    if (addApplicationBtn) {
        addApplicationBtn.addEventListener('click', () => openApplicationModal());
    }

    // Modal
    if (closeModal) {
        closeModal.addEventListener('click', closeApplicationModal);
    }
    if (cancelBtn) {
        cancelBtn.addEventListener('click', closeApplicationModal);
    }

    // Application form
    if (applicationForm) {
        applicationForm.addEventListener('submit', handleApplicationSubmit);
    }

    // Drag and drop
    setupDragAndDrop();

    // Горизонтальная прокрутка доски колёсиком мыши
    kanbanBoard.addEventListener('wheel', (e) => {
        // Если курсор внутри колонки (зона вертикального скролла) — не перехватываем
        if (e.target.closest('.cards-container')) {
            return;
        }
        // Иначе скроллим доску горизонтально
        e.preventDefault();
        kanbanBoard.scrollLeft += e.deltaY * 1.5;
    }, { passive: false });

    // Панорамирование доски через Пробел + перетаскивание мышью
    let spacePressed = false;
    let panStartX = 0;
    let panStartScrollLeft = 0;
    let isPanning = false;
    let panRafId = null;

    document.addEventListener('keydown', (e) => {
        if (e.code === 'Space') {
            // Если фокус в поле ввода — не перехватываем пробел
            const tag = e.target.tagName;
            if (tag === 'INPUT' || tag === 'TEXTAREA' || e.target.isContentEditable) {
                return;
            }
            spacePressed = true;
            e.preventDefault(); // не скроллить страницу вниз
            kanbanBoard.classList.add('pan-active');
        }
    });

    document.addEventListener('keyup', (e) => {
        if (e.code === 'Space') {
            spacePressed = false;
            if (isPanning) {
                isPanning = false;
                kanbanBoard.classList.remove('pan-grabbing');
                document.body.style.userSelect = '';
                if (panRafId) {
                    cancelAnimationFrame(panRafId);
                    panRafId = null;
                }
            }
            kanbanBoard.classList.remove('pan-active', 'pan-grabbing');
        }
    });

    kanbanBoard.addEventListener('mousedown', (e) => {
        if (!spacePressed) return;
        // Если клик внутри поля ввода — не панорамируем
        if (e.target.closest('input, textarea, [contenteditable]')) return;
        e.preventDefault(); // блокируем выделение текста
        isPanning = true;
        panStartX = e.clientX;
        panStartScrollLeft = kanbanBoard.scrollLeft;
        kanbanBoard.classList.add('pan-grabbing');
        document.body.style.userSelect = 'none'; // глобально запрещаем выделение
    });

    document.addEventListener('mousemove', (e) => {
        if (!isPanning) return;
        e.preventDefault();
        if (panRafId) {
            cancelAnimationFrame(panRafId);
        }
        const clientX = e.clientX;
        panRafId = requestAnimationFrame(() => {
            kanbanBoard.scrollLeft = panStartScrollLeft - (clientX - panStartX);
            panRafId = null;
        });
    });

    document.addEventListener('mouseup', () => {
        if (isPanning) {
            isPanning = false;
            kanbanBoard.classList.remove('pan-grabbing');
            document.body.style.userSelect = '';
            if (panRafId) {
                cancelAnimationFrame(panRafId);
                panRafId = null;
            }
        }
    });

    document.addEventListener('mouseleave', () => {
        if (isPanning) {
            isPanning = false;
            kanbanBoard.classList.remove('pan-grabbing');
            document.body.style.userSelect = '';
            if (panRafId) {
                cancelAnimationFrame(panRafId);
                panRafId = null;
            }
        }
    });

    // Делегирование кликов по карточкам
    kanbanBoard.addEventListener('click', (e) => {
        const viewBtn = e.target.closest('.card-btn.view');
        const editBtn = e.target.closest('.card-btn.edit');
        const deleteBtn = e.target.closest('.card-btn.delete');

        if (viewBtn) {
            const card = viewBtn.closest('.card');
            const app = applications.find(a => a.id === parseInt(card.dataset.applicationId));
            openViewModal(app);
        } else if (editBtn) {
            const card = editBtn.closest('.card');
            const app = applications.find(a => a.id === parseInt(card.dataset.applicationId));
            openApplicationModal(app);
        } else if (deleteBtn) {
            const card = deleteBtn.closest('.card');
            deleteApplication(parseInt(card.dataset.applicationId));
        }
    });

    // View modal
    if (closeViewBtn) {
        closeViewBtn.addEventListener('click', closeViewModal);
    }
    const viewCloseModal = viewModal?.querySelector('.close-modal');
    if (viewCloseModal) {
        viewCloseModal.addEventListener('click', closeViewModal);
    }

    // Close modal on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (!applicationModal.classList.contains('hidden')) {
                closeApplicationModal();
            } else if (!viewModal.classList.contains('hidden')) {
                closeViewModal();
            } else if (!logoutModal.classList.contains('hidden')) {
                closeLogoutModal();
            } else if (!deleteModal.classList.contains('hidden')) {
                closeDeleteModal();
            }
        }
    });

    // Filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const period = btn.dataset.period;
            setFilterPeriod(period);
        });
    });

    // Apply custom range
    const applyRangeBtn = document.getElementById('apply-range-btn');
    if (applyRangeBtn) {
        applyRangeBtn.addEventListener('click', applyCustomRange);
    }

    // Enter key on date inputs triggers custom range
    document.getElementById('date-from')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') applyCustomRange();
    });
    document.getElementById('date-to')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') applyCustomRange();
    });

    console.log('Event listeners setup complete');
}

// Authentication
async function checkAuth() {
    try {
        console.log('Checking authentication...');
        const response = await authenticatedFetch(`${API_BASE}/users/me`);
        console.log('Auth check response:', response.status);
        if (response.ok) {
            currentUser = await response.json();
            console.log('User authenticated:', currentUser);
            showApp();
        } else {
            console.log('Not authenticated');
            showAuth();
        }
    } catch (error) {
        console.error('Auth check error:', error);
        showAuth();
    }
}

async function handleLogin(e) {
    console.log('handleLogin called');
    e.preventDefault();
    const login = document.getElementById('login-login').value;
    const password = document.getElementById('login-password').value;
    console.log('Login attempt:', { login, password: '***' });

    try {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ login, password }),
            credentials: 'include'
        });

        console.log('Login response:', response.status);
        if (response.ok) {
            authMessage.textContent = '';
            authMessage.style.color = '';
            loginForm.reset();
            await checkAuth();
        } else {
            const data = await response.json();
            console.log('Login error:', data);
            authMessage.textContent = data.detail || 'Ошибка входа';
        }
    } catch (error) {
        console.error('Login fetch error:', error);
        authMessage.textContent = 'Ошибка подключения';
    }
}

async function handleRegister(e) {
    console.log('handleRegister called');
    e.preventDefault();
    const login = document.getElementById('register-login').value;
    const password = document.getElementById('register-password').value;
    console.log('Register attempt:', { login, password: '***' });

    try {
        const response = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ login, password }),
            credentials: 'include'
        });

        console.log('Register response:', response.status);
        if (response.ok) {
            authMessage.textContent = '';
            registerForm.reset();
            switchTab('login');
            authMessage.textContent = 'Регистрация успешна! Войдите в систему.';
            authMessage.style.color = '#27ae60';
        } else {
            const data = await response.json();
            console.log('Register error:', data);
            
            // Handle validation errors (422 status)
            if (response.status === 422 && data.detail) {
                let errorMessages = '';
                if (Array.isArray(data.detail)) {
                    // Extract all validation error messages, remove "Value error, " prefix and add "Ошибка: " prefix
                    errorMessages = 'Ошибка: ' + data.detail
                        .map(err => {
                            let msg = err.msg || '';
                            // Remove "Value error, " prefix if present
                            if (msg.startsWith('Value error, ')) {
                                msg = msg.slice(12);
                            }
                            return msg;
                        })
                        .join(' ');
                } else if (typeof data.detail === 'string') {
                    // Handle case where detail is a string
                    let msg = data.detail;
                    if (msg.startsWith('Value error, ')) {
                        msg = msg.slice(12);
                    }
                    errorMessages = 'Ошибка: ' + msg;
                } else {
                    errorMessages = data.detail || 'Ошибка регистрации';
                }
                authMessage.textContent = errorMessages;
            } else {
                authMessage.textContent = data.detail || 'Ошибка регистрации';
            }
            authMessage.style.color = '#e74c3c';
        }
    } catch (error) {
        console.error('Register fetch error:', error);
        authMessage.textContent = 'Ошибка подключения';
        authMessage.style.color = '#e74c3c';
    }
}

function showLogoutModal() {
    if (logoutModal) {
        logoutModal.classList.remove('hidden');
    }
}

function closeLogoutModal() {
    if (logoutModal) {
        logoutModal.classList.add('hidden');
    }
}

async function handleLogout() {
    closeLogoutModal();
    try {
        await fetch(`${API_BASE}/auth/logout`, {
            method: 'POST',
            credentials: 'include'
        });
        currentUser = null;
        showAuth();
    } catch (error) {
        console.error('Logout error:', error);
    }
}

// UI Helpers
function showAuth() {
    console.log('Showing auth screen');
    authContainer.classList.remove('hidden');
    appContainer.classList.add('hidden');
}

function updateSortButton() {
    const sortBtn = document.getElementById('sort-btn');
    if (sortBtn) {
        sortBtn.dataset.ascending = sortAscending;
        sortBtn.textContent = sortAscending ? '⬇ Сначала старые' : '⬆ Сначала новые';
    }
}

function showApp() {
    console.log('Showing app screen');
    authContainer.classList.add('hidden');
    appContainer.classList.remove('hidden');
    usernameDisplay.textContent = currentUser.login;
    updateSortButton();
    loadApplications();
}

function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `${tab}-form`);
    });
    authMessage.textContent = '';
    authMessage.style.color = '#e74c3c';
}

// Filter helpers
function setFilterPeriod(period) {
    filterPeriod = period;
    customDateFrom = '';
    customDateTo = '';

    // Update active button style
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.period === period);
    });

    // Clear custom range inputs and remove highlight
    document.querySelector('.custom-range')?.classList.remove('active');
    document.getElementById('date-from').value = '';
    document.getElementById('date-to').value = '';

    loadApplications();
}

function applyCustomRange() {
    const dateFrom = document.getElementById('date-from').value;
    const dateTo = document.getElementById('date-to').value;

    if (!dateFrom && !dateTo) return;

    if (!isValidDateString(dateFrom) || !isValidDateString(dateTo)) {
        alert('Дата должна содержать четырёхзначный год (от 2000 до 2100)');
        return;
    }

    customDateFrom = dateFrom;
    customDateTo = dateTo;
    filterPeriod = ''; // сбрасываем предустановленный период

    // Deselect all preset buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // Highlight custom range block
    document.querySelector('.custom-range')?.classList.add('active');

    loadApplications();
}

function isValidDateString(dateStr) {
    if (!dateStr) return true;
    const match = dateStr.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!match) return false;
    const year = parseInt(match[1], 10);
    return year >= 2000 && year <= 2100;
}

function buildFilterQuery() {
    let query = `reverse=${sortAscending}`;

    if (filterPeriod) {
        query += `&period=${filterPeriod}`;
    } else if (customDateFrom || customDateTo) {
        if (customDateFrom) query += `&date_from=${customDateFrom}`;
        if (customDateTo) query += `&date_to=${customDateTo}`;
    }

    return query;
}

// Applications
async function loadApplications() {
    try {
        console.log('Loading applications...');
        const filterQuery = buildFilterQuery();
        const response = await authenticatedFetch(`${API_BASE}/applications?${filterQuery}`);
        if (!response.ok) {
            let detail = 'Ошибка загрузки заявок';
            try {
                const errData = await response.json();
                if (errData.detail) detail = errData.detail;
            } catch (_) {
                // ignore if body is not JSON
            }
            throw new Error(detail);
        }
        applications = await response.json();
        console.log('Applications loaded:', applications.length);
        renderKanbanBoard();
    } catch (error) {
        console.error('Error loading applications:', error);
        alert(error.message || 'Ошибка загрузки заявок');
    }
}

function toggleSort() {
    sortAscending = !sortAscending;
    sessionStorage.setItem('sortAscending', sortAscending);
    updateSortButton();
    loadApplications();
}

async function handleApplicationSubmit(e) {
    e.preventDefault();

    const applicationData = {
        company_name: document.getElementById('company-name').value,
        vacancy_name: document.getElementById('vacancy-name').value,
        vacancy_url: document.getElementById('vacancy-url').value || null,
        contacts: document.getElementById('contacts').value || null,
        comments: document.getElementById('comments').value || null
    };

    // Only include status when editing
    if (editingApplicationId) {
        applicationData.status = document.getElementById('status').value;
    }

    try {
        let response;
        if (editingApplicationId) {
            response = await authenticatedFetch(`${API_BASE}/applications/${editingApplicationId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(applicationData)
            });
        } else {
            response = await authenticatedFetch(`${API_BASE}/applications`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(applicationData)
            });
        }

        if (response.ok) {
            closeApplicationModal();
            await loadApplications();
        } else {
            const data = await response.json();
            alert(data.detail || 'Ошибка сохранения заявки');
        }
    } catch (error) {
        alert('Ошибка подключения');
    }
}

function showDeleteModal(applicationId) {
    currentDeleteApplicationId = applicationId;
    if (deleteModal) {
        deleteModal.classList.remove('hidden');
    }
}

function closeDeleteModal(resetId = true) {
    if (deleteModal) {
        deleteModal.classList.add('hidden');
    }
    if (resetId) {
        currentDeleteApplicationId = null;
    }
}

async function handleConfirmDelete() {
    if (!currentDeleteApplicationId) return;
    
    const applicationId = currentDeleteApplicationId;
    closeDeleteModal(false); // Close modal without resetting ID
    
    try {
        const response = await authenticatedFetch(`${API_BASE}/applications/${applicationId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            await loadApplications();
        } else {
            const data = await response.json();
            const errorMessage = typeof data.detail === 'string'
                ? data.detail
                : (data.detail?.message || data.detail || 'Ошибка удаления заявки');
            alert(errorMessage);
        }
    } catch (error) {
        alert('Ошибка подключения');
    }
    
    currentDeleteApplicationId = null;
}

// Update deleteApplication to use custom modal
async function deleteApplication(applicationId) {
    showDeleteModal(applicationId);
}

async function updateApplicationStatus(applicationId, newStatus) {
    // Оставляем только fetch. Возвращаем response, чтобы drop-обработчик мог обработать ошибку.
    return await authenticatedFetch(`${API_BASE}/applications/${applicationId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
    });
}

// Kanban Board
function renderKanbanBoard() {
    const statuses = Object.keys(STATUS_LABELS);

    // Clear board
    kanbanBoard.innerHTML = '';

    // Create columns for each status
    statuses.forEach(status => {
        const column = document.createElement('div');
        column.className = 'column';
        column.dataset.status = status;

        const columnApps = applications.filter(app => app.status === status);

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

        kanbanBoard.appendChild(column);
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

// Modal
function openApplicationModal(application = null) {
    editingApplicationId = application ? application.id : null;
    const statusFormGroup = document.getElementById('status').closest('.form-group');

    if (application) {
        modalTitle.textContent = 'Редактировать заявку';
        document.getElementById('company-name').value = application.company_name;
        document.getElementById('vacancy-name').value = application.vacancy_name || '';
        document.getElementById('vacancy-url').value = application.vacancy_url || '';
        document.getElementById('contacts').value = application.contacts || '';
        document.getElementById('comments').value = application.comments || '';
        document.getElementById('status').value = application.status;
        statusFormGroup.classList.remove('hidden');
    } else {
        modalTitle.textContent = 'Новая заявка';
        applicationForm.reset();
        statusFormGroup.classList.add('hidden');
    }

    applicationModal.classList.remove('hidden');
}

function closeApplicationModal() {
    applicationModal.classList.add('hidden');
    editingApplicationId = null;
    applicationForm.reset();
}

// View Modal (read-only)
function openViewModal(application) {
    if (!application) return;

    viewModalTitle.textContent = escapeHtml(application.company_name) +
        (application.vacancy_name ? ` — ${escapeHtml(application.vacancy_name)}` : '');

    const statusLabel = STATUS_LABELS[application.status] || application.status;

    const daysWarning = application.days_since_creation > 7
        ? `<span style="color: #e74c3c;">${application.days_since_creation} дн.</span>`
        : `${application.days_since_creation} дн.`;

    viewModalBody.innerHTML = `
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
            const detail = typeof data.detail === 'string'
                ? data.detail
                : (data.detail?.message || 'Ошибка удаления');
            errorEl.textContent = detail;
            errorEl.style.display = 'block';
        }
    } catch (err) {
        errorEl.textContent = 'Ошибка подключения';
        errorEl.style.display = 'block';
    }
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

function closeViewModal() {
    viewModal.classList.add('hidden');
}

// Drag and Drop
function setupDragAndDrop() {
    let draggedCard = null;
    let sourceContainer = null;
    let touchGhost = null;
    let touchOffsetX = 0;
    let touchOffsetY = 0;
    let isTouchDragging = false;
    let longPressTimer = null;
    let touchStartTime = 0;
    let touchStartX = 0;
    let touchStartY = 0;
    const LONG_PRESS_DELAY = 400; // ms
    const MOVE_THRESHOLD = 10; // px

    // ========== MOUSE / HTML5 DnD ==========
    document.addEventListener('dragstart', (e) => {
        if (!e.target.classList.contains('card')) return;

        draggedCard = e.target;
        sourceContainer = e.target.parentElement;
        e.target.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
    });

    document.addEventListener('dragend', (e) => {
        if (draggedCard) {
            draggedCard.classList.remove('dragging');
            draggedCard = null;
        }
        if (sourceContainer) {
            sourceContainer.classList.remove('drag-over');
            sourceContainer = null;
        }
    });

    document.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        const container = e.target.closest('.cards-container');
        if (container && container !== sourceContainer && !container.classList.contains('drag-over')) {
            container.classList.add('drag-over');
        }
    });

    document.addEventListener('dragleave', (e) => {
        const container = e.target.closest('.cards-container');
        if (container) {
            container.classList.remove('drag-over');
        }
    });

    document.addEventListener('drop', async (e) => {
        e.preventDefault();
        const container = e.target.closest('.cards-container');
        if (!container || !draggedCard) return;

        container.classList.remove('drag-over');
        await handleDrop(container, draggedCard);
    });

    // ========== TOUCH ==========
    document.addEventListener('touchstart', (e) => {
        const card = e.target.closest('.card');
        if (!card) return;

        const touch = e.touches[0];
        touchStartX = touch.clientX;
        touchStartY = touch.clientY;
        touchStartTime = Date.now();

        // Запускаем таймер долгого нажатия
        longPressTimer = setTimeout(() => {
            isTouchDragging = true;
            draggedCard = card;
            sourceContainer = card.parentElement;
            card.classList.add('dragging');
            createTouchGhost(card, touch);
            // Виброотклик если доступен
            if (navigator.vibrate) navigator.vibrate(50);
        }, LONG_PRESS_DELAY);
    }, { passive: false });

    document.addEventListener('touchmove', (e) => {
        if (!isTouchDragging) {
            // Если двигаем палец до срабатывания long press — отменяем
            const touch = e.touches[0];
            const dx = Math.abs(touch.clientX - touchStartX);
            const dy = Math.abs(touch.clientY - touchStartY);
            if (dx > MOVE_THRESHOLD || dy > MOVE_THRESHOLD) {
                clearTimeout(longPressTimer);
                longPressTimer = null;
            }
            return;
        }

        e.preventDefault(); // Предотвращаем скролл страницы
        const touch = e.touches[0];
        updateTouchGhostPosition(touch);

        // Подсвечиваем колонку под пальцем
        const elementBelow = document.elementFromPoint(touch.clientX, touch.clientY);
        if (elementBelow) {
            document.querySelectorAll('.cards-container').forEach(c => c.classList.remove('drag-over'));
            const container = elementBelow.closest('.cards-container');
            if (container && container !== sourceContainer) {
                container.classList.add('drag-over');
            }
        }
    }, { passive: false });

    document.addEventListener('touchend', async (e) => {
        clearTimeout(longPressTimer);
        longPressTimer = null;

        if (!isTouchDragging) return;

        const touch = e.changedTouches[0];
        const elementBelow = document.elementFromPoint(touch.clientX, touch.clientY);

        removeTouchGhost();

        if (draggedCard) {
            draggedCard.classList.remove('dragging');
        }
        document.querySelectorAll('.cards-container').forEach(c => c.classList.remove('drag-over'));

        if (elementBelow) {
            const container = elementBelow.closest('.cards-container');
            if (container && draggedCard) {
                await handleDrop(container, draggedCard);
            }
        }

        draggedCard = null;
        sourceContainer = null;
        isTouchDragging = false;
    });

    document.addEventListener('touchcancel', () => {
        clearTimeout(longPressTimer);
        longPressTimer = null;
        removeTouchGhost();
        if (draggedCard) {
            draggedCard.classList.remove('dragging');
        }
        document.querySelectorAll('.cards-container').forEach(c => c.classList.remove('drag-over'));
        draggedCard = null;
        sourceContainer = null;
        isTouchDragging = false;
    });

    // ========== HELPERS ==========
    function createTouchGhost(card, touch) {
        touchGhost = card.cloneNode(true);
        touchGhost.classList.add('touch-ghost');
        touchGhost.style.width = card.offsetWidth + 'px';
        touchGhost.style.height = card.offsetHeight + 'px';

        const rect = card.getBoundingClientRect();
        touchOffsetX = touch.clientX - rect.left;
        touchOffsetY = touch.clientY - rect.top;

        updateTouchGhostPosition(touch);
        document.body.appendChild(touchGhost);
    }

    function updateTouchGhostPosition(touch) {
        if (!touchGhost) return;
        touchGhost.style.left = (touch.clientX - touchOffsetX) + 'px';
        touchGhost.style.top = (touch.clientY - touchOffsetY) + 'px';
    }

    function removeTouchGhost() {
        if (touchGhost) {
            touchGhost.remove();
            touchGhost = null;
        }
    }

    async function handleDrop(container, card) {
        const column = container.closest('.column');
        const newStatus = column.dataset.status;
        const applicationId = parseInt(card.dataset.applicationId);

        const app = applications.find(a => a.id === applicationId);
        if (!app || app.status === newStatus) return;

        const oldContainer = card.parentElement;
        const oldStatus = app.status;

        // 1. Мгновенно перемещаем карточку в новый столбец
        container.appendChild(card);

        // 2. Обновляем локальное состояние и счётчики колонок
        app.status = newStatus;
        updateColumnCounts();

        // 3. Отправляем запрос на сервер в фоне
        try {
            const response = await authenticatedFetch(`${API_BASE}/applications/${applicationId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: newStatus })
            });

            if (!response.ok) throw new Error('Server error');
        } catch (error) {
            // Откат при ошибке сети или сервера
            oldContainer.appendChild(card);
            app.status = oldStatus;
            updateColumnCounts();
            alert('Не удалось обновить статус заявки');
        }
    }
}

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

function updateColumnCounts() {
    document.querySelectorAll('.column').forEach(col => {
        const status = col.dataset.status;
        const count = applications.filter(app => app.status === status).length;
        col.querySelector('.column-count').textContent = count;
    });
}
// Expose for testing
window.CareerTracker = {
    loadApplications,
    deleteApplication,
    updateApplicationStatus
};
