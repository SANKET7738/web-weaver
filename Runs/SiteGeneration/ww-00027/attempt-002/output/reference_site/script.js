// Visual-only behaviors

(function () {
  // Mobile nav toggle
  var toggle = document.querySelector('.nav-toggle');
  var nav = document.querySelector('.site-nav');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      nav.classList.toggle('open');
    });
  }

  // FAQ accordion
  var faqItems = document.querySelectorAll('.faq-item');
  faqItems.forEach(function (item) {
    var btn = item.querySelector('.faq-item__btn');
    if (!btn) return;
    btn.addEventListener('click', function () {
      var isOpen = item.classList.toggle('open');
      var toggleEl = item.querySelector('.faq-item__toggle');
      if (toggleEl) toggleEl.textContent = isOpen ? '−' : '+';
    });
  });

  // Inquiry form — visual feedback only
  var form = document.querySelector('.contact__form');
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var btn = form.querySelector('.contact__submit');
      if (btn) {
        var original = btn.textContent;
        btn.textContent = 'Submitted ✓';
        btn.disabled = true;
        setTimeout(function () {
          btn.textContent = original;
          btn.disabled = false;
        }, 2400);
      }
    });
  }
})();
