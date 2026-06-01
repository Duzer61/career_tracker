// Authentication logic

async function checkAuth() {
    const token = localStorage.getItem('access_token');
    if (token) {
        try {
            const response = await authenticatedFetch(`${API_BASE}/users/me`);
            if (response.ok) {
                currentUser = await response.json();
                showApp();
                await loadApplications();
                return;
            }
        } catch (err) {
            // Token invalid
        }
    }
    showAuth();
}

async function handleLogin(e) {
    e.preventDefault();
    const login = document.getElementById('login-login').value;
    const password = document.getElementById('login-password').value;
    const messageEl = document.getElementById('auth-message');

    try {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ login, password })
        });

        const data = await response.json();

        if (response.ok) {
            localStorage.setItem('access_token', data.access_token);
            localStorage.setItem('refresh_token', data.refresh_token);
            await checkAuth();
        } else {
            const detail = typeof data.detail === 'string'
                ? data.detail
                : (data.detail?.message || 'Ошибка входа');
            messageEl.textContent = detail;
        }
    } catch (err) {
        messageEl.textContent = 'Ошибка подключения';
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const login = document.getElementById('register-login').value;
    const password = document.getElementById('register-password').value;
    const messageEl = document.getElementById('auth-message');

    try {
        const response = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ login, password })
        });

        const data = await response.json();

        if (response.ok) {
            localStorage.setItem('access_token', data.access_token);
            localStorage.setItem('refresh_token', data.refresh_token);
            await checkAuth();
        } else {
            const detail = typeof data.detail === 'string'
                ? data.detail
                : (data.detail?.message || 'Ошибка регистрации');
            messageEl.textContent = detail;
        }
    } catch (err) {
        messageEl.textContent = 'Ошибка подключения';
    }
}

function showLogoutModal() {
    document.getElementById('logout-modal').classList.remove('hidden');
}

function closeLogoutModal() {
    document.getElementById('logout-modal').classList.add('hidden');
}

async function handleLogout() {
    const token = getToken();
    if (token) {
        try {
            await authenticatedFetch(`${API_BASE}/auth/logout`, { method: 'POST' });
        } catch (err) {
            // Ignore logout errors
        }
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    currentUser = null;
    applications = [];
    closeLogoutModal();
    showAuth();
}