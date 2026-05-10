// RevvLot — visual-only behaviors

document.addEventListener('DOMContentLoaded', () => {
  // Tab rail (gallery interior)
  const tabs = document.querySelectorAll('[data-tab-target]');
  tabs.forEach((tab) => {
    tab.addEventListener('click', (e) => {
      e.preventDefault();
      const target = tab.getAttribute('data-tab-target');
      const shell = tab.closest('[data-tab-shell]');
      if (!shell) return;
      shell.querySelectorAll('[data-tab-target]').forEach((t) => t.classList.remove('is-active'));
      shell.querySelectorAll('[data-tab-panel]').forEach((p) => p.classList.remove('is-active'));
      tab.classList.add('is-active');
      const panel = shell.querySelector(`[data-tab-panel="${target}"]`);
      if (panel) panel.classList.add('is-active');
    });
  });

  // Filter toggle buttons
  document.querySelectorAll('.filter-toggles button').forEach((b) => {
    b.addEventListener('click', () => b.classList.toggle('is-on'));
  });

  // Hit counter little increment vibe (visual only)
  document.querySelectorAll('[data-hit-counter]').forEach((el) => {
    let base = parseInt(el.getAttribute('data-hit-counter'), 10);
    setInterval(() => {
      base += 1;
      el.textContent = String(base).padStart(8, '0');
    }, 4500);
  });
});
