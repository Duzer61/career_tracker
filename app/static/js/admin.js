// Admin panel for user management

// State
let currentSortBy = 'created_at';
let currentOrder = 'desc';
let currentPage = 1;
let currentPageSize = null; // будет получен из ответа API
let totalPages = 1;
let totalUsers = 0;
let deleteUserId = null;
let toggleAdminUserId = null;
let toggleAdminIsCurrentlyAdmin = null;
let searchTimeout = null;

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
const toggleAdminModal = document.getElementById('toggle-admin-modal');
const toggleAdminModalTitle = document.getElementById('toggle-admin-modal-title');
const toggleAdminModalText = document.getElementById('toggle-admin-modal-text');
const confirmToggleAdminBtn = document.getElementById('confirm-toggle-admin-btn');
const cancelToggleAdminBtn = document.getElementById('cancel-toggle-admin-btn');
const paginationContainer = document.getElementById('pagination');
const paginationPrev = document.getElementById('pagination-prev');
const paginationNext = document.getElementById('pagination-next');
const paginationInfo = document.getElementById('pagination-info');

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
    document.getElementById('logout-btn').addEventListener('click', showLogoutModal);
    document.getElementById('cancel-logout-btn').addEventListener('click', closeLogoutModal);
    document.getElementById('confirm-logout-btn').addEventListener('click', handleLogoutWithRedirect);

    searchInput.addEventListener('input', handleSearch);
    searchClearBtn.addEventListener('click', clearSearch);

    // Сортировка по клику на заголовки таблицы
    sortableHeaders.forEach(th => {
        th.addEventListener('click', () => handleSort(th.dataset.sortField));
    });

    // Пагинация
    paginationPrev.addEventListener('click', prevPage);
    paginationNext.addEventListener('click', nextPage);

    // Удаление — делегирование события через tbody
    usersTbody.addEventListener('click', (e) => {
        const btn = e.target.closest('.btn-delete-user');
        if (!btn) {
            // Toggle admin status
            const toggleBtn = e.target.closest('.btn-toggle-admin');
            if (toggleBtn) {
                openToggleAdminModal(
                    parseInt(toggleBtn.dataset.userId),
                    toggleBtn.dataset.currentAdmin === 'true',
                    toggleBtn.dataset.userLogin
                );
            }
            return;
        }
        openDeleteModal(parseInt(btn.dataset.userId), btn.dataset.userLogin);
    });

    confirmDeleteBtn.addEventListener('click', confirmDelete);
    cancelDeleteBtn.addEventListener('click', closeDeleteModal);
    document.querySelectorAll('.close-modal').forEach(btn => {
        btn.addEventListener('click', closeModal);
    });

    // Toggle admin modal
    confirmToggleAdminBtn.addEventListener('click', confirmToggleAdmin);
    cancelToggleAdminBtn.addEventListener('click', closeToggleAdminModal);

    // Close on Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeDeleteModal();
            closeToggleAdminModal();
            closeLogoutModal();
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
        const params = new URLSearchParams({
            sort_by: currentSortBy,
            order: currentOrder,
            page: currentPage,
        });

        // Передаём page_size только если уже получили его с сервера
        if (currentPageSize !== null) {
            params.set('page_size', currentPageSize);
        }

        const search = searchInput.value.trim();
        if (search) {
            params.set('search', search);
        }

        const url = `${API_BASE}/users?${params.toString()}`;
        const response = await authenticatedFetch(url);
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || 'Ошибка загрузки пользователей');
        }
        const data = await response.json();

        // Сохраняем page_size из ответа как единственный source of truth
        currentPageSize = data.page_size;
        totalUsers = data.total;
        totalPages = data.total_pages;
        currentPage = data.page;

        renderUsers(data.items);
        updatePagination();
    } catch (error) {
        showToast('Ошибка загрузки пользователей: ' + error.message, 'error');
    }
}

function renderUsers(users) {
    const hasUsers = users.length > 0;

    userCount.textContent = totalUsers;
    emptyState.classList.toggle('hidden', hasUsers);
    usersTbody.innerHTML = '';

    if (!hasUsers) return;

    const isSuper = currentUser && currentUser.is_superadmin;

    for (const user of users) {
        const tr = document.createElement('tr');
        const isAdmin = user.is_admin ? 'Да' : 'Нет';
        const isSelf = currentUser && currentUser.id === user.id;

        let actionsHtml = '';
        if (isSuper) {
            const adminLabel = user.is_admin ? 'Снять админа' : 'Назначить админом';
            const toggleClass = user.is_admin ? 'btn-toggle-admin--remove' : 'btn-toggle-admin--add';
            actionsHtml = `
                <button class="btn-toggle-admin ${toggleClass}" data-user-id="${escapeHtml(user.id)}" data-current-admin="${user.is_admin}" data-user-login="${escapeHtml(user.login)}">${adminLabel}</button>
            `;
        }

        tr.innerHTML = `
            <td data-label="ID">${escapeHtml(user.id)}</td>
            <td data-label="Логин">${escapeHtml(user.login)}</td>
            <td data-label="Дата создания">${formatDateTime(user.created_at)}</td>
            <td data-label="Отклики" class="cell-application-count">${escapeHtml(user.application_count)}</td>
            <td data-label="Админ"><span class="admin-badge ${user.is_admin ? 'admin-badge--yes' : 'admin-badge--no'}">${isAdmin}</span></td>
            <td data-label="Действия">
                <button class="btn-delete-user" data-user-id="${escapeHtml(user.id)}" data-user-login="${escapeHtml(user.login)}">Удалить</button>
            </td>
            <td data-label="Управление">${actionsHtml}</td>
        `;
        usersTbody.appendChild(tr);
    }
}

function updatePagination() {
    if (totalPages <= 1) {
        paginationContainer.classList.add('hidden');
        return;
    }

    paginationContainer.classList.remove('hidden');
    paginationInfo.textContent = `Страница ${currentPage} из ${totalPages}`;
    paginationPrev.disabled = currentPage <= 1;
    paginationNext.disabled = currentPage >= totalPages;
}

function goToPage(page) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    loadUsers();
}

function prevPage() {
    goToPage(currentPage - 1);
}

function nextPage() {
    goToPage(currentPage + 1);
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
    const hasValue = !!searchInput.value;
    searchClearBtn.classList.toggle('hidden', !hasValue);

    // Debounce: сбрасываем предыдущий таймер
    if (searchTimeout) {
        clearTimeout(searchTimeout);
    }

    searchTimeout = setTimeout(() => {
        currentPage = 1;
        loadUsers();
    }, 300);
}

function clearSearch() {
    searchInput.value = '';
    searchClearBtn.classList.add('hidden');
    currentPage = 1;
    loadUsers();
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
    currentPage = 1;
    loadUsers();
}

function updateSortIndicators() {
    sortableHeaders.forEach(th => {
        const field = th.dataset.sortField;
        if (currentSortBy === field) {
            th.innerHTML = field === 'login' ? 'Логин' : field === 'application_count' ? 'Отклики' : field === 'is_admin' ? 'Админ' : 'Дата создания';
            th.innerHTML += currentOrder === 'asc' ? ' ▴' : ' ▾';
            th.classList.add('active-sort');
        } else {
            th.innerHTML = field === 'login' ? 'Логин' : field === 'application_count' ? 'Отклики' : field === 'is_admin' ? 'Админ' : 'Дата создания';
            th.classList.remove('active-sort');
        }
    });
}

// Toggle Admin modal
function openToggleAdminModal(userId, isCurrentlyAdmin, userLogin) {
    toggleAdminUserId = userId;
    toggleAdminIsCurrentlyAdmin = isCurrentlyAdmin;
    toggleAdminModalTitle.textContent = isCurrentlyAdmin ? 'Снять админа' : 'Назначить админом';
    const text = isCurrentlyAdmin
        ? `Вы действительно хотите снять права администратора с пользователя «<strong>${userLogin}</strong>»?`
        : `Вы действительно хотите назначить пользователя «<strong>${userLogin}</strong>» администратором?`;
    toggleAdminModalText.innerHTML = text;
    toggleAdminModal.classList.remove('hidden');
}

function closeToggleAdminModal() {
    toggleAdminUserId = null;
    toggleAdminIsCurrentlyAdmin = null;
    toggleAdminModal.classList.add('hidden');
    confirmToggleAdminBtn.disabled = false;
    confirmToggleAdminBtn.textContent = 'Подтвердить';
}

function closeModal(e) {
    // Close whichever modal is currently open
    closeDeleteModal();
    closeToggleAdminModal();
    closeLogoutModal();
}

async function confirmToggleAdmin() {
    if (toggleAdminUserId === null) return;

    confirmToggleAdminBtn.disabled = true;
    confirmToggleAdminBtn.textContent = 'Сохранение...';

    try {
        const response = await authenticatedFetch(`${API_BASE}/users/${toggleAdminUserId}/admin`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_admin: !toggleAdminIsCurrentlyAdmin }),
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || 'Ошибка изменения статуса администратора');
        }
        showToast('Статус администратора обновлён', 'success');
        closeToggleAdminModal();
        await loadUsers();
    } catch (error) {
        showToast('Ошибка: ' + error.message, 'error');
        closeToggleAdminModal();
    } finally {
        confirmToggleAdminBtn.disabled = false;
        confirmToggleAdminBtn.textContent = 'Подтвердить';
    }
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

        // 409 — нельзя удалить последнего админа, 403 — защищённый пользователь (суперадмин)
        if (response.status === 409 || response.status === 403) {
            const err = await response.json().catch(() => ({}));
            showToast(err.detail || 'Нельзя удалить пользователя', 'error');
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