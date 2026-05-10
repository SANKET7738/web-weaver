/* ===========================================================
   LAVA MOUTH — site behavior & motion orchestration
=========================================================== */

(function () {
  'use strict';

  // ---------- Scroll-triggered reveals ----------
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('in');
          // Don't unobserve elements that need staggered children re-reveal? Just unobserve.
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15, rootMargin: '0px 0px -60px 0px' }
  );

  document
    .querySelectorAll('.reveal, .stagger, .timeline-block, .dani, .heat-bar, .stats-yellow__rule, .wholesale__strip')
    .forEach((el) => observer.observe(el));

  // ---------- Hero word-by-word reveal (for story headers) ----------
  document.querySelectorAll('[data-words]').forEach((el) => {
    const text = el.textContent.trim();
    el.textContent = '';
    text.split(' ').forEach((w, i) => {
      const s = document.createElement('span');
      s.className = 'word';
      s.style.marginRight = '0.25em';
      s.textContent = w;
      el.appendChild(s);
      // staggered reveal
      setTimeout(() => s.classList.add('in'), 250 + i * 80);
    });
  });

  // ---------- Stats counter animation (signature moment) ----------
  function animateCount(el, target, duration, suffix, prefix) {
    suffix = suffix || '';
    prefix = prefix || '';
    const start = 0;
    const startTime = performance.now();
    function step(now) {
      const t = Math.min(1, (now - startTime) / duration);
      const eased = 1 - Math.pow(1 - t, 3); // ease-out cubic
      const v = Math.floor(start + (target - start) * eased);
      el.textContent = prefix + formatNum(v) + suffix;
      if (t < 1) {
        requestAnimationFrame(step);
      } else {
        el.textContent = prefix + formatNum(target) + suffix;
        el.classList.add('bounce');
        setTimeout(() => el.classList.remove('bounce'), 260);
      }
    }
    requestAnimationFrame(step);
  }
  function formatNum(n) {
    return n.toLocaleString('en-US');
  }

  const statsObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const nums = entry.target.querySelectorAll('[data-count]');
          nums.forEach((el, i) => {
            const raw = el.getAttribute('data-count');
            const suffix = el.getAttribute('data-suffix') || '';
            const target = parseInt(raw, 10);
            setTimeout(() => {
              animateCount(el, target, 1000, suffix);
            }, i * 280);
          });
          statsObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.35 }
  );
  document.querySelectorAll('[data-counter-group]').forEach((g) => statsObserver.observe(g));

  // ---------- Marquee duplication for seamless loop ----------
  document.querySelectorAll('.marquee__track').forEach((track) => {
    track.innerHTML = track.innerHTML + track.innerHTML;
  });

  // ---------- Heat bar ignition (products page signature) ----------
  // Bars start with cream cover at scaleX(1); adding .ignite collapses cover to scaleX(0), revealing the gradient
  const heatObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const bar = entry.target;
          bar.classList.add('ignite');
          const nodes = bar.querySelectorAll('.heat-bar__node');
          nodes.forEach((node, i) => {
            setTimeout(() => node.classList.add('lit'), 250 + i * 220);
          });
          heatObserver.unobserve(bar);
        }
      });
    },
    { threshold: 0.3 }
  );
  document.querySelectorAll('.heat-bar').forEach((bar) => heatObserver.observe(bar));

  // ---------- Confetti burst on CTA close ----------
  const confettiObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const shapes = entry.target.querySelectorAll('.confetti-shape');
          shapes.forEach((s, i) => {
            setTimeout(() => s.classList.add('show'), i * 60);
          });
          confettiObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.2 }
  );
  document.querySelectorAll('[data-confetti-burst]').forEach((el) => confettiObserver.observe(el));

  // ---------- Map pin staggered pop ----------
  document.querySelectorAll('.map-pin').forEach((pin, i) => {
    // staggered using --d CSS variable
    pin.style.setProperty('--d', 0.6 + i * 0.08 + 's');
  });

  // ---------- Contact header decorative shape pop ----------
  const contactHeaderObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const shapes = entry.target.querySelectorAll('.cs-shape');
          shapes.forEach((s, i) => {
            setTimeout(() => s.classList.add('in'), 600 + i * 100);
          });
          contactHeaderObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.1 }
  );
  document.querySelectorAll('[data-shape-burst]').forEach((el) => contactHeaderObserver.observe(el));

  // ---------- Philosophy stripe wipe ----------
  const stripeObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('draw');
          stripeObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.3 }
  );
  document.querySelectorAll('.philosophy__stripe').forEach((s) => stripeObserver.observe(s));

  // ---------- FAQ Accordion ----------
  document.querySelectorAll('.faq-item').forEach((item) => {
    const btn = item.querySelector('.faq-item__q');
    if (!btn) return;
    btn.addEventListener('click', () => {
      const isOpen = item.classList.contains('open');
      // close all
      document.querySelectorAll('.faq-item.open').forEach((o) => o.classList.remove('open'));
      if (!isOpen) item.classList.add('open');
    });
  });

  // ---------- Form: prevent default submit (visual only) ----------
  document.querySelectorAll('form[data-visual-only]').forEach((form) => {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const btn = form.querySelector('button[type="submit"]');
      if (!btn) return;
      const original = btn.textContent;
      btn.textContent = 'Sent! 🔥';
      btn.style.background = 'var(--teal)';
      btn.style.color = 'var(--cream)';
      setTimeout(() => {
        btn.textContent = original;
        btn.style.background = '';
        btn.style.color = '';
        form.reset();
      }, 2500);
    });
  });

  // ---------- Hero parallax for memphis shapes ----------
  const heroShapes = document.querySelectorAll('.hero__shape');
  if (heroShapes.length) {
    let ticking = false;
    window.addEventListener('scroll', () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          const y = window.scrollY;
          heroShapes.forEach((s, i) => {
            const speed = (i % 3) * 0.05 + 0.05;
            s.style.translate = `0 ${y * speed * -1}px`;
          });
          ticking = false;
        });
        ticking = true;
      }
    });
  }

  // ---------- Stats yellow rule extend ----------
  document.querySelectorAll('.stats-yellow__rule').forEach((r) => {
    const ruleObs = new IntersectionObserver(
      (es) => {
        es.forEach((e) => {
          if (e.isIntersecting) {
            r.classList.add('in');
            ruleObs.unobserve(r);
          }
        });
      },
      { threshold: 0.4 }
    );
    ruleObs.observe(r);
  });

  // ---------- Wholesale strip slide-in ----------
  document.querySelectorAll('.wholesale__strip').forEach((s) => {
    const o = new IntersectionObserver(
      (es) => {
        es.forEach((e) => {
          if (e.isIntersecting) {
            s.classList.add('in');
            o.unobserve(s);
          }
        });
      },
      { threshold: 0.2 }
    );
    o.observe(s);
  });
})();
