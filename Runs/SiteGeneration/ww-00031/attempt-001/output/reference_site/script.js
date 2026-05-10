/* Inkwell Jazz Festival — scroll reveals, parallax, accordion, map labels */

(function () {
  'use strict';

  /* ---- Reveal on scroll ---- */
  const reveals = document.querySelectorAll('.reveal, .stagger, .dark-story, .pricing-section');
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-in');
            entry.target.classList.add('is-visible');
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.18, rootMargin: '0px 0px -8% 0px' }
    );
    reveals.forEach((el) => io.observe(el));
  } else {
    reveals.forEach((el) => { el.classList.add('is-in'); el.classList.add('is-visible'); });
  }

  /* ---- Parallax for ghost text on Experience story ---- */
  const ghost = document.querySelector('.ghost-text');
  if (ghost) {
    let raf = null;
    const update = () => {
      const rect = ghost.parentElement.getBoundingClientRect();
      const viewport = window.innerHeight;
      const progress = (viewport - rect.top) / (viewport + rect.height);
      const shift = (progress - 0.5) * -60;
      ghost.style.transform = `translate(0, calc(-45% + ${shift}px))`;
      raf = null;
    };
    window.addEventListener('scroll', () => {
      if (!raf) raf = requestAnimationFrame(update);
    }, { passive: true });
    update();
  }

  /* ---- Lineup poster background parallax ---- */
  const poster = document.querySelector('.poster-bg');
  if (poster) {
    let raf = null;
    const update = () => {
      const rect = poster.getBoundingClientRect();
      const progress = rect.top / window.innerHeight;
      const shift = progress * -20;
      poster.style.transform = `translateY(${shift}px)`;
      raf = null;
    };
    window.addEventListener('scroll', () => {
      if (!raf) raf = requestAnimationFrame(update);
    }, { passive: true });
  }

  /* ---- FAQ accordion ---- */
  const faqs = document.querySelectorAll('.faq-item');
  faqs.forEach((item) => {
    const trigger = item.querySelector('.faq-trigger');
    const body = item.querySelector('.faq-body');
    if (!trigger || !body) return;
    trigger.addEventListener('click', () => {
      const isOpen = item.classList.toggle('is-open');
      if (isOpen) {
        body.style.maxHeight = body.scrollHeight + 'px';
        trigger.setAttribute('aria-expanded', 'true');
      } else {
        body.style.maxHeight = '0px';
        trigger.setAttribute('aria-expanded', 'false');
      }
    });
  });

  /* ---- Map label stagger pop-in ---- */
  const mapBlock = document.querySelector('.map-block');
  if (mapBlock) {
    const labels = mapBlock.querySelectorAll('.map-label-anim');
    if ('IntersectionObserver' in window && labels.length) {
      const mIO = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              labels.forEach((label, i) => {
                setTimeout(() => label.classList.add('is-shown'), 700 + i * 110);
              });
              mIO.unobserve(entry.target);
            }
          });
        },
        { threshold: 0.32 }
      );
      mIO.observe(mapBlock);
    } else {
      labels.forEach((l) => l.classList.add('is-shown'));
    }
  }

  /* ---- Nav: mark current page ---- */
  const slug = document.body.getAttribute('data-page-slug');
  document.querySelectorAll('.nav-links a').forEach((a) => {
    const href = a.getAttribute('href') || '';
    if (
      (slug === 'home' && (href === 'index.html' || href === './' || href === '/')) ||
      href.startsWith(slug + '.html')
    ) {
      a.classList.add('is-current');
    }
  });
})();
