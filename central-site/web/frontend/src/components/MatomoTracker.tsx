"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";

/**
 * Composant de tracking Matomo pour Next.js App Router.
 * Envoie un trackPageView à chaque changement de pathname (navigation SPA).
 */
export default function MatomoTracker() {
  const pathname = usePathname();
  const isFirstRender = useRef(true);

  useEffect(() => {
    // Ignorer le premier rendu — déjà tracké par le script inline du layout
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }

    // Attendre que _paq soit disponible
    const _paq = (window as unknown as { _paq?: unknown[][] })._paq;
    if (!_paq) return;

    const url = window.location.href;
    _paq.push(["setCustomUrl", url]);
    _paq.push(["setDocumentTitle", document.title]);
    _paq.push(["trackPageView"]);
    _paq.push(["enableLinkTracking"]);
  }, [pathname]);

  return null;
}
