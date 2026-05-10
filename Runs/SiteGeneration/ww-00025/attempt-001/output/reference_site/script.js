// NEONRIFT — visual behaviors only
(function () {
  'use strict';

  // FAQ accordion
  document.addEventListener('click', function (e) {
    const btn = e.target.closest('.faq-question');
    if (!btn) return;
    const item = btn.closest('.faq-item');
    if (!item) return;
    const open = item.classList.contains('open');
    document.querySelectorAll('.faq-item.open').forEach(el => el.classList.remove('open'));
    if (!open) item.classList.add('open');
  });

  // Form submit — visual only, prevent default
  document.addEventListener('submit', function (e) {
    const form = e.target.closest('.transmission-form');
    if (!form) return;
    e.preventDefault();
    const btn = form.querySelector('.submit-btn');
    if (btn) {
      const original = btn.textContent;
      btn.textContent = 'TRANSMISSION SENT';
      btn.style.background = 'var(--acid-circuit)';
      setTimeout(function () {
        btn.textContent = original;
        btn.style.background = '';
      }, 2400);
    }
  });

  // Set the hero headline data-text dynamically (for chromatic aberration ::before)
  const heroHeadline = document.querySelector('.hero-headline');
  if (heroHeadline && !heroHeadline.dataset.text) {
    heroHeadline.dataset.text = heroHeadline.textContent.trim();
  }
})();
