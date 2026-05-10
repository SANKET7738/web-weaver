// RevvLot — visual-only behaviors

(function () {
  // Gallery side tabs
  const tabs = document.querySelectorAll('.tab-rail .tab-item');
  if (tabs.length) {
    tabs.forEach((tab) => {
      tab.addEventListener('click', () => {
        const target = tab.getAttribute('data-tab');
        const rail = tab.closest('.tab-layout');
        if (!rail) return;

        rail.querySelectorAll('.tab-item').forEach((t) => {
          t.classList.toggle('active', t === tab);
          t.setAttribute('aria-selected', t === tab ? 'true' : 'false');
        });
        rail.querySelectorAll('.tab-pane').forEach((p) => {
          p.classList.toggle('active', p.id === target);
        });
      });
    });
  }

  // Filter toggles (visual only)
  const filterToggles = document.querySelectorAll('.filter-toggle');
  filterToggles.forEach((t) => {
    t.addEventListener('click', () => t.classList.toggle('active'));
  });

  // Animated hit counter (purely cosmetic increment on load)
  const counters = document.querySelectorAll('.nav-counter, .hit-counter, .trust-sidebar .counter, .faq-final-cta .counter');
  counters.forEach((c) => {
    const text = c.textContent;
    const match = text.match(/(\D*)(\d[\d,]*)(.*)/);
    if (!match) return;
    const prefix = match[1];
    const numStr = match[2].replace(/,/g, '');
    const suffix = match[3] || '';
    let n = parseInt(numStr, 10);
    if (Number.isNaN(n)) return;
    let i = 0;
    const id = setInterval(() => {
      n += 1;
      const padded = numStr.length > 0
        ? n.toString().padStart(numStr.length, '0')
        : n.toString();
      // re-introduce comma at thousands if original had it
      const formatted = match[2].includes(',')
        ? padded.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
        : padded;
      c.textContent = prefix + formatted + suffix;
      i += 1;
      if (i > 6) clearInterval(id);
    }, 1700);
  });

  // Smooth-scroll for in-page anchors
  document.querySelectorAll('a[href^="#"]').forEach((a) => {
    a.addEventListener('click', (e) => {
      const id = a.getAttribute('href');
      if (id.length > 1) {
        const el = document.querySelector(id);
        if (el) {
          e.preventDefault();
          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }
    });
  });
})();
