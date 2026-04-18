import styles from "./landing.module.css";

export default function HomePage() {
  return (
    <>
      {/* ===== Section Accueil / Hero ===== */}
      <section className={styles.hero}>
        <div className={styles.heroColumns}>
          <div className={styles.heroImageCol}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/judi-expert-img1.jpg"
              alt="Judi-Expert — assistance IA pour experts judiciaires"
              className={styles.heroImage}
            />
          </div>
          <div className={styles.heroTextCol}>
            <h1 className={styles.heroTitle}>
              Réduisez de 50% votre temps de production des dossiers
              d&apos;expertise avec l&apos;IA
            </h1>
            <p className={styles.heroSubtitle}>
              Une solution d&apos;assistance aux experts judiciaires,
              multi-domaines, garantissant qualité professionnelle, conformité
              RGPD et strict respect de l&apos;AI Act européen.
            </p>
            <p className={styles.heroSubtitle}>
              Vos données d&apos;expertise restent exclusivement sur votre PC.
              Aucune donnée sensible ne transite par nos serveurs ni par
              Internet.
            </p>
            <span className={styles.heroBadge}>
              🕐 Le site est ouvert pendant les horaires bureau de 8h à 20h
            </span>
          </div>
        </div>
      </section>

      {/* ===== Section Domaines Couverts ===== */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Domaines couverts</h2>
        <p className={styles.sectionSubtitle}>
          Judi-expert couvre plusieurs domaines d&apos;expertise judiciaire avec
          des corpus spécialisés et des trames adaptées.
        </p>
        <div className={styles.domainesGrid}>
          <div className={styles.domaineCard}>
            <div className={styles.domaineIcon}>🩺</div>
            <h3 className={styles.domaineTitle}>Santé</h3>
            <p className={styles.domaineDesc}>
              Psychologie, psychiatrie et médecine légale. Corpus de référence
              incluant guides méthodologiques, textes réglementaires et
              référentiels de bonnes pratiques.
            </p>
          </div>
          <div className={styles.domaineCard}>
            <div className={styles.domaineIcon}>🏗️</div>
            <h3 className={styles.domaineTitle}>Bâtiment</h3>
            <p className={styles.domaineDesc}>
              Expertise en construction, malfaçons, sinistres et conformité des
              ouvrages. Normes techniques et jurisprudence spécialisée.
            </p>
          </div>
          <div className={styles.domaineCard}>
            <div className={styles.domaineIcon}>📊</div>
            <h3 className={styles.domaineTitle}>Comptabilité</h3>
            <p className={styles.domaineDesc}>
              Expertise comptable et financière judiciaire. Analyse de comptes,
              évaluation de préjudices et détection d&apos;anomalies.
            </p>
          </div>
        </div>
      </section>

      {/* ===== Section Comment ça marche ===== */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Comment ça marche ?</h2>
        <p className={styles.sectionSubtitle}>
          Un processus simple en 4 étapes pour démarrer avec Judi-expert.
        </p>
        <div className={styles.stepsRow}>
          <div className={styles.stepItem}>
            <div className={styles.stepNumber}>1</div>
            <p className={styles.stepLabel}>Inscription</p>
            <p className={styles.stepDesc}>
              Créez votre compte expert en quelques minutes et sélectionnez
              votre domaine d&apos;expertise.
            </p>
          </div>
          <div className={styles.stepItem}>
            <div className={styles.stepNumber}>2</div>
            <p className={styles.stepLabel}>Téléchargement</p>
            <p className={styles.stepDesc}>
              Téléchargez et installez l&apos;application locale sur votre PC.
              Elle fonctionne de manière autonome.
            </p>
          </div>
          <div className={styles.stepItem}>
            <div className={styles.stepNumber}>3</div>
            <p className={styles.stepLabel}>Configuration</p>
            <p className={styles.stepDesc}>
              Configurez votre domaine, importez votre trame d&apos;entretien et
              votre template de rapport.
            </p>
          </div>
          <div className={styles.stepItem}>
            <div className={styles.stepNumber}>4</div>
            <p className={styles.stepLabel}>Achat de tickets</p>
            <p className={styles.stepDesc}>
              Achetez des tickets d&apos;expertise en ligne via Stripe pour
              créer vos dossiers.
            </p>
          </div>
          <div className={styles.stepItem}>
            <div className={styles.stepNumber}>5</div>
            <p className={styles.stepLabel}>Production du rapport</p>
            <p className={styles.stepDesc}>
              Lancez le workflow d&apos;expertise pour produire le rapport final
              assisté par l&apos;IA.
            </p>
          </div>
        </div>
        <div className={styles.dataNotice}>
          🔒 Toutes les données d&apos;expertise restent exclusivement sur le PC
          de l&apos;expert. Seuls les tickets transitent entre votre application
          et le site central.
        </div>
      </section>

      {/* ===== Section Workflow d'expertise ===== */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Workflow d&apos;expertise</h2>
        <p className={styles.sectionSubtitle}>
          Chaque dossier suit un workflow en 4 étapes séquentielles assistées par
          l&apos;IA.
        </p>
        <div className={styles.workflowContainer}>
          <p className={styles.workflowExample}>
            Exemple : expertise en psychologie judiciaire
          </p>
          <div className={styles.workflowSteps}>
            <div className={styles.workflowStep}>
              <div className={styles.workflowBadge}>Step 0</div>
              <p className={styles.workflowStepTitle}>Extraction</p>
              <p className={styles.workflowStepDesc}>
                Conversion de la réquisition PDF-scan en Markdown via OCR et IA
              </p>
            </div>
            <span className={styles.workflowArrow}>→</span>
            <div className={styles.workflowStep}>
              <div className={styles.workflowBadge}>Step 1</div>
              <p className={styles.workflowStepTitle}>Préparation entretien</p>
              <p className={styles.workflowStepDesc}>
                Génération du plan d&apos;entretien à partir des questions du
                tribunal et de la trame
              </p>
            </div>
            <span className={styles.workflowArrow}>→</span>
            <div className={styles.workflowStep}>
              <div className={styles.workflowBadge}>Step 2</div>
              <p className={styles.workflowStepTitle}>Mise en forme RE-Projet</p>
              <p className={styles.workflowStepDesc}>
                Upload du NEA (Notes d&apos;Entretien et Analyse) et production
                du RE-Projet et RE-Projet-Auxiliaire par l&apos;IA
              </p>
            </div>
            <span className={styles.workflowArrow}>→</span>
            <div className={styles.workflowStep}>
              <div className={styles.workflowBadge}>Step 3</div>
              <p className={styles.workflowStepTitle}>Upload / Compression dossier final</p>
              <p className={styles.workflowStepDesc}>
                Upload du REF (rapport d&apos;expertise final) par l&apos;expert,
                génération de l&apos;archive et du timbre à horodater.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ===== Section Conformité AI Act ===== */}
      <section className={styles.section}>
        <div className={styles.aiActBox}>
          <h2 className={styles.aiActTitle}>
            Conformité réglementaire AI Act
          </h2>
          <p className={styles.aiActText}>
            Judi-expert est conçu dans le respect de l&apos;AI Act européen.
            L&apos;IA intervient uniquement comme assistant à l&apos;expert, qui
            conserve le contrôle total sur chaque étape du processus
            d&apos;expertise. Toutes les données restent sur le poste de
            l&apos;expert, garantissant la souveraineté des données et la
            conformité RGPD. Un document de méthodologie détaillé est fourni pour
            justifier l&apos;usage de l&apos;IA auprès des instances
            judiciaires.
          </p>
        </div>
      </section>
    </>
  );
}
