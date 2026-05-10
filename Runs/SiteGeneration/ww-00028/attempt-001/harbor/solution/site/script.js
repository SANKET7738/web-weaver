/* Hearthstone Law — visual-only enhancements */
(function () {
  'use strict';

  // Consultation method selector toggle (visual only)
  const methodCards = document.querySelectorAll('.method-card');
  if (methodCards.length) {
    methodCards.forEach((card) => {
      card.addEventListener('click', () => {
        methodCards.forEach((c) => {
          c.classList.remove('is-active');
          c.setAttribute('aria-checked', 'false');
        });
        card.classList.add('is-active');
        card.setAttribute('aria-checked', 'true');
      });
    });
  }

  // Subtle parallax for hero watermark on scroll (desktop only)
  const watermark = document.querySelector('.hero-watermark');
  if (watermark && window.matchMedia('(min-width: 1024px)').matches) {
    let ticking = false;
    window.addEventListener('scroll', () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          const y = window.scrollY * 0.08;
          watermark.style.transform = 'translate(0, calc(-50% + ' + y + 'px))';
          ticking = false;
        });
        ticking = true;
      }
    }, { passive: true });
  }
})();
