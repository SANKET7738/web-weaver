/* Axiom Hotel — visual-only enhancements */

(function () {
  'use strict';

  // Mobile nav toggle: simple show/hide of the .nav-links list
  const toggle = document.querySelector('.nav-toggle');
  const links = document.querySelector('.nav-links');
  if (toggle && links) {
    toggle.addEventListener('click', () => {
      const open = links.classList.toggle('is-open');
      toggle.textContent = open ? 'Close' : 'Menu';
      if (open) {
        links.style.display = 'flex';
        links.style.flexDirection = 'column';
        links.style.position = 'absolute';
        links.style.top = '72px';
        links.style.left = '0';
        links.style.right = '0';
        links.style.background = 'var(--c-void)';
        links.style.borderBottom = '1px solid var(--c-graphite)';
        links.style.padding = '24px';
        links.style.gap = '20px';
        links.style.zIndex = '99';
      } else {
        links.removeAttribute('style');
      }
    });
  }

  // Reveal-on-scroll: add .is-visible to sections / cards when they enter the viewport
  const revealTargets = document.querySelectorAll(
    '.feature-card, .room-card, .price-card, .article-row, .channel-card, .index-row, .location-cell'
  );

  if ('IntersectionObserver' in window && revealTargets.length) {
    revealTargets.forEach((el) => {
      el.style.opacity = '0';
      el.style.transform = 'translateY(12px)';
      el.style.transition = 'opacity 600ms cubic-bezier(0.4,0,0.2,1), transform 600ms cubic-bezier(0.4,0,0.2,1)';
    });

    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry, i) => {
          if (entry.isIntersecting) {
            const el = entry.target;
            const delay = (i % 4) * 60;
            setTimeout(() => {
              el.style.opacity = '1';
              el.style.transform = 'translateY(0)';
            }, delay);
            io.unobserve(el);
          }
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
    );

    revealTargets.forEach((el) => io.observe(el));
  }

  // Subtle parallax for hero pattern
  const heroPattern = document.querySelector('.hero-pattern');
  if (heroPattern && window.matchMedia('(min-width: 900px)').matches) {
    let ticking = false;
    const onScroll = () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          const y = Math.min(window.scrollY, 800);
          heroPattern.style.transform = `translateY(${y * 0.15}px)`;
          ticking = false;
        });
        ticking = true;
      }
    };
    window.addEventListener('scroll', onScroll, { passive: true });
  }
})();
