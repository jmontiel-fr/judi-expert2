"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "./Header.module.css";

const SITE_CENTRAL_URL = "https://judi-expert.fr";
const FAQ_URL = "https://judi-expert.fr/faq";

export default function Header() {
  const pathname = usePathname();

  return (
    <header className={styles.header}>
      <nav className={styles.nav}>
        <Link href="/" className={styles.logo}>
          Judi-expert Local
        </Link>
        <ul className={styles.links}>
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
              href="/chatbot"
              className={`${styles.link} ${pathname === "/chatbot" ? styles.active : ""}`}
            >
              ChatBot
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
              <span className={styles.externalIcon} aria-hidden="true">
                ↗
              </span>
            </a>
          </li>
          <li>
            <a
              href={FAQ_URL}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.link}
            >
              FAQ
              <span className={styles.externalIcon} aria-hidden="true">
                ↗
              </span>
            </a>
          </li>
        </ul>
      </nav>
    </header>
  );
}
