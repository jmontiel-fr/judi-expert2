/**
 * Step Configuration — Centralized metadata for each workflow step.
 *
 * Defines step names, banner texts, button labels, and file type
 * classifications used to partition files into input/output sections.
 */

import type { StepFileItem } from "./api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type WorkflowType = "standard" | "simple";

export interface StepConfig {
  name: string;
  bannerText: string | ((dossierName: string) => string);
  buttonLabel: string;
  inputFileTypes: string[];
  outputFileTypes: string[];
  /** Description structurée affichée dans le bloc frontal de chaque step */
  description: {
    objectif: string;
    preparation: string[];
    entrees: string[];
    operation: string;
    sorties: string[];
    roleExpert: string;
  };
}

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

export const STEP_CONFIG: Record<number, StepConfig> = {
  1: {
    name: "Initialisation dossier",
    bannerText: (dossierName: string) =>
      `Import de l'ordonnance (PDF) et des pièces complémentaires. Extraction OCR → Markdown structuré. Identification des questions du tribunal (Q1…Qn) et extraction des valeurs de placeholders. Fichiers stockés dans C:\\judi-expert\\${dossierName}\\step1`,
    buttonLabel: "Extraire et structurer",
    inputFileTypes: ["pdf_scan", "complementary"],
    outputFileTypes: ["markdown", "docx", "questions", "place_holders", "complementary_ocr"],
    description: {
      objectif: "Importer les fichiers du dossier, extraire le texte par OCR, identifier les questions du tribunal et les valeurs de placeholders.",
      preparation: ["Scanner l'ordonnance de commission d'expert (réquisition) en PDF", "Scanner les pièces complémentaires jointes (rapports, courriers, etc.)", "S'assurer que les PDF scannés sont lisibles (résolution ≥ 300 dpi)"],
      entrees: ["ordonnance.pdf (PDF-scan de la réquisition)", "piece-xxx.* (pièces complémentaires : PDF, DOCX, images)"],
      operation: "OCR → conversion en Markdown structuré. Extraction des questions numérotées Q1…Qn. Extraction des valeurs de placeholders depuis l'ordonnance.",
      sorties: ["ordonnance.md (texte structuré)", "piece-xxx.md (texte extrait des pièces)", "questions.md (liste Q1…Qn)", "place_holders.csv (valeurs extraites)"],
      roleExpert: "Vérifier le texte extrait, corriger les erreurs OCR, valider les questions et placeholders avant de passer à l'étape suivante.",
    },
  },
  2: {
    name: "Validation TRE → PREA",
    bannerText:
      "Validation du TRE (Template de Rapport d'Expertise) : vérification syntaxique des annotations et des placeholders. Production du PREA — copie du TRE validée pour annotation lors du Step E/A.",
    buttonLabel: "Valider le TRE",
    inputFileTypes: ["tre", "markdown", "template_tpe", "template_tpa", "complementary_ocr"],
    outputFileTypes: ["pea", "plan_entretien_docx"],
    description: {
      objectif: "Valider la syntaxe du TRE et produire le PREA (Projet de Rapport d'Expertise Annoté).",
      preparation: ["Vérifier que le TRE (Template de Rapport d'Expertise) est configuré (page Configuration ou upload ici)", "S'assurer que le Step 1 est validé (placeholders et questions disponibles)"],
      entrees: ["tre.docx (uploadé ici ou depuis la Configuration)", "placeholders.csv (métadonnées et questions du Step 1)"],
      operation: "Validation syntaxique du TRE (annotations, placeholders) puis copie en prea.docx.",
      sorties: ["prea.docx (PREA — document de travail pour le Step E/A)"],
      roleExpert: "Télécharger le PREA, l'enrichir lors des entretiens/analyses (Step E/A), puis l'importer au Step 4.",
    },
  },
  3: {
    name: "Consolidation documentaire",
    bannerText:
      "Import des pièces complémentaires reçues en réponse aux diligences (courriers, rapports médicaux, etc.). Les fichiers PDF/scan sont convertis en texte (.md) par OCR pour exploitation au Step 4.",
    buttonLabel: "Extraire les documents",
    inputFileTypes: ["diligence_response"],
    outputFileTypes: ["diligence_ocr"],
    description: {
      objectif: "Importer les pièces complémentaires issues des diligences et les convertir en Markdown exploitable.",
      preparation: ["Rassembler les pièces reçues en réponse aux diligences (courriers, rapports médicaux, résultats d'examens, etc.)", "Scanner en PDF les documents papier reçus", "Nommer les fichiers de façon descriptive (ex: diligence-medecin-rapport.pdf)"],
      entrees: ["diligence-xxx-piece-yyy.* (pièces reçues en réponse aux diligences : PDF, DOCX, images)"],
      operation: "OCR → extraction du texte en format .md pour chaque pièce PDF/scan.",
      sorties: ["diligence-xxx-piece-yyy.md (texte extrait de chaque pièce)"],
      roleExpert: "Téléverser les pièces reçues, vérifier les extractions OCR, valider avant de passer au Step 4.",
    },
  },
  4: {
    name: "Production pré-rapport",
    bannerText:
      "Import du PREA complété par l'expert. Génération du PRE par substitution directe dans le document : reformulation LLM des @dires/@analyse, résolution des @resume/@question/@cite, substitution des <<placeholders>>. Le document conserve sa structure et ses styles. Le DAC (analyse contradictoire) peut être généré séparément.",
    buttonLabel: "Générer le PRE",
    inputFileTypes: ["pea", "paa", "template_rapport", "place_holders", "diligence_ocr"],
    outputFileTypes: ["re_projet", "re_projet_auxiliaire"],
    description: {
      objectif: "Produire le Pré-Rapport d'Expertise (PRE) à partir du PREA complété au Step E/A.",
      preparation: ["Finaliser le PREA : compléter toutes les annotations @dires et @analyse", "Vérifier que les @verbatim sont entre guillemets", "S'assurer que les @conclusion contiennent les réponses aux questions du tribunal", "Importer le PREA finalisé dans le Step 4"],
      entrees: ["prea.docx (PREA annoté par l'expert — balises @dires, @analyse, @verbatim, etc.)", "placeholders.csv (valeurs extraites au Step 1)"],
      operation: "1. Validation syntaxique des annotations — 2. Reformulation LLM des @dires et @analyse ⏳ — 3. Résolution des @resume ⏳ — 4. Résolution des @question, @reference, @cite — 5. Substitution in-place dans le .docx (annotations → texte, <<placeholders>> → valeurs). Le document conserve sa structure, styles et table des matières. Optionnel : génération du DAC.",
      sorties: ["pre.docx (Pré-Rapport d'Expertise)", "dac.docx (Document d'Analyse Contradictoire — optionnel)"],
      roleExpert: "Relire le PRE, affiner les conclusions. Lancer le DAC si souhaité. Ajuster le rapport pour produire le REF à importer au Step 5.",
    },
  },
  5: {
    name: "Finalisation et archivage",
    bannerText:
      "Import du Rapport d'Expertise Final (REF) — le pré-rapport ajusté et validé par l'expert. Création d'une archive ZIP immuable contenant tous les fichiers du dossier. Génération d'un timbre d'horodatage (date + hash SHA-256 du ZIP) stocké sur S3.",
    buttonLabel: "Archiver le dossier",
    inputFileTypes: ["rapport_final"],
    outputFileTypes: ["archive_zip", "timbre"],
    description: {
      objectif: "Importer le rapport final ajusté et archiver l'ensemble du dossier avec horodatage technique.",
      preparation: ["Relire et ajuster le PRE produit au Step 4 pour obtenir le REF définitif", "Vérifier l'intégralité du rapport (conclusions, mise en forme, signatures)", "Enregistrer le document final en .docx"],
      entrees: ["ref.docx (Rapport d'Expertise Final — pré-rapport ajusté et validé par l'expert)"],
      operation: "Création d'une archive ZIP immuable contenant tous les fichiers du dossier. Génération d'un fichier timbre (date + hash SHA-256 du ZIP). Stockage du timbre sur S3.",
      sorties: ["<dossier-xxx>.zip (archive immuable)", "<dossier-xxx>-timbre.txt (horodatage technique SHA-256)"],
      roleExpert: "Importer le rapport final ajusté, valider pour archivage définitif. Compléter par un horodatage juridiquement certifié si nécessaire (solutions externes).",
    },
  },
};

/** Workflow simple — 2 étapes : PRE→PREF puis archivage */
export const SIMPLE_STEP_CONFIG: Record<number, StepConfig> = {
  1: {
    name: "Mise en forme linguistique",
    bannerText:
      "Import du Pré-Rapport d'Expertise (PRE.docx). Révision linguistique par IA → PREF (Projet de Rapport d'Expertise Final). Génération optionnelle du DAC. Vous pouvez relancer cette étape après modifications.",
    buttonLabel: "Mettre en forme linguistique",
    inputFileTypes: ["re_projet"],
    outputFileTypes: ["re_projet", "re_projet_auxiliaire"],
    description: {
      objectif: "Appliquer une révision linguistique au PRE pour produire le PREF, avec préservation des verbatim.",
      preparation: ["Rédiger le PRE (Pré-Rapport d'Expertise) dans Word", "Encadrer les citations exactes entre guillemets (protégées de la révision)", "Enregistrer le document final en .docx"],
      entrees: ["pre.docx (Pré-Rapport d'Expertise rédigé par l'expert)"],
      operation: "Révision linguistique LLM (orthographe, grammaire, syntaxe) avec préservation des textes entre guillemets. Option : génération du DAC.",
      sorties: ["pref.docx (Projet de Rapport d'Expertise Final)", "dac.docx (optionnel)"],
      roleExpert: "Importer le PRE, vérifier le PREF, relancer si nécessaire après corrections manuelles, puis valider avant l'archivage.",
    },
  },
  2: {
    name: "Archivage",
    bannerText:
      "Archivage du dossier : création d'une archive ZIP immuable et d'un timbre d'horodatage (SHA-256). Le PREF validé au Step 1 est inclus dans l'archive.",
    buttonLabel: "Archiver le dossier",
    inputFileTypes: ["rapport_final"],
    outputFileTypes: ["archive_zip", "timbre"],
    description: {
      objectif: "Archiver l'ensemble du dossier avec horodatage technique.",
      preparation: ["Vérifier le PREF produit au Step 1 (ou uploader une version ajustée)", "S'assurer que le rapport est dans sa version définitive"],
      entrees: ["pref.docx (depuis Step 1, ou version ajustée uploadée ici)"],
      operation: "Création d'une archive ZIP + fichier timbre (date + hash SHA-256). Stockage du timbre (S3 lorsque configuré).",
      sorties: ["<dossier>.zip (archive immuable)", "<dossier>-timbre.txt (horodatage SHA-256)"],
      roleExpert: "Vérifier le PREF final, lancer l'archivage, valider l'étape.",
    },
  },
};

// ---------------------------------------------------------------------------
// Helper functions
// ---------------------------------------------------------------------------

export function getMaxStepNumber(workflowType: WorkflowType = "standard"): number {
  return workflowType === "simple" ? 2 : 5;
}

export function getStepConfig(
  stepNumber: number,
  workflowType: WorkflowType = "standard",
): StepConfig | undefined {
  if (workflowType === "simple") {
    return SIMPLE_STEP_CONFIG[stepNumber];
  }
  return STEP_CONFIG[stepNumber];
}

/**
 * Filters files whose `file_type` is classified as an input type for the given step.
 */
export function getInputFiles(
  stepNumber: number,
  files: StepFileItem[],
  workflowType: WorkflowType = "standard",
): StepFileItem[] {
  const config = getStepConfig(stepNumber, workflowType);
  if (!config) return [];
  return files.filter((file) => config.inputFileTypes.includes(file.file_type));
}

/**
 * Filters files whose `file_type` is classified as an output type for the given step.
 * Files with unknown file_type (not in inputFileTypes) are included as fallback.
 */
export function getOutputFiles(
  stepNumber: number,
  files: StepFileItem[],
  workflowType: WorkflowType = "standard",
): StepFileItem[] {
  const config = getStepConfig(stepNumber, workflowType);
  if (!config) return [];
  return files.filter(
    (file) =>
      config.outputFileTypes.includes(file.file_type) ||
      !config.inputFileTypes.includes(file.file_type),
  );
}
