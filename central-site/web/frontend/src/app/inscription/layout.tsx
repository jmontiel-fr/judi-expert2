import { buildPageMetadata } from "@/lib/seo";

export const metadata = buildPageMetadata({
  title: "Inscription",
  description:
    "Créez votre compte expert sur Judi-Expert et accédez à l'application locale d'assistance aux dossiers d'expertise.",
  path: "/inscription",
});

export default function InscriptionLayout({ children }: { children: React.ReactNode }) {
  return children;
}
