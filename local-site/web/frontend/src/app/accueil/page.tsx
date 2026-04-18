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
            un workflow en 4 étapes guidées par l&apos;IA.
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
            Générez automatiquement le rapport final et le rapport auxiliaire
            d&apos;analyse au format Word.
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
          Chaque dossier suit 4 étapes séquentielles assistées par l&apos;IA.
        </p>
        <div className={styles.stepsRow}>
          <div className={styles.stepItem}>
            <div className={styles.stepNumber}>0</div>
            <p className={styles.stepLabel}>Extraction</p>
            <p className={styles.stepDesc}>
              OCR de la réquisition PDF en Markdown structuré
            </p>
          </div>
          <div className={styles.stepItem}>
            <div className={styles.stepNumber}>1</div>
            <p className={styles.stepLabel}>Plan d&apos;entretien</p>
            <p className={styles.stepDesc}>
              Génération du QMEC à partir des questions du tribunal
            </p>
          </div>
          <div className={styles.stepItem}>
            <div className={styles.stepNumber}>2</div>
            <p className={styles.stepLabel}>Notes &amp; rapport brut</p>
            <p className={styles.stepDesc}>
              Upload de vos notes d&apos;entretien et du rapport brut
            </p>
          </div>
          <div className={styles.stepItem}>
            <div className={styles.stepNumber}>3</div>
            <p className={styles.stepLabel}>Rapport final</p>
            <p className={styles.stepDesc}>
              Génération du rapport final et du rapport auxiliaire
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
