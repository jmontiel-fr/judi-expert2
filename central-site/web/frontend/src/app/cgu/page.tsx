import styles from "../(legal)/legal.module.css";

export const metadata = {
  title: "Conditions Générales d'Utilisation — Judi-expert",
  description: "Conditions générales d'utilisation du service Judi-expert",
};

export default function CGUPage() {
  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Conditions Générales d&apos;Utilisation</h1>
      <p className={styles.subtitle}>
        Les présentes CGU régissent l&apos;utilisation du site et du service Judi-expert.
      </p>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>1. Objet</h2>
        <p className={styles.paragraph}>
          Les présentes Conditions Générales d&apos;Utilisation (ci-après « CGU ») ont pour objet de définir les modalités et conditions d&apos;utilisation du site Judi-expert (ci-après « le Site ») et du service d&apos;assistance aux experts judiciaires (ci-après « le Service »), édités par la société ITechSource.
        </p>
        <p className={styles.paragraph}>
          L&apos;inscription sur le Site implique l&apos;acceptation pleine et entière des présentes CGU. Si vous n&apos;acceptez pas ces conditions, vous ne devez pas utiliser le Service.
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>2. Accès au service</h2>
        <p className={styles.paragraph}>
          Le Site est accessible pendant les horaires bureau, de 8h à 20h (heure de Paris), du lundi au vendredi. En dehors de ces horaires, le Site peut être indisponible pour des raisons de maintenance et d&apos;optimisation des coûts d&apos;hébergement.
        </p>
        <p className={styles.paragraph}>
          ITechSource se réserve le droit de suspendre temporairement l&apos;accès au Site pour des opérations de maintenance, sans préavis ni indemnité.
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>3. Inscription</h2>
        <p className={styles.paragraph}>
          L&apos;utilisation du Service nécessite la création d&apos;un compte utilisateur. L&apos;inscription requiert la fourniture d&apos;informations exactes et à jour : nom, prénom, adresse, domaine d&apos;expertise et adresse email.
        </p>
        <p className={styles.paragraph}>
          L&apos;utilisateur s&apos;engage à :
        </p>
        <ul className={styles.list}>
          <li>Fournir des informations véridiques et complètes lors de l&apos;inscription</li>
          <li>Maintenir la confidentialité de ses identifiants de connexion</li>
          <li>Informer ITechSource de toute utilisation non autorisée de son compte</li>
          <li>Disposer d&apos;un chiffrement de disque actif (BitLocker ou équivalent) sur le poste où l&apos;application locale est installée</li>
        </ul>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>4. Tickets d&apos;expertise</h2>
        <p className={styles.paragraph}>
          La création d&apos;un dossier d&apos;expertise dans l&apos;application locale nécessite un ticket à usage unique, acheté sur le Site via la plateforme de paiement sécurisée Stripe.
        </p>
        <ul className={styles.list}>
          <li>Chaque ticket est associé au domaine d&apos;expertise de l&apos;utilisateur</li>
          <li>Un ticket ne peut être utilisé qu&apos;une seule fois pour la création d&apos;un dossier</li>
          <li>Les tickets achetés ne sont ni remboursables ni échangeables, sauf disposition légale contraire</li>
          <li>Le prix des tickets est indiqué en euros TTC sur le Site</li>
        </ul>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>5. Responsabilités</h2>
        <p className={styles.paragraph}>
          Le Service Judi-expert est un outil d&apos;assistance à la rédaction de rapports d&apos;expertise. Il utilise l&apos;intelligence artificielle comme assistant, conformément à l&apos;AI Act européen.
        </p>
        <div className={styles.highlight}>
          <strong>Important :</strong> L&apos;expert judiciaire reste seul responsable du contenu de ses rapports d&apos;expertise. Les documents générés par le Service constituent une aide à la rédaction et doivent être vérifiés, validés et le cas échéant modifiés par l&apos;expert avant toute utilisation officielle.
        </div>
        <p className={styles.paragraph}>
          ITechSource ne saurait être tenue responsable des conséquences directes ou indirectes résultant de l&apos;utilisation des documents générés par le Service.
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>6. Données personnelles</h2>
        <p className={styles.paragraph}>
          Les données personnelles collectées lors de l&apos;inscription sont traitées conformément à notre <a href="/politique-confidentialite">Politique de confidentialité</a> et au Règlement Général sur la Protection des Données (RGPD).
        </p>
        <div className={styles.highlight}>
          <strong>Principe fondamental :</strong> Toutes les données d&apos;expertise (dossiers, documents, rapports) restent exclusivement sur le PC de l&apos;expert. Aucune donnée d&apos;expertise ne transite par les serveurs d&apos;ITechSource. Seuls les tickets d&apos;expertise transitent entre l&apos;application locale et le Site pour vérification.
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>7. Propriété intellectuelle</h2>
        <p className={styles.paragraph}>
          Le logiciel Judi-expert, son code source, son architecture et sa documentation sont la propriété d&apos;ITechSource. Le Service utilise des composants open-source sous licences compatibles avec un usage commercial (Apache 2.0, MIT, BSD).
        </p>
        <p className={styles.paragraph}>
          Les rapports et documents générés par l&apos;expert à l&apos;aide du Service restent la propriété intellectuelle de l&apos;expert.
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>8. Modification des CGU</h2>
        <p className={styles.paragraph}>
          ITechSource se réserve le droit de modifier les présentes CGU à tout moment. Les utilisateurs seront informés de toute modification par email ou par notification sur le Site. La poursuite de l&apos;utilisation du Service après modification vaut acceptation des nouvelles CGU.
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>9. Droit applicable</h2>
        <p className={styles.paragraph}>
          Les présentes CGU sont régies par le droit français. En cas de litige, les parties s&apos;engagent à rechercher une solution amiable avant toute action judiciaire. À défaut d&apos;accord amiable, les tribunaux compétents de <span className={styles.placeholder}>[ville à préciser]</span> seront seuls compétents.
        </p>
      </section>

      <p className={styles.lastUpdated}>
        Dernière mise à jour : <span className={styles.placeholder}>[date à préciser]</span>
      </p>
    </div>
  );
}
