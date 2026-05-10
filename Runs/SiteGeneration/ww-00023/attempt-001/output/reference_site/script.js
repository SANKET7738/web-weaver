// Pixelwave — visual-only behaviors
(function () {
  // Subtle parallax shimmer on chrome headlines via mousemove
  var chromeTargets = document.querySelectorAll(
    '.chrome-text, .chrome-text-silver, .chrome-text-billboard, .chrome-text-headline'
  );
  if (chromeTargets.length && window.matchMedia('(pointer:fine)').matches) {
    document.addEventListener('mousemove', function (e) {
      var x = (e.clientX / window.innerWidth - 0.5) * 14;
      chromeTargets.forEach(function (el) {
        el.style.backgroundPosition = (50 + x) + '% 50%';
      });
    });
  }

  // Glossy pill ornament drift on the newsletter band
  var pills = document.querySelectorAll('.newsletter-band .ornament-pill');
  pills.forEach(function (pill, i) {
    var dir = i === 0 ? 1 : -1;
    var t = 0;
    setInterval(function () {
      t += 0.02 * dir;
      pill.style.transform =
        'translate(' + (Math.sin(t) * 6) + 'px,' + (Math.cos(t) * 4) + 'px) rotate(' +
        (i === 0 ? 15 + Math.sin(t) * 2 : -10 + Math.cos(t) * 2) + 'deg)';
    }, 50);
  });

  // Newsletter form: visual confirmation only
  var form = document.querySelector('.subscribe-form');
  if (form) {
    var btn = form.querySelector('button');
    var input = form.querySelector('input');
    var originalLabel = btn ? btn.textContent : '';
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (!btn) return;
      btn.textContent = 'Subscribed ✓';
      btn.style.background = '#CC00AA';
      if (input) input.value = '';
      setTimeout(function () {
        btn.textContent = originalLabel;
        btn.style.background = '';
      }, 2400);
    });
  }
})();
