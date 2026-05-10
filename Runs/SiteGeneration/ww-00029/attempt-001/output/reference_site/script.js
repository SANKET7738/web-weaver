// IronPop Gym - small visual-only behaviors

(function () {
  // Mobile nav toggle
  var toggle = document.querySelector('.nav-toggle');
  var list   = document.getElementById('primary-nav');

  if (toggle && list) {
    toggle.addEventListener('click', function () {
      var open = list.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  // Subtle parallax on hero squiggle
  var squiggle = document.querySelector('.hero__squiggle');
  if (squiggle && window.matchMedia('(min-width: 769px)').matches) {
    window.addEventListener('scroll', function () {
      var y = window.scrollY;
      if (y < 600) {
        squiggle.style.transform = 'translate(-50%, -50%) rotate(' + (y * 0.04) + 'deg)';
      }
    }, { passive: true });
  }

  // Day-pill keyboard hover bounce
  var pills = document.querySelectorAll('.day-pills span');
  pills.forEach(function (p) {
    p.addEventListener('mouseenter', function () {
      p.style.transform = 'translateY(-2px) rotate(-2deg)';
    });
    p.addEventListener('mouseleave', function () {
      p.style.transform = '';
    });
  });
})();
