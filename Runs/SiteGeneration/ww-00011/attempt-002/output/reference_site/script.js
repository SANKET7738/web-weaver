/* Mobile nav toggle */
document.addEventListener('DOMContentLoaded', function () {
  var toggle = document.querySelector('.nav-toggle');
  var links = document.querySelector('.nav-links');
  if (toggle && links) {
    toggle.addEventListener('click', function () {
      links.classList.toggle('open');
      var open = links.classList.contains('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      toggle.textContent = open ? 'Close' : 'Menu';
    });
    document.addEventListener('click', function (e) {
      if (!links.contains(e.target) && !toggle.contains(e.target) && links.classList.contains('open')) {
        links.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
        toggle.textContent = 'Menu';
      }
    });
  }
});
