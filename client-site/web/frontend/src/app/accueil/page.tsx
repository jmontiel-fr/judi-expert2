"use client";

import { useState } from "react";
import Link from "next/link";
import styles from "./accueil.module.css";

const SITE_CENTRAL_URL = process.env.NEXT_PUBLIC_SITE_CENTRAL_URL || "http://localhost:3001";

export default function AccueilPage() {
  return (
    <div className={styles.container}>
      {/* Hero */}
      <section className={styles.hero}>
        <h1 className={styles.heroTitle}>
          Bienvenue sur Judi-Expert Site Client
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

      {/* Introduction — Parcours de démarrage */}
      <section className={styles.introSection}>
        <h2 className={styles.sectionTitle}>Parcours de démarrage</h2>
        <p className={styles.sectionSubtitle}>
          Les étapes pour être opérationnel — de l&apos;installation à votre première expertise.
        </p>
        <div className={styles.introFlow}>
          <div className={styles.introStep}>
            <div className={styles.introIcon}>💿</div>
            <h3 className={styles.introStepTitle}>1. Installation</h3>
            <p className={styles.introStepDesc}>
              Lancez l&apos;installateur. Il configure Docker, déploie les conteneurs et télécharge le modèle IA.
            </p>
            <Link href="/guide" className={styles.introBtn}>
              Voir le guide →
            </Link>
          </div>
          <div className={styles.introArrow}>→</div>
          <div className={styles.introStep}>
            <div className={styles.introIcon}>⚙️</div>
            <h3 className={styles.introStepTitle}>2. Configuration</h3>
            <p className={styles.introStepDesc}>
              Domaine d&apos;expertise, corpus RAG, profil matériel. Indispensable avant de créer un dossier.
            </p>
            <Link href="/config" className={styles.introBtn}>
              Configurer →
            </Link>
          </div>
          <div className={styles.introArrow}>→</div>
          <div className={styles.introStep}>
            <div className={styles.introIcon}>📝</div>
            <h3 className={styles.introStepTitle}>3. Personnaliser le TRE</h3>
            <p className={styles.introStepDesc}>
              Préparez votre template de rapport Word avec annotations et placeholders (workflow standard).
            </p>
            <Link href="/guide" className={styles.introBtn}>
              Mode d&apos;emploi TRE →
            </Link>
          </div>
          <div className={styles.introArrow}>→</div>
          <div className={styles.introStep}>
            <div className={styles.introIcon}>🚀</div>
            <h3 className={styles.introStepTitle}>4. Créer un dossier</h3>
            <p className={styles.introStepDesc}>
              Avec un ticket valide, lancez le workflow d&apos;expertise : standard (5 étapes) ou simple (2 étapes).
            </p>
            <Link href="/" className={styles.introBtn}>
              Mes dossiers →
            </Link>
          </div>
        </div>
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
            un workflow en 5 étapes guidées par l&apos;IA.
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
            Générez automatiquement le pré-rapport d&apos;expertise et le
            document d&apos;analyse contradictoire au format Word.
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

      {/* Workflows */}
      <section className={styles.stepsSection}>
        <h2 className={styles.sectionTitle}>Workflows</h2>
        <p className={styles.sectionSubtitle}>
          Deux types de workflow sont disponibles selon votre besoin :
        </p>

        <div className={styles.workflowChoices}>
          <div className={styles.workflowChoiceCard}>
            <h3>📋 Workflow Standard</h3>
            <p>5 étapes + entretien — pour une expertise complète avec investigations, entretien et production du rapport assistée par l&apos;IA.</p>
          </div>
          <div className={styles.workflowChoiceCard}>
            <h3>⚡ Workflow Simplifié</h3>
            <p>2 étapes — pour une mise en forme linguistique d&apos;un rapport déjà rédigé par l&apos;expert (correction orthographe/grammaire + archivage).</p>
          </div>
        </div>

        <div className={styles.workflowNote}>
          <p className={styles.workflowNoteTitle}>📘 Modèle TRE avec annotations</p>
          <p>
            Le workflow standard repose sur un <strong>TRE (Template de Rapport d&apos;Expertise)</strong> :
            votre trame de rapport Word enrichie de <strong>balises d&apos;annotation</strong> (<code>@dires</code>,{" "}
            <code>@analyse</code>, <code>@verbatim</code>, <code>@conclusion</code>, etc.).
          </p>
          <p>
            Lors de l&apos;entretien (Step E/A), vous remplissez les annotations dans le PREA.
            Au Step 4, l&apos;IA reformule les dires en style professionnel, résout les références
            et substitue les placeholders <code>&lt;&lt;nom_pex&gt;&gt;</code> pour produire le pré-rapport.
          </p>
          <p>
            <Link href="/guide" className={styles.workflowNoteLink}>
              Consulter le Guide complet →
            </Link>
          </p>
        </div>

        {/* ═══════════════ Workflow Standard ═══════════════ */}
        <h3 className={styles.workflowSubtitle}>Workflow Standard (5 étapes)</h3>

        <div className={styles.stepsRow}>
          <StepCard
            number="0"
            label="Création de dossier"
            desc="Créer un nouveau dossier en choisissant le type de workflow et en utilisant un ticket d'expertise."
            detail={{
              objectif: "Initialiser un nouveau dossier d'expertise dans l'application.",
              preparation: ["Acheter un ticket d'expertise sur le Site Central (onglet Mon Espace)", "Récupérer le token du ticket reçu par email", "Décider du type de workflow adapté à la mission"],
              entrees: ["Token du ticket (reçu par email après achat)", "Nom du dossier", "Choix du workflow : Standard ou Simple"],
              operation: "Validation du ticket auprès du Site Central, création du dossier et de son arborescence de fichiers.",
              sorties: ["Dossier créé avec ses étapes initialisées"],
              roleExpert: "Choisir le type de workflow adapté à la mission.",
            }}
          />
          <StepCard
            number="1"
            label="Initialisation dossier"
            desc="Import de l'ordonnance, extraction OCR, identification des questions et placeholders."
            detail={{
              objectif: "Importer les fichiers du dossier, extraire le texte par OCR, identifier les questions du tribunal et les valeurs de placeholders.",
              preparation: ["Scanner l'ordonnance de commission d'expert en PDF (≥ 300 dpi)", "Scanner les pièces complémentaires jointes"],
              entrees: ["ordonnance.pdf (PDF-scan de la réquisition)", "piece-xxx.* (pièces complémentaires)"],
              operation: "OCR → Markdown structuré. Extraction des questions Q1…Qn et des placeholders.",
              sorties: ["ordonnance.md", "questions.md", "place_holders.csv"],
              roleExpert: "Vérifier les extractions OCR, valider questions et placeholders.",
            }}
          />
          <StepCard
            number="2"
            label="Validation TRE → PREA"
            desc="Validation syntaxique du TRE et production du PREA pour annotation."
            detail={{
              objectif: "Valider la syntaxe du TRE et produire le PREA (Projet de Rapport d'Expertise Annoté).",
              preparation: ["Vérifier que le TRE est configuré (page Configuration)", "S'assurer que le Step 1 est validé"],
              entrees: ["tre.docx (Template de Rapport d'Expertise)", "placeholders.csv"],
              operation: "Validation syntaxique du TRE puis copie en prea.docx.",
              sorties: ["prea.docx (PREA — document de travail pour l'entretien)"],
              roleExpert: "Télécharger le PREA pour l'annoter lors de l'entretien.",
            }}
          />
          <StepCard
            number="3"
            label="Consolidation documentaire"
            desc="Import des pièces de diligence et extraction OCR."
            detail={{
              objectif: "Importer les pièces complémentaires issues des diligences.",
              preparation: ["Rassembler les pièces reçues en réponse aux diligences", "Scanner les documents papier en PDF"],
              entrees: ["diligence-xxx.* (pièces de diligence : PDF, DOCX, images)"],
              operation: "OCR → extraction du texte en .md pour chaque pièce.",
              sorties: ["diligence-xxx.md (texte extrait)"],
              roleExpert: "Téléverser les pièces, vérifier les extractions OCR.",
            }}
          />
        </div>

        {/* E/A centré */}
        <div className={styles.stepsRowMiddle}>
          <StepCard
            number="E/A"
            label="Entretien ou Analyse"
            desc="L'expert mène ses entretiens hors application et annote le PREA."
            variant="expert"
            detail={{
              objectif: "Réaliser les investigations terrain : entretiens cliniques ou analyses de pièces.",
              preparation: ["Télécharger le prea.docx produit au Step 2", "Planifier les entretiens", "Préparer l'environnement d'entretien"],
              entrees: ["prea.docx (téléchargé au Step 2)"],
              operation: "Hors application : l'expert renseigne les annotations @dires, @analyse, @verbatim dans le PREA.",
              sorties: ["prea.docx (annoté — à réimporter au Step 4)"],
              roleExpert: "Mener les entretiens, remplir les annotations avec dires, observations et analyses.",
            }}
          />
        </div>

        {/* Steps 4 et 5 centrés */}
        <div className={styles.stepsRowBottom}>
          <StepCard
            number="4"
            label="Production pré-rapport"
            desc="Génération du PRE et du DAC à partir du PREA annoté."
            detail={{
              objectif: "Produire le Pré-Rapport d'Expertise (PRE) à partir du PREA complété.",
              preparation: ["Finaliser le PREA : compléter toutes les annotations", "Vérifier les @verbatim entre guillemets", "Importer le PREA finalisé"],
              entrees: ["prea.docx (PREA annoté)", "placeholders.csv"],
              operation: "Reformulation LLM → résolution annotations → substitution placeholders → PRE. Option : DAC.",
              sorties: ["pre.docx (Pré-Rapport)", "dac.docx (optionnel)"],
              roleExpert: "Relire le PRE, affiner les conclusions, ajuster pour produire le REF.",
            }}
          />
          <StepCard
            number="5"
            label="Finalisation et archivage"
            desc="Import du rapport final, archive ZIP + timbre SHA-256."
            detail={{
              objectif: "Archiver le dossier avec horodatage technique.",
              preparation: ["Ajuster le PRE pour obtenir le REF définitif", "Vérifier l'intégralité du rapport"],
              entrees: ["ref.docx (Rapport d'Expertise Final)"],
              operation: "Archive ZIP immuable + timbre (date + hash SHA-256).",
              sorties: ["<dossier>.zip", "<dossier>-timbre.txt"],
              roleExpert: "Importer le rapport final, valider pour archivage définitif.",
            }}
          />
        </div>

        {/* ═══════════════ Workflow Simplifié ═══════════════ */}
        <h3 className={styles.workflowSubtitle}>Workflow Simplifié (2 étapes)</h3>

        <div className={styles.stepsRow}>
          <StepCard
            number="0"
            label="Création de dossier"
            desc="Créer un dossier en mode simple avec un ticket d'expertise."
            detail={{
              objectif: "Initialiser un dossier en workflow simplifié.",
              preparation: ["Acheter un ticket sur le Site Central", "Récupérer le token reçu par email"],
              entrees: ["Token du ticket", "Nom du dossier", "Choix : Simple"],
              operation: "Validation du ticket, création du dossier avec 2 étapes.",
              sorties: ["Dossier créé (2 étapes)"],
              roleExpert: "Avoir déjà rédigé son rapport (PRE) en .docx.",
            }}
          />
          <StepCard
            number="E/A"
            label="Rédaction du PRE"
            desc="L'expert rédige son rapport hors application avant de démarrer le workflow."
            variant="expert"
            detail={{
              objectif: "Rédiger le Pré-Rapport d'Expertise (PRE) manuellement dans Word.",
              preparation: ["Mener les entretiens et analyses", "Rédiger le rapport complet dans Word"],
              entrees: ["Notes d'entretien, observations cliniques"],
              operation: "Hors application : l'expert rédige son PRE avec ses propres outils.",
              sorties: ["pre.docx (Pré-Rapport rédigé par l'expert)"],
              roleExpert: "Rédiger intégralement le rapport. Encadrer les citations entre guillemets pour les protéger de la révision.",
            }}
          />
          <StepCard
            number="1"
            label="Mise en forme linguistique"
            desc="Import du PRE, révision linguistique IA → PREF."
            detail={{
              objectif: "Appliquer une révision linguistique au PRE pour produire le PREF.",
              preparation: ["Rédiger le PRE dans Word", "Encadrer les citations entre guillemets (protégées)", "Enregistrer en .docx"],
              entrees: ["pre.docx (Pré-Rapport rédigé par l'expert)"],
              operation: "Révision LLM (orthographe, grammaire, syntaxe). Préservation des verbatim entre guillemets. Option : génération du DAC.",
              sorties: ["pref.docx (Projet de Rapport Final)", "dac.docx (optionnel)"],
              roleExpert: "Vérifier le PREF, relancer si nécessaire, valider avant archivage.",
            }}
          />
          <StepCard
            number="2"
            label="Archivage"
            desc="Archive ZIP immuable + timbre d'horodatage SHA-256."
            detail={{
              objectif: "Archiver le dossier avec horodatage technique.",
              preparation: ["Vérifier le PREF final", "S'assurer de la version définitive"],
              entrees: ["pref.docx (depuis Step 1 ou version ajustée)"],
              operation: "Archive ZIP + fichier timbre (date + hash SHA-256).",
              sorties: ["<dossier>.zip", "<dossier>-timbre.txt"],
              roleExpert: "Valider l'archivage définitif.",
            }}
          />
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

// ---------------------------------------------------------------------------
// StepCard — carte de step avec "Lire plus..." ouvrant un détail
// ---------------------------------------------------------------------------

interface StepDetail {
  objectif: string;
  preparation?: string[];
  entrees: string[];
  operation: string;
  sorties: string[];
  roleExpert: string;
}

function StepCard({
  number,
  label,
  desc,
  detail,
  variant,
}: {
  number: string;
  label: string;
  desc: string;
  detail: StepDetail;
  variant?: "expert";
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className={`${styles.stepItem} ${variant === "expert" ? styles.stepItemExpert : ""}`}>
      <div className={`${styles.stepNumber} ${variant === "expert" ? styles.stepNumberExpert : ""}`}>{number}</div>
      <p className={styles.stepLabel}>{label}</p>
      <p className={styles.stepDesc}>{desc}</p>
      <button
        type="button"
        className={styles.readMoreBtn}
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        {open ? "Fermer ▲" : "Lire plus... ▼"}
      </button>
      {open && (
        <div className={styles.stepDetail} onClick={() => setOpen(false)}>
          <div className={styles.stepDetailInner} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ margin: "0 0 16px", fontSize: "1.1rem", color: "var(--color-primary, #1e40af)" }}>
              Step {number} — {label}
            </h3>
            <p><strong>Objectif</strong></p>
            <p>{detail.objectif}</p>
            {detail.preparation && detail.preparation.length > 0 && (
              <>
                <p><strong>Préparation (avant déclenchement)</strong></p>
                <ul>
                  {detail.preparation.map((p, i) => <li key={i}>{p}</li>)}
                </ul>
              </>
            )}
            <p><strong>Entrées</strong></p>
            <ul>
              {detail.entrees.map((e, i) => <li key={i}>{e}</li>)}
            </ul>
            <p><strong>Opération</strong></p>
            <p>{detail.operation}</p>
            <p><strong>Sorties</strong></p>
            <ul>
              {detail.sorties.map((s, i) => <li key={i}>{s}</li>)}
            </ul>
            <p><strong>Rôle de l&apos;expert</strong></p>
            <p>{detail.roleExpert}</p>
            <button type="button" className={styles.stepDetailClose} onClick={() => setOpen(false)}>
              Fermer
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
