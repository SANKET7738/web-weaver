// RevvLot — small visual-only behaviors
(function () {
  'use strict';

  // Interior gallery tab switching
  document.querySelectorAll('.tab-rail').forEach(function (rail) {
    var items = rail.querySelectorAll('.tab-item');
    items.forEach(function (tab) {
      tab.addEventListener('click', function (e) {
        e.preventDefault();
        var target = tab.getAttribute('data-target');
        if (!target) return;

        items.forEach(function (i) { i.classList.remove('active'); });
        tab.classList.add('active');

        document.querySelectorAll('.tab-content').forEach(function (panel) {
          panel.classList.toggle('active', panel.id === target);
        });
      });
    });
  });

  // Filter toggle chips on product page
  document.querySelectorAll('.filter-toggle').forEach(function (chip) {
    chip.addEventListener('click', function () {
      var active = chip.classList.toggle('on');
      if (active) {
        chip.style.background = '#00FF33';
        chip.style.borderTopColor = '#808080';
        chip.style.borderLeftColor = '#808080';
        chip.style.borderRightColor = '#FFFFFF';
        chip.style.borderBottomColor = '#FFFFFF';
      } else {
        chip.style.background = '';
        chip.style.borderTopColor = '';
        chip.style.borderLeftColor = '';
        chip.style.borderRightColor = '';
        chip.style.borderBottomColor = '';
      }
    });
  });

  // Animate hit-counter visitor digits softly on page load
  var counter = document.querySelector('.counter-box');
  if (counter) {
    var base = 847291;
    var step = 0;
    var iv = setInterval(function () {
      step++;
      counter.textContent = 'VISITORS: 00' + (base + step).toLocaleString().replace(/,/g, ',');
      if (step >= 12) clearInterval(iv);
    }, 1500);
  }

  // FAQ items: click question to subtly highlight
  document.querySelectorAll('.faq-item h3').forEach(function (q) {
    q.style.cursor = 'pointer';
    q.addEventListener('click', function () {
      q.parentElement.classList.toggle('faq-highlight');
      q.style.color = q.parentElement.classList.contains('faq-highlight') ? '#00FF33' : '';
    });
  });
})();
