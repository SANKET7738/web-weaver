/* RevvLot — visual-only behaviors */
(function () {
  // Tab switching for interior gallery (visual only)
  document.querySelectorAll('.tab-rail').forEach(function (rail) {
    var items = rail.querySelectorAll('.tab-item');
    items.forEach(function (item) {
      item.addEventListener('click', function () {
        items.forEach(function (i) { i.classList.remove('active'); });
        item.classList.add('active');
      });
    });
  });

  // Auto-increment hit counters very slowly for retro feel
  document.querySelectorAll('[data-counter]').forEach(function (el) {
    var n = parseInt(el.getAttribute('data-counter'), 10);
    if (isNaN(n)) return;
    setInterval(function () {
      n += 1;
      el.textContent = String(n).padStart(8, '0');
    }, 4500);
  });

  // Filter toggle visual
  document.querySelectorAll('.filter-toggle span').forEach(function (s) {
    s.addEventListener('click', function () {
      s.classList.toggle('on');
    });
  });
})();
