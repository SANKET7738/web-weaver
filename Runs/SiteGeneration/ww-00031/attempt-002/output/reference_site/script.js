/* Inkwell Jazz Festival - reveal & interaction scripts */

(function () {
  'use strict';

  // ---- Active nav link based on page slug ----
  function setActiveNav() {
    var slug = document.body.dataset.pageSlug;
    if (!slug) return;
    document.querySelectorAll('.nav-links a[data-slug]').forEach(function (link) {
      if (link.dataset.slug === slug) link.classList.add('is-active');
    });
  }

  // ---- IntersectionObserver-based reveal ----
  function setupReveals() {
    var els = document.querySelectorAll('[data-reveal]');
    if (!('IntersectionObserver' in window)) {
      els.forEach(function (el) { el.classList.add('is-in'); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          var el = entry.target;
          var delay = parseInt(el.dataset.delay || '0', 10);
          if (delay) {
            setTimeout(function () { el.classList.add('is-in'); }, delay);
          } else {
            el.classList.add('is-in');
          }
          io.unobserve(el);
        }
      });
    }, { threshold: 0.18, rootMargin: '0px 0px -40px 0px' });
    els.forEach(function (el) { io.observe(el); });
  }

  // ---- Staggered children inside a container ----
  function setupStaggers() {
    var groups = document.querySelectorAll('[data-stagger]');
    if (!('IntersectionObserver' in window)) {
      groups.forEach(function (g) {
        Array.prototype.forEach.call(g.children, function (c) { c.classList.add('is-in'); });
      });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          var children = entry.target.children;
          var step = parseInt(entry.target.dataset.stagger, 10) || 90;
          Array.prototype.forEach.call(children, function (child, idx) {
            setTimeout(function () { child.classList.add('is-in'); }, idx * step);
          });
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.2, rootMargin: '0px 0px -40px 0px' });
    groups.forEach(function (g) { io.observe(g); });
  }

  // ---- FAQ accordion ----
  function setupFAQ() {
    document.querySelectorAll('.faq-trigger').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var item = btn.closest('.faq-item');
        if (!item) return;
        item.classList.toggle('is-open');
        btn.setAttribute('aria-expanded', item.classList.contains('is-open'));
      });
    });
  }

  // ---- Wristband enter animation ----
  function setupWristband() {
    var wr = document.querySelector('.wristband');
    if (!wr) return;
    if (!('IntersectionObserver' in window)) { wr.classList.add('is-in'); return; }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { wr.classList.add('is-in'); io.unobserve(wr); }
      });
    }, { threshold: 0.3 });
    io.observe(wr);
  }

  // ---- Ghost text bloom on experience page ----
  function setupGhost() {
    var ghost = document.querySelector('.story-plum .ghost');
    if (!ghost) return;
    if (!('IntersectionObserver' in window)) { ghost.classList.add('is-in'); return; }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { ghost.classList.add('is-in'); io.unobserve(ghost); }
      });
    }, { threshold: 0.2 });
    io.observe(ghost);

    // Parallax drift
    var ticking = false;
    function onScroll() {
      if (!ticking) {
        requestAnimationFrame(function () {
          var rect = ghost.parentElement.getBoundingClientRect();
          var offset = (window.innerHeight / 2 - rect.top) * 0.15;
          ghost.style.transform = 'translateY(' + (-offset) + 'px)';
          ticking = false;
        });
        ticking = true;
      }
    }
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  // ---- Map labels stamp-in ----
  function setupMapLabels() {
    var labels = document.querySelectorAll('.map-label');
    if (!labels.length) return;
    var container = document.querySelector('.map-canvas');
    if (!container) return;
    if (!('IntersectionObserver' in window)) {
      labels.forEach(function (l) { l.classList.add('is-in'); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          labels.forEach(function (l, i) {
            setTimeout(function () { l.classList.add('is-in'); }, 900 + i * 160);
          });
          io.unobserve(container);
        }
      });
    }, { threshold: 0.3 });
    io.observe(container);
  }

  // ---- Map header word reveal ----
  function setupWordReveal() {
    document.querySelectorAll('.word-reveal').forEach(function (el) {
      var text = el.textContent;
      el.textContent = '';
      var words = text.split(/\s+/);
      words.forEach(function (w, i) {
        var span = document.createElement('span');
        span.className = 'word';
        span.textContent = w + ' ';
        span.style.animationDelay = (300 + i * 80) + 'ms';
        el.appendChild(span);
      });
    });
  }

  // ---- Bill hero parallax (lineup) ----
  function setupBillParallax() {
    var bg = document.querySelector('.bill-hero-bg');
    if (!bg) return;
    var ticking = false;
    function onScroll() {
      if (!ticking) {
        requestAnimationFrame(function () {
          var y = window.scrollY;
          bg.style.transform = 'translateY(' + (y * -0.08) + 'px)';
          ticking = false;
        });
        ticking = true;
      }
    }
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  document.addEventListener('DOMContentLoaded', function () {
    setActiveNav();
    setupReveals();
    setupStaggers();
    setupFAQ();
    setupWristband();
    setupGhost();
    setupMapLabels();
    setupWordReveal();
    setupBillParallax();
  });
})();
