// Clearmind Therapy — minimal vanilla JS for visual interactivity only.
(function () {
  'use strict';

  function initAccordion(scopeSelector) {
    const items = document.querySelectorAll(scopeSelector + ' .faq-item');
    items.forEach(function (item) {
      const toggle = item.querySelector('.faq-item__toggle');
      if (!toggle) return;
      toggle.addEventListener('click', function () {
        const isOpen = item.classList.contains('is-open');
        if (item.dataset.accordionGroup) {
          // Single-open accordion behavior: close all in group, then maybe open this one.
          const group = document.querySelectorAll(
            '[data-accordion-group="' + item.dataset.accordionGroup + '"]'
          );
          group.forEach(function (other) {
            other.classList.remove('is-open');
            const otherToggle = other.querySelector('.faq-item__toggle');
            if (otherToggle) otherToggle.setAttribute('aria-expanded', 'false');
          });
          if (!isOpen) {
            item.classList.add('is-open');
            toggle.setAttribute('aria-expanded', 'true');
          }
        } else {
          // Independent toggle behavior
          item.classList.toggle('is-open');
          toggle.setAttribute('aria-expanded', String(!isOpen));
        }
      });
      // Initialize aria state
      toggle.setAttribute('aria-expanded', String(item.classList.contains('is-open')));
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    initAccordion('body');

    // Soft form submit prevention (purely visual demo)
    const forms = document.querySelectorAll('form[data-demo-form]');
    forms.forEach(function (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        const button = form.querySelector('button[type="submit"]');
        if (!button) return;
        const original = button.textContent;
        button.disabled = true;
        button.textContent = 'Thank you — we will be in touch';
        setTimeout(function () {
          button.disabled = false;
          button.textContent = original;
        }, 3500);
      });
    });
  });
})();
