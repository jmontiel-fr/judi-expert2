"use client";

import { useState } from "react";
import styles from "./faq.module.css";

interface FAQItem {
  question: string;
  answer: string;
}

interface FAQSection {
  title: string;
  items: FAQItem[];
}

const FAQ_DATA: FAQSection[] = [
  {
    title: "Installation et configuration",
    items: [
      {
        question: "Quels sont les prérequis pour installer l'application locale ?",
        answer:
          "Votre PC doit disposer d'un processeur multi-cœurs récent, d'au moins 16 Go de RAM, de 50 Go d'espace disque disponible et d'un chiffrement de disque activé (BitLocker ou équivalent). Le programme d'installation vérifie automatiquement ces conditions.",
      },
      {
        question: "Comment installer l'application locale ?",
        answer:
          "Téléchargez le package d'installation depuis la page Téléchargements, puis lancez l'installateur. Il installe automatiquement le runtime Docker et les conteneurs nécessaires. Au premier lancement, vous devrez définir un mot de passe local et sélectionner votre domaine d'expertise.",
      },
      {
        question: "Comment configurer mon domaine d'expertise ?",
        answer:
          "Lors du premier lancement, sélectionnez votre domaine dans la liste proposée. Vous pourrez ensuite télécharger le module RAG correspondant depuis le menu Configuration, puis importer votre trame d'entretien (TPE) et votre template de rapport au format Word.",
      },
    ],
  },
  {
    title: "Tickets et workflow",
    items: [
      {
        question: "Comment acheter un ticket d'expertise ?",
        answer:
          "Connectez-vous à votre espace personnel sur le site central, puis accédez à la section Tickets. Le paiement s'effectue en ligne via Stripe. Une fois le paiement confirmé, le ticket est généré et envoyé par email.",
      },
      {
        question: "Comment fonctionne le workflow d'expertise ?",
        answer:
          "Chaque dossier suit 4 étapes séquentielles : Step 0 (extraction OCR de la réquisition), Step 1 (génération du plan d'entretien QMEC), Step 2 (upload des notes d'entretien et du rapport brut), Step 3 (génération du rapport final et du rapport auxiliaire). Chaque étape doit être validée avant de passer à la suivante.",
      },
      {
        question: "Puis-je revenir en arrière une fois une étape validée ?",
        answer:
          "Non. Une fois une étape validée, elle est verrouillée et ne peut plus être modifiée. Cela garantit l'intégrité du processus d'expertise. Assurez-vous de vérifier chaque étape avant de la valider.",
      },
    ],
  },
  {
    title: "Confidentialité et données",
    items: [
      {
        question: "Mes données d'expertise sont-elles envoyées sur un serveur ?",
        answer:
          "Non. Toutes les données d'expertise restent exclusivement sur votre PC. L'application locale fonctionne de manière autonome grâce aux conteneurs Docker. Seuls les tickets transitent entre votre application et le site central pour la vérification.",
      },
      {
        question: "Comment mes données sont-elles protégées ?",
        answer:
          "L'application exige un chiffrement de disque (BitLocker ou équivalent) comme prérequis d'installation. Les données sont stockées localement dans une base SQLite chiffrée. Aucune donnée sensible ne transite par nos serveurs.",
      },
    ],
  },
  {
    title: "Intelligence artificielle",
    items: [
      {
        question: "Quel modèle d'IA est utilisé ?",
        answer:
          "Judi-expert utilise Mistral 7B Instruct v0.3, un modèle open-source sous licence Apache 2.0, optimisé pour le français. Il fonctionne entièrement en local sur votre PC via Ollama, sans aucun appel à un service cloud.",
      },
      {
        question: "L'IA remplace-t-elle l'expert ?",
        answer:
          "Non. L'IA intervient uniquement comme assistant. L'expert conserve le contrôle total sur chaque étape du processus : il peut modifier le Markdown extrait, ajuster le plan d'entretien, et valider chaque document généré. Un document de méthodologie est fourni pour justifier l'usage de l'IA auprès des instances judiciaires.",
      },
      {
        question: "Judi-expert est-il conforme à l'AI Act européen ?",
        answer:
          "Oui. Judi-expert est conçu dans le respect de l'AI Act européen. L'IA est utilisée comme outil d'assistance, l'expert reste décisionnaire à chaque étape, et toutes les données restent sur le poste de l'expert, garantissant la souveraineté des données et la conformité RGPD.",
      },
    ],
  },
];

function FAQAccordionItem({ item }: { item: FAQItem }) {
  const [open, setOpen] = useState(false);

  return (
    <div className={styles.item}>
      <button
        className={styles.question}
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
      >
        <span>{item.question}</span>
        <span className={`${styles.chevron} ${open ? styles.chevronOpen : ""}`}>
          ▼
        </span>
      </button>
      {open && <div className={styles.answer}>{item.answer}</div>}
    </div>
  );
}

export default function FAQPage() {
  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Questions fréquentes</h1>
      <p className={styles.subtitle}>
        Retrouvez les réponses aux questions les plus courantes sur Judi-expert.
      </p>

      {FAQ_DATA.map((section) => (
        <div key={section.title} className={styles.section}>
          <h2 className={styles.sectionTitle}>{section.title}</h2>
          {section.items.map((item) => (
            <FAQAccordionItem key={item.question} item={item} />
          ))}
        </div>
      ))}
    </div>
  );
}
