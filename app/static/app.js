// API base URL
const API_BASE = '/api';

// Application statuses mapping
const STATUS_LABELS = {
    created: 'Создана',
    hr_interview: 'HR собеседование',
    tech_interview: 'Техническое собеседование',
    director_interview: 'Собеседование с директором',
    offer: 'Оффер',
    rejected: 'Отказ',
    archived: 'Архив'
};

// State
let currentUser = null;
let applications = [];
let editingApplicationId = null;

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
        logoutBtn.addEventListener('click', handleLogout);
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
            authMessage.textContent = data.detail || 'Ошибка регистрации';
            authMessage.style.color = '#e74c3c';
        }
    } catch (error) {
        console.error('Register fetch error:', error);
        authMessage.textContent = 'Ошибка подключения';
        authMessage.style.color = '#e74c3c';
    }
}

async function handleLogout() {
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
        const response = await authenticatedFetch(`${API_BASE}/applications`);
        if (!response.ok) throw new Error('Failed to load applications');
        applications = await response.json();
        console.log('Applications loaded:', applications.length);
        renderKanbanBoard();
    } catch (error) {
        console.error('Error loading applications:', error);
        alert('Ошибка загрузки заявок');
    }
}

async function handleApplicationSubmit(e) {
    e.preventDefault();

    const applicationData = {
        company_name: document.getElementById('company-name').value,
        vacancy_url: document.getElementById('vacancy-url').value || null,
        contacts: document.getElementById('contacts').value || null,
        comments: document.getElementById('comments').value || null,
        status: document.getElementById('status').value
    };

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

async function deleteApplication(applicationId) {
    if (!confirm('Удалить заявку?')) return;

    try {
        const response = await authenticatedFetch(`${API_BASE}/applications/${applicationId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            await loadApplications();
        } else {
            alert('Ошибка удаления заявки');
        }
    } catch (error) {
        alert('Ошибка подключения');
    }
}

async function updateApplicationStatus(applicationId, newStatus) {
    try {
        const response = await authenticatedFetch(`${API_BASE}/applications/${applicationId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus })
        });

        if (response.ok) {
            await loadApplications();
        } else {
            alert('Ошибка обновления статуса');
            await loadApplications(); // Reload to restore original state
        }
    } catch (error) {
        alert('Ошибка подключения');
        await loadApplications();
    }
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
    card.querySelector('.edit').addEventListener('click', () => {
        openApplicationModal(app);
    });

    card.querySelector('.delete').addEventListener('click', () => {
        deleteApplication(app.id);
    });

    return card;
}

// Modal
function openApplicationModal(application = null) {
    editingApplicationId = application ? application.id : null;

    if (application) {
        modalTitle.textContent = 'Редактировать заявку';
        document.getElementById('company-name').value = application.company_name;
        document.getElementById('vacancy-url').value = application.vacancy_url || '';
        document.getElementById('contacts').value = application.contacts || '';
        document.getElementById('comments').value = application.comments || '';
        document.getElementById('status').value = application.status;
    } else {
        modalTitle.textContent = 'Новая заявка';
        applicationForm.reset();
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
        const container = e.target.closest('.cards-container');
        if (!container || container === sourceContainer) return;

        container.classList.add('drag-over');
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

        const column = container.closest('.column');
        const newStatus = column.dataset.status;
        const applicationId = parseInt(draggedCard.dataset.applicationId);

        // Find the current application to check if status changed
        const app = applications.find(a => a.id === applicationId);
        if (app && app.status !== newStatus) {
            await updateApplicationStatus(applicationId, newStatus);
        }
    });
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

// Expose for testing
window.CareerTracker = {
    loadApplications,
    deleteApplication,
    updateApplicationStatus
};
