// Admin panel for user management

// State
let allUsers = [];
let currentSortBy = 'created_at';
let currentOrder = 'desc';
let deleteUserId = null;

// DOM references
const usersTbody = document.getElementById('users-tbody');
const userCount = document.getElementById('user-count');
const emptyState = document.getElementById('empty-state');
const searchInput = document.getElementById('search-input');
const searchClearBtn = document.getElementById('search-clear-btn');
const sortLoginBtn = document.getElementById('sort-login-btn');
const sortDateBtn = document.getElementById('sort-date-btn');
const deleteModal = document.getElementById('delete-modal');
const deleteUserName = document.getElementById('delete-user-name');
const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
const cancelDeleteBtn = document.getElementById('cancel-delete-btn');

// Initialize admin page
async function initAdmin() {
    // Получаем данные текущего пользователя через API
    try {
        const response = await authenticatedFetch(`${API_BASE}/users/me`);
        if (!response.ok) {
            window.location.href = '/';
            return;
        }
        const user = await response.json();
        if (!user.is_admin) {
            window.location.href = '/';
            return;
        }
        currentUser = user;
    } catch {
        window.location.href = '/';
        return;
    }

    document.getElementById('username-display').textContent = currentUser.login;

    // Setup event listeners
    document.getElementById('logout-btn').addEventListener('click', handleLogout);

    searchInput.addEventListener('input', handleSearch);
    searchClearBtn.addEventListener('click', clearSearch);

    sortLoginBtn.addEventListener('click', () => handleSort('login'));
    sortDateBtn.addEventListener('click', () => handleSort('created_at'));

    confirmDeleteBtn.addEventListener('click', confirmDelete);
    cancelDeleteBtn.addEventListener('click', closeDeleteModal);
    document.querySelectorAll('.close-modal').forEach(btn => {
        btn.addEventListener('click', closeDeleteModal);
    });
    deleteModal.addEventListener('click', (e) => {
        if (e.target === deleteModal) closeDeleteModal();
    });

    // Load users
    await loadUsers();
}

async function loadUsers() {
    try {
        const url = `${API_BASE}/users?sort_by=${currentSortBy}&order=${currentOrder}`;
        const response = await authenticatedFetch(url);
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || 'Ошибка загрузки пользователей');
        }
        allUsers = await response.json();
        renderUsers();
    } catch (error) {
        showToast('Ошибка загрузки пользователей: ' + error.message, 'error');
    }
}

function renderUsers() {
    const search = searchInput.value.trim().toLowerCase();

    // Filter by login on client side
    let filtered = allUsers;
    if (search) {
        filtered = allUsers.filter(user => user.login.toLowerCase().includes(search));
    }

    const hasUsers = filtered.length > 0;

    userCount.textContent = filtered.length;
    emptyState.classList.toggle('hidden', hasUsers);
    usersTbody.innerHTML = '';

    if (!hasUsers) return;

    for (const user of filtered) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td data-label="ID">${escapeHtml(user.id)}</td>
            <td data-label="Логин">${escapeHtml(user.login)}</td>
            <td data-label="Дата создания">${formatDateTime(user.created_at)}</td>
            <td data-label="Действия">
                <button class="btn-delete-user" data-user-id="${escapeHtml(user.id)}" data-user-login="${escapeHtml(user.login)}">Удалить</button>
            </td>
        `;
        tr.querySelector('.btn-delete-user').addEventListener('click', (e) => {
            const btn = e.currentTarget;
            openDeleteModal(parseInt(btn.dataset.userId), btn.dataset.userLogin);
        });
        usersTbody.appendChild(tr);
    }
}

function handleSearch() {
    searchClearBtn.classList.toggle('hidden', !searchInput.value);
    renderUsers();
}

function clearSearch() {
    searchInput.value = '';
    searchClearBtn.classList.add('hidden');
    renderUsers();
    searchInput.focus();
}

function handleSort(field) {
    // Toggle order if same field, else default to asc for login, desc for date
    if (currentSortBy === field) {
        currentOrder = currentOrder === 'asc' ? 'desc' : 'asc';
    } else {
        currentSortBy = field;
        currentOrder = field === 'login' ? 'asc' : 'desc';
    }

    updateSortButtons();
    loadUsers();
}

function updateSortButtons() {
    sortLoginBtn.innerHTML = currentSortBy === 'login'
        ? `Логин ${currentOrder === 'asc' ? '▴' : '▾'}`
        : 'Логин ▾';
    sortDateBtn.innerHTML = currentSortBy === 'created_at'
        ? `Дата ${currentOrder === 'asc' ? '▴' : '▾'}`
        : 'Дата ▾';

    sortLoginBtn.classList.toggle('active-sort', currentSortBy === 'login');
    sortDateBtn.classList.toggle('active-sort', currentSortBy === 'created_at');
}

// Delete modal
function openDeleteModal(userId, userLogin) {
    deleteUserId = userId;
    deleteUserName.textContent = userLogin;
    deleteModal.classList.remove('hidden');
}

function closeDeleteModal() {
    deleteUserId = null;
    deleteModal.classList.add('hidden');
}

async function confirmDelete() {
    if (deleteUserId === null) return;

    // Disable button to prevent double-click
    confirmDeleteBtn.disabled = true;
    confirmDeleteBtn.textContent = 'Удаление...';

    try {
        const response = await authenticatedFetch(`${API_BASE}/users/${deleteUserId}`, {
            method: 'DELETE',
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || 'Ошибка удаления пользователя');
        }
        showToast('Пользователь удалён', 'success');
        closeDeleteModal();
        await loadUsers();
    } catch (error) {
        showToast('Ошибка: ' + error.message, 'error');
    } finally {
        confirmDeleteBtn.disabled = false;
        confirmDeleteBtn.textContent = 'Удалить';
    }
}

// Logout
async function handleLogout() {
    try {
        const response = await fetch(`${API_BASE}/auth/logout`, {
            method: 'POST',
            credentials: 'include',
        });
        if (response.ok) {
            currentUser = null;
            window.location.href = '/';
        }
    } catch (error) {
        showToast('Ошибка при выходе', 'error');
    }
}

// Toast notification (inline, reuses same pattern as main app)
function showToast(message, type = 'success') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Start admin page when DOM ready
document.addEventListener('DOMContentLoaded', initAdmin);