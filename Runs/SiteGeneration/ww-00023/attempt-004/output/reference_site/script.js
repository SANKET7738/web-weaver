// Pixelwave — visual-only behavior

(function () {
  // Animated chrome shimmer on .hero__line2 (cycles gradient position)
  const heroLine = document.querySelector('.hero__line2');
  if (heroLine) {
    let pos = 0;
    setInterval(() => {
      pos = (pos + 1) % 200;
      const offset = pos - 100;
      heroLine.style.backgroundImage = `linear-gradient(${90 + offset * 0.6}deg, #7EC8F0 0%, #F0F4FF 50%, #B8A0E8 100%)`;
    }, 80);
  }

  // Subtle parallax on archive starburst spine
  const spine = document.querySelector('.archive-header__starburst-spine');
  if (spine) {
    window.addEventListener('scroll', () => {
      const y = Math.min(window.scrollY, 400);
      spine.style.transform = `translateY(${y * 0.18}px)`;
    }, { passive: true });
  }

  // Subscribe form: visual confirmation only (no backend)
  const subForm = document.querySelector('.subscribe-form');
  if (subForm) {
    subForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const btn = subForm.querySelector('.subscribe-form__btn');
      if (!btn) return;
      const original = btn.textContent;
      btn.textContent = 'Subscribed';
      btn.style.background = '#CC00AA';
      setTimeout(() => {
        btn.textContent = original;
        btn.style.background = '';
      }, 1800);
    });
  }
})();
