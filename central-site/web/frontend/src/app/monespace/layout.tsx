import MonEspaceShell from "./MonEspaceShell";
import { noindexMetadata } from "@/lib/seo";

export const metadata = noindexMetadata("Mon espace", "/monespace");

export default function MonEspaceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <MonEspaceShell>{children}</MonEspaceShell>;
}
