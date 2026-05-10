// Pixelwave — light visual JS (mobile sidebar drawer)
(function () {
  const toggle = document.getElementById('menuToggle');
  const sidebar = document.getElementById('sidebar');
  if (!toggle || !sidebar) return;

  toggle.addEventListener('click', function () {
    sidebar.classList.toggle('open');
    toggle.textContent = sidebar.classList.contains('open') ? 'Close' : 'Menu';
  });

  // Close drawer when a nav link is clicked on mobile
  sidebar.querySelectorAll('.nav a').forEach(function (link) {
    link.addEventListener('click', function () {
      if (window.matchMedia('(max-width: 1024px)').matches) {
        sidebar.classList.remove('open');
        toggle.textContent = 'Menu';
      }
    });
  });

  // Close drawer when clicking outside
  document.addEventListener('click', function (e) {
    if (!sidebar.classList.contains('open')) return;
    if (sidebar.contains(e.target) || toggle.contains(e.target)) return;
    sidebar.classList.remove('open');
    toggle.textContent = 'Menu';
  });
})();
