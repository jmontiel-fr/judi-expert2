import { redirect } from "next/navigation";

/**
 * Catch-all route for invalid sub-routes under /outils.
 * Redirects to /outils/mettre-en-forme.
 *
 * This handles cases like /outils/inexistant, /outils/foo/bar, etc.
 */
export default function OutilsCatchAll() {
  redirect("/outils/mettre-en-forme");
}
