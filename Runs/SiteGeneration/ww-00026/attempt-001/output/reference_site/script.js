// Lumi & Bloom — visual interactions only

(function () {
  'use strict';

  // FAQ accordion
  const faqItems = document.querySelectorAll('.faq-item');
  faqItems.forEach((item) => {
    const head = item.querySelector('.faq-item__head');
    if (!head) return;
    head.addEventListener('click', () => {
      const isOpen = item.classList.contains('is-open');
      faqItems.forEach((other) => {
        other.classList.remove('is-open');
        const btn = other.querySelector('.faq-item__head');
        if (btn) btn.setAttribute('aria-expanded', 'false');
      });
      if (!isOpen) {
        item.classList.add('is-open');
        head.setAttribute('aria-expanded', 'true');
      }
    });
  });

  // Contact form — visual-only feedback
  const form = document.querySelector('.contact-form');
  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const btn = form.querySelector('button[type="submit"]');
      if (!btn) return;
      const original = btn.textContent;
      btn.textContent = 'Message Sent ✓';
      btn.style.background = '#5BC8D0';
      setTimeout(() => {
        btn.textContent = original;
        btn.style.background = '';
        form.reset();
      }, 2200);
    });
  }

  // Catalog "Add to Ritual" — visual-only feedback
  document.querySelectorAll('.catalog-card__btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const original = btn.textContent;
      btn.textContent = 'Added ✓';
      btn.style.background = '#2D3A35';
      setTimeout(() => {
        btn.textContent = original;
        btn.style.background = '';
      }, 1400);
    });
  });
})();
