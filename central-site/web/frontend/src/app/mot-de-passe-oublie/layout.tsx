import { noindexMetadata } from "@/lib/seo";

export const metadata = noindexMetadata("Mot de passe oublié", "/mot-de-passe-oublie");

export default function ForgotPasswordLayout({ children }: { children: React.ReactNode }) {
  return children;
}
