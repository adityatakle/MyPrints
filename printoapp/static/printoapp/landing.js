document.addEventListener('DOMContentLoaded', function () {

  /* ── SCROLL REVEAL ──────────────────────────────────────── */
  const revealEls = document.querySelectorAll('.mp-reveal');
  const revealObserver = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) e.target.classList.add('on');
    });
  }, { threshold: 0.1 });

  revealEls.forEach(function (el) { revealObserver.observe(el); });

  /* ── STICKY MOBILE CTA ──────────────────────────────────── */
  // Shows the bottom sticky "Order Print!" bar only after the
  // hero section scrolls out of view, and only on mobile (<640px).
  var hero    = document.querySelector('.mp-hero');
  var stickyCta = document.getElementById('mpStickyCta');

  if (hero && stickyCta) {
    var heroObserver = new IntersectionObserver(function (entries) {
      if (window.innerWidth < 640) {
        stickyCta.classList.toggle('hidden', entries[0].isIntersecting);
      }
    });
    heroObserver.observe(hero);
  }
});
