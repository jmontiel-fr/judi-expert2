"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import axios from "axios";
import styles from "./Footer.module.css";

const SITE_CENTRAL_URL = process.env.NEXT_PUBLIC_SITE_CENTRAL_URL || "http://localhost:3001";
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const CGU_URL = `${SITE_CENTRAL_URL}/cgu`;
const CONTACT_URL = `${SITE_CENTRAL_URL}/contact`;

const FRENCH_MONTHS = [
  "janvier", "février", "mars", "avril", "mai", "juin",
  "juillet", "août", "septembre", "octobre", "novembre", "décembre",
];

/**
 * Formate une date ISO (YYYY-MM-DD) en français : "{jour} {mois} {année}"
 * Le jour n'a pas de zéro initial (ex: "8 mai 2026").
 */
function formatDateFrench(isoDate: string): string {
  const [yearStr, monthStr, dayStr] = isoDate.split("-");
  const day = parseInt(dayStr, 10);
  const monthIndex = parseInt(monthStr, 10) - 1;
  const monthName = FRENCH_MONTHS[monthIndex] || monthStr;
  return `${day} ${monthName} ${yearStr}`;
}

export default function Footer() {
  const [versionLabel, setVersionLabel] = useState<string | null>(null);

  useEffect(() => {
    axios
      .get(`${API_URL}/api/version`)
      .then((res) => {
        const { current_version, current_date } = res.data;
        if (current_version && current_date) {
          const formattedDate = formatDateFrench(current_date);
          setVersionLabel(`V${current_version} - ${formattedDate}`);
        }
      })
      .catch(() => {
        // Silently fail — footer displays without version info
      });
  }, []);

  return (
    <footer className={styles.footer}>
      <div className={styles.container}>
        <p className={styles.copyright}>
          © ItechSource 2026
          {versionLabel && ` - ${versionLabel}`}
        </p>
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
      </div>
    </footer>
  );
}
