// UI helpers

function showAuth() {
    document.getElementById('auth-container').classList.remove('hidden');
    document.getElementById('app-container').classList.add('hidden');
    // Render Yandex SmartCaptcha widgets
    if (typeof renderAuthCaptchas === 'function') {
        setTimeout(renderAuthCaptchas, 100);
    }
}

function showApp() {
    document.getElementById('auth-container').classList.add('hidden');
    document.getElementById('app-container').classList.remove('hidden');
    document.getElementById('username-display').textContent = currentUser.login;

    // Show admin button for admin or superadmin users
    const adminBtn = document.getElementById('admin-btn');
    if (adminBtn) {
        adminBtn.classList.toggle('hidden', !currentUser.is_admin && !currentUser.is_superadmin);
    }
}

function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    document.getElementById(`${tabName}-form`).classList.add('active');
}

function updateSortButton() {
    const btn = document.getElementById('sort-btn');
    btn.textContent = sortAscending ? '⬇ Сначала старые' : '⬆ Сначала новые';
    btn.dataset.ascending = sortAscending.toString();
}

function updateColumnCounts() {
    document.querySelectorAll('.column').forEach(col => {
        const status = col.dataset.status;
        const count = applications.filter(app => app.status === status).length;
        col.querySelector('.column-count').textContent = count;
    });
}

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
    }, 5000);
}
