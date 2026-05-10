/* Clearmind Therapy — Visual interaction helpers */
(function () {
  // Mobile nav toggle
  var navToggle = document.querySelector(".nav-toggle");
  var navLinks = document.querySelector(".site-nav__links");
  if (navToggle && navLinks) {
    navToggle.addEventListener("click", function () {
      var isOpen = navLinks.classList.toggle("is-open");
      navToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    });
  }

  // FAQ accordions (multiple accordion groups)
  document.querySelectorAll(".faq-list").forEach(function (list) {
    var singleOpen = list.dataset.singleOpen === "true";
    list.addEventListener("click", function (event) {
      var trigger = event.target.closest(".faq-item__question");
      if (!trigger) return;
      var item = trigger.closest(".faq-item");
      if (!item) return;
      var isOpen = item.classList.contains("is-open");
      if (singleOpen) {
        list.querySelectorAll(".faq-item.is-open").forEach(function (other) {
          if (other !== item) other.classList.remove("is-open");
        });
      }
      item.classList.toggle("is-open", !isOpen);
      trigger.setAttribute("aria-expanded", !isOpen ? "true" : "false");
    });
  });

  // Form: prevent default submit (no backend), give a visual confirmation
  var contactForm = document.querySelector("#contact-form");
  if (contactForm) {
    contactForm.addEventListener("submit", function (event) {
      event.preventDefault();
      var btn = contactForm.querySelector("button[type='submit']");
      if (!btn) return;
      var original = btn.textContent;
      btn.textContent = "Request received — we'll be in touch";
      btn.disabled = true;
      setTimeout(function () {
        btn.textContent = original;
        btn.disabled = false;
        contactForm.reset();
      }, 2800);
    });
  }
})();
