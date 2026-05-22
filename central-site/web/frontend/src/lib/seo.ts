import type { Metadata } from "next";

export const SITE_NAME = "Judi-Expert";
export const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") ||
  "https://www.judi-expert.fr";

/** Image Open Graph / partage social (1200x630), derivee du logo. */
export const OG_IMAGE_PATH = "/og-image.png";
export const OG_IMAGE_URL = () => absoluteUrl(OG_IMAGE_PATH);
export const OG_IMAGE_SIZE = { width: 1200, height: 630 };

export const DEFAULT_DESCRIPTION =
  "Solution d'assistance IA pour experts judiciaires : réduisez le temps de production de vos dossiers d'expertise. Données hébergées localement, conformité RGPD et AI Act.";

export const DEFAULT_KEYWORDS = [
  "expert judiciaire",
  "expertise judiciaire",
  "psychologie judiciaire",
  "dossier d'expertise",
  "IA expert judiciaire",
  "Judi-Expert",
];

/** Routes publiques indexables (sitemap). */
export const PUBLIC_ROUTES: { path: string; priority: number; changeFrequency: "weekly" | "monthly" | "yearly" }[] = [
  { path: "/", priority: 1, changeFrequency: "weekly" },
  { path: "/tarification", priority: 0.9, changeFrequency: "monthly" },
  { path: "/faq", priority: 0.8, changeFrequency: "monthly" },
  { path: "/downloads", priority: 0.85, changeFrequency: "weekly" },
  { path: "/corpus", priority: 0.7, changeFrequency: "monthly" },
  { path: "/contact", priority: 0.6, changeFrequency: "yearly" },
  { path: "/news", priority: 0.7, changeFrequency: "weekly" },
  { path: "/securite", priority: 0.6, changeFrequency: "yearly" },
  { path: "/inscription", priority: 0.75, changeFrequency: "monthly" },
  { path: "/cgu", priority: 0.3, changeFrequency: "yearly" },
  { path: "/mentions-legales", priority: 0.3, changeFrequency: "yearly" },
  { path: "/politique-confidentialite", priority: 0.3, changeFrequency: "yearly" },
];

export function absoluteUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${SITE_URL}${normalized}`;
}

type PageMetadataOptions = {
  title: string;
  description?: string;
  path: string;
  noindex?: boolean;
  keywords?: string[];
};

export function buildPageMetadata({
  title,
  description = DEFAULT_DESCRIPTION,
  path,
  noindex = false,
  keywords = DEFAULT_KEYWORDS,
}: PageMetadataOptions): Metadata {
  const pageTitle = title.includes(SITE_NAME) ? title : `${title} — ${SITE_NAME}`;
  const url = absoluteUrl(path);
  const ogImage = OG_IMAGE_URL();

  return {
    title: pageTitle,
    description,
    keywords,
    alternates: { canonical: url },
    robots: noindex
      ? { index: false, follow: false, googleBot: { index: false, follow: false } }
      : {
          index: true,
          follow: true,
          googleBot: { index: true, follow: true, "max-image-preview": "large" },
        },
    openGraph: {
      type: "website",
      locale: "fr_FR",
      url,
      siteName: SITE_NAME,
      title: pageTitle,
      description,
      images: [
        {
          url: ogImage,
          width: OG_IMAGE_SIZE.width,
          height: OG_IMAGE_SIZE.height,
          alt: SITE_NAME,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: pageTitle,
      description,
      images: [ogImage],
    },
  };
}

export const NOINDEX_ROUTES = [
  "/connexion",
  "/mot-de-passe-oublie",
  "/confirmation",
  "/monespace",
  "/admin",
] as const;

export function noindexMetadata(title: string, path: string): Metadata {
  return buildPageMetadata({
    title,
    path,
    noindex: true,
    description: DEFAULT_DESCRIPTION,
  });
}
