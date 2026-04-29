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
let sortAscending = false; // false = сначала новые (desc), true = сначала старые (asc)

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
    // Close logout modal on clicking X or outside modal
    const logoutCloseModal = logoutModal?.querySelector('.close-modal');
    if (logoutCloseModal) {
        logoutCloseModal.addEventListener('click', closeLogoutModal);
    }
    if (logoutModal) {
        logoutModal.addEventListener('click', (e) => {
            if (e.target === logoutModal) closeLogoutModal();
        });
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
    if (deleteModal) {
        deleteModal.addEventListener('click', (e) => {
            if (e.target === deleteModal) closeDeleteModal();
        });
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
    if (applicationModal) {
        applicationModal.addEventListener('click', (e) => {
            if (e.target === applicationModal) closeApplicationModal();
        });
    }

    // Application form
    if (applicationForm) {
        applicationForm.addEventListener('submit', handleApplicationSubmit);
    }

    // Drag and drop
    setupDragAndDrop();

    // Делегирование кликов по карточкам
    kanbanBoard.addEventListener('click', (e) => {
        const editBtn = e.target.closest('.card-btn.edit');
        const deleteBtn = e.target.closest('.card-btn.delete');

        if (editBtn) {
            const card = editBtn.closest('.card');
            const app = applications.find(a => a.id === parseInt(card.dataset.applicationId));
            openApplicationModal(app);
        } else if (deleteBtn) {
            const card = deleteBtn.closest('.card');
            deleteApplication(parseInt(card.dataset.applicationId));
        }
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

function showApp() {
    console.log('Showing app screen');
    authContainer.classList.add('hidden');
    appContainer.classList.remove('hidden');
    usernameDisplay.textContent = currentUser.login;
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

// Applications
async function loadApplications() {
    try {
        console.log('Loading applications...');
        const response = await authenticatedFetch(`${API_BASE}/applications?reverse=${sortAscending}`);
        if (!response.ok) throw new Error('Failed to load applications');
        applications = await response.json();
        console.log('Applications loaded:', applications.length);
        renderKanbanBoard();
    } catch (error) {
        console.error('Error loading applications:', error);
        alert('Ошибка загрузки заявок');
    }
}

function toggleSort() {
    sortAscending = !sortAscending;
    const sortBtn = document.getElementById('sort-btn');
    if (sortBtn) {
        sortBtn.dataset.ascending = sortAscending;
        sortBtn.textContent = sortAscending ? '⬇ Сначала старые' : '⬆ Сначала новые';
    }
    loadApplications();
}

async function handleApplicationSubmit(e) {
    e.preventDefault();

    const applicationData = {
        company_name: document.getElementById('company-name').value,
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
                <button class="card-btn edit" title="Редактировать">✏️</button>
                <button class="card-btn delete" title="Удалить">🗑️</button>
            </div>
        </div>
        <div class="card-body">
            ${app.vacancy_url ? `<div class="card-field"><strong>Вакансия:</strong> <a href="${escapeHtml(app.vacancy_url)}" target="_blank">ссылка</a></div>` : ''}
            ${app.contacts ? `<div class="card-field"><strong>Контакты:</strong> ${escapeHtml(app.contacts)}</div>` : ''}
            ${commentsHtml}
        </div>
        <div class="card-footer">
            <span class="card-days" ${daysClass}>${app.days_since_creation} дн.</span>
            <span>${formatDate(app.created_at)}</span>
        </div>
    `;

    // Event listeners


    return card;
}

// Modal
function openApplicationModal(application = null) {
    editingApplicationId = application ? application.id : null;
    const statusFormGroup = document.getElementById('status').closest('.form-group');

    if (application) {
        modalTitle.textContent = 'Редактировать заявку';
        document.getElementById('company-name').value = application.company_name;
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
    const date = new Date(dateString);
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
