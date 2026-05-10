/* Clearmind Therapy — visual interactivity only */
(function () {
  'use strict';

  // Mobile nav toggle
  const navToggle = document.querySelector('.nav-toggle');
  const navLinks = document.getElementById('primary-nav');
  if (navToggle && navLinks) {
    navToggle.addEventListener('click', function () {
      const open = navLinks.classList.toggle('is-open');
      navToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  // Generic chevron-FAQ (services page) — multiple panels can be open
  document.querySelectorAll('[data-faq] .faq-item').forEach(function (item) {
    const btn = item.querySelector('.faq-item__btn');
    if (!btn) return;
    btn.addEventListener('click', function () {
      const isOpen = item.classList.toggle('is-open');
      btn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });
  });

  // Plus-style FAQ (contact page) — accordion: only one open at a time
  document.querySelectorAll('[data-faq-plus]').forEach(function (list) {
    const items = list.querySelectorAll('.contact-faq-item');
    items.forEach(function (item) {
      const btn = item.querySelector('.contact-faq-item__btn');
      if (!btn) return;
      btn.addEventListener('click', function () {
        const wasOpen = item.classList.contains('is-open');
        items.forEach(function (other) {
          other.classList.remove('is-open');
          const ob = other.querySelector('.contact-faq-item__btn');
          if (ob) ob.setAttribute('aria-expanded', 'false');
        });
        if (!wasOpen) {
          item.classList.add('is-open');
          btn.setAttribute('aria-expanded', 'true');
        }
      });
    });
  });
})();
