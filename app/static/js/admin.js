// Admin panel for user management

// State
let allUsers = [];
let currentSortBy = 'created_at';
let currentOrder = 'desc';
let deleteUserId = null;
let currentUser = null;

// DOM references
const usersTbody = document.getElementById('users-tbody');
const userCount = document.getElementById('user-count');
const emptyState = document.getElementById('empty-state');
const searchInput = document.getElementById('search-input');
const searchClearBtn = document.getElementById('search-clear-btn');
const sortableHeaders = document.querySelectorAll('th.sortable');
const deleteModal = document.getElementById('delete-modal');
const deleteUserName = document.getElementById('delete-user-name');
const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
const cancelDeleteBtn = document.getElementById('cancel-delete-btn');
const adminActionsCol = document.getElementById('admin-actions-col');

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
        if (!user.is_admin && !user.is_superadmin) {
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

    // Сортировка по клику на заголовки таблицы
    sortableHeaders.forEach(th => {
        th.addEventListener('click', () => handleSort(th.dataset.sortField));
    });

    // Удаление — делегирование события через tbody
    usersTbody.addEventListener('click', (e) => {
        const btn = e.target.closest('.btn-delete-user');
        if (!btn) {
            // Toggle admin status
            const toggleBtn = e.target.closest('.btn-toggle-admin');
            if (toggleBtn) {
                handleToggleAdmin(parseInt(toggleBtn.dataset.userId), toggleBtn.dataset.currentAdmin === 'true');
            }
            return;
        }
        openDeleteModal(parseInt(btn.dataset.userId), btn.dataset.userLogin);
    });

    confirmDeleteBtn.addEventListener('click', confirmDelete);
    cancelDeleteBtn.addEventListener('click', closeDeleteModal);
    document.querySelectorAll('.close-modal').forEach(btn => {
        btn.addEventListener('click', closeDeleteModal);
    });

    // Close on Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeDeleteModal();
        }
    });

    // Show admin actions column only for superadmin
    if (currentUser.is_superadmin) {
        adminActionsCol.classList.remove('hidden');
    }

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

    const isSuper = currentUser && currentUser.is_superadmin;

    for (const user of filtered) {
        const tr = document.createElement('tr');
        const isAdmin = user.is_admin ? 'Да' : 'Нет';
        const isSelf = currentUser && currentUser.id === user.id;

        let actionsHtml = '';
        if (isSuper && !isSelf) {
            const adminLabel = user.is_admin ? 'Снять админа' : 'Назначить админом';
            const toggleClass = user.is_admin ? 'btn-toggle-admin--remove' : 'btn-toggle-admin--add';
            actionsHtml = `
                <button class="btn-toggle-admin ${toggleClass}" data-user-id="${escapeHtml(user.id)}" data-current-admin="${user.is_admin}">${adminLabel}</button>
            `;
        }

        tr.innerHTML = `
            <td data-label="ID">${escapeHtml(user.id)}</td>
            <td data-label="Логин">${escapeHtml(user.login)}</td>
            <td data-label="Дата создания">${formatDateTime(user.created_at)}</td>
            <td data-label="Админ"><span class="admin-badge ${user.is_admin ? 'admin-badge--yes' : 'admin-badge--no'}">${isAdmin}</span></td>
            <td data-label="Действия">
                <button class="btn-delete-user" data-user-id="${escapeHtml(user.id)}" data-user-login="${escapeHtml(user.login)}">Удалить</button>
            </td>
            <td data-label="Управление">${actionsHtml}</td>
        `;
        usersTbody.appendChild(tr);
    }
}

async function handleToggleAdmin(userId, isCurrentlyAdmin) {
    try {
        const response = await authenticatedFetch(`${API_BASE}/users/${userId}/admin`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_admin: !isCurrentlyAdmin }),
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || 'Ошибка изменения статуса администратора');
        }
        showToast('Статус администратора обновлён', 'success');
        await loadUsers();
    } catch (error) {
        showToast('Ошибка: ' + error.message, 'error');
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
    // Toggle order if same field, else default to asc for login, desc for date and is_admin
    if (currentSortBy === field) {
        currentOrder = currentOrder === 'asc' ? 'desc' : 'asc';
    } else {
        currentSortBy = field;
        if (field === 'login') {
            currentOrder = 'asc';
        } else {
            currentOrder = 'desc';
        }
    }

    updateSortIndicators();
    loadUsers();
}

function updateSortIndicators() {
    sortableHeaders.forEach(th => {
        const field = th.dataset.sortField;
        if (currentSortBy === field) {
            th.innerHTML = field === 'login' ? 'Логин' : field === 'is_admin' ? 'Админ' : 'Дата создания';
            th.innerHTML += currentOrder === 'asc' ? ' ▴' : ' ▾';
            th.classList.add('active-sort');
        } else {
            th.innerHTML = field === 'login' ? 'Логин' : field === 'is_admin' ? 'Админ' : 'Дата создания';
            th.classList.remove('active-sort');
        }
    });
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
        console.log('Deleting user ID:', deleteUserId);
        const response = await authenticatedFetch(`${API_BASE}/users/${deleteUserId}`, {
            method: 'DELETE',
        });
        console.log('Delete response status:', response.status);

        // 409 — нельзя удалить последнего админа, показываем сообщение без редиректа
        if (response.status === 409) {
            const err = await response.json().catch(() => ({}));
            showToast(err.detail || 'Нельзя удалить последнего администратора', 'error');
            closeDeleteModal();
            return;
        }

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            console.error('Delete error response:', err);
            throw new Error(err.detail || 'Ошибка удаления пользователя');
        }
        showToast('Пользователь удалён', 'success');
        closeDeleteModal();
        await loadUsers();
    } catch (error) {
        console.error('Error in confirmDelete:', error);
        showToast('Ошибка: ' + error.message, 'error');
        closeDeleteModal();
        window.location.href = '/';
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