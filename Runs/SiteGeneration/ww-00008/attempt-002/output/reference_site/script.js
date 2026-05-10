// RevvLot — visual-only behaviors (no business logic)

(function () {
  'use strict';

  // ---------- FAQ accordion ----------
  document.querySelectorAll('[data-faq]').forEach(function (faq) {
    faq.querySelectorAll('.faq-row').forEach(function (row) {
      var btn = row.querySelector('.faq-row__btn');
      if (!btn) return;
      btn.addEventListener('click', function () {
        var isOpen = row.classList.contains('is-open');
        // close all rows
        faq.querySelectorAll('.faq-row').forEach(function (r) {
          r.classList.remove('is-open');
          var t = r.querySelector('.toggle');
          if (t) t.textContent = '[+]';
        });
        if (!isOpen) {
          row.classList.add('is-open');
          var t = row.querySelector('.toggle');
          if (t) t.textContent = '[-]';
        }
      });
    });
  });

  // ---------- Tabs (interior gallery) ----------
  document.querySelectorAll('[data-tabs]').forEach(function (tabs) {
    var buttons = tabs.querySelectorAll('.tab-button');
    var panes = tabs.querySelectorAll('.tab-content');
    buttons.forEach(function (btn) {
      btn.addEventListener('click', function () {
        var target = btn.getAttribute('data-tab');
        buttons.forEach(function (b) { b.classList.remove('is-active'); });
        panes.forEach(function (p) { p.classList.remove('is-active'); });
        btn.classList.add('is-active');
        var pane = tabs.querySelector('#' + target);
        if (pane) pane.classList.add('is-active');
      });
    });
  });

  // ---------- Filter chip toggle ----------
  document.querySelectorAll('.chip').forEach(function (chip) {
    chip.addEventListener('click', function () {
      chip.classList.toggle('is-active');
    });
  });
})();
