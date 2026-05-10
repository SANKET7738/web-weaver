/* Forma Intime — motion orchestration (vanilla JS) */
(function () {
  "use strict";

  /* ---------- nav highlight + mobile toggle ---------- */
  function setupNav() {
    var slug = document.body.getAttribute("data-page-slug");
    document.querySelectorAll(".nav-links a").forEach(function (a) {
      if (a.getAttribute("data-target") === slug) a.classList.add("is-active");
    });

    var toggle = document.querySelector(".nav-toggle");
    var nav = document.querySelector(".site-nav");
    if (toggle && nav) {
      toggle.addEventListener("click", function () {
        nav.classList.toggle("open");
      });
    }
  }

  /* ---------- generic reveal observer ---------- */
  function setupRevealObserver() {
    var els = document.querySelectorAll(".reveal");
    if (!("IntersectionObserver" in window)) {
      els.forEach(function (el) { el.classList.add("is-visible"); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
    els.forEach(function (el) { io.observe(el); });
  }

  /* ---------- section visibility flag (for grouped staggers) ---------- */
  function setupSectionFlags() {
    var sections = document.querySelectorAll("[data-watch]");
    if (!("IntersectionObserver" in window)) {
      sections.forEach(function (s) { s.classList.add("is-visible"); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.18 });
    sections.forEach(function (s) { io.observe(s); });
  }

  /* ---------- counter animations (data-count-to) ---------- */
  function animateCounter(node, target, opts) {
    opts = opts || {};
    var suffix = opts.suffix || "";
    var duration = opts.duration || 1100;
    var startTs = null;
    var ease = function (t) { return 1 - Math.pow(1 - t, 3); };

    function step(ts) {
      if (!startTs) startTs = ts;
      var p = Math.min(1, (ts - startTs) / duration);
      var v = Math.round(target * ease(p));
      node.textContent = v + suffix;
      if (p < 1) requestAnimationFrame(step);
      else node.textContent = (opts.finalText !== undefined ? opts.finalText : (target + suffix));
    }
    requestAnimationFrame(step);
  }

  function setupCounters() {
    var counters = document.querySelectorAll("[data-count-to]");
    if (!("IntersectionObserver" in window)) {
      counters.forEach(function (c) { c.textContent = c.getAttribute("data-final-text") || c.getAttribute("data-count-to"); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var node = entry.target;
        var target = parseInt(node.getAttribute("data-count-to"), 10);
        var suffix = node.getAttribute("data-suffix") || "";
        var finalText = node.getAttribute("data-final-text") || undefined;
        var dur = parseInt(node.getAttribute("data-duration") || "1100", 10);
        var delay = parseInt(node.getAttribute("data-delay-ms") || "0", 10);
        setTimeout(function () {
          animateCounter(node, target, { suffix: suffix, finalText: finalText, duration: dur });
        }, delay);
        io.unobserve(node);
      });
    }, { threshold: 0.5 });
    counters.forEach(function (c) { io.observe(c); });
  }

  /* ---------- hero anatomy baseline (home page) ---------- */
  function setupAnatomyBaseline() {
    var baseline = document.querySelector(".anatomy-baseline");
    var ann = document.querySelector(".anatomy-annotation");
    if (!baseline) return;
    requestAnimationFrame(function () {
      baseline.classList.add("is-drawn");
      if (ann) setTimeout(function () { ann.classList.add("is-visible"); }, 100);
    });
  }

  /* ---------- materials specimen index counters ---------- */
  function setupSpecimenIndex() {
    var indices = document.querySelectorAll(".specimen-index[data-index]");
    if (!("IntersectionObserver" in window)) {
      indices.forEach(function (i) { i.textContent = i.getAttribute("data-index"); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var node = entry.target;
        var target = parseInt(node.getAttribute("data-index"), 10);
        var delay = parseInt(node.getAttribute("data-stagger") || "0", 10);
        setTimeout(function () {
          animateCounter(node, target, {
            duration: 280,
            finalText: String(target).padStart(2, "0")
          });
        }, delay);
        io.unobserve(node);
      });
    }, { threshold: 0.45 });
    indices.forEach(function (i) { io.observe(i); });
  }

  /* ---------- materials bar chart (uses --bar-w custom prop) ---------- */
  /* CSS-driven via .is-visible on .materials-features */

  /* ---------- collection comparison highlighted row ---------- */
  // pure CSS via .is-active on first <tr>

  /* ---------- stockists map dot reveal & ambient pulse ---------- */
  function setupMapDots() {
    var dots = document.querySelectorAll(".map-dot");
    if (!dots.length) return;
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        dots.forEach(function (dot, i) {
          setTimeout(function () { dot.classList.add("appear"); }, 200 + i * 80);
        });
        io.unobserve(entry.target);
      });
    }, { threshold: 0.2 });
    var host = dots[0].closest("svg") || dots[0];
    io.observe(host);
  }

  /* ---------- campaign diagram annotation lines (clinical diagram) ---------- */
  function setupDiagramAnnotations() {
    var diagrams = document.querySelectorAll("[data-clinical-diagram]");
    if (!diagrams.length) return;
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var svg = entry.target;
        var lines = svg.querySelectorAll(".anno-line");
        var labels = svg.querySelectorAll(".anno-label-group");
        lines.forEach(function (line, i) {
          setTimeout(function () {
            line.classList.add("drawn");
            var lab = labels[i];
            if (lab) setTimeout(function () { lab.classList.add("shown"); }, 180);
          }, i * 180);
        });
        io.unobserve(svg);
      });
    }, { threshold: 0.25 });
    diagrams.forEach(function (d) { io.observe(d); });
  }

  /* ---------- generic page-header loaded flag ---------- */
  function setupPageHeaderLoaded() {
    var hdrs = document.querySelectorAll(".page-header, .materials-header, .stockists-header");
    hdrs.forEach(function (h) {
      requestAnimationFrame(function () { h.classList.add("is-loaded"); });
    });
  }

  /* ---------- init ---------- */
  document.addEventListener("DOMContentLoaded", function () {
    setupNav();
    setupRevealObserver();
    setupSectionFlags();
    setupCounters();
    setupAnatomyBaseline();
    setupSpecimenIndex();
    setupMapDots();
    setupDiagramAnnotations();
    setupPageHeaderLoaded();
  });
})();
