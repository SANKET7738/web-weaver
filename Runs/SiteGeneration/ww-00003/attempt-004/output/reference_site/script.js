// Clearmind Therapy — vanilla JS visual behavior

(function () {
  'use strict';

  // ----- Mobile nav toggle -----
  const navToggle = document.querySelector('.nav-toggle');
  const navLinks = document.querySelector('.nav-links');
  if (navToggle && navLinks) {
    navToggle.addEventListener('click', function () {
      const isOpen = navLinks.classList.toggle('is-open');
      navToggle.setAttribute('aria-expanded', String(isOpen));
    });
  }

  // ----- FAQ accordions (single-open behavior per group) -----
  document.querySelectorAll('.faq-list, .contact-faq-list').forEach(function (group) {
    const items = group.querySelectorAll('.faq-item');
    items.forEach(function (item) {
      const button = item.querySelector('.faq-question');
      if (!button) return;
      button.addEventListener('click', function () {
        const wasOpen = item.classList.contains('is-open');
        // close all in group
        items.forEach(function (other) {
          other.classList.remove('is-open');
          const btn = other.querySelector('.faq-question');
          if (btn) btn.setAttribute('aria-expanded', 'false');
        });
        if (!wasOpen) {
          item.classList.add('is-open');
          button.setAttribute('aria-expanded', 'true');
        }
      });
    });
  });
})();
