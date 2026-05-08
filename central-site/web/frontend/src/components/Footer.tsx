"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import styles from "./Footer.module.css";

const FRENCH_MONTHS = [
  "janvier",
  "février",
  "mars",
  "avril",
  "mai",
  "juin",
  "juillet",
  "août",
  "septembre",
  "octobre",
  "novembre",
  "décembre",
];

function formatFrenchDate(isoDate: string): string {
  const [year, month, day] = isoDate.split("-");
  return `${parseInt(day)} ${FRENCH_MONTHS[parseInt(month) - 1]} ${year}`;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export default function Footer() {
  const [versionLabel, setVersionLabel] = useState<string>("");

  useEffect(() => {
    fetch(`${API_BASE}/api/health`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data?.version) {
          const datePart = data.version_date
            ? ` - ${formatFrenchDate(data.version_date)}`
            : "";
          setVersionLabel(` - V${data.version}${datePart}`);
        }
      })
      .catch(() => {
        // Silently ignore — version won't be displayed
      });
  }, []);

  return (
    <footer className={styles.footer}>
      <div className={styles.container}>
        <span className={styles.copyright}>
          © ITechSource 2026{versionLabel}
        </span>
        <span className={styles.separator}>—</span>
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
            <Link href="/securite" className={styles.link}>
              Sécurité
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
      </div>
    </footer>
  );
}
