import Link from "next/link";
import styles from "./Footer.module.css";

const SITE_CENTRAL_URL = process.env.NEXT_PUBLIC_SITE_CENTRAL_URL || "http://localhost:3001";
const CGU_URL = `${SITE_CENTRAL_URL}/cgu`;
const CONTACT_URL = `${SITE_CENTRAL_URL}/contact`;

export default function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={styles.container}>
        <ul className={styles.links}>
          <li>
            <Link href="/mentions-legales" className={styles.link}>
              Mentions légales
            </Link>
          </li>
          <li>
            <a
              href={CGU_URL}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.link}
            >
              CGU
              <span className={styles.externalIcon} aria-hidden="true">
                ↗
              </span>
            </a>
          </li>
          <li>
            <a
              href={CONTACT_URL}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.link}
            >
              Contact
              <span className={styles.externalIcon} aria-hidden="true">
                ↗
              </span>
            </a>
          </li>
        </ul>
        <p className={styles.copyright}>© ItechSource 2026</p>
      </div>
    </footer>
  );
}
