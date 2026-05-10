/* Lava Mouth — visual orchestration */

(function () {
  'use strict';

  /* ------------------ Mobile nav toggle ------------------ */
  const menuToggle = document.querySelector('.menu-toggle');
  const navLinks = document.querySelector('.nav-links');
  if (menuToggle && navLinks) {
    menuToggle.addEventListener('click', () => {
      navLinks.classList.toggle('open');
    });
  }

  /* ------------------ Generic scroll reveal ------------------ */
  const revealTargets = document.querySelectorAll(
    '.reveal, .reveal-stagger, .reveal-scale'
  );
  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('in');
          revealObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15, rootMargin: '0px 0px -60px 0px' }
  );
  revealTargets.forEach((el) => revealObserver.observe(el));

  /* ------------------ Section-level "in" flag (for sections needing nested anims) ------------------ */
  const sectionFlagTargets = document.querySelectorAll('[data-trigger="section"]');
  const sectionObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('in');
          sectionObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.25 }
  );
  sectionFlagTargets.forEach((el) => sectionObserver.observe(el));

  /* ------------------ Counter animation (stats blocks) ------------------ */
  function animateCounter(el, durationMs) {
    const finalStr = el.getAttribute('data-final') || el.textContent.trim();
    // parse final: extract leading number, suffix, and optional '+' or '%'
    const match = finalStr.match(/^([\d,]+)(.*)$/);
    if (!match) {
      el.textContent = finalStr;
      return;
    }
    const targetNum = parseInt(match[1].replace(/,/g, ''), 10);
    const suffix = match[2] || '';
    const startTime = performance.now();
    const formatter = new Intl.NumberFormat('en-US');
    function tick(now) {
      const t = Math.min(1, (now - startTime) / durationMs);
      const ease = 1 - Math.pow(1 - t, 3); // easeOutCubic
      const current = Math.round(targetNum * ease);
      el.textContent = formatter.format(current) + (t === 1 ? suffix : '');
      if (t < 1) {
        requestAnimationFrame(tick);
      } else {
        el.classList.add('bounce');
        setTimeout(() => el.classList.remove('bounce'), 600);
      }
    }
    requestAnimationFrame(tick);
  }

  const counterGroups = document.querySelectorAll('[data-counter-group]');
  const counterObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('in');
        const nums = entry.target.querySelectorAll('.stat__num, .stockist-stat__num');
        nums.forEach((num, i) => {
          setTimeout(() => {
            num.parentElement.classList.add('in');
            animateCounter(num, 1100);
          }, i * 280);
        });
        counterObserver.unobserve(entry.target);
      });
    },
    { threshold: 0.3 }
  );
  counterGroups.forEach((el) => counterObserver.observe(el));

  /* ------------------ FAQ accordion ------------------ */
  document.querySelectorAll('.faq-item').forEach((item) => {
    const btn = item.querySelector('.faq-item__btn');
    const body = item.querySelector('.faq-item__body');
    if (!btn || !body) return;
    btn.addEventListener('click', () => {
      const isOpen = item.classList.contains('open');
      // close all
      document.querySelectorAll('.faq-item.open').forEach((other) => {
        other.classList.remove('open');
        const b = other.querySelector('.faq-item__body');
        if (b) b.style.maxHeight = '0';
      });
      if (!isOpen) {
        item.classList.add('open');
        body.style.maxHeight = body.scrollHeight + 'px';
      }
    });
  });

  /* ------------------ Map pin staggered entrance + tooltips ------------------ */
  const pins = document.querySelectorAll('.map-pin[data-city]');
  pins.forEach((pin, i) => {
    pin.style.animationDelay = `${0.5 + i * 0.1}s, ${2 + i * 0.2}s`;
  });
  pins.forEach((pin) => {
    const tooltip = document.createElement('div');
    tooltip.className = 'pin-tooltip';
    tooltip.textContent = pin.getAttribute('data-city');
    document.body.appendChild(tooltip);

    function showTooltip(e) {
      const rect = pin.getBoundingClientRect();
      tooltip.style.left = (rect.left + rect.width / 2 + window.scrollX) + 'px';
      tooltip.style.top = (rect.top + window.scrollY - 36) + 'px';
      tooltip.classList.add('show');
    }
    function hideTooltip() {
      tooltip.classList.remove('show');
    }
    pin.addEventListener('mouseenter', showTooltip);
    pin.addEventListener('mouseleave', hideTooltip);
    pin.addEventListener('focus', showTooltip);
    pin.addEventListener('blur', hideTooltip);
  });

  // Inject tooltip styles
  if (document.querySelector('.map-pin[data-city]')) {
    const style = document.createElement('style');
    style.textContent = `
      .pin-tooltip {
        position: absolute;
        background: #1A1209;
        color: #FFF5E1;
        font-family: 'Permanent Marker', cursive;
        font-size: 12px;
        padding: 4px 10px;
        border-radius: 6px;
        border: 2px solid #FFD600;
        pointer-events: none;
        transform: translate(-50%, 0) scale(0);
        transition: transform 0.2s cubic-bezier(.2,.9,.3,1.4);
        z-index: 1000;
        white-space: nowrap;
      }
      .pin-tooltip.show { transform: translate(-50%, 0) scale(1); }
    `;
    document.head.appendChild(style);
  }

  /* ------------------ Confetti random placement helper ------------------ */
  // For pages that include .auto-confetti containers
  document.querySelectorAll('[data-confetti-canvas]').forEach((canvas) => {
    const positions = canvas.querySelectorAll('.confetti');
    // already positioned via inline style; keep as-is
  });

})();
