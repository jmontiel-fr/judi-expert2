import styles from "../(legal)/legal.module.css";

export const metadata = {
  title: "Politique de confidentialité — Judi-expert",
  description: "Politique de confidentialité et gestion des données personnelles de Judi-expert",
};

export default function PolitiqueConfidentialitePage() {
  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Politique de confidentialité et de gestion des données</h1>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Collecte et conservation des données utilisateurs</h2>
        <p className={styles.paragraph}>
          Lors de l&apos;inscription, nous collectons : nom, prénom, adresse postale, ville,
          code postal, téléphone, email et domaine d&apos;expertise.
        </p>
        <p className={styles.paragraph}>
          Les comptes utilisateurs sont conservés maximum 2 ans. En fin de chaque année,
          les comptes inactifs sont avertis par email et disposent de 30 jours pour se
          reconnecter. Sans connexion dans ce délai, le compte est supprimé automatiquement
          avec toutes les données associées.
        </p>
        <p className={styles.paragraph}>
          Les utilisateurs peuvent demander à tout moment la suppression volontaire de
          leur compte et de leurs données depuis leur espace personnel.
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Données d&apos;expertise — Traitement exclusivement local</h2>
        <div className={styles.highlight}>
          Les données d&apos;expertise (dossiers, réquisitions, notes d&apos;entretien, rapports)
          restent <strong>exclusivement sur le PC de l&apos;expert</strong>. Elles ne sont jamais
          transmises, stockées ni traitées par les serveurs d&apos;ITechSource. Le traitement
          par intelligence artificielle (LLM) s&apos;effectue entièrement en local sur le poste
          de l&apos;expert.
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Logs et statistiques</h2>
        <p className={styles.paragraph}>
          À chaque connexion, la date et l&apos;heure sont enregistrées pour la sécurité des
          comptes. Ces informations permettent de produire des statistiques anonymisées qui
          ne permettent pas d&apos;identifier individuellement un utilisateur.
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Paiements</h2>
        <p className={styles.paragraph}>
          Les paiements sont traités exclusivement via Stripe. Nous conservons uniquement :
          identifiant de transaction, date, montant, type d&apos;opération et email de
          l&apos;utilisateur. Ces données sont conservées pour la durée légale requise (≥ 6 ans).
          <strong> Aucune information bancaire sensible n&apos;est stockée sur notre site.</strong>
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Mesures de protection</h2>
        <ul className={styles.list}>
          <li>Chiffrement des communications (HTTPS/TLS)</li>
          <li>Authentification sécurisée via AWS Cognito</li>
          <li>Paiements sécurisés via Stripe (certifié PCI DSS)</li>
          <li>Suppression des comptes après inactivité ou demande de l&apos;utilisateur</li>
          <li>Anonymisation des statistiques</li>
          <li>Contrôle d&apos;accès aux systèmes et bases de données</li>
          <li>Chiffrement du disque exigé sur le PC de l&apos;expert (BitLocker ou équivalent)</li>
        </ul>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Cookies</h2>
        <p className={styles.paragraph}>
          Ce site utilise uniquement des cookies techniques nécessaires à son fonctionnement
          (authentification, session). Aucun cookie publicitaire ou de suivi n&apos;est utilisé.
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Droits des utilisateurs</h2>
        <p className={styles.paragraph}>
          Conformément au RGPD, vous disposez d&apos;un droit d&apos;accès, de rectification et de
          suppression de vos données personnelles. Pour exercer ces droits, contactez-nous
          via la page <a href="/contact">Contact</a> ou supprimez directement votre compte
          depuis votre espace personnel.
        </p>
        <p className={styles.paragraph}>
          En cas de désaccord, vous pouvez introduire une réclamation auprès de la CNIL :
          {" "}<a href="https://www.cnil.fr" target="_blank" rel="noopener noreferrer">www.cnil.fr</a>.
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Acceptation</h2>
        <p className={styles.paragraph}>
          En utilisant ce site, vous acceptez notre politique de confidentialité et de gestion
          des données telle que décrite ci-dessus.
        </p>
      </section>

      <p className={styles.lastUpdated}>Dernière mise à jour : avril 2026</p>
    </div>
  );
}
