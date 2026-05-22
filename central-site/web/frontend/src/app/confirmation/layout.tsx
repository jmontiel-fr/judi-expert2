import { noindexMetadata } from "@/lib/seo";

export const metadata = noindexMetadata("Confirmation", "/confirmation");

export default function ConfirmationLayout({ children }: { children: React.ReactNode }) {
  return children;
}
