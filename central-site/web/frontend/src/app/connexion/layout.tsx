import { noindexMetadata } from "@/lib/seo";

export const metadata = noindexMetadata("Connexion", "/connexion");

export default function ConnexionLayout({ children }: { children: React.ReactNode }) {
  return children;
}
