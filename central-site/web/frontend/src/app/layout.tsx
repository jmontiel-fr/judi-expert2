import type { Metadata, Viewport } from "next";
import Script from "next/script";
import { AuthProvider } from "@/contexts/AuthContext";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import ChatBot from "@/components/ChatBot";
import MatomoTracker from "@/components/MatomoTracker";
import PwaRegister from "@/components/PwaRegister";
import {
  DEFAULT_DESCRIPTION,
  DEFAULT_KEYWORDS,
  OG_IMAGE_SIZE,
  OG_IMAGE_URL,
  SITE_NAME,
  SITE_URL,
} from "@/lib/seo";
import "./globals.css";
import layoutStyles from "./layout.module.css";

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#1a365d",
};

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: `${SITE_NAME} — Assistance IA pour experts judiciaires`,
    template: `%s — ${SITE_NAME}`,
  },
  description: DEFAULT_DESCRIPTION,
  keywords: DEFAULT_KEYWORDS,
  authors: [{ name: SITE_NAME, url: SITE_URL }],
  creator: SITE_NAME,
  publisher: SITE_NAME,
  formatDetection: { email: false, address: false, telephone: false },
  alternates: { canonical: SITE_URL },
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: SITE_NAME,
  },
  openGraph: {
    type: "website",
    locale: "fr_FR",
    url: SITE_URL,
    siteName: SITE_NAME,
    title: `${SITE_NAME} — Assistance IA pour experts judiciaires`,
    description: DEFAULT_DESCRIPTION,
    images: [
      {
        url: OG_IMAGE_URL(),
        width: OG_IMAGE_SIZE.width,
        height: OG_IMAGE_SIZE.height,
        alt: SITE_NAME,
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: `${SITE_NAME} — Assistance IA pour experts judiciaires`,
    description: DEFAULT_DESCRIPTION,
    images: [OG_IMAGE_URL()],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true, "max-image-preview": "large" },
  },
  icons: {
    icon: [{ url: "/favicon.svg", type: "image/svg+xml" }],
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <body
        style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}
      >
        <AuthProvider>
          <PwaRegister />
          <MatomoTracker />
          <Header />
          <main className={layoutStyles.main}>
            {children}
          </main>
          <Footer />
          <ChatBot />
        </AuthProvider>
        <Script id="matomo" strategy="afterInteractive"
          dangerouslySetInnerHTML={{ __html: `
            var _paq = window._paq = window._paq || [];
            _paq.push(['disableCookies']);
            _paq.push(['trackPageView']);
            _paq.push(['enableLinkTracking']);
            (function() {
              var u="https://matomo.itechsource.fr/";
              _paq.push(['setTrackerUrl', u+'matomo.php']);
              _paq.push(['setSiteId', '3']);
              var d=document, g=d.createElement('script'), s=d.getElementsByTagName('script')[0];
              g.async=true; g.src=u+'matomo.js'; s.parentNode.insertBefore(g,s);
            })();
          `}}
        />
      </body>
    </html>
  );
}
