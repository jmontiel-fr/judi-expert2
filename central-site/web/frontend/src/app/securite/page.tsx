import styles from "./securite.module.css";

export default function SecuritePage() {
  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Sécurité</h1>
      <p className={styles.subtitle}>
        Judi-Expert est conçu avec la sécurité comme priorité absolue pour
        protéger les données sensibles d&apos;expertise judiciaire.
      </p>

      <section className={styles.section}>
        <h2>🔒 Isolation réseau de l&apos;application locale</h2>
        <p>
          Les conteneurs IA (LLM, OCR, RAG) fonctionnent dans un réseau Docker
          interne <strong>sans aucun accès à Internet</strong>. Les données
          d&apos;expertise ne peuvent physiquement pas fuiter vers l&apos;extérieur,
          même en cas de compromission d&apos;un conteneur ou de présence d&apos;un
          logiciel malveillant sur le PC.
        </p>
        <p>
          Seul le backend communique avec le Site Central pour la vérification
          des tickets d&apos;activation. Aucune donnée d&apos;expertise ne transite
          par cette connexion.
        </p>
      </section>

      <section className={styles.section}>
        <h2>🛡️ Chiffrement des données</h2>
        <ul>
          <li><strong>Au repos</strong> : BitLocker (Windows 11 Pro) ou FileVault (macOS) obligatoire</li>
          <li><strong>En transit</strong> : HTTPS/TLS 1.3 pour les communications avec le Site Central</li>
          <li><strong>Intégrité</strong> : hash SHA-256 de l&apos;archive finale de chaque dossier</li>
        </ul>
      </section>

      <section className={styles.section}>
        <h2>🏗️ Intégrité des conteneurs</h2>
        <ul>
          <li>Images Docker épinglées par version (pas de tag <code>latest</code> en production)</li>
          <li>Images personnalisées construites localement depuis le code source</li>
          <li>Images tierces (Ollama, Qdrant) depuis les registres officiels Docker Hub</li>
          <li>Scan de vulnérabilités via AWS ECR en production</li>
        </ul>
      </section>

      <section className={styles.section}>
        <h2>🤖 IA locale et souveraine</h2>
        <p>
          Le modèle d&apos;IA (Mistral 7B) tourne <strong>entièrement en local</strong> sur
          le PC de l&apos;expert via Ollama. Aucune requête n&apos;est envoyée à un
          service cloud d&apos;IA (OpenAI, Google, etc.). Le modèle est open-source
          (licence Apache 2.0) et auditable.
        </p>
      </section>

      <section className={styles.section}>
        <h2>🔐 Authentification</h2>
        <ul>
          <li><strong>Site Central</strong> : AWS Cognito (OAuth 2.0 / OpenID Connect), MFA recommandé</li>
          <li><strong>Application locale</strong> : JWT local (HS256) avec vérification via le Site Central</li>
          <li>Pas de stockage de mot de passe en local</li>
        </ul>
      </section>

      <section className={styles.section}>
        <h2>📋 Conformité</h2>
        <ul>
          <li><strong>RGPD</strong> : données traitées localement, droit à l&apos;effacement, minimisation des données</li>
          <li><strong>AI Act européen</strong> : IA comme assistant, validation humaine à chaque étape</li>
          <li><strong>Expertise judiciaire</strong> : traçabilité, horodatage, hash d&apos;intégrité</li>
        </ul>
      </section>

      <section className={styles.section}>
        <h2>🏢 Sécurité du Site Central (AWS)</h2>
        <ul>
          <li>Hébergement AWS (ECS Fargate, RDS PostgreSQL) en région eu-west-3 (Paris)</li>
          <li>HTTPS obligatoire via CloudFront + certificat ACM</li>
          <li>Base de données chiffrée au repos (AES-256)</li>
          <li>Secrets gérés via AWS Secrets Manager</li>
          <li>Paiements sécurisés via Stripe (PCI DSS)</li>
          <li>Protection anti-bot : reCAPTCHA sur les formulaires</li>
          <li>Logs et monitoring via CloudWatch</li>
        </ul>
      </section>
    </div>
  );
}
