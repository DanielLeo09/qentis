/* ============================================================
   QENTIS — Shared layout components
   Call injectNavbar() and injectSidebar(role, activePage)
   at the top of every dashboard page.
   ============================================================ */

function injectNavbar() {
  const nav = document.createElement('nav');
  nav.className = 'q-navbar';
  nav.innerHTML = `
    <a href="/index.html" class="q-logo">Qen<span>tis</span></a>
    <div style="margin-left:auto;display:flex;align-items:center;gap:16px">
      <span style="font-size:13px;color:var(--q-text-muted)" id="navbar-user"></span>
      <button onclick="Auth.logout()" class="btn-q-outline" style="padding:6px 14px;font-size:13px">
        Sign out
      </button>
    </div>
  `;
  document.body.prepend(nav);
}

/* Sidebar configs per role */
const SIDEBAR_LINKS = {
  issuer: [
    { href: '/pages/issuer/dashboard.html',       icon: '▦', label: 'Dashboard',       id: 'dashboard' },
    { href: '/pages/issuer/register-item.html',   icon: '+', label: 'Register Item',   id: 'register-item' },
    { href: '/pages/issuer/my-items.html',        icon: '≡', label: 'My Items',        id: 'my-items' },
    { href: '/pages/issuer/account.html',         icon: '◎', label: 'Account',         id: 'account' },
  ],
  owner: [
    { href: '/pages/owner/dashboard.html',        icon: '▦', label: 'Dashboard',       id: 'dashboard' },
    { href: '/pages/owner/claim-item.html',       icon: '⊕', label: 'Claim Item',      id: 'claim-item' },
    { href: '/pages/owner/my-items.html',         icon: '≡', label: 'My Items',        id: 'my-items' },
    { href: '/pages/owner/account.html',          icon: '◎', label: 'Account',         id: 'account' },
  ],
  admin: [
    { href: '/pages/admin/dashboard.html',        icon: '▦', label: 'Dashboard',       id: 'dashboard' },
    { href: '/pages/admin/pending-issuers.html',  icon: '⏳', label: 'Pending Issuers', id: 'pending-issuers' },
    { href: '/pages/admin/all-issuers.html',      icon: '🏢', label: 'All Issuers',     id: 'all-issuers' },
    { href: '/pages/admin/activity.html',         icon: '≡', label: 'All Activity',    id: 'activity' },
    { href: '/pages/admin/fraud-alerts.html',     icon: '⚠', label: 'Fraud Alerts',   id: 'fraud-alerts' },
    { href: '/pages/admin/analytics.html',        icon: '◈', label: 'Analytics',       id: 'analytics' },
  ],
};

function injectSidebar(role, activePage) {
  const links = SIDEBAR_LINKS[role] || [];

  const sidebar = document.createElement('aside');
  sidebar.className = 'q-sidebar';
  sidebar.innerHTML = `
    <div class="q-sidebar-section">${role.toUpperCase()}</div>
    ${links.map(l => `
      <a href="${l.href}" class="q-sidebar-link ${l.id === activePage ? 'active' : ''}">
        <span style="font-size:14px;width:18px;text-align:center">${l.icon}</span>
        ${l.label}
      </a>
    `).join('')}
  `;

  /* Insert after navbar */
  const nav = document.querySelector('.q-navbar');
  if (nav) nav.after(sidebar);
  else document.body.prepend(sidebar);
}
