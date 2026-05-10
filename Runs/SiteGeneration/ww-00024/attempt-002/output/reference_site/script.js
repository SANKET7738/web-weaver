// Pinnacle Estates — visual-only behaviors
(function () {
  const nav = document.querySelector('.site-nav');
  const toggle = document.querySelector('.nav-toggle');
  if (toggle && nav) {
    toggle.addEventListener('click', () => {
      nav.classList.toggle('open');
    });
  }

  // Highlight active nav based on data-page-slug
  const slug = document.body.getAttribute('data-page-slug');
  if (slug) {
    document.querySelectorAll('.nav-links a[data-nav]').forEach((a) => {
      if (a.getAttribute('data-nav') === slug) a.classList.add('active');
    });
  }

  // Form: prevent submit (visual-only)
  document.querySelectorAll('form[data-visual-only]').forEach((form) => {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const btn = form.querySelector('.submit-btn');
      if (btn) {
        const original = btn.textContent;
        btn.textContent = 'Inquiry Received';
        btn.disabled = true;
        setTimeout(() => {
          btn.textContent = original;
          btn.disabled = false;
        }, 2400);
      }
    });
  });
})();
