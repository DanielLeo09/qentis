(function () {
  const b = document.body;
  Auth.guard(b.dataset.role || null);
  injectNavbar();
  injectSidebar(b.dataset.sidebar, b.dataset.page);
}());
