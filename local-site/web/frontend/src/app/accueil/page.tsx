"use client";

import Link from "next/link";
import styles from "./accueil.module.css";

const SITE_CENTRAL_URL = process.env.NEXT_PUBLIC_SITE_CENTRAL_URL || "http://localhost:3001";

export default function AccueilPage() {
  return (
    <div className={styles.container}>
      {/* Hero */}
      <section className={styles.hero}>
        <h1 className={styles.heroTitle}>
          Bienvenue sur Judi-Expert Local
        </h1>
        <p className={styles.heroSubtitle}>
          Votre assistant IA pour la production de rapports d&apos;expertise
          judiciaire. Toutes vos données restent sur votre PC — rien ne
          transite par Internet.
        </p>
        <span className={styles.heroBadge}>
          🔒 100% local — conforme RGPD et AI Act
        </span>
      </section>

      {/* Fonctionnalités */}
      <h2 className={styles.sectionTitle}>Fonctionnalités</h2>
      <p className={styles.sectionSubtitle}>
        Tout ce dont vous avez besoin pour produire vos rapports d&apos;expertise.
      </p>
      <div className={styles.featuresGrid}>
        <div className={styles.featureCard}>
          <div className={styles.featureIcon}>📂</div>
          <h3 className={styles.featureTitle}>Gestion des dossiers</h3>
          <p className={styles.featureDesc}>
            Créez et suivez vos dossiers d&apos;expertise. Chaque dossier suit
            un workflow en 5 étapes guidées par l&apos;IA.
          </p>
          <Link href="/" className={styles.featureLink}>
            Accéder aux dossiers →
          </Link>
        </div>

        <div className={styles.featureCard}>
          <div className={styles.featureIcon}>📝</div>
          <h3 className={styles.featureTitle}>Extraction OCR</h3>
          <p className={styles.featureDesc}>
            Convertissez vos réquisitions PDF scannées en texte Markdown
            structuré grâce à l&apos;OCR et l&apos;IA.
          </p>
          <Link href="/" className={styles.featureLink}>
            Créer un dossier →
          </Link>
        </div>

        <div className={styles.featureCard}>
          <div className={styles.featureIcon}>🤖</div>
          <h3 className={styles.featureTitle}>ChatBot expert</h3>
          <p className={styles.featureDesc}>
            Posez des questions sur votre domaine d&apos;expertise. Le ChatBot
            utilise le corpus RAG local pour des réponses contextualisées.
          </p>
          <Link href="/chatbot" className={styles.featureLink}>
            Ouvrir le ChatBot →
          </Link>
        </div>

        <div className={styles.featureCard}>
          <div className={styles.featureIcon}>⚙️</div>
          <h3 className={styles.featureTitle}>Configuration</h3>
          <p className={styles.featureDesc}>
            Choisissez votre domaine, importez votre trame d&apos;entretien
            et votre template de rapport Word.
          </p>
          <Link href="/config" className={styles.featureLink}>
            Configurer →
          </Link>
        </div>

        <div className={styles.featureCard}>
          <div className={styles.featureIcon}>📄</div>
          <h3 className={styles.featureTitle}>Génération de rapports</h3>
          <p className={styles.featureDesc}>
            Générez automatiquement le pré-rapport d&apos;expertise et le
            document d&apos;analyse contradictoire au format Word.
          </p>
          <Link href="/" className={styles.featureLink}>
            Voir les dossiers →
          </Link>
        </div>

        <div className={styles.featureCard}>
          <div className={styles.featureIcon}>🎟️</div>
          <h3 className={styles.featureTitle}>Tickets d&apos;expertise</h3>
          <p className={styles.featureDesc}>
            Achetez vos tickets sur le site central. Chaque ticket permet
            de créer un dossier d&apos;expertise.
          </p>
          <a
            href={`${SITE_CENTRAL_URL}/monespace`}
            target="_blank"
            rel="noopener noreferrer"
            className={styles.featureLink}
          >
            Acheter un ticket ↗
          </a>
        </div>
      </div>

      {/* Workflow */}
      <section className={styles.stepsSection}>
        <h2 className={styles.sectionTitle}>Workflow d&apos;expertise</h2>
        <p className={styles.sectionSubtitle}>
          Chaque dossier suit 5 étapes séquentielles assistées par l&apos;IA,
          plus une étape intermédiaire réalisée par l&apos;expert hors application.
        </p>
        <div className={styles.stepsRow}>
          <div className={styles.stepItem}>
            <div className={styles.stepNumber}>1</div>
            <p className={styles.stepLabel}>Création dossier</p>
            <p className={styles.stepDesc}>
              Import de l&apos;ordonnance et des pièces, extraction OCR,
              identification des questions et des placeholders
            </p>
          </div>
          <div className={styles.stepItem}>
            <div className={styles.stepNumber}>2</div>
            <p className={styles.stepLabel}>Préparation investigations</p>
            <p className={styles.stepDesc}>
              Génération du Plan d&apos;Entretien (PE) ou Plan d&apos;Analyse (PA)
              à partir du TPE/TPA et du contexte RAG
            </p>
          </div>
          <div className={styles.stepItem}>
            <div className={styles.stepNumber}>E/A</div>
            <p className={styles.stepLabel}>Entretien ou Analyse</p>
            <p className={styles.stepDesc}>
              L&apos;expert mène ses entretiens ou analyses hors application
              et annote le plan (PEA/PAA)
            </p>
          </div>
          <div className={styles.stepItem}>
            <div className={styles.stepNumber}>3</div>
            <p className={styles.stepLabel}>Consolidation documentaire</p>
            <p className={styles.stepDesc}>
              Import des pièces de diligence complémentaires et extraction OCR
            </p>
          </div>
          <div className={styles.stepItem}>
            <div className={styles.stepNumber}>4</div>
            <p className={styles.stepLabel}>Production pré-rapport</p>
            <p className={styles.stepDesc}>
              Import du PEA/PAA annoté, génération du Pré-Rapport (PRE)
              et du Document d&apos;Analyse Contradictoire (DAC)
            </p>
          </div>
          <div className={styles.stepItem}>
            <div className={styles.stepNumber}>5</div>
            <p className={styles.stepLabel}>Finalisation et archivage</p>
            <p className={styles.stepDesc}>
              Import du rapport final, création de l&apos;archive ZIP
              avec timbre d&apos;horodatage SHA-256
            </p>
          </div>
        </div>
      </section>

      {/* Sécurité */}
      <div className={styles.securityBox}>
        <p className={styles.securityTitle}>🔒 Sécurité et confidentialité</p>
        <p className={styles.securityText}>
          Toutes vos données d&apos;expertise restent exclusivement sur votre PC.
          Le modèle d&apos;IA (Mistral 7B) tourne en local via Ollama. Aucune
          donnée sensible ne transite par nos serveurs ni par Internet.
        </p>
      </div>
    </div>
  );
}
