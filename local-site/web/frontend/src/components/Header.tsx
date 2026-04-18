"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { getToken, clearToken } from "@/lib/api";
import styles from "./Header.module.css";

const SITE_CENTRAL_URL = process.env.NEXT_PUBLIC_SITE_CENTRAL_URL || "http://localhost:3001";

export default function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const [loggedIn, setLoggedIn] = useState(false);

  useEffect(() => {
    setLoggedIn(!!getToken());
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
                Déconnexion
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
