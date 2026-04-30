/* ============================================================
   QENTIS — API config & auth utilities
   All API base URLs live here. Change once, applies everywhere.
   ============================================================ */

const API = {
  AUTH:         'http://localhost:8001/api',   // auth service
  INSTITUTION:  'http://localhost:8002/api',   // institution management
  ITEMS:        'http://localhost:8003/api',   // item registration
  BLOCKCHAIN:   'http://localhost:8004/api',   // blockchain service
  VERIFICATION: 'http://localhost:8005/api',   // verification service
  ADMIN:        'http://localhost:8006/api',   // admin & analytics
};

/* ── Token management ── */
const Auth = {
  getToken()  { return localStorage.getItem('qentis_token'); },
  setToken(t) { localStorage.setItem('qentis_token', t); },
  getUser()   { return JSON.parse(localStorage.getItem('qentis_user') || 'null'); },
  setUser(u)  { localStorage.setItem('qentis_user', JSON.stringify(u)); },

  logout() {
    localStorage.removeItem('qentis_token');
    localStorage.removeItem('qentis_user');
    window.location.href = '/pages/login.html';
  },

  /* Call at top of every protected page */
  guard(requiredRole = null) {
    const token = this.getToken();
    const user  = this.getUser();

    if (!token || !user) {
      window.location.href = '/pages/login.html';
      return false;
    }

    if (requiredRole && user.role !== requiredRole) {
      window.location.href = '/pages/login.html';
      return false;
    }

    /* Populate navbar user info if element exists */
    const el = document.getElementById('navbar-user');
    if (el) el.textContent = user.email || user.name || 'Account';

    return true;
  },
};

/* ── Fetch wrapper — adds JWT header automatically ── */
async function qFetch(url, options = {}) {
  const token = Auth.getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const res = await fetch(url, { ...options, headers });

  if (res.status === 401) {
    Auth.logout();
    return null;
  }

  return res;
}

/* ── UI helpers ── */
function showAlert(id, message, type = 'error') {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = `q-alert q-alert-${type} show`;
  el.textContent = message;
}

function hideAlert(id) {
  const el = document.getElementById(id);
  if (el) el.className = 'q-alert';
}

function setLoading(btnId, loading = true, text = 'Loading...') {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  if (loading) {
    btn.disabled = true;
    btn.dataset.originalText = btn.textContent;
    btn.innerHTML = `<span class="q-spinner"></span> ${text}`;
  } else {
    btn.disabled = false;
    btn.textContent = btn.dataset.originalText || text;
  }
}

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
  });
}

function formatHash(hash) {
  if (!hash) return '—';
  return hash.slice(0, 10) + '...' + hash.slice(-6);
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    showToast('Copied to clipboard');
  });
}

function showToast(message, type = 'success') {
  const toast = document.createElement('div');
  toast.className = `q-toast q-toast-${type}`;
  toast.textContent = message;
  toast.style.cssText = `
    position:fixed; bottom:24px; right:24px; z-index:9999;
    background:var(--q-primary); color:#fff;
    padding:10px 18px; border-radius:var(--q-radius);
    font-size:13px; font-family:var(--q-font);
    box-shadow:0 4px 16px rgba(0,0,0,.2);
    animation: slideUp .2s ease;
  `;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 2800);
}
