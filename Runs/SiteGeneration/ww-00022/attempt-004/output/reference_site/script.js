// BoltWorks — light visual behaviors only.
(function () {
  // Mark active nav link based on current page slug.
  function markActiveNav() {
    var body = document.body;
    var slug = body && body.dataset ? body.dataset.pageSlug : null;
    if (!slug) return;
    var links = document.querySelectorAll('[data-nav-link]');
    links.forEach(function (el) {
      if (el.dataset.navLink === slug) {
        el.classList.add('active');
      }
    });
  }

  // Simple FAQ toggle (visual only). FAQ rows remain visible — clicking
  // a row just flips the "+" indicator to "-" for poster theatrics.
  function wireFaqToggle() {
    var rows = document.querySelectorAll('.faq-row');
    rows.forEach(function (row) {
      row.addEventListener('click', function () {
        var plus = row.querySelector('.faq-plus');
        if (!plus) return;
        plus.textContent = plus.textContent.trim() === '+' ? '−' : '+';
      });
    });
  }

  // Prevent contact form submission (no backend) — show a friendly note.
  function wireContactForm() {
    var form = document.getElementById('contact-form');
    if (!form) return;
    var note = document.getElementById('form-note');
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (note) note.style.display = 'block';
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    markActiveNav();
    wireFaqToggle();
    wireContactForm();
  });
})();
