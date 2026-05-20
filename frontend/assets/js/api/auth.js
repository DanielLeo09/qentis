// ─────────────────────────────────────────────
// Qentis — User & Auth Service API
// Base URL: http://localhost:8001/api/auth
// ─────────────────────────────────────────────

const AuthAPI = {

    /**
     * Register a new user account.
     * POST /api/auth/register/
     */
    register: async (email, password, passwordConfirm, role) => {
        return await apiRequest(`${API_BASE.AUTH}/register/`, {
            method: 'POST',
            headers: headers.json(),
            body: JSON.stringify({
                email,
                password,
                password_confirm: passwordConfirm,
                role,
            }),
        });
    },

    /**
     * Login with email and password.
     * POST /api/auth/login/
     * Stores tokens and user info in localStorage.
     */
    login: async (email, password) => {
        const data = await apiRequest(`${API_BASE.AUTH}/login/`, {
            method: 'POST',
            headers: headers.json(),
            body: JSON.stringify({ email, password }),
        });

        if (data && data.tokens) {
            Auth.setTokens(data.tokens.access, data.tokens.refresh);
            Auth.setUser(data.user);
        }

        return data;
    },

    /**
     * Logout — blacklist refresh token.
     * POST /api/auth/logout/
     */
    logout: async () => {
        const refresh_token = Auth.getRefreshToken();
        try {
            await apiRequest(`${API_BASE.AUTH}/logout/`, {
                method: 'POST',
                headers: headers.auth(),
                body: JSON.stringify({ refresh_token }),
            });
        } catch (e) {
            // Even if logout fails on server, clear local storage
        } finally {
            Auth.clear();
            window.location.href = '/login.html';
        }
    },

    /**
     * Refresh access token using refresh token.
     * POST /api/auth/token/refresh/
     */
    refreshToken: async () => {
        const refresh_token = Auth.getRefreshToken();
        const data = await apiRequest(`${API_BASE.AUTH}/token/refresh/`, {
            method: 'POST',
            headers: headers.json(),
            body: JSON.stringify({ refresh_token }),
        });

        if (data && data.access) {
            localStorage.setItem('access_token', data.access);
        }

        return data;
    },

    /**
     * Get current user profile.
     * GET /api/auth/profile/
     */
    getProfile: async () => {
        return await apiRequest(`${API_BASE.AUTH}/profile/`, {
            method: 'GET',
            headers: headers.auth(),
        });
    },

    /**
     * Update current user profile.
     * PUT /api/auth/profile/
     */
    updateProfile: async (profileData) => {
        return await apiRequest(`${API_BASE.AUTH}/profile/update/`, {
            method: 'PUT',
            headers: headers.auth(),
            body: JSON.stringify(profileData),
        });
    },

    /**
     * Change password.
     * POST /api/auth/change-password/
     */
    changePassword: async (oldPassword, newPassword, newPasswordConfirm) => {
        return await apiRequest(`${API_BASE.AUTH}/change-password/`, {
            method: 'POST',
            headers: headers.auth(),
            body: JSON.stringify({
                old_password: oldPassword,
                new_password: newPassword,
                new_password_confirm: newPasswordConfirm,
            }),
        });
    },

    /**
     * Verify JWT token is valid.
     * GET /api/auth/verify/
     */
    verifyToken: async () => {
        return await apiRequest(`${API_BASE.AUTH}/verify/`, {
            method: 'GET',
            headers: headers.auth(),
        });
    },

    /**
     * List all users (Admin only).
     * GET /api/auth/users/
     */
    listUsers: async () => {
        return await apiRequest(`${API_BASE.AUTH}/users/`, {
            method: 'GET',
            headers: headers.auth(),
        });
    },

    /**
     * Deactivate a user (Admin only).
     * PUT /api/auth/users/{user_id}/deactivate/
     */
    deactivateUser: async (userId) => {
        return await apiRequest(`${API_BASE.AUTH}/users/${userId}/deactivate/`, {
            method: 'PUT',
            headers: headers.auth(),
        });
    },
};