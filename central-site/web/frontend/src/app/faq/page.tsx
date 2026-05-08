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
          "Chaque dossier suit 5 étapes séquentielles : Step 1 (création dossier — extraction OCR et identification des questions), Step 2 (préparation investigations — génération du plan d'entretien PE ou plan d'analyse PA), Step 3 (consolidation documentaire — import des pièces de diligence), Step 4 (production pré-rapport — génération du PRE et du DAC à partir du plan annoté PEA/PAA), Step 5 (finalisation et archivage — import du rapport final et création de l'archive ZIP avec timbre SHA-256). Entre les étapes 2 et 3, l'expert mène ses entretiens ou analyses hors application (étape E/A). Chaque étape doit être validée avant de passer à la suivante.",
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
      {
        question: "Judi-expert est-il conforme au RGPD pour tous les domaines d'expertise, y compris hors santé ?",
        answer:
          "Oui. Les dossiers d'expertise judiciaire contiennent systématiquement des données personnelles sensibles au sens du RGPD, quel que soit le domaine : identités des parties, données financières en comptabilité, adresses et litiges en bâtiment, données de santé en psychiatrie ou psychologie. Avec Judi-expert, toutes ces données restent exclusivement sur le PC de l'expert. L'IA tourne en local, rien ne sort du poste. La situation RGPD est donc exactement la même que lorsque l'expert rédige son rapport manuellement : le chiffrement du disque et la protection d'accès au poste relèvent de la responsabilité de l'expert, comme c'est déjà le cas aujourd'hui sans IA. Judi-expert n'ajoute aucune contrainte RGPD supplémentaire par rapport à la pratique actuelle. À l'inverse, une solution 100% cloud nécessiterait une analyse d'impact (DPIA), un hébergement souverain, une certification HDS pour les domaines santé, et potentiellement la qualification SecNumCloud de l'ANSSI.",
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
  {
    title: "Sécurité",
    items: [
      {
        question: "Comment les données d'expertise sont-elles protégées ?",
        answer:
          "L'application locale utilise une architecture réseau isolée : les conteneurs IA (LLM, OCR, RAG) fonctionnent dans un réseau Docker interne sans aucun accès à Internet. Seul le backend communique avec le Site Central pour la vérification des tickets. Le chiffrement du disque (BitLocker) est obligatoire. Chaque dossier finalisé est archivé avec un hash SHA-256 pour garantir l'intégrité. Consultez notre page Sécurité pour le détail complet.",
      },
      {
        question: "Les données d'expertise transitent-elles par le cloud ?",
        answer:
          "Non. Toutes les données d'expertise (documents, rapports, notes d'entretien) restent exclusivement sur le PC de l'expert. Seuls les tokens de tickets (codes d'activation) transitent entre l'application locale et le Site Central. L'IA tourne 100% en local.",
      },
      {
        question: "Comment garantir que les conteneurs Docker sont authentiques ?",
        answer:
          "Les images personnalisées (backend, frontend, OCR) sont construites localement à partir du code source. Les images tierces (Ollama pour le LLM, Qdrant pour le RAG) proviennent des registres officiels Docker Hub avec des versions épinglées. En production, les images sont stockées dans un registre privé AWS ECR avec scan de vulnérabilités.",
      },
    ],
  },
  {
    title: "Configuration PC recommandée",
    items: [
      {
        question: "Minimum — PC bureautique (traitement en 5-10 min par étape)",
        answer:
          "Processeur : Intel Core i5 (10e gén.) ou AMD Ryzen 5. RAM : 16 Go. Stockage : SSD 256 Go. GPU : non requis (CPU uniquement). OS : Windows 11 Pro (BitLocker obligatoire). Docker Desktop + WSL 2. Temps de traitement estimé : 5 à 10 minutes par étape IA.",
      },
      {
        question: "Confort — PC performant (traitement en 2-5 min par étape)",
        answer:
          "Processeur : Intel Core i7 (12e gén.) ou AMD Ryzen 7. RAM : 32 Go. Stockage : SSD NVMe 512 Go. GPU : non requis (CPU uniquement). OS : Windows 11 Pro (BitLocker obligatoire). Docker Desktop + WSL 2. Temps de traitement estimé : 2 à 5 minutes par étape IA.",
      },
      {
        question: "Performance — PC avec GPU (traitement en 10-30 sec par étape)",
        answer:
          "Processeur : Intel Core i7/i9 ou AMD Ryzen 7/9. RAM : 32 Go. Stockage : SSD NVMe 1 To. GPU : NVIDIA RTX 3060 (12 Go VRAM) ou supérieur — RTX 4060/4070 recommandé. OS : Windows 11 Pro (BitLocker obligatoire). Drivers NVIDIA + NVIDIA Container Toolkit. Docker Desktop + WSL 2. Temps de traitement estimé : 10 à 30 secondes par étape IA.",
      },
      {
        question: "Pourquoi Windows 11 Pro et BitLocker ?",
        answer:
          "Windows 11 Pro est requis pour activer BitLocker, le chiffrement de disque intégré de Microsoft. Le chiffrement du disque est obligatoire pour protéger les données d'expertise judiciaire conformément au RGPD et à la réglementation sur les données sensibles. BitLocker est activé par défaut sur Windows 11 Pro avec un compte Microsoft.",
      },
      {
        question: "Comment activer le GPU pour accélérer l'IA ?",
        answer:
          "Si votre PC dispose d'une carte NVIDIA, installez les drivers NVIDIA récents et le NVIDIA Container Toolkit. L'application détecte automatiquement le GPU au démarrage et l'utilise pour l'inférence IA. Aucune configuration manuelle n'est nécessaire.",
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
