// Haven & Paw — animation orchestration & light interactivity
(function () {
  'use strict';

  // -------- Mobile nav toggle --------
  function initMobileNav() {
    var toggle = document.querySelector('.mobile-toggle');
    var links = document.querySelector('.nav-links');
    if (!toggle || !links) return;
    toggle.addEventListener('click', function () {
      var isOpen = links.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });
  }

  // -------- Intersection-based reveal --------
  function initRevealObserver() {
    if (!('IntersectionObserver' in window)) {
      document.querySelectorAll('.reveal-on-scroll, .reveal-block, .stagger-child, .stats-panel, .budget-bar, .give-strip')
        .forEach(function (el) { el.classList.add('is-visible'); });
      return;
    }

    var revealObserver = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          obs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15, rootMargin: '0px 0px -8% 0px' });

    document.querySelectorAll('.reveal-on-scroll, .reveal-block').forEach(function (el) {
      revealObserver.observe(el);
    });

    // Stagger reveal — group children inside a parent
    var staggerObserver = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          var children = entry.target.querySelectorAll('.stagger-child');
          children.forEach(function (child, i) {
            child.style.transitionDelay = (i * 120) + 'ms';
            child.classList.add('is-visible');
          });
          obs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15, rootMargin: '0px 0px -6% 0px' });

    document.querySelectorAll('[data-stagger]').forEach(function (group) {
      staggerObserver.observe(group);
    });
  }

  // -------- Stats panel reveal --------
  function initStatsPanel() {
    var panel = document.querySelector('.stats-panel');
    if (!panel) return;
    if (!('IntersectionObserver' in window)) {
      panel.classList.add('is-visible');
      runCountUps();
      return;
    }
    var obs = new IntersectionObserver(function (entries, ob) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          // delay count-ups so they begin after slide-up arrival
          setTimeout(runCountUps, 700);
          ob.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15 });
    obs.observe(panel);
  }

  function runCountUps() {
    var nums = document.querySelectorAll('.stat-num');
    nums.forEach(function (el, idx) {
      var raw = el.getAttribute('data-target');
      if (raw == null) return;
      var hasPercent = el.textContent.indexOf('%') !== -1 || raw.indexOf('%') !== -1;
      var target = parseFloat(raw.replace(/[^\d.]/g, ''));
      if (isNaN(target)) return;
      var startTime = null;
      var duration = 1800;
      var startDelay = idx * 250;
      el.textContent = '0' + (hasPercent ? '%' : '');

      setTimeout(function () {
        function step(ts) {
          if (!startTime) startTime = ts;
          var elapsed = ts - startTime;
          var t = Math.min(elapsed / duration, 1);
          // easeOutQuart
          var eased = 1 - Math.pow(1 - t, 4);
          var val = target * eased;
          var formatted = formatNumber(val, target, hasPercent);
          el.textContent = formatted;
          if (t < 1) {
            requestAnimationFrame(step);
          } else {
            el.textContent = formatFinal(target, hasPercent);
          }
        }
        requestAnimationFrame(step);
      }, startDelay);
    });
  }

  function formatNumber(val, target, hasPercent) {
    if (hasPercent) {
      return Math.round(val) + '%';
    }
    if (target >= 1000) {
      return Math.round(val).toLocaleString();
    }
    return String(Math.round(val));
  }

  function formatFinal(target, hasPercent) {
    if (hasPercent) return target + '%';
    if (target >= 1000) return target.toLocaleString();
    return String(target);
  }

  // -------- Budget bar reveal --------
  function initBudgetBar() {
    var bar = document.querySelector('.budget-bar');
    if (!bar) return;
    if (!('IntersectionObserver' in window)) {
      bar.classList.add('is-visible');
      return;
    }
    var obs = new IntersectionObserver(function (entries, ob) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          ob.unobserve(entry.target);
        }
      });
    }, { threshold: 0.3 });
    obs.observe(bar);
  }

  // -------- GIVE strip reveal --------
  function initGiveStrip() {
    var strip = document.querySelector('.give-strip');
    if (!strip) return;
    if (!('IntersectionObserver' in window)) {
      strip.classList.add('is-visible');
      return;
    }
    var obs = new IntersectionObserver(function (entries, ob) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          ob.unobserve(entry.target);
        }
      });
    }, { threshold: 0.2 });
    obs.observe(strip);
  }

  // -------- Donate form local interactivity (visual only) --------
  function initDonateForm() {
    var freq = document.querySelectorAll('.frequency-toggle button');
    freq.forEach(function (btn) {
      btn.addEventListener('click', function () {
        freq.forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
      });
    });
    var amt = document.querySelectorAll('.amount-btn');
    amt.forEach(function (btn) {
      btn.addEventListener('click', function () {
        amt.forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
      });
    });
    var form = document.querySelector('.donate-form');
    if (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var btn = form.querySelector('.btn-donate');
        if (btn) {
          var prev = btn.textContent;
          btn.textContent = 'Thank You — Receipt Sent';
          btn.disabled = true;
          setTimeout(function () { btn.textContent = prev; btn.disabled = false; }, 2400);
        }
      });
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    initMobileNav();
    initRevealObserver();
    initStatsPanel();
    initBudgetBar();
    initGiveStrip();
    initDonateForm();
  });
})();
