/* Pixelwave — visual-only client behavior */
(function () {
  'use strict';

  // 1. Light parallax shimmer on lens-flare elements as the cursor moves
  //    over the hero panels — keeps the Y2K gloss feeling alive without
  //    interfering with content.
  const flareSelectors = [
    '.home-hero__lensflare',
    '.features-header__flare-lg',
    '.features-header__flare-sm',
    '.article-header__flare',
    '.archive-header__flare',
    '.about-story__decor-flare',
  ];

  const flares = document.querySelectorAll(flareSelectors.join(','));

  if (flares.length) {
    document.addEventListener('mousemove', function (e) {
      const x = (e.clientX / window.innerWidth) - 0.5;
      const y = (e.clientY / window.innerHeight) - 0.5;
      flares.forEach(function (el) {
        const range = 12;
        el.style.transform = 'translate(' + (x * range).toFixed(2) + 'px, ' + (y * range).toFixed(2) + 'px)';
      });
    });
  }

  // 2. Newsletter form — visual confirmation only (no submission).
  const form = document.querySelector('.cta-newsletter__form');
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      const submit = form.querySelector('.cta-newsletter__submit');
      if (!submit) return;
      const original = submit.textContent;
      submit.textContent = 'Subscribed ✓';
      submit.style.background = '#CC00AA';
      setTimeout(function () {
        submit.textContent = original;
        submit.style.background = '';
        form.reset();
      }, 1800);
    });
  }

  // 3. Add a subtle entrance offset to story / feature / cat / team cards
  //    so the page feels alive on first paint.
  const animatedCards = document.querySelectorAll(
    '.story-card, .feature-card, .related-card, .cat-card, .team-card, .archive-row'
  );
  if ('IntersectionObserver' in window && animatedCards.length) {
    animatedCards.forEach(function (c, i) {
      c.style.opacity = '0';
      c.style.transform = 'translateY(12px)';
      c.style.transition = 'opacity 480ms ease ' + Math.min(i * 60, 300) + 'ms, transform 480ms ease ' + Math.min(i * 60, 300) + 'ms';
    });

    const io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });

    animatedCards.forEach(function (c) { io.observe(c); });
  }
})();
