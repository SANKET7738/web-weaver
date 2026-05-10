// Visual-only enhancements for Levante reference site.
(function () {
  // Mobile nav toggle
  const toggle = document.querySelector('.site-nav__toggle');
  const menu = document.querySelector('.site-nav__menu');
  if (toggle && menu) {
    toggle.addEventListener('click', function () {
      const open = menu.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  // Mark current nav link as active based on body data-page-slug
  const slug = document.body.getAttribute('data-page-slug');
  if (slug) {
    document.querySelectorAll('.site-nav__menu a[data-slug]').forEach(function (link) {
      if (link.getAttribute('data-slug') === slug) {
        link.setAttribute('aria-current', 'page');
      }
    });
  }
})();
