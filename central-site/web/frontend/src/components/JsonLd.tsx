import { OG_IMAGE_URL, SITE_NAME, SITE_URL, absoluteUrl } from "@/lib/seo";

type JsonLdProps = {
  data: Record<string, unknown> | Record<string, unknown>[];
};

export default function JsonLd({ data }: JsonLdProps) {
  const payload = Array.isArray(data) ? data : [data];
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(payload) }}
    />
  );
}

export function HomePageJsonLd() {
  return (
    <JsonLd
      data={[
        {
          "@context": "https://schema.org",
          "@type": "Organization",
          name: SITE_NAME,
          url: SITE_URL,
          logo: OG_IMAGE_URL(),
          description:
            "Assistance IA pour experts judiciaires — production de dossiers d'expertise en local.",
          contactPoint: {
            "@type": "ContactPoint",
            contactType: "customer support",
            url: absoluteUrl("/contact"),
            availableLanguage: "French",
          },
        },
        {
          "@context": "https://schema.org",
          "@type": "WebSite",
          name: SITE_NAME,
          url: SITE_URL,
          inLanguage: "fr-FR",
          potentialAction: {
            "@type": "SearchAction",
            target: `${SITE_URL}/faq?q={search_term_string}`,
            "query-input": "required name=search_term_string",
          },
        },
        {
          "@context": "https://schema.org",
          "@type": "SoftwareApplication",
          name: SITE_NAME,
          applicationCategory: "BusinessApplication",
          operatingSystem: "Windows, Linux",
          offers: {
            "@type": "Offer",
            url: absoluteUrl("/tarification"),
            priceCurrency: "EUR",
          },
        },
      ]}
    />
  );
}
