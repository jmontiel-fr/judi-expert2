"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { getToken, clearToken } from "@/lib/api";
import styles from "./Header.module.css";

const SITE_CENTRAL_URL = process.env.NEXT_PUBLIC_SITE_CENTRAL_URL || "http://localhost:3001";

/**
 * Decode a JWT payload (without verification) to extract claims.
 */
function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1]));
    return payload;
  } catch {
    return null;
  }
}

export default function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const [loggedIn, setLoggedIn] = useState(false);
  const [userEmail, setUserEmail] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    if (token) {
      setLoggedIn(true);
      const payload = decodeJwtPayload(token);
      if (payload && typeof payload.email === "string") {
        setUserEmail(payload.email);
      } else {
        setUserEmail(null);
      }
    } else {
      setLoggedIn(false);
      setUserEmail(null);
    }
  }, [pathname]);

  const handleLogout = useCallback(() => {
    clearToken();
    setLoggedIn(false);
    router.push("/login");
  }, [router]);

  return (
    <header className={styles.header}>
      <nav className={styles.nav}>
        <Link href="/" className={styles.logo}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.svg" alt="" className={styles.logoIcon} />
          <span>Judi-Expert Local</span>
          <span className={styles.devBadge}>dev</span>
        </Link>
        <ul className={styles.links}>
          <li>
            <Link
              href="/accueil"
              className={`${styles.link} ${pathname === "/accueil" ? styles.active : ""}`}
            >
              Accueil
            </Link>
          </li>
          <li>
            <Link
              href="/"
              className={`${styles.link} ${pathname === "/" ? styles.active : ""}`}
            >
              Dossiers
            </Link>
          </li>
          <li>
            <Link
              href="/config"
              className={`${styles.link} ${pathname === "/config" ? styles.active : ""}`}
            >
              Configuration
            </Link>
          </li>
          <li>
            <Link
              href="/revision"
              className={`${styles.link} ${pathname === "/revision" ? styles.active : ""}`}
            >
              Révision
            </Link>
          </li>
          <li>
            <a
              href={SITE_CENTRAL_URL}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.link}
            >
              Site Central
              <span className={styles.externalIcon} aria-hidden="true">↗</span>
            </a>
          </li>
          <li>
            <Link
              href="/faq"
              className={`${styles.link} ${pathname === "/faq" ? styles.active : ""}`}
            >
              FAQ
            </Link>
          </li>
          <li>
            {loggedIn ? (
              <button
                type="button"
                className={styles.link}
                onClick={handleLogout}
                style={{ background: "none", border: "none", cursor: "pointer", font: "inherit" }}
              >
                Déconnexion{userEmail ? ` (${userEmail})` : ""}
              </button>
            ) : (
              <Link
                href="/login"
                className={`${styles.link} ${pathname === "/login" ? styles.active : ""}`}
              >
                Connexion
              </Link>
            )}
          </li>
        </ul>
      </nav>
    </header>
  );
}
