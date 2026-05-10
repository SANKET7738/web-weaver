// Lumi & Bloom — visual-only behaviors

(function () {
  // Mobile nav toggle
  const navToggles = document.querySelectorAll("[data-nav-toggle]");
  navToggles.forEach((btn) => {
    btn.addEventListener("click", () => {
      const nav = btn.closest(".nav");
      if (nav) nav.classList.toggle("is-open");
    });
  });

  // FAQ accordion (only one open at a time)
  const faqButtons = document.querySelectorAll("[data-faq-toggle]");
  faqButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const item = btn.closest(".faq-item");
      if (!item) return;
      const wasOpen = item.classList.contains("is-open");
      item.parentElement
        .querySelectorAll(".faq-item.is-open")
        .forEach((el) => el.classList.remove("is-open"));
      if (!wasOpen) item.classList.add("is-open");
    });
  });
})();
