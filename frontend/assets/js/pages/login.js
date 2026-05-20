// ─────────────────────────────────────────────
// Qentis — Login Page
// ─────────────────────────────────────────────

// Redirect if already logged in
if (Auth.isLoggedIn()) {
    redirectByRole(Auth.getRole());
}

async function handleLogin() {
    const email    = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;

    if (!email || !password) {
        showAlert('alert', 'Please fill in all fields.', 'error');
        return;
    }

    setLoading('login-btn', true, 'Signing in...');
    hideAlert('alert');

    try {
        const data = await AuthAPI.login(email, password);

        if (data && data.user) {
            redirectByRole(data.user.role);
        }

    } catch (error) {
        const message = error.data?.error ||
                        error.data?.detail ||
                        'Invalid credentials.';
        showAlert('alert', message, 'error');
    } finally {
        setLoading('login-btn', false, 'Sign in');
    }
}

function redirectByRole(role) {
    if (!role) return;
    const map = {
        ISSUER:   '../pages/issuer/dashboard.html',
        ADMIN:    '../pages/admin/dashboard.html',
        VERIFIER: '../pages/verifier/verify.html',
    };
    window.location.href = map[role] || '../index.html';
}

document.addEventListener('keydown', e => {
    if (e.key === 'Enter') handleLogin();
});