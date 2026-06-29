/**
 * Matomo Tracking — Code à injecter dans les pages des applications
 *
 * Mode : cookieless (pas de bannière RGPD nécessaire)
 * Serveur : https://matomo.itechsource.fr
 *
 * CONFIGURATION :
 * - Remplacer SITE_ID par l'idSite de l'application dans Matomo :
 *     1 = itechsource.fr
 *     2 = viamalin.com
 *     3 = judi-expert.fr
 *
 * INTÉGRATION :
 * - Ajouter ce script avant </body> ou dans le <head> de chaque page
 * - Pour Next.js : utiliser <Script strategy="afterInteractive">
 * - Pour Vue/Nuxt : ajouter dans nuxt.config.js (head.script)
 * - Pour HTML classique : copier le bloc <script> tel quel
 */

// ============================================================================
// SNIPPET À COPIER (remplacer SITE_ID)
// ============================================================================

var _paq = window._paq = window._paq || [];
_paq.push(['disableCookies']);
_paq.push(['trackPageView']);
_paq.push(['enableLinkTracking']);
(function() {
  var u = "//matomo.itechsource.fr/";
  _paq.push(['setTrackerUrl', u + 'matomo.php']);
  _paq.push(['setSiteId', 'SITE_ID']); // ← Remplacer par 1, 2 ou 3
  var d = document, g = d.createElement('script'), s = d.getElementsByTagName('script')[0];
  g.async = true; g.src = u + 'matomo.js'; s.parentNode.insertBefore(g, s);
})();

// ============================================================================
// EXEMPLES PAR FRAMEWORK
// ============================================================================

// --- Next.js (layout.tsx) ---
// import Script from 'next/script';
//
// <Script id="matomo" strategy="afterInteractive"
//   dangerouslySetInnerHTML={{ __html: `
//     var _paq = window._paq = window._paq || [];
//     _paq.push(['disableCookies']);
//     _paq.push(['trackPageView']);
//     _paq.push(['enableLinkTracking']);
//     (function() {
//       var u="//matomo.itechsource.fr/";
//       _paq.push(['setTrackerUrl', u+'matomo.php']);
//       _paq.push(['setSiteId', 'SITE_ID']);
//       var d=document, g=d.createElement('script'), s=d.getElementsByTagName('script')[0];
//       g.async=true; g.src=u+'matomo.js'; s.parentNode.insertBefore(g,s);
//     })();
//   `}}
// />

// --- Vue / Nuxt (nuxt.config.js) ---
// head: {
//   script: [{
//     innerHTML: `
//       var _paq = window._paq = window._paq || [];
//       _paq.push(['disableCookies']);
//       _paq.push(['trackPageView']);
//       _paq.push(['enableLinkTracking']);
//       (function() {
//         var u="//matomo.itechsource.fr/";
//         _paq.push(['setTrackerUrl', u+'matomo.php']);
//         _paq.push(['setSiteId', 'SITE_ID']);
//         var d=document, g=d.createElement('script'), s=d.getElementsByTagName('script')[0];
//         g.async=true; g.src=u+'matomo.js'; s.parentNode.insertBefore(g,s);
//       })();
//     `,
//     type: 'text/javascript',
//   }],
// }

// --- HTML classique ---
// <script>
//   var _paq = window._paq = window._paq || [];
//   _paq.push(['disableCookies']);
//   _paq.push(['trackPageView']);
//   _paq.push(['enableLinkTracking']);
//   (function() {
//     var u="//matomo.itechsource.fr/";
//     _paq.push(['setTrackerUrl', u+'matomo.php']);
//     _paq.push(['setSiteId', 'SITE_ID']);
//     var d=document, g=d.createElement('script'), s=d.getElementsByTagName('script')[0];
//     g.async=true; g.src=u+'matomo.js'; s.parentNode.insertBefore(g,s);
//   })();
// </script>
