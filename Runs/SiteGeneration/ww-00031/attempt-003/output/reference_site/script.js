/* Inkwell Jazz Festival — motion orchestration */

(function () {
  'use strict';

  // ---------- IntersectionObserver for .reveal elements ----------
  const revealEls = document.querySelectorAll('.reveal, [data-reveal]');
  if ('IntersectionObserver' in window && revealEls.length) {
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.18, rootMargin: '0px 0px -8% 0px' }
    );
    revealEls.forEach((el) => io.observe(el));
  } else {
    revealEls.forEach((el) => el.classList.add('is-visible'));
  }

  // ---------- Section-aware observers for atmospheric ghost & map labels ----------
  const atmosphere = document.querySelector('.atmosphere');
  if (atmosphere && 'IntersectionObserver' in window) {
    const aio = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            atmosphere.classList.add('is-visible');
            aio.unobserve(atmosphere);
          }
        });
      },
      { threshold: 0.25 }
    );
    aio.observe(atmosphere);
  }

  // Map labels staggered reveal
  const mapCanvas = document.querySelector('.map-canvas');
  if (mapCanvas && 'IntersectionObserver' in window) {
    const mio = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            mapCanvas.classList.add('is-visible');
            const labels = mapCanvas.querySelectorAll('[data-map-label]');
            labels.forEach((label, i) => {
              setTimeout(() => label.classList.add('is-visible'), 800 + i * 220);
            });
            mio.unobserve(mapCanvas);
          }
        });
      },
      { threshold: 0.25 }
    );
    mio.observe(mapCanvas);
  }

  // Wristband signature settle
  const wristband = document.querySelector('.wristband-art');
  if (wristband && 'IntersectionObserver' in window) {
    const wio = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setTimeout(() => wristband.classList.add('is-visible'), 120);
            wio.unobserve(wristband);
          }
        });
      },
      { threshold: 0.2 }
    );
    wio.observe(wristband);
  }

  // Final CTA stars
  const finalStars = document.querySelector('.final-cta-stars');
  if (finalStars && 'IntersectionObserver' in window) {
    const sio = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            finalStars.classList.add('is-visible');
            sio.unobserve(finalStars);
          }
        });
      },
      { threshold: 0.2 }
    );
    sio.observe(finalStars);
  }

  // ---------- Atmospheric ghost-text parallax ----------
  const atmosphereSection = document.querySelector('.atmosphere');
  if (atmosphereSection) {
    let ticking = false;
    const onScroll = () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          const rect = atmosphereSection.getBoundingClientRect();
          const progress = 1 - rect.top / window.innerHeight;
          // The ghost text moves up at half the scroll speed
          const offset = Math.max(-80, Math.min(80, progress * -40));
          atmosphereSection.style.setProperty('--ghost-offset', offset + 'px');
          atmosphereSection.style.setProperty(
            'background-position-y',
            offset + 'px'
          );
          ticking = false;
        });
        ticking = true;
      }
    };
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  // ---------- FAQ accordion ----------
  const faqTriggers = document.querySelectorAll('.faq-item .trigger');
  faqTriggers.forEach((trigger) => {
    trigger.addEventListener('click', () => {
      const item = trigger.closest('.faq-item');
      const isOpen = item.getAttribute('data-open') === 'true';
      // Close all
      document.querySelectorAll('.faq-item[data-open="true"]').forEach((el) => {
        el.setAttribute('data-open', 'false');
        el.querySelector('.trigger').setAttribute('aria-expanded', 'false');
      });
      if (!isOpen) {
        item.setAttribute('data-open', 'true');
        trigger.setAttribute('aria-expanded', 'true');
      }
    });
  });

  // ---------- Page header word reveal ----------
  const wordReveals = document.querySelectorAll('.word-reveal');
  wordReveals.forEach((node) => {
    if (node.dataset.split === 'true') return;
    const text = node.textContent.trim();
    const words = text.split(/(\s+)/);
    node.textContent = '';
    let delay = 0;
    words.forEach((w) => {
      if (w.match(/^\s+$/)) {
        node.appendChild(document.createTextNode(w));
      } else {
        const span = document.createElement('span');
        span.className = 'word';
        span.textContent = w;
        span.style.animationDelay = delay + 'ms';
        node.appendChild(span);
        delay += 110;
      }
    });
    node.dataset.split = 'true';
  });

  // ---------- Marquee seamless ----------
  // The CSS marquee already animates the .marquee-track from 0 to -50% with the
  // duplicated content; nothing to compute. We just pause on hover via CSS.

  // ---------- Lineup illustrated bg fallback parallax ----------
  const lineupBg = document.querySelector('.lineup-hero .bg-svg');
  if (lineupBg) {
    let ticking = false;
    window.addEventListener(
      'scroll',
      () => {
        if (!ticking) {
          requestAnimationFrame(() => {
            const y = window.scrollY;
            lineupBg.style.transform = `translateY(${Math.min(40, y * 0.18)}px)`;
            ticking = false;
          });
          ticking = true;
        }
      },
      { passive: true }
    );
  }

  // ---------- Active nav link ----------
  const slug = document.body.dataset.pageSlug;
  if (slug) {
    document.querySelectorAll('.nav-links a[data-link]').forEach((link) => {
      if (link.dataset.link === slug) link.classList.add('active');
    });
  }
})();
