/* ============================================================
   LAVA MOUTH — site behavior + animation orchestration
   ============================================================ */
(function () {
  'use strict';

  // ----------------------------------------------------------
  // 1) Generic IntersectionObserver — applies .in to elements
  //    that opt into reveals with .reveal / .reveal-left / etc.
  // ----------------------------------------------------------
  const revealSelectors = '.reveal, .reveal-left, .reveal-right, .reveal-scale, .fade-up';

  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const el = entry.target;
        const delay = parseFloat(el.dataset.delay || '0');
        if (delay > 0) {
          setTimeout(() => el.classList.add('in'), delay);
        } else {
          el.classList.add('in');
        }
        revealObserver.unobserve(el);
      }
    });
  }, { threshold: 0.15, rootMargin: '0px 0px -8% 0px' });

  function registerReveals(root = document) {
    root.querySelectorAll(revealSelectors).forEach((el) => revealObserver.observe(el));
  }

  // ----------------------------------------------------------
  // 2) Section-level "in" flag — toggles .in on whole sections
  //    so descendant CSS rules can drive coordinated motion.
  // ----------------------------------------------------------
  const sectionObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('in');
        // Stagger children if requested
        const stagger = entry.target.querySelector('[data-stagger]');
        if (stagger) {
          stagger.querySelectorAll(':scope > *').forEach((child, i) => {
            child.style.transitionDelay = (i * 0.12) + 's';
            child.classList.add('in');
          });
        }
        sectionObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });

  function registerSectionFlags(root = document) {
    root.querySelectorAll('[data-section-flag]').forEach((el) => sectionObserver.observe(el));
  }

  // ----------------------------------------------------------
  // 3) Hero word-by-word headline arrival
  // ----------------------------------------------------------
  function animateHeroWords() {
    const wordsContainers = document.querySelectorAll('[data-headline-words]');
    wordsContainers.forEach((container, ci) => {
      const words = container.querySelectorAll('.word');
      words.forEach((w, i) => {
        const base = parseFloat(container.dataset.startDelay || '0.3');
        w.style.transition = 'opacity .6s ease, transform .6s cubic-bezier(.2,1.4,.4,1)';
        setTimeout(() => {
          w.style.opacity = '1';
          w.style.transform = 'translateY(0)';
        }, (base + i * 0.12) * 1000);
      });
    });
  }

  // ----------------------------------------------------------
  // 4) Count-up animation for stat numerals
  // ----------------------------------------------------------
  function parseStatTarget(str) {
    // Extract number and remember formatting
    const match = str.match(/(\d[\d,]*)(.*)/);
    if (!match) return { value: 0, suffix: '', formatComma: false };
    const numStr = match[1].replace(/,/g, '');
    return {
      value: parseInt(numStr, 10),
      suffix: match[2],
      formatComma: match[1].includes(','),
    };
  }
  function formatNumber(n, withComma) {
    if (withComma) return n.toLocaleString('en-US');
    return String(n);
  }

  function easeOutCubic(t) { return 1 - Math.pow(1 - t, 3); }

  function animateCounter(el, parsed, duration = 1000, onDone) {
    const start = performance.now();
    function tick(now) {
      const elapsed = now - start;
      const t = Math.min(1, elapsed / duration);
      const e = easeOutCubic(t);
      const value = Math.round(parsed.value * e);
      el.textContent = formatNumber(value, parsed.formatComma) + parsed.suffix;
      if (t < 1) {
        requestAnimationFrame(tick);
      } else {
        el.classList.add('bounce');
        setTimeout(() => el.classList.remove('bounce'), 420);
        if (onDone) onDone();
      }
    }
    requestAnimationFrame(tick);
  }

  function setupStatCounters() {
    const groups = document.querySelectorAll('[data-counter-group]');
    if (!groups.length) return;

    const obs = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const group = entry.target;
        const blocks = group.querySelectorAll('.stat-block');
        blocks.forEach((block, i) => {
          const numEl = block.querySelector('.num');
          if (!numEl) return;
          const target = numEl.dataset.target || numEl.textContent.trim();
          const parsed = parseStatTarget(target);
          // Start at 0 with formatted suffix preserved
          numEl.textContent = '0' + parsed.suffix;
          setTimeout(() => {
            animateCounter(numEl, parsed, 1000, () => {
              block.classList.add('in');
            });
          }, i * 220);
        });
        obs.unobserve(group);
      });
    }, { threshold: 0.4 });

    groups.forEach((g) => obs.observe(g));
  }

  // ----------------------------------------------------------
  // 5) Heat bar ignition (products page)
  // ----------------------------------------------------------
  function setupHeatBar() {
    const chart = document.querySelector('.heat-chart');
    if (!chart) return;
    const flames = chart.querySelectorAll('.heat-flame');
    const obs = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        chart.classList.add('in');
        flames.forEach((f, i) => {
          setTimeout(() => f.classList.add('pop'), 250 + i * 200);
        });
        obs.unobserve(chart);
      });
    }, { threshold: 0.3 });
    obs.observe(chart);
  }

  // ----------------------------------------------------------
  // 6) Map pins (stockists page) staggered pop-in + hover tooltip
  // ----------------------------------------------------------
  function setupMapPins() {
    const map = document.querySelector('.us-map-wrap');
    if (!map) return;
    const pins = map.querySelectorAll('.map-pin');
    const order = Array.from(pins).map((p, i) => ({
      el: p,
      delay: parseInt(p.dataset.delay || (i * 80), 10),
    }));
    // Trigger on initial mount (header in-view)
    const obs = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        order.forEach(({ el, delay }) => {
          setTimeout(() => el.classList.add('pop-in'), delay);
        });
        obs.unobserve(map);
      });
    }, { threshold: 0.1 });
    obs.observe(map);

    // Tooltip for each pin
    pins.forEach((pin) => {
      const city = pin.dataset.city;
      if (!city) return;
      pin.addEventListener('mouseenter', () => {
        let label = pin.querySelector('.pin-tooltip');
        if (!label) {
          label = document.createElementNS('http://www.w3.org/2000/svg', 'g');
          label.setAttribute('class', 'pin-tooltip');
          const x = parseFloat(pin.dataset.tooltipX || pin.getAttribute('data-x') || '0');
          const y = parseFloat(pin.dataset.tooltipY || pin.getAttribute('data-y') || '0');
          const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
          bg.setAttribute('x', x - 36);
          bg.setAttribute('y', y - 32);
          bg.setAttribute('width', 72);
          bg.setAttribute('height', 22);
          bg.setAttribute('rx', 4);
          bg.setAttribute('fill', '#FFD600');
          bg.setAttribute('stroke', '#1A1209');
          bg.setAttribute('stroke-width', 1.5);
          const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
          text.setAttribute('x', x);
          text.setAttribute('y', y - 17);
          text.setAttribute('text-anchor', 'middle');
          text.setAttribute('font-family', 'Permanent Marker, cursive');
          text.setAttribute('font-size', '11');
          text.setAttribute('fill', '#1A1209');
          text.textContent = city;
          label.appendChild(bg);
          label.appendChild(text);
          pin.appendChild(label);
        }
      });
      pin.addEventListener('mouseleave', () => {
        const t = pin.querySelector('.pin-tooltip');
        if (t) t.remove();
      });
    });
  }

  // ----------------------------------------------------------
  // 7) FAQ accordion (contact page)
  // ----------------------------------------------------------
  function setupFaq() {
    const rows = document.querySelectorAll('.faq-row');
    rows.forEach((row) => {
      const btn = row.querySelector('.faq-question');
      if (!btn) return;
      btn.addEventListener('click', () => {
        const wasOpen = row.classList.contains('open');
        rows.forEach((r) => r.classList.remove('open'));
        if (!wasOpen) row.classList.add('open');
      });
    });
  }

  // ----------------------------------------------------------
  // 8) Pull-stripe & Squiggle reveal (story-section-4)
  // ----------------------------------------------------------
  function setupPullStripe() {
    const stripes = document.querySelectorAll('.pull-stripe');
    if (!stripes.length) return;
    const obs = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('in');
          obs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.3 });
    stripes.forEach((s) => obs.observe(s));
  }

  // ----------------------------------------------------------
  // 9) Contact form: prevent default submit & flash feedback
  // ----------------------------------------------------------
  function setupContactForm() {
    const form = document.querySelector('.contact-form');
    if (!form) return;
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const submitBtn = form.querySelector('.submit');
      if (!submitBtn) return;
      const original = submitBtn.textContent;
      submitBtn.textContent = 'Thanks! Got it.';
      submitBtn.style.background = 'var(--green)';
      submitBtn.disabled = true;
      setTimeout(() => {
        submitBtn.textContent = original;
        submitBtn.style.background = '';
        submitBtn.disabled = false;
        form.reset();
      }, 2400);
    });
  }

  // ----------------------------------------------------------
  // 10) Hero memphis-shape scatter (home page) — applies entry vars
  // ----------------------------------------------------------
  function setupShapeScatter() {
    document.querySelectorAll('[data-scatter]').forEach((el, i) => {
      const dx = (Math.random() * 60 - 30) + 'px';
      const dy = (Math.random() * 60 - 30) + 'px';
      el.style.setProperty('--x', dx);
      el.style.setProperty('--y', dy);
      el.style.animationDelay = (0.1 + i * 0.08) + 's';
    });
    document.querySelectorAll('.confetti-piece').forEach((el, i) => {
      const bx = (Math.random() * 80 - 40) + 'px';
      const by = (Math.random() * 80 - 40) + 'px';
      el.style.setProperty('--bx', bx);
      el.style.setProperty('--by', by);
      el.style.animationDelay = (0.1 + i * 0.07) + 's';
    });
  }

  // ----------------------------------------------------------
  // 11) Boot
  // ----------------------------------------------------------
  function boot() {
    registerReveals();
    registerSectionFlags();
    animateHeroWords();
    setupStatCounters();
    setupHeatBar();
    setupMapPins();
    setupFaq();
    setupPullStripe();
    setupContactForm();
    setupShapeScatter();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
