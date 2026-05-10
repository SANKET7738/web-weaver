/* Clearmind Therapy — visual-only behavior */

(function () {
  // Mobile nav toggle
  const toggle = document.querySelector('[data-nav-toggle]');
  const nav = document.querySelector('[data-nav]');
  if (toggle && nav) {
    toggle.addEventListener('click', () => {
      const open = nav.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  // FAQ accordions (services-style — multiple can be open)
  const faqItems = document.querySelectorAll('[data-faq-item]');
  faqItems.forEach((item) => {
    const button = item.querySelector('[data-faq-toggle]');
    if (!button) return;
    button.addEventListener('click', () => {
      item.classList.toggle('is-open');
      const expanded = item.classList.contains('is-open');
      button.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    });
  });

  // Contact FAQ accordions (single-open behavior)
  const contactFaqItems = document.querySelectorAll('[data-contact-faq-item]');
  contactFaqItems.forEach((item) => {
    const button = item.querySelector('[data-contact-faq-toggle]');
    if (!button) return;
    button.addEventListener('click', () => {
      const wasOpen = item.classList.contains('is-open');
      contactFaqItems.forEach((other) => {
        other.classList.remove('is-open');
        const btn = other.querySelector('[data-contact-faq-toggle]');
        if (btn) btn.setAttribute('aria-expanded', 'false');
      });
      if (!wasOpen) {
        item.classList.add('is-open');
        button.setAttribute('aria-expanded', 'true');
      }
    });
  });

  // Prevent default form submit (visual-only)
  const form = document.querySelector('[data-contact-form]');
  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
    });
  }
})();
