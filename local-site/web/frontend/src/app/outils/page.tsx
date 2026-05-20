import { redirect } from "next/navigation";

/**
 * /outils page — redirects to /outils/mettre-en-forme.
 * This server component handles the redirect for direct navigation to /outils.
 */
export default function OutilsPage() {
  redirect("/outils/mettre-en-forme");
}
