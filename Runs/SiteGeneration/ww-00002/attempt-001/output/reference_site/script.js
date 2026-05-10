// Mobile nav toggle (visual only)
(function () {
  var nav = document.querySelector('.nav');
  if (!nav) return;
  var btn = nav.querySelector('.nav__toggle');
  if (!btn) return;
  btn.addEventListener('click', function () {
    nav.classList.toggle('is-open');
    btn.setAttribute(
      'aria-expanded',
      nav.classList.contains('is-open') ? 'true' : 'false'
    );
  });
})();

// Form prevent-default (visual only — no backend)
(function () {
  var form = document.querySelector('.contact-form');
  if (!form) return;
  form.addEventListener('submit', function (e) {
    e.preventDefault();
  });
})();
