/* Axiom Public Lab — visual-only behaviors */
(function () {
  'use strict';

  // Mobile nav toggle
  var toggle = document.querySelector('.nav-toggle');
  var navList = document.querySelector('.nav-list');
  if (toggle && navList) {
    toggle.addEventListener('click', function () {
      var isOpen = navList.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });
  }

  // FAQ accordion
  var faqHeads = document.querySelectorAll('.faq-item__head');
  Array.prototype.forEach.call(faqHeads, function (head) {
    head.addEventListener('click', function () {
      var item = head.parentElement;
      var isOpen = item.classList.toggle('is-open');
      head.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });
  });
})();
