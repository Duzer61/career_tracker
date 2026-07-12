// Authentication logic

// Yandex SmartCaptcha state
let captchaWidgets = {};
let smartCaptchaReady = false;

// Called by Yandex SmartCaptcha script when API is ready
window.onSmartCaptchaReady = function () {
    smartCaptchaReady = true;
};

function renderCaptcha(containerId) {
    if (!smartCaptchaReady || !SMARTCAPTCHA_SITE_KEY) return null;
    const container = document.getElementById(containerId);
    if (!container) return null;
    if (captchaWidgets[containerId]) return captchaWidgets[containerId];

    const widgetId = window.smartCaptcha.render(containerId, {
        sitekey: SMARTCAPTCHA_SITE_KEY,
        callback: function (token) {
            // Token is available, form can be submitted
        },
    });
    captchaWidgets[containerId] = widgetId;
    return widgetId;
}

function getCaptchaToken(containerId) {
    const widgetId = captchaWidgets[containerId];
    if (widgetId === undefined) return '';
    try {
        return window.smartCaptcha.getResponse(widgetId);
    } catch {
        return '';
    }
}

function resetCaptcha(containerId) {
    const widgetId = captchaWidgets[containerId];
    if (widgetId !== undefined) {
        try {
            window.smartCaptcha.reset(widgetId);
        } catch {
            // ignore
        }
    }
}

async function checkAuth() {
    // First try with httponly cookies (tokens set by server)
    try {
        const response = await authenticatedFetch(`${API_BASE}/users/me`);
        if (response.ok) {
            currentUser = await response.json();
            showApp();
            await loadApplications();
            return;
        }
    } catch (err) {
        // Token invalid or missing
    }

    // Fallback: try with localStorage token (legacy)
    const token = localStorage.getItem('access_token');
    if (token) {
        try {
            const response = await fetch(`${API_BASE}/users/me`, {
                headers: { 'Authorization': `Bearer ${token}` },
                credentials: 'include'
            });
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

    const captchaToken = getCaptchaToken('login-captcha-container');

    try {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ login, password, captcha_token: captchaToken })
        });

        const data = await response.json();

        if (response.ok) {
            await checkAuth();
        } else {
            resetCaptcha('login-captcha-container');
            let detail;
            if (typeof data.detail === 'string') {
                detail = data.detail;
            } else if (Array.isArray(data.detail)) {
                const messages = data.detail.map(e => e.msg.replace(/^Value error, /, ''));
                detail = messages.join('; ');
            } else {
                detail = 'Ошибка входа';
            }
            messageEl.textContent = detail;
        }
    } catch (err) {
        resetCaptcha('login-captcha-container');
        messageEl.textContent = 'Ошибка подключения';
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const login = document.getElementById('register-login').value;
    const password = document.getElementById('register-password').value;
    const passwordConfirm = document.getElementById('register-password-confirm').value;
    const messageEl = document.getElementById('auth-message');

    const captchaToken = getCaptchaToken('register-captcha-container');

    try {
        const response = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ login, password, password_confirm: passwordConfirm, captcha_token: captchaToken })
        });

        const data = await response.json();

        if (response.ok) {
            showToast('Регистрация прошла успешно', 'success');
            await checkAuth();
        } else {
            resetCaptcha('register-captcha-container');
            let detail;
            if (typeof data.detail === 'string') {
                detail = data.detail;
            } else if (Array.isArray(data.detail)) {
                const messages = data.detail.map(e => e.msg.replace(/^Value error, /, ''));
                detail = messages.join('; ');
            } else {
                detail = 'Ошибка регистрации';
            }
            messageEl.textContent = detail;
        }
    } catch (err) {
        resetCaptcha('register-captcha-container');
        messageEl.textContent = 'Ошибка подключения';
    }
}

// Render captchas when auth forms are shown
function renderAuthCaptchas() {
    if (!smartCaptchaReady || !SMARTCAPTCHA_SITE_KEY) {
        // Retry after a short delay if API not ready yet
        setTimeout(renderAuthCaptchas, 500);
        return;
    }
    renderCaptcha('login-captcha-container');
    renderCaptcha('register-captcha-container');
}

function showLogoutModal() {
    document.getElementById('logout-modal').classList.remove('hidden');
}

function closeLogoutModal() {
    document.getElementById('logout-modal').classList.add('hidden');
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

async function handleLogoutWithRedirect() {
    closeLogoutModal();
    try {
        await fetch(`${API_BASE}/auth/logout`, {
            method: 'POST',
            credentials: 'include'
        });
        currentUser = null;
        window.location.href = '/';
    } catch (error) {
        console.error('Logout error:', error);
        window.location.href = '/';
    }
}
