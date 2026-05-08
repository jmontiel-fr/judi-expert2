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

export interface StepConfig {
  name: string;
  bannerText: string | ((dossierName: string) => string);
  buttonLabel: string;
  inputFileTypes: string[];
  outputFileTypes: string[];
  /** Description structurée affichée dans le bloc frontal de chaque step */
  description: {
    objectif: string;
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
    name: "Création dossier",
    bannerText: (dossierName: string) =>
      `Import de l'ordonnance (PDF) et des pièces complémentaires. Extraction OCR → Markdown structuré. Identification des questions du tribunal (Q1…Qn) et extraction des valeurs de placeholders. Fichiers stockés dans C:\\judi-expert\\${dossierName}\\step1`,
    buttonLabel: "Extraire et structurer",
    inputFileTypes: ["pdf_scan", "complementary"],
    outputFileTypes: ["markdown", "docx", "questions", "place_holders", "complementary_ocr"],
    description: {
      objectif: "Importer les fichiers du dossier, extraire le texte par OCR, identifier les questions du tribunal et les valeurs de placeholders.",
      entrees: ["ordonnance.pdf (PDF-scan de la réquisition)", "piece-xxx.* (pièces complémentaires : PDF, DOCX, images)"],
      operation: "OCR → conversion en Markdown structuré. Extraction des questions numérotées Q1…Qn. Extraction des valeurs de placeholders depuis l'ordonnance.",
      sorties: ["ordonnance.md (texte structuré)", "piece-xxx.md (texte extrait des pièces)", "questions.md (liste Q1…Qn)", "place_holders.csv (valeurs extraites)"],
      roleExpert: "Vérifier le texte extrait, corriger les erreurs OCR, valider les questions et placeholders avant de passer à l'étape suivante.",
    },
  },
  2: {
    name: "Préparation investigations",
    bannerText:
      "Génération du Plan d'Entretien (PE) ou du Plan d'Analyse (PA) à partir de l'ordonnance structurée, du template personnel (TPE/TPA) et du contexte RAG du domaine. En mode Analyse, génère également des projets de courriers de diligence.",
    buttonLabel: "Générer le plan",
    inputFileTypes: ["markdown", "template_tpe", "template_tpa", "complementary_ocr"],
    outputFileTypes: ["plan_entretien", "plan_entretien_docx", "plan_analyse", "plan_analyse_docx", "courrier_diligence"],
    description: {
      objectif: "Générer un plan d'entretien (PE) ou un plan d'analyse (PA) structuré, adapté aux questions du tribunal.",
      entrees: ["ordonnance.md (texte structuré du Step 1)", "TPE ou TPA (template personnel de l'expert)", "piece-xxx.md (pièces complémentaires extraites)"],
      operation: "Récupération du template et du corpus RAG → Génération du PE ou PA par le LLM. En mode Analyse : génération de courriers de diligence.",
      sorties: ["Mode Entretien : pe.md, pe.docx (Plan d'Entretien)", "Mode Analyse : pa.md, pa.docx, diligence-xxx.docx (Plan d'Analyse + courriers)"],
      roleExpert: "Télécharger le PE/PA, l'adapter si nécessaire, puis mener les entretiens ou analyses (étape E/A hors application).",
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
      entrees: ["diligence-xxx-piece-yyy.* (pièces reçues en réponse aux diligences : PDF, DOCX, images)"],
      operation: "OCR → extraction du texte en format .md pour chaque pièce PDF/scan.",
      sorties: ["diligence-xxx-piece-yyy.md (texte extrait de chaque pièce)"],
      roleExpert: "Téléverser les pièces reçues, vérifier les extractions OCR, valider avant de passer au Step 4.",
    },
  },
  4: {
    name: "Production pré-rapport",
    bannerText:
      "Import du PEA (Plan d'Entretien Annoté) ou PAA (Plan d'Analyse Annoté) complété par l'expert avec les annotations balisées (@dires, @analyse, @verbatim, @question, @reference). Génération du Pré-Rapport (PRE) via le template TRE et substitution des placeholders. Génération du Document d'Analyse Contradictoire (DAC).",
    buttonLabel: "Générer le pré-rapport",
    inputFileTypes: ["pea", "paa", "template_rapport", "place_holders", "diligence_ocr"],
    outputFileTypes: ["pre_rapport", "dac"],
    description: {
      objectif: "Produire le Pré-Rapport d'Expertise (PRE) et le Document d'Analyse Contradictoire (DAC).",
      entrees: ["pea.docx ou paa.docx (plan annoté par l'expert avec balises @dires, @analyse, @question, @reference)", "tre.docx (template de rapport avec placeholders <<...>>)", "place_holders.csv (valeurs extraites au Step 1)", "Documents de diligence (Step 3, si existants)"],
      operation: "Interprétation des annotations balisées → Substitution des placeholders dans le TRE (docxtpl) → Génération du PRE par le LLM → Génération du DAC (analyse contradictoire).",
      sorties: ["pre.docx (Pré-Rapport d'Expertise)", "dac.docx (Document d'Analyse Contradictoire)"],
      roleExpert: "Relire le PRE et le DAC, affiner les conclusions, puis ajuster le rapport pour produire le REF (rapport final) à importer au Step 5.",
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
      entrees: ["ref.docx (Rapport d'Expertise Final — pré-rapport ajusté et validé par l'expert)"],
      operation: "Création d'une archive ZIP immuable contenant tous les fichiers du dossier. Génération d'un fichier timbre (date + hash SHA-256 du ZIP). Stockage du timbre sur S3.",
      sorties: ["<dossier-xxx>.zip (archive immuable)", "<dossier-xxx>-timbre.txt (horodatage technique SHA-256)"],
      roleExpert: "Importer le rapport final ajusté, valider pour archivage définitif. Compléter par un horodatage juridiquement certifié si nécessaire (solutions externes).",
    },
  },
};

// ---------------------------------------------------------------------------
// Helper functions
// ---------------------------------------------------------------------------

/**
 * Filters files whose `file_type` is classified as an input type for the given step.
 */
export function getInputFiles(stepNumber: number, files: StepFileItem[]): StepFileItem[] {
  const config = STEP_CONFIG[stepNumber];
  if (!config) return [];
  return files.filter((file) => config.inputFileTypes.includes(file.file_type));
}

/**
 * Filters files whose `file_type` is classified as an output type for the given step.
 * Files with unknown file_type (not in inputFileTypes) are included as fallback.
 */
export function getOutputFiles(stepNumber: number, files: StepFileItem[]): StepFileItem[] {
  const config = STEP_CONFIG[stepNumber];
  if (!config) return [];
  return files.filter(
    (file) =>
      config.outputFileTypes.includes(file.file_type) ||
      !config.inputFileTypes.includes(file.file_type),
  );
}
