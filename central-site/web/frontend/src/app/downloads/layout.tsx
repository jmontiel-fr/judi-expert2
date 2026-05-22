import { buildPageMetadata } from "@/lib/seo";

export const metadata = buildPageMetadata({
  title: "Téléchargements",
  description:
    "Téléchargez l'application locale Judi-Expert pour Windows ou Linux et commencez vos dossiers d'expertise.",
  path: "/downloads",
});

export default function DownloadsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
