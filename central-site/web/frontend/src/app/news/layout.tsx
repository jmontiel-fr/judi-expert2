import { buildPageMetadata } from "@/lib/seo";

export const metadata = buildPageMetadata({
  title: "Actualités",
  description: "Actualités et annonces du service Judi-Expert pour les experts judiciaires.",
  path: "/news",
});

export default function NewsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
