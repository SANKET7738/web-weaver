// Mobile navigation toggle
(function () {
  var toggle = document.querySelector('.nav-toggle');
  var menu = document.querySelector('.nav-links');
  if (!toggle || !menu) return;
  toggle.addEventListener('click', function () {
    menu.classList.toggle('open');
    var expanded = menu.classList.contains('open');
    toggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    toggle.textContent = expanded ? 'CLOSE' : 'MENU';
  });
})();

// Subtle reveal on scroll for cards / stats / timeline items
(function () {
  if (!('IntersectionObserver' in window)) return;
  var els = document.querySelectorAll(
    '.feature-card, .stat-cell, .timeline-item, .value-card, .team-card, .dept-card, .division-tile, .project-card, .milestone-card, .info-card, .testimonial'
  );
  els.forEach(function (el) {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
  });
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.style.opacity = '1';
        entry.target.style.transform = 'translateY(0)';
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });
  els.forEach(function (el) { io.observe(el); });
})();
