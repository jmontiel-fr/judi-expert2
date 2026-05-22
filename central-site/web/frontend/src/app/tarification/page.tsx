import { buildPageMetadata } from "@/lib/seo";
import styles from "./tarification.module.css";

export const metadata = buildPageMetadata({
  title: "Tarification",
  description:
    "Tarifs Judi-Expert à l'acte par dossier d'expertise. Offre de lancement : 2 dossiers gratuits pour le premier achat. Module psychologie disponible.",
  path: "/tarification",
});

export default function TarificationPage() {
  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Tarification</h1>
      <p className={styles.subtitle}>
        Judi-Expert fonctionne à l&apos;acte, par module d&apos;expertise.
        Chaque dossier consomme un ticket.
      </p>

      {/* Offre de lancement */}
      <div className={styles.promoBox}>
        <div className={styles.promoIcon}>🎁</div>
        <div>
          <h2 className={styles.promoTitle}>Offre de lancement</h2>
          <p className={styles.promoText}>
            <strong>2 dossiers gratuits</strong> pour le premier dossier acheté.
            Offre valable sur votre premier achat de ticket.
          </p>
        </div>
      </div>

      {/* Grille tarifaire */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Tarifs par module</h2>
        <p className={styles.sectionSubtitle}>
          La tarification est à l&apos;acte : vous achetez des tickets
          correspondant à votre domaine d&apos;expertise.
        </p>

        <div className={styles.pricingGrid}>
          {/* Module Psychologie */}
          <div className={`${styles.pricingCard} ${styles.pricingCardActive}`}>
            <div className={styles.pricingBadge}>Disponible</div>
            <div className={styles.pricingIcon}>🩺</div>
            <h3 className={styles.pricingName}>Psychologie</h3>
            <div className={styles.pricingPrice}>
              <span className={styles.priceAmount}>49€</span>
              <span className={styles.priceUnit}>HT / dossier</span>
            </div>
            <ul className={styles.pricingFeatures}>
              <li>Corpus spécialisé psychologie judiciaire</li>
              <li>Trames d&apos;entretien adaptées</li>
              <li>Modèle de rapport pré-configuré</li>
              <li>Workflow complet en 5 étapes</li>
              <li>2 dossiers gratuits pour le premier dossier acheté</li>
            </ul>
          </div>

          {/* Module Psychiatrie */}
          <div className={styles.pricingCard}>
            <div className={styles.pricingBadgeInactive}>Prochainement</div>
            <div className={styles.pricingIcon}>🧠</div>
            <h3 className={styles.pricingName}>Psychiatrie</h3>
            <div className={styles.pricingPrice}>
              <span className={styles.priceAmountMuted}>—</span>
            </div>
            <ul className={styles.pricingFeatures}>
              <li>Corpus psychiatrie judiciaire</li>
              <li>Trames spécifiques psychiatrie</li>
              <li>Modèle de rapport adapté</li>
            </ul>
          </div>

          {/* Module Médecine légale */}
          <div className={styles.pricingCard}>
            <div className={styles.pricingBadgeInactive}>Prochainement</div>
            <div className={styles.pricingIcon}>⚕️</div>
            <h3 className={styles.pricingName}>Médecine légale</h3>
            <div className={styles.pricingPrice}>
              <span className={styles.priceAmountMuted}>—</span>
            </div>
            <ul className={styles.pricingFeatures}>
              <li>Corpus médecine légale</li>
              <li>Trames spécifiques</li>
              <li>Modèle de rapport adapté</li>
            </ul>
          </div>

          {/* Module Bâtiment */}
          <div className={styles.pricingCard}>
            <div className={styles.pricingBadgeInactive}>Prochainement</div>
            <div className={styles.pricingIcon}>🏗️</div>
            <h3 className={styles.pricingName}>Bâtiment</h3>
            <div className={styles.pricingPrice}>
              <span className={styles.priceAmountMuted}>—</span>
            </div>
            <ul className={styles.pricingFeatures}>
              <li>Corpus construction et malfaçons</li>
              <li>Normes techniques intégrées</li>
              <li>Modèle de rapport adapté</li>
            </ul>
          </div>

          {/* Module Comptabilité */}
          <div className={styles.pricingCard}>
            <div className={styles.pricingBadgeInactive}>Prochainement</div>
            <div className={styles.pricingIcon}>📊</div>
            <h3 className={styles.pricingName}>Comptabilité</h3>
            <div className={styles.pricingPrice}>
              <span className={styles.priceAmountMuted}>—</span>
            </div>
            <ul className={styles.pricingFeatures}>
              <li>Corpus comptabilité judiciaire</li>
              <li>Analyse financière assistée</li>
              <li>Modèle de rapport adapté</li>
            </ul>
          </div>
        </div>
      </section>

      {/* Fonctionnement */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Comment ça fonctionne ?</h2>
        <div className={styles.howItWorks}>
          <div className={styles.howStep}>
            <div className={styles.howNumber}>1</div>
            <p className={styles.howText}>
              Inscrivez-vous gratuitement, puis achetez votre premier ticket :
              <strong> 2 dossiers gratuits</strong> offerts en plus.
            </p>
          </div>
          <div className={styles.howStep}>
            <div className={styles.howNumber}>2</div>
            <p className={styles.howText}>
              Chaque ticket permet de créer <strong>un dossier d&apos;expertise</strong> complet
              (workflow en 5 étapes).
            </p>
          </div>
          <div className={styles.howStep}>
            <div className={styles.howNumber}>3</div>
            <p className={styles.howText}>
              Achetez des tickets supplémentaires à <strong>49€ HT</strong> l&apos;unité
              via paiement sécurisé Stripe.
            </p>
          </div>
        </div>
      </section>

      {/* Note */}
      <div className={styles.noteBox}>
        <p>
          <strong>Note :</strong> Les inscriptions sont actuellement limitées au
          domaine <strong>psychologie</strong>. Les autres modules seront
          disponibles prochainement avec une tarification adaptée à chaque
          spécialité.
        </p>
      </div>
    </div>
  );
}
