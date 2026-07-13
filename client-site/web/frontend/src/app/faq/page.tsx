"use client";

import { useState, useMemo } from "react";
import styles from "./faq.module.css";

const SITE_CENTRAL_URL = process.env.NEXT_PUBLIC_SITE_CENTRAL_URL || "http://localhost:3001";

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
    title: "Installation et prérequis",
    items: [
      {
        question: "Quels sont les prérequis matériels pour le Site Client ?",
        answer:
          "Votre PC doit disposer d'un processeur multi-cœurs récent, d'au moins 16 Go de RAM, de 50 Go d'espace disque disponible et d'un chiffrement de disque activé (BitLocker sous Windows, FileVault sous macOS). Docker Desktop doit être installé.",
      },
      {
        question: "Comment installer le Site Client ?",
        answer:
          "Téléchargez le package d'installation depuis la page Téléchargements du site central, puis lancez l'installateur. Il configure automatiquement Docker et les conteneurs nécessaires (backend, frontend, OCR, LLM, RAG).",
      },
      {
        question: "Docker Desktop ne démarre pas, que faire ?",
        answer:
          "Vérifiez que la virtualisation est activée dans le BIOS de votre PC (Intel VT-x ou AMD-V). Sous Windows, assurez-vous que WSL 2 est installé. Redémarrez Docker Desktop. Si le problème persiste, relancez votre PC.",
      },
      {
        question: "Comment mettre à jour l'application ?",
        answer:
          "Les mises à jour mineures (code des conteneurs) s'appliquent automatiquement depuis l'application. Pour les mises à jour majeures (nouvelle configuration), téléchargez la dernière version de l'installateur depuis le Site Central et relancez-le. Vos données (dossiers, configuration) sont automatiquement préservées dans les deux cas.",
      },
    ],
  },
  {
    title: "Configuration",
    items: [
      {
        question: "Comment configurer mon domaine d'expertise ?",
        answer:
          "Accédez à la page Configuration depuis le menu. Sélectionnez votre domaine, téléchargez le module RAG correspondant, puis importez votre TRE (Template de Rapport d'Expertise) au format Word.",
      },
      {
        question: "Comment importer mon TRE personnalisé ?",
        answer:
          "Dans Configuration, section TRE / Template rapport, importez votre fichier tre.docx. Il sera utilisé au Step 2 (validation → PREA) du workflow standard.",
      },
      {
        question: "Comment importer mon template de rapport Word ?",
        answer:
          "Le TRE (tre.docx) sert de template central pour le workflow standard. Importez-le dans Configuration ; il contient les placeholders <<...>> et annotations @type@ utilisés aux Steps 2, E/A et 4.",
      },
      {
        question: "Puis-je changer de domaine d'expertise ?",
        answer:
          "Oui, vous pouvez changer de domaine dans la page Configuration. Vous devrez télécharger le nouveau module RAG correspondant. Les dossiers existants conservent le domaine avec lequel ils ont été créés.",
      },
    ],
  },
  {
    title: "Workflow d'expertise",
    items: [
      {
        question: "Comment créer un nouveau dossier d'expertise ?",
        answer:
          "Depuis la page Dossiers, cliquez sur « Nouveau dossier ». Saisissez un nom, le token du ticket, puis choisissez le type de workflow : Standard (5 étapes + Step E/A) ou Simple (2 étapes — PRE déjà rédigé).",
      },
      {
        question: "Quelles sont les étapes du workflow standard ?",
        answer:
          "Step 1 — Création dossier (OCR ordonnance, placeholders, questions). Step 2 — Validation TRE → PREA. Step 3 — Consolidation documentaire (pièces de diligence). Step E/A — Entretien ou Analyse hors application (après Step 3) : enrichissement du PREA. Step 4 — Production PRE (+ DAC optionnel) depuis le PREA complété. Step 5 — Import REF, archivage ZIP + timbre SHA-256.",
      },
      {
        question: "Qu'est-ce que le workflow simple ?",
        answer:
          "Pour les expertises où le PRE (pre.docx) est déjà rédigé : Step 1 — mise en forme linguistique → PREF (relance possible) + DAC optionnel ; Step 2 — archivage ZIP + timbre. Deux étapes seulement.",
      },
      {
        question: "Puis-je modifier le texte extrait par l'OCR ?",
        answer:
          "Oui, au Step 1 du workflow standard. Vérifiez et corrigez le Markdown avant de valider l'étape.",
      },
      {
        question: "Puis-je revenir en arrière une fois une étape validée ?",
        answer:
          "Non. Une étape validée est verrouillée. Utilisez Reset avant validation si vous devez recommencer (dossier actif).",
      },
      {
        question: "Comment télécharger le rapport final ?",
        answer:
          "Workflow standard : téléchargez le PRE au Step 4, ajustez-le hors application en REF, importez-le au Step 5 puis archivez. Workflow simple : le PREF est produit au Step 1 ; l'archive est générée au Step 2.",
      },
      {
        question: "Où sont stockés mes dossiers ?",
        answer:
          "Vos dossiers d'expertise sont stockés exclusivement sur votre PC, dans le répertoire C:\\judi-expert\\ (par défaut). " +
          "Ce répertoire contient :\n\n" +
          "• judi-expert.db — la base de données locale (métadonnées des dossiers)\n" +
          "• config/ — votre configuration (TRE, templates, paramètres)\n" +
          "• Un sous-répertoire par dossier, portant son nom (ex : Expertise Dupont 2026/)\n\n" +
          "Chaque dossier contient des sous-répertoires step1/ à step5/, chacun avec :\n" +
          "• in/ — fichiers d'entrée (vos uploads : PDF, .docx)\n" +
          "• out/ — fichiers de sortie (générés par l'IA : .md, .docx)\n\n" +
          "Aucune donnée ne quitte votre machine. Seul le token du ticket transite vers le Site Central lors de la création d'un dossier.",
      },
    ],
  },
  {
    title: "ChatBot",
    items: [
      {
        question: "À quoi sert le ChatBot ?",
        answer:
          "Le ChatBot vous permet de poser des questions sur votre domaine d'expertise. Il utilise le corpus RAG local pour fournir des réponses contextualisées basées sur les documents de référence de votre spécialité.",
      },
      {
        question: "Le ChatBot envoie-t-il mes questions sur Internet ?",
        answer:
          "Non. Le ChatBot fonctionne entièrement en local. Le modèle d'IA (Mistral 7B) tourne sur votre PC via Ollama. Aucune donnée ne quitte votre machine.",
      },
    ],
  },
  {
    title: "Tickets",
    items: [
      {
        question: "Où acheter un ticket d'expertise ?",
        answer:
          "Les tickets s'achètent sur le site central (judi-expert.fr), dans votre espace personnel, section Tickets. Le paiement s'effectue via Stripe.",
      },
      {
        question: "Un ticket peut-il être utilisé plusieurs fois ?",
        answer:
          "Non. Chaque ticket est à usage unique. Une fois associé à un dossier, il ne peut plus être réutilisé.",
      },
    ],
  },
  {
    title: "Dépannage",
    items: [
      {
        question: "L'application affiche « Service indisponible », que faire ?",
        answer:
          "Vérifiez que Docker Desktop est démarré et que tous les conteneurs sont en cours d'exécution. Relancez l'application avec le script restart.sh. Si le problème persiste, consultez les logs Docker.",
      },
      {
        question: "L'OCR ne fonctionne pas ou donne un résultat vide.",
        answer:
          "Assurez-vous que le fichier PDF est lisible (pas protégé par mot de passe). Pour les PDF scannés, la qualité du scan influence directement le résultat. Essayez avec un scan de meilleure résolution (300 DPI minimum).",
      },
      {
        question: "Le modèle LLM est très lent ou ne répond pas.",
        answer:
          "Le modèle Mistral 7B nécessite au moins 8 Go de RAM disponible. Fermez les applications gourmandes en mémoire. Au premier lancement, le téléchargement du modèle peut prendre plusieurs minutes selon votre connexion.",
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
        <span className={`${styles.chevron} ${open ? styles.chevronOpen : ""}`}>▼</span>
      </button>
      {open && <div className={styles.answer}>{item.answer}</div>}
    </div>
  );
}

export default function FAQPage() {
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    if (!search.trim()) return FAQ_DATA;
    const q = search.toLowerCase();
    return FAQ_DATA.map((section) => ({
      ...section,
      items: section.items.filter(
        (item) =>
          item.question.toLowerCase().includes(q) ||
          item.answer.toLowerCase().includes(q)
      ),
    })).filter((section) => section.items.length > 0);
  }, [search]);

  const totalResults = filtered.reduce((sum, s) => sum + s.items.length, 0);

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>FAQ — Site Client</h1>
      <p className={styles.subtitle}>
        Questions fréquentes sur l&apos;installation, la configuration et
        l&apos;utilisation du Site Client Judi-Expert.
      </p>

      <div className={styles.searchRow}>
        <input
          type="text"
          className={styles.searchInput}
          placeholder="Rechercher dans la FAQ…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Rechercher dans la FAQ"
        />
        {search.trim() && (
          <span className={styles.resultCount}>
            {totalResults} résultat{totalResults !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {filtered.length === 0 && (
        <p className={styles.noResults}>
          Aucun résultat pour « {search} ».
        </p>
      )}

      {filtered.map((section) => (
        <div key={section.title} className={styles.section}>
          <h2 className={styles.sectionTitle}>{section.title}</h2>
          {section.items.map((item) => (
            <FAQAccordionItem key={item.question} item={item} />
          ))}
        </div>
      ))}

      <div className={styles.centralLink}>
        <p>
          Vous ne trouvez pas votre réponse ? Consultez la{" "}
          <a
            href={`${SITE_CENTRAL_URL}/faq`}
            target="_blank"
            rel="noopener noreferrer"
          >
            FAQ générale sur le site central ↗
          </a>
        </p>
      </div>
    </div>
  );
}
