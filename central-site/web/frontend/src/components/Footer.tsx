import Link from "next/link";
import styles from "./Footer.module.css";

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
            <Link href="/cgu" className={styles.link}>
              CGU
            </Link>
          </li>
          <li>
            <Link href="/politique-confidentialite" className={styles.link}>
              Confidentialité
            </Link>
          </li>
          <li>
            <Link href="/faq" className={styles.link}>
              FAQ
            </Link>
          </li>
          <li>
            <Link href="/contact" className={styles.link}>
              Contact
            </Link>
          </li>
        </ul>
        <p className={styles.copyright}>© ITechSource 2026</p>
      </div>
    </footer>
  );
}
