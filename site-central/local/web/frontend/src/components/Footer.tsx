import Link from "next/link";
import styles from "./Footer.module.css";

const CHU_URL = "https://www.chu.fr";
const CGU_URL = "https://judi-expert.fr/cgu";
const CONTACT_URL = "https://judi-expert.fr/contact";

export default function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={styles.container}>
        <ul className={styles.links}>
          <li>
            <a
              href={CHU_URL}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.link}
            >
              CHU
              <span className={styles.externalIcon} aria-hidden="true">
                ↗
              </span>
            </a>
          </li>
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
