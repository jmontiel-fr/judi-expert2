"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import styles from "./monespace.module.css";

const tabs = [
  { href: "/monespace/profil", label: "Profil" },
  { href: "/monespace/tickets", label: "Tickets" },
];

export default function MonEspaceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/connexion");
    }
  }, [user, loading, router]);

  if (loading) {
    return <div className={styles.loading}>Chargement…</div>;
  }

  if (!user) {
    return <div className={styles.loading}>Redirection…</div>;
  }

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Mon Espace</h1>
      <p className={styles.subtitle}>
        Gérez votre profil et vos tickets d&apos;expertise
      </p>

      <nav className={styles.tabNav} aria-label="Espace personnel">
        {tabs.map((tab) => (
          <Link
            key={tab.href}
            href={tab.href}
            className={`${styles.tabLink} ${pathname === tab.href ? styles.tabLinkActive : ""}`}
          >
            {tab.label}
          </Link>
        ))}
      </nav>

      {children}
    </div>
  );
}
