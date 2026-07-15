"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import styles from "./Header.module.css";

export default function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isAdmin, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  useEffect(() => {
    document.body.style.overflow = menuOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [menuOpen]);

  async function handleLogout() {
    setMenuOpen(false);
    await logout();
    router.push("/");
  }

  const linkClass = (href: string, matchPrefix = false) => {
    const active = matchPrefix ? pathname.startsWith(href) : pathname === href;
    return `${styles.link} ${active ? styles.active : ""}`;
  };

  const navLinks = (
    <>
      <li>
        <Link href="/" className={linkClass("/")} onClick={() => setMenuOpen(false)}>
          Accueil
        </Link>
      </li>
      <li>
        <Link href="/corpus" className={linkClass("/corpus")} onClick={() => setMenuOpen(false)}>
          Corpus
        </Link>
      </li>
      <li>
        <Link href="/faq" className={linkClass("/faq")} onClick={() => setMenuOpen(false)}>
          FAQ
        </Link>
      </li>
      <li>
        <Link href="/tarification" className={linkClass("/tarification")} onClick={() => setMenuOpen(false)}>
          Tarifs
        </Link>
      </li>
      <li>
        <Link href="/contact" className={linkClass("/contact")} onClick={() => setMenuOpen(false)}>
          Contact
        </Link>
      </li>

      {!user && (
        <li>
          <Link href="/connexion" className={linkClass("/connexion")} onClick={() => setMenuOpen(false)}>
            Connexion
          </Link>
        </li>
      )}

      {user && (
        <li>
          <Link href="/news" className={linkClass("/news")} onClick={() => setMenuOpen(false)}>
            News
          </Link>
        </li>
      )}

      {user && (
        <li>
          <Link href="/downloads" className={linkClass("/downloads")} onClick={() => setMenuOpen(false)}>
            Downloads
          </Link>
        </li>
      )}

      {user && (
        <li>
          <Link
            href="/monespace"
            className={linkClass("/monespace", true)}
            onClick={() => setMenuOpen(false)}
          >
            Mon Espace
          </Link>
        </li>
      )}

      {user && isAdmin && (
        <li>
          <Link href="/admin" className={linkClass("/admin", true)} onClick={() => setMenuOpen(false)}>
            Administration
          </Link>
        </li>
      )}

      {user && (
        <li>
          <button
            type="button"
            className={`${styles.link} ${styles.logoutBtn}`}
            onClick={handleLogout}
          >
            Déconnexion
            <span className={styles.userEmail}>{user.email}</span>
          </button>
        </li>
      )}
    </>
  );

  return (
    <header className={styles.header}>
      <nav className={styles.nav} aria-label="Navigation principale">
        <Link href="/" className={styles.logo}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.svg" alt="" className={styles.logoIcon} />
          <span className={styles.logoText}>Judi-Expert</span>
          {process.env.NEXT_PUBLIC_APP_ENV !== "production" && (
            <span className={styles.devBadge}>dev</span>
          )}
        </Link>

        <div className={styles.navActions}>
          <a href="tel:+33451209140" className={styles.phone}>
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M6.62 10.79a15.053 15.053 0 006.59 6.59l2.2-2.2a1 1 0 011.01-.24c1.12.37 2.33.57 3.57.57a1 1 0 011 1V20a1 1 0 01-1 1A17 17 0 013 4a1 1 0 011-1h3.5a1 1 0 011 1c0 1.25.2 2.45.57 3.57a1 1 0 01-.25 1.02l-2.2 2.2z" />
            </svg>
            <span className={styles.phoneNumber}>04 51 20 91 40</span>
          </a>

          <button
            type="button"
            className={styles.menuButton}
            aria-expanded={menuOpen}
            aria-controls="main-nav-menu"
            aria-label={menuOpen ? "Fermer le menu" : "Ouvrir le menu"}
            onClick={() => setMenuOpen((open) => !open)}
          >
            <span className={styles.menuIcon} aria-hidden="true" />
          </button>
        </div>

        <ul className={styles.links}>{navLinks}</ul>
      </nav>

      {menuOpen && (
        <button
          type="button"
          className={styles.backdrop}
          aria-label="Fermer le menu"
          onClick={() => setMenuOpen(false)}
        />
      )}

      <div
        id="main-nav-menu"
        className={`${styles.mobileMenu} ${menuOpen ? styles.mobileMenuOpen : ""}`}
        aria-hidden={!menuOpen}
      >
        <a href="tel:+33451209140" className={styles.mobilePhone} onClick={() => setMenuOpen(false)}>
          Appeler le 04 51 20 91 40
        </a>
        <ul className={styles.mobileLinks}>{navLinks}</ul>
      </div>
    </header>
  );
}
