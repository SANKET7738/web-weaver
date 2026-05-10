/* ============================================================
   BRUTALK — Motion orchestration & visual interactions
   ============================================================ */

(function () {
  'use strict';

  /* ---------- IntersectionObserver helpers ---------- */
  function makeObserver(callback, options) {
    return new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          callback(entry.target);
          observer.unobserve(entry.target);
        }
      });
    }, options || { threshold: 0.15, rootMargin: '0px 0px -80px 0px' });
  }

  /* ---------- Generic reveal-on-scroll (.reveal items) ---------- */
  function setupBasicReveals() {
    const observer = makeObserver((el) => {
      el.classList.add('is-in');
    });
    document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
  }

  /* ---------- Staggered child reveals ---------- */
  function setupStaggers() {
    const observer = makeObserver((container) => {
      const children = container.querySelectorAll('[data-stagger-child]');
      const baseDelay = parseInt(container.dataset.staggerStart || '0', 10);
      const step = parseInt(container.dataset.staggerStep || '80', 10);
      children.forEach((child, i) => {
        setTimeout(() => child.classList.add('is-in'), baseDelay + i * step);
      });
    });
    document.querySelectorAll('[data-stagger]').forEach(c => observer.observe(c));
  }

  /* ---------- Home hero on-load sequence ---------- */
  function setupHeroIntro() {
    const hero = document.querySelector('[data-hero-intro]');
    if (!hero) return;

    const logo = hero.querySelector('.hero-logo');
    const eyebrow = hero.querySelector('.hero-eyebrow');
    const lines = hero.querySelectorAll('.hero-h1-line');
    const subEl = hero.querySelector('.hero-sub');
    const ctas = hero.querySelector('.hero-ctas');
    const fullText = subEl ? (subEl.dataset.text || subEl.textContent.trim()) : '';

    if (subEl) {
      subEl.innerHTML = '<span class="typed"></span><span class="cursor">|</span>';
    }

    const timeline = [
      [80, () => logo && logo.classList.add('is-in')],
      [340, () => eyebrow && eyebrow.classList.add('is-in')],
      [520, () => lines[0] && lines[0].classList.add('is-in')],
      [780, () => lines[1] && lines[1].classList.add('is-in')],
      [1040, () => lines[2] && lines[2].classList.add('is-in')],
    ];
    timeline.forEach(([t, fn]) => setTimeout(fn, t));

    // type-in subheadline
    if (subEl && fullText) {
      const typedEl = subEl.querySelector('.typed');
      const cursorEl = subEl.querySelector('.cursor');
      let i = 0;
      setTimeout(function type() {
        if (i <= fullText.length) {
          typedEl.textContent = fullText.slice(0, i);
          i++;
          setTimeout(type, 22);
        } else {
          setTimeout(() => cursorEl && cursorEl.classList.add('hidden'), 600);
          setTimeout(() => ctas && ctas.classList.add('is-in'), 200);
        }
      }, 1500);
    }
  }

  /* ---------- Marquee duplication for seamless loop ---------- */
  function setupMarquee() {
    document.querySelectorAll('[data-marquee]').forEach(track => {
      const html = track.innerHTML;
      track.innerHTML = html + html;
    });
  }

  /* ---------- CTA-close section: hard color cut + headline slam ---------- */
  function setupCtaClose() {
    const observer = makeObserver((el) => {
      el.classList.add('is-in');
    }, { threshold: 0.25 });
    document.querySelectorAll('[data-cta-close]').forEach(el => observer.observe(el));
  }

  /* ---------- Page header lines (drop in from above) ---------- */
  function setupPhHeader() {
    const ph = document.querySelector('[data-ph-intro]');
    if (!ph) return;
    const lines = ph.querySelectorAll('.ph-h1-line');
    const sub = ph.querySelector('.ph-sub');
    const illo = ph.querySelector('.ph-illo');
    const bleed = ph.querySelector('.bleed-word');

    setTimeout(() => lines[0] && lines[0].classList.add('is-in'), 240);
    setTimeout(() => lines[1] && lines[1].classList.add('is-in'), 480);
    setTimeout(() => {
      if (lines[2]) lines[2].classList.add('is-in');
      if (bleed) {
        setTimeout(() => bleed.classList.add('slam'), 80);
      }
    }, 720);
    setTimeout(() => sub && sub.classList.add('is-in'), 1100);
    setTimeout(() => illo && illo.classList.add('is-in'), 1200);
  }

  /* ---------- Classes comparison rule + row cascade ---------- */
  function setupCompare() {
    const sec = document.querySelector('[data-compare]');
    if (!sec) return;
    const rule = sec.querySelector('.compare-rule');
    const rows = sec.querySelectorAll('.compare-row');

    const obs = makeObserver(() => {
      if (rule) rule.classList.add('is-in');
      rows.forEach((row, i) => {
        setTimeout(() => row.classList.add('is-in'), 320 + i * 140);
      });
    }, { threshold: 0.1 });
    obs.observe(sec);
  }

  /* ---------- FAQ accordions ---------- */
  function setupFaq() {
    document.querySelectorAll('.faq-q').forEach(btn => {
      btn.addEventListener('click', () => {
        const item = btn.closest('.faq-item');
        const open = item.classList.contains('is-open');
        item.classList.toggle('is-open', !open);
        btn.setAttribute('aria-expanded', String(!open));
      });
    });
  }

  /* ---------- Schedule signature word + cards reveal ---------- */
  function setupSchedGrid() {
    const sec = document.querySelector('[data-sched-grid]');
    if (!sec) return;
    const word = sec.querySelector('.sched-bg-word');
    const cards = sec.querySelectorAll('.sched-card');

    const obs = makeObserver(() => {
      setTimeout(() => word && word.classList.add('is-in'), 280);
      cards.forEach((card, i) => {
        setTimeout(() => card.classList.add('is-in'), 220 + i * 90);
      });
    }, { threshold: 0.1 });
    obs.observe(sec);
  }

  /* ---------- Schedule header slam ---------- */
  function setupSchedHeader() {
    const h1 = document.querySelector('[data-sched-h1]');
    if (h1) {
      setTimeout(() => h1.classList.add('is-in'), 360);
    }
  }

  /* ---------- Count-up animations ---------- */
  function setupCountUp() {
    const observer = makeObserver((el) => {
      const target = parseFloat(el.dataset.count);
      const decimals = parseInt(el.dataset.decimals || '0', 10);
      const prefix = el.dataset.prefix || '';
      const suffix = el.dataset.suffix || '';
      const duration = parseInt(el.dataset.duration || '1200', 10);
      const startTime = performance.now();

      function tick(now) {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const val = target * progress;
        el.textContent = prefix + val.toFixed(decimals) + suffix;
        if (progress < 1) requestAnimationFrame(tick);
        else el.textContent = prefix + target.toFixed(decimals) + suffix;
      }
      requestAnimationFrame(tick);
    }, { threshold: 0.3 });
    document.querySelectorAll('[data-count]').forEach(el => observer.observe(el));
  }

  /* ---------- Instructors page header sequence ---------- */
  function setupInstrHeader() {
    const sec = document.querySelector('[data-instr-header]');
    if (!sec) return;
    const h1 = sec.querySelector('.instr-h1');
    const sub = sec.querySelector('.instr-sub');
    const numObj = sec.querySelector('.instr-200');

    setTimeout(() => h1 && h1.classList.add('is-in'), 200);
    setTimeout(() => numObj && numObj.classList.add('is-in'), 700);
    setTimeout(() => sub && sub.classList.add('is-in'), 1100);
  }

  /* ---------- Instructors story slide-up ---------- */
  function setupInstrStory() {
    const observer = makeObserver((el) => el.classList.add('is-in'), { threshold: 0.2 });
    document.querySelectorAll('[data-instr-story]').forEach(el => observer.observe(el));
  }

  /* ---------- Timeline reveal ---------- */
  function setupTimeline() {
    const sec = document.querySelector('[data-timeline]');
    if (!sec) return;
    const line = sec.querySelector('.timeline-line');
    const stages = sec.querySelectorAll('.stage');

    const obs = makeObserver(() => {
      if (line) line.classList.add('is-in');
      stages.forEach((stage, i) => {
        setTimeout(() => stage.classList.add('is-in'), 200 + i * 180);
      });
    }, { threshold: 0.2 });
    obs.observe(sec);
  }

  /* ---------- Instructors CTA close ---------- */
  function setupInstrCta() {
    const observer = makeObserver((el) => {
      const h2 = el.querySelector('h2');
      if (h2) h2.classList.add('is-in');
    });
    document.querySelectorAll('[data-instr-cta]').forEach(el => observer.observe(el));
  }

  /* ---------- Instructor card stagger ---------- */
  function setupInstrGrid() {
    const sec = document.querySelector('[data-instr-grid]');
    if (!sec) return;
    const cards = sec.querySelectorAll('.instr-card');
    const obs = makeObserver(() => {
      cards.forEach((card, i) => {
        setTimeout(() => card.classList.add('is-in'), 80 + i * 70);
      });
    }, { threshold: 0.1 });
    obs.observe(sec);
  }

  /* ---------- Pricing header typewriter ---------- */
  function setupPricingHeader() {
    const h1 = document.querySelector('[data-pricing-h1]');
    if (h1) {
      const fullText = h1.dataset.text || h1.textContent.trim();
      h1.innerHTML = '<span class="typed-text"></span><span class="typewriter-cursor">|</span>';
      const typedEl = h1.querySelector('.typed-text');
      let i = 0;
      setTimeout(function type() {
        if (i <= fullText.length) {
          typedEl.textContent = fullText.slice(0, i);
          i++;
          setTimeout(type, 28);
        }
      }, 240);
    }
    const sub = document.querySelector('[data-pricing-sub]');
    const rule = document.querySelector('[data-pricing-rule]');
    if (sub) setTimeout(() => sub.classList.add('is-in'), 1400);
    if (rule) setTimeout(() => rule.classList.add('is-in'), 1800);
  }

  /* ---------- Pricing card stagger + price slam ---------- */
  function setupPricingCards() {
    const sec = document.querySelector('[data-pricing-cards]');
    if (!sec) return;
    const cards = sec.querySelectorAll('.plan');
    const obs = makeObserver(() => {
      cards.forEach((card, i) => {
        setTimeout(() => {
          card.classList.add('is-in');
          const slamPrice = card.querySelector('.plan-price.featured-price');
          if (slamPrice) {
            setTimeout(() => slamPrice.classList.add('slam'), 280);
          }
        }, 180 + i * 200);
      });
    }, { threshold: 0.15 });
    obs.observe(sec);
  }

  /* ---------- Pricing FAQ stagger ---------- */
  function setupPricingFaq() {
    const sec = document.querySelector('[data-pricing-faq]');
    if (!sec) return;
    const items = sec.querySelectorAll('.pfaq-item');
    const obs = makeObserver(() => {
      items.forEach((item, i) => {
        setTimeout(() => item.classList.add('is-in'), 80 + i * 110);
      });
    }, { threshold: 0.1 });
    obs.observe(sec);
  }

  /* ---------- Pricing CTA close ---------- */
  function setupPricingClose() {
    const observer = makeObserver((el) => {
      const h2 = el.querySelector('h2');
      if (h2) h2.classList.add('is-in');
    }, { threshold: 0.25 });
    document.querySelectorAll('[data-pricing-close]').forEach(el => observer.observe(el));
  }

  /* ---------- Story (schedule) ---------- */
  function setupStory() {
    const observer = makeObserver((el) => {
      el.querySelectorAll('.story-text, .story-chart').forEach(c => c.classList.add('is-in'));
    }, { threshold: 0.2 });
    document.querySelectorAll('[data-story]').forEach(el => observer.observe(el));
  }

  /* ---------- Boot ---------- */
  function init() {
    setupMarquee();
    setupBasicReveals();
    setupStaggers();
    setupHeroIntro();
    setupCtaClose();
    setupPhHeader();
    setupCompare();
    setupFaq();
    setupSchedGrid();
    setupSchedHeader();
    setupCountUp();
    setupInstrHeader();
    setupInstrStory();
    setupTimeline();
    setupInstrCta();
    setupInstrGrid();
    setupPricingHeader();
    setupPricingCards();
    setupPricingFaq();
    setupPricingClose();
    setupStory();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
