async function handleRegister() {
  const name      = document.getElementById('name').value.trim();
  const email     = document.getElementById('email').value.trim();
  const password  = document.getElementById('password').value;
  const password2 = document.getElementById('password2').value;

  if (!name || !email || !password) {
    showAlert('alert', 'Please fill in all required fields.', 'error');
    return;
  }
  if (password !== password2) {
    showAlert('alert', 'Passwords do not match.', 'error');
    return;
  }
  if (password.length < 8) {
    showAlert('alert', 'Password must be at least 8 characters.', 'error');
    return;
  }

  const institution_name = document.getElementById('institution-name').value.trim();
  const institution_type = document.getElementById('institution-type').value;
  if (!institution_name || !institution_type) {
    showAlert('alert', 'Please fill in institution details.', 'error');
    return;
  }

  setLoading('register-btn', true, 'Creating account...');
  hideAlert('alert');

  try {
    const res  = await fetch(`${API.AUTH}/auth/register/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password, role: 'ISSUER', institution_name, institution_type }),
    });
    const data = await res.json();

    if (res.ok) {
      window.location.href = 'pending-approval.html';
    } else {
      const msg = data.email?.[0] || data.detail || 'Registration failed.';
      showAlert('alert', msg, 'error');
    }
  } catch (e) {
    showAlert('alert', 'Connection error. Please try again.', 'error');
  } finally {
    setLoading('register-btn', false, 'Create account');
  }
}
