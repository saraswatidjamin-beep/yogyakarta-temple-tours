// Yogyakarta Temple Tours — shared navigation and document chrome.
(function () {
  'use strict';

  var button = document.querySelector('.nav-toggle');
  var menu = document.querySelector('.nav-links');
  var scrim = document.querySelector('.nav-scrim');
  var siteNav = document.querySelector('.site-nav');

  if (button) button.setAttribute('aria-controls', 'nav-menu');
  if (siteNav && !siteNav.hasAttribute('aria-label')) siteNav.setAttribute('aria-label', 'Primary');

  function setMenu(open, returnFocus) {
    if (!button || !menu) return;
    button.setAttribute('aria-expanded', String(open));
    button.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    menu.classList.toggle('nav-open', open);
    if (scrim) scrim.classList.toggle('open', open);
    document.body.classList.toggle('nav-is-open', open);

    if (open) {
      var firstLink = menu.querySelector('a');
      if (firstLink) window.setTimeout(function () { firstLink.focus(); }, 80);
    } else if (returnFocus) {
      button.focus();
    }
  }

  if (button && menu) {
    button.addEventListener('click', function () {
      setMenu(button.getAttribute('aria-expanded') !== 'true', false);
    });
    menu.addEventListener('click', function (event) {
      if (event.target.closest('a')) setMenu(false, false);
    });
    if (scrim) scrim.addEventListener('click', function () { setMenu(false, true); });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && button.getAttribute('aria-expanded') === 'true') {
        setMenu(false, true);
      }
    });

    var desktop = window.matchMedia('(min-width: 901px)');
    var closeAtDesktop = function (event) { if (event.matches) setMenu(false, false); };
    if (desktop.addEventListener) desktop.addEventListener('change', closeAtDesktop);
    else desktop.addListener(closeAtDesktop);
  }

  // Mark the current destination without relying on generated-page markup.
  var currentPath = window.location.pathname.replace(/\/$/, '') || '/';
  document.querySelectorAll('.nav-links a').forEach(function (link) {
    var linkPath = new URL(link.href, window.location.origin).pathname.replace(/\/$/, '') || '/';
    if (!link.hash && (currentPath === linkPath || (linkPath !== '/' && currentPath.indexOf(linkPath) === 0))) {
      link.setAttribute('aria-current', 'page');
    }
  });

})();
