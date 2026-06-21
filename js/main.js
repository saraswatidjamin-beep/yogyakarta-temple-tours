/* Yogyakarta Temple Tours — Mobile Nav Toggle */
(function() {
  const toggle = document.querySelector('.nav-toggle');
  const links = document.querySelector('.nav-links');
  if (!toggle || !links) return;

  toggle.addEventListener('click', function() {
    const isOpen = toggle.classList.toggle('open');
    links.classList.toggle('open');
    toggle.setAttribute('aria-expanded', isOpen);
    document.body.classList.toggle('no-scroll', isOpen);
  });

  /* Close menu when a link is clicked */
  links.querySelectorAll('a').forEach(function(link) {
    link.addEventListener('click', function() {
      toggle.classList.remove('open');
      links.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
      document.body.classList.remove('no-scroll');
    });
  });
})();
