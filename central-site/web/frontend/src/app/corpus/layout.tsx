import { buildPageMetadata } from "@/lib/seo";

export const metadata = buildPageMetadata({
  title: "Corpus juridiques",
  description:
    "Corpus de référence pour l'expertise judiciaire : accès aux bases documentaires par domaine d'expertise.",
  path: "/corpus",
});

export default function CorpusLayout({ children }: { children: React.ReactNode }) {
  return children;
}
