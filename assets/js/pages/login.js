if (Auth.getToken()) redirectByRole(Auth.getUser()?.role);

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
    const res = await fetch(`${API.AUTH}/auth/login/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    const data = await res.json();

    if (res.ok) {
      Auth.setToken(data.access);
      Auth.setUser(data.user);
      redirectByRole(data.user.role);
    } else {
      showAlert('alert', data.detail || 'Invalid credentials.', 'error');
    }
  } catch (e) {
    showAlert('alert', 'Connection error. Please try again.', 'error');
  } finally {
    setLoading('login-btn', false, 'Sign in');
  }
}

function redirectByRole(role) {
  if (!role) return;
  const map = {
    ISSUER: '../pages/issuer/dashboard.html',
    ADMIN:  '../pages/admin/dashboard.html',
  };
  window.location.href = map[role] || '../index.html';
}

document.addEventListener('keydown', e => {
  if (e.key === 'Enter') handleLogin();
});
