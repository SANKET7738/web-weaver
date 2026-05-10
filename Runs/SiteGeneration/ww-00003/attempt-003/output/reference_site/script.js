/* Visual-only behavior:
   1. Toggle the mobile nav menu.
   2. Make FAQ accordions exclusive (one open at a time within the same list).
*/

(function () {
  // --- Mobile nav toggle ---
  var toggle = document.querySelector('.nav-toggle');
  var links = document.querySelector('.nav-links');
  if (toggle && links) {
    toggle.addEventListener('click', function () {
      var open = links.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  // --- Exclusive FAQ accordions per list ---
  document.querySelectorAll('.faq-list').forEach(function (list) {
    var items = list.querySelectorAll('details.faq-item');
    items.forEach(function (item) {
      item.addEventListener('toggle', function () {
        if (item.open) {
          items.forEach(function (other) {
            if (other !== item && other.open) other.open = false;
          });
        }
      });
    });
  });
})();
