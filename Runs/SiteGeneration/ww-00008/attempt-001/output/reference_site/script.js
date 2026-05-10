// RevvLot — visual-only behavior

(function () {
  // Filter chip toggle
  document.querySelectorAll('.chip').forEach(function (chip) {
    chip.addEventListener('click', function () {
      chip.classList.toggle('active');
    });
  });

  // Interior tabs
  var tabs = document.querySelectorAll('.tab');
  if (tabs.length) {
    tabs.forEach(function (tab) {
      tab.addEventListener('click', function () {
        var target = tab.getAttribute('data-target');
        tabs.forEach(function (t) { t.classList.remove('active'); });
        tab.classList.add('active');
        document.querySelectorAll('.tab-pane').forEach(function (p) {
          p.hidden = p.id !== target;
        });
      });
    });
  }

  // Mechanical rows
  var mech = document.querySelectorAll('.mech-row');
  if (mech.length) {
    mech.forEach(function (row) {
      row.addEventListener('click', function () {
        var target = row.getAttribute('data-mech');
        mech.forEach(function (r) { r.classList.remove('active'); });
        row.classList.add('active');
        document.querySelectorAll('.mech-pane').forEach(function (p) {
          p.hidden = p.id !== target;
        });
      });
    });
  }

  // Range slider thumb drag (visual only)
  document.querySelectorAll('.range-bar').forEach(function (bar) {
    var thumbLeft = bar.querySelector('.thumb.left');
    var thumbRight = bar.querySelector('.thumb.right');
    var fill = bar.querySelector('.fill');
    if (!thumbLeft || !thumbRight || !fill) return;
    var dragging = null;
    function onMove(e) {
      if (!dragging) return;
      var rect = bar.getBoundingClientRect();
      var x = (e.touches ? e.touches[0].clientX : e.clientX) - rect.left;
      var pct = Math.max(0, Math.min(100, (x / rect.width) * 100));
      if (dragging === 'left') {
        var rightPct = parseFloat(thumbRight.style.right || '30');
        if (pct > 100 - rightPct - 4) pct = 100 - rightPct - 4;
        thumbLeft.style.left = 'calc(' + pct + '% - 6px)';
        fill.style.left = pct + '%';
      } else {
        var leftPct = parseFloat((thumbLeft.style.left || '20%').replace(/.*\(([\d.]+)%.*/, '$1'));
        if (isNaN(leftPct)) leftPct = 20;
        var rPct = 100 - pct;
        if (rPct < 0) rPct = 0;
        if (pct < leftPct + 4) rPct = 100 - (leftPct + 4);
        thumbRight.style.right = 'calc(' + rPct + '% - 6px)';
        fill.style.right = rPct + '%';
      }
    }
    function stop() { dragging = null; document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', stop); }
    thumbLeft.addEventListener('mousedown', function () { dragging = 'left'; document.addEventListener('mousemove', onMove); document.addEventListener('mouseup', stop); });
    thumbRight.addEventListener('mousedown', function () { dragging = 'right'; document.addEventListener('mousemove', onMove); document.addEventListener('mouseup', stop); });
  });

  // Radio square selection
  document.querySelectorAll('.radio-group').forEach(function (group) {
    group.querySelectorAll('label').forEach(function (lbl) {
      lbl.addEventListener('click', function () {
        group.querySelectorAll('.radio-square').forEach(function (sq) {
          sq.style.background = 'var(--lot-black)';
        });
        var sq = lbl.querySelector('.radio-square');
        if (sq) sq.style.background = 'var(--revv-cyan)';
      });
    });
  });
})();
