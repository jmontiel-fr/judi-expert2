import styles from "../(legal)/legal.module.css";

export const metadata = {
  title: "Mentions légales — Judi-expert",
  description: "Mentions légales du site Judi-expert",
};

export default function MentionsLegalesPage() {
  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Mentions légales</h1>
      <p className={styles.subtitle}>
        Informations légales relatives au site Judi-expert.
      </p>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Éditeur du site</h2>
        <p className={styles.paragraph}>
          Le site Judi-expert est édité par la société <strong>ITechSource</strong>.
        </p>
        <ul className={styles.list}>
          <li>Raison sociale : ITechSource <span className={styles.placeholder}>[forme juridique à préciser]</span></li>
          <li>Siège social : <span className={styles.placeholder}>[adresse à préciser]</span></li>
          <li>Capital social : <span className={styles.placeholder}>[montant à préciser]</span></li>
          <li>RCS : <span className={styles.placeholder}>[numéro RCS à préciser]</span></li>
          <li>SIRET : <span className={styles.placeholder}>[numéro SIRET à préciser]</span></li>
          <li>Numéro de TVA intracommunautaire : <span className={styles.placeholder}>[numéro TVA à préciser]</span></li>
        </ul>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Directeur de publication</h2>
        <p className={styles.paragraph}>
          Le directeur de la publication est <span className={styles.placeholder}>[nom et prénom du directeur de publication à préciser]</span>, en qualité de <span className={styles.placeholder}>[fonction à préciser]</span> de la société ITechSource.
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Hébergement</h2>
        <p className={styles.paragraph}>
          Le site est hébergé par Amazon Web Services (AWS).
        </p>
        <ul className={styles.list}>
          <li>Amazon Web Services EMEA SARL</li>
          <li>38 avenue John F. Kennedy, L-1855 Luxembourg</li>
          <li>Site web : <a href="https://aws.amazon.com" target="_blank" rel="noopener noreferrer">https://aws.amazon.com</a></li>
        </ul>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Contact</h2>
        <p className={styles.paragraph}>
          Pour toute question relative au site Judi-expert, vous pouvez nous contacter :
        </p>
        <ul className={styles.list}>
          <li>Email : <span className={styles.placeholder}>[email de contact à préciser]</span></li>
          <li>Téléphone : <span className={styles.placeholder}>[numéro de téléphone à préciser]</span></li>
          <li>Adresse postale : <span className={styles.placeholder}>[adresse postale à préciser]</span></li>
        </ul>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Propriété intellectuelle</h2>
        <p className={styles.paragraph}>
          L&apos;ensemble du contenu du site Judi-expert (textes, images, graphismes, logo, icônes, logiciels, base de données) est la propriété exclusive d&apos;ITechSource ou de ses partenaires et est protégé par les lois françaises et internationales relatives à la propriété intellectuelle.
        </p>
        <p className={styles.paragraph}>
          Toute reproduction, représentation, modification, publication, adaptation de tout ou partie des éléments du site, quel que soit le moyen ou le procédé utilisé, est interdite sans l&apos;autorisation écrite préalable d&apos;ITechSource.
        </p>
        <p className={styles.paragraph}>
          Le logiciel Judi-expert utilise exclusivement des composants open-source sous licences compatibles avec un usage commercial. L&apos;inventaire complet des licences est disponible dans la documentation du projet.
        </p>
      </section>

      <p className={styles.lastUpdated}>
        Dernière mise à jour : <span className={styles.placeholder}>[date à préciser]</span>
      </p>
    </div>
  );
}
