"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import styles from "./outils.module.css";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TabItem {
  label: string;
  href: string;
  slug: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const TABS: TabItem[] = [
  { label: "Mettre en forme", href: "/outils/mettre-en-forme", slug: "mettre-en-forme" },
  { label: "Résumer", href: "/outils/resumer", slug: "resumer" },
  { label: "Editer PEA", href: "/outils/editer-pea", slug: "editer-pea" },
];

const VALID_SLUGS = new Set(TABS.map((t) => t.slug));

const DEFAULT_ROUTE = "/outils/mettre-en-forme";

// ---------------------------------------------------------------------------
// OutilsTabs Component
// ---------------------------------------------------------------------------

interface OutilsTabsProps {
  activeSlug: string;
}

function OutilsTabs({ activeSlug }: OutilsTabsProps) {
  return (
    <nav className={styles.tabs} role="tablist" aria-label="Onglets Outils">
      {TABS.map((tab) => (
        <Link
          key={tab.slug}
          href={tab.href}
          role="tab"
          aria-selected={activeSlug === tab.slug}
          className={`${styles.tab} ${activeSlug === tab.slug ? styles.tabActive : ""}`}
        >
          {tab.label}
        </Link>
      ))}
    </nav>
  );
}

// ---------------------------------------------------------------------------
// OutilsLayout
// ---------------------------------------------------------------------------

export default function OutilsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  // Extract the sub-route slug from the pathname
  const segments = pathname.split("/").filter(Boolean);
  // segments: ["outils"] or ["outils", "mettre-en-forme"] etc.
  const slug = segments.length > 1 ? segments[1] : null;

  // Redirect /outils (no sub-route) or invalid sub-routes to /outils/mettre-en-forme
  const needsRedirect = !slug || !VALID_SLUGS.has(slug);

  useEffect(() => {
    if (needsRedirect) {
      router.replace(DEFAULT_ROUTE);
    }
  }, [needsRedirect, router]);

  // While redirecting, show the layout with default active tab
  const activeSlug = slug && VALID_SLUGS.has(slug) ? slug : "mettre-en-forme";

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Outils</h1>
      <p className={styles.subtitle}>
        Outils d&apos;édition et de traitement de texte pour l&apos;expert judiciaire.
      </p>
      <OutilsTabs activeSlug={activeSlug} />
      {children}
    </div>
  );
}
