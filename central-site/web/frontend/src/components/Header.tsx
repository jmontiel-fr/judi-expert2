"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import styles from "./Header.module.css";

export default function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isAdmin, logout } = useAuth();

  async function handleLogout() {
    await logout();
    router.push("/");
  }

  return (
    <header className={styles.header}>
      <nav className={styles.nav}>
        <Link href="/" className={styles.logo}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.svg" alt="" className={styles.logoIcon} />
          Judi-Expert
          <span className={styles.devBadge}>dev</span>
        </Link>
        <ul className={styles.links}>
          <li>
            <Link
              href="/"
              className={`${styles.link} ${pathname === "/" ? styles.active : ""}`}
            >
              Accueil
            </Link>
          </li>
          <li>
            <Link
              href="/corpus"
              className={`${styles.link} ${pathname === "/corpus" ? styles.active : ""}`}
            >
              Corpus
            </Link>
          </li>
          <li>
            <Link
              href="/faq"
              className={`${styles.link} ${pathname === "/faq" ? styles.active : ""}`}
            >
              FAQ
            </Link>
          </li>

          {!user && (
            <>
              <li>
                <Link
                  href="/connexion"
                  className={`${styles.link} ${pathname === "/connexion" ? styles.active : ""}`}
                >
                  Connexion
                </Link>
              </li>
              <li>
                <Link
                  href="/inscription"
                  className={`${styles.link} ${pathname === "/inscription" ? styles.active : ""}`}
                >
                  Inscription
                </Link>
              </li>
            </>
          )}

          {user && (
            <li>
              <Link
                href="/news"
                className={`${styles.link} ${pathname === "/news" ? styles.active : ""}`}
              >
                News
              </Link>
            </li>
          )}

          {user && (
            <li>
              <Link
                href="/downloads"
                className={`${styles.link} ${pathname === "/downloads" ? styles.active : ""}`}
              >
                Downloads
              </Link>
            </li>
          )}

          {user && (
            <li>
              <Link
                href="/monespace"
                className={`${styles.link} ${pathname.startsWith("/monespace") ? styles.active : ""}`}
              >
                Mon Espace
              </Link>
            </li>
          )}

          {user && isAdmin && (
            <li>
              <Link
                href="/admin"
                className={`${styles.link} ${pathname.startsWith("/admin") ? styles.active : ""}`}
              >
                Administration
              </Link>
            </li>
          )}

          {user && (
            <li>
              <button
                type="button"
                className={styles.link}
                onClick={handleLogout}
                style={{ background: "none", border: "none", cursor: "pointer", font: "inherit" }}
              >
                Déconnexion ({user.email})
              </button>
            </li>
          )}
        </ul>
      </nav>
    </header>
  );
}
