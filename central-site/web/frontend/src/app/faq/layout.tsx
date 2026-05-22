import { buildPageMetadata } from "@/lib/seo";

export const metadata = buildPageMetadata({
  title: "FAQ",
  description:
    "Questions fréquentes sur Judi-Expert : installation, tickets, sécurité des données, modules d'expertise et conformité RGPD.",
  path: "/faq",
});

export default function FaqLayout({ children }: { children: React.ReactNode }) {
  return children;
}
