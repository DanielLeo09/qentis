// ─────────────────────────────────────────────
// Qentis — API Configuration
// Central place for all backend service URLs
// ─────────────────────────────────────────────

const API_BASE = {
    AUTH:         'http://localhost:8001/api/auth',
    INSTITUTION:  'http://localhost:8002/api/institution',
    ITEMS:        'http://localhost:8003/api/items',
    BLOCKCHAIN:   'http://localhost:8004/api/blockchain',
    OUTPUT:       'http://localhost:8005/api/output',
    VERIFICATION: 'http://localhost:8006/api/verify',
    ADMIN:        'http://localhost:8007/api/admin',
};

// ─────────────────────────────────────────────
// Token & User Management
// ─────────────────────────────────────────────

const Auth = {
    getToken: () => localStorage.getItem('access_token'),
    getRefreshToken: () => localStorage.getItem('refresh_token'),
    getUser: () => JSON.parse(localStorage.getItem('user') || '{}'),
    getRole: () => localStorage.getItem('user_role'),

    setToken: (access) => {
        localStorage.setItem('access_token', access);
    },

    setTokens: (access, refresh) => {
        localStorage.setItem('access_token', access);
        localStorage.setItem('refresh_token', refresh);
    },

    setUser: (user) => {
        localStorage.setItem('user', JSON.stringify(user));
        localStorage.setItem('user_role', user.role);
    },

    clear: () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        localStorage.removeItem('user_role');
    },

    isLoggedIn: () => !!localStorage.getItem('access_token'),

    // Guard — redirect if not logged in or wrong role
    guard: (requiredRole = null) => {
        if (!Auth.isLoggedIn()) {
            window.location.href = '/login.html';
            return;
        }
        if (requiredRole && Auth.getRole() !== requiredRole) {
            redirectByRole(Auth.getRole());
        }
    },

    // Logout — clear storage and redirect
    logout: async () => {
        const refresh_token = Auth.getRefreshToken();
        try {
            await fetch(`${API_BASE.AUTH}/logout/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${Auth.getToken()}`
                },
                body: JSON.stringify({ refresh_token }),
            });
        } catch (e) {
            // Clear even if server call fails
        } finally {
            Auth.clear();
            window.location.href = '/login.html';
        }
    },
};

// ─────────────────────────────────────────────
// HTTP Headers
// ─────────────────────────────────────────────

const headers = {
    json: () => ({
        'Content-Type': 'application/json',
    }),

    auth: () => ({
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${Auth.getToken()}`,
    }),

    authOnly: () => ({
        'Authorization': `Bearer ${Auth.getToken()}`,
    }),
};

// ─────────────────────────────────────────────
// Base API Request Handler
// ─────────────────────────────────────────────

async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, options);

        if (response.status === 401) {
            Auth.clear();
            window.location.href = '/login.html';
            return;
        }

        const data = await response.json();

        if (!response.ok) {
            throw { status: response.status, data };
        }

        return data;

    } catch (error) {
        if (error.status) throw error;
        throw { status: 0, data: { error: 'Network error. Please check your connection.' } };
    }
}

// ─────────────────────────────────────────────
// Role-based redirect
// ─────────────────────────────────────────────

function redirectByRole(role) {
    const map = {
        ISSUER:   '/pages/issuer/dashboard.html',
        ADMIN:    '/pages/admin/dashboard.html',
        VERIFIER: '/pages/verifier/verify.html',
    };
    window.location.href = map[role] || '/login.html';
}

// ─────────────────────────────────────────────
// UI Helpers — used across all pages
// ─────────────────────────────────────────────

function showAlert(elementId, message, type = 'error') {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.textContent = message;
    el.className = `q-alert q-alert--${type}`;
    el.style.display = 'block';
}

function hideAlert(elementId) {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.style.display = 'none';
    el.textContent = '';
}

function setLoading(buttonId, loading, loadingText = 'Loading...') {
    const btn = document.getElementById(buttonId);
    if (!btn) return;
    btn.disabled = loading;
    if (loading) {
        btn.dataset.originalText = btn.textContent;
        btn.textContent = loadingText;
    } else {
        btn.textContent = btn.dataset.originalText || loadingText;
    }
}

function showSuccess(elementId, message) {
    showAlert(elementId, message, 'success');
}

function formatDate(dateString) {
    if (!dateString) return '—';
    return new Date(dateString).toLocaleDateString('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
    });
}

function formatDateTime(dateString) {
    if (!dateString) return '—';
    return new Date(dateString).toLocaleString('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}