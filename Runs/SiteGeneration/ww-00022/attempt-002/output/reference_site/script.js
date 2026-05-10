// BoltWorks — minimal visual-only JS
(function () {
  // 1) Mark current nav link as active by matching pathname
  const path = (location.pathname.split('/').pop() || 'index.html').toLowerCase();
  const slugMap = {
    'index.html': 'home',
    '': 'home',
    'about.html': 'about',
    'departments.html': 'departments',
    'research.html': 'research',
    'contact.html': 'contact'
  };
  const currentSlug = slugMap[path] || 'home';
  document.querySelectorAll('.nav-links a[data-slug]').forEach(function (a) {
    if (a.getAttribute('data-slug') === currentSlug) a.classList.add('is-active');
  });

  // 2) Form submit visual feedback (no backend) — prevent default and flash button
  const form = document.querySelector('.contact-form');
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      const btn = form.querySelector('.submit-bar');
      const originalText = btn.textContent;
      btn.textContent = 'MESSAGE QUEUED ⚡';
      btn.disabled = true;
      setTimeout(function () {
        btn.textContent = originalText;
        btn.disabled = false;
        form.reset();
      }, 2200);
    });
  }

  // 3) Subtle parallax for hero illustrations on desktop
  const heroArt = document.querySelector('.home-hero__art .art-bleed');
  if (heroArt && window.matchMedia('(min-width: 960px)').matches) {
    window.addEventListener('scroll', function () {
      const y = window.scrollY;
      if (y < 800) {
        heroArt.style.transform = 'translateY(' + (y * 0.04) + 'px)';
      }
    }, { passive: true });
  }
})();
