/* Courtside & Crown — visual-only enhancements */

(function () {
  'use strict';

  // Mobile nav toggle
  var toggle = document.querySelector('.nav-toggle');
  var nav = document.querySelector('.primary-nav');

  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      var open = nav.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });

    // Close nav when a link is clicked (mobile)
    nav.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        nav.classList.remove('is-open');
        toggle.setAttribute('aria-expanded', 'false');
      });
    });
  }

  // Subtle reveal-on-scroll for cards and section headers
  if ('IntersectionObserver' in window) {
    var revealTargets = document.querySelectorAll(
      '.section-header, .stat-card, .pillar-card, .feature-card, .facility-card, ' +
      '.testimonial-card, .timeline-card, .coach-card, .pricing-card, ' +
      '.fixture-card, .result-card, .article-card, .lead-article, ' +
      '.category-tile, .enquiry-card, .contact-item, .chart-card'
    );

    revealTargets.forEach(function (el) {
      el.style.opacity = '0';
      el.style.transform = 'translateY(14px)';
      el.style.transition = 'opacity 600ms ease, transform 600ms ease';
    });

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

    revealTargets.forEach(function (el) { io.observe(el); });
  }

  // Smooth-scroll on the hero scroll indicator
  var scrollIndicator = document.querySelector('.scroll-indicator');
  if (scrollIndicator) {
    scrollIndicator.addEventListener('click', function () {
      var hero = document.querySelector('.hero');
      if (hero) {
        var next = hero.nextElementSibling;
        if (next && next.scrollIntoView) {
          next.scrollIntoView({ behavior: 'smooth' });
        }
      }
    });
    scrollIndicator.style.cursor = 'pointer';
  }
})();
