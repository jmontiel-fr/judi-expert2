/**
 * PEA Editor Types — Type definitions for the PEA document editor.
 *
 * These types represent the structured blocks extracted from a PEA/TPE .docx
 * document, used for rendering the form-based editor and communicating with
 * the backend parse/save endpoints.
 */

// ---------------------------------------------------------------------------
// Block & Annotation Type Enums
// ---------------------------------------------------------------------------

/** Types de blocs dans le document PEA */
export type PEABlockType = "heading" | "text" | "placeholder" | "annotation";

/** Types d'annotations modifiables */
export type EditableAnnotationType = "remplir" | "dires" | "analyse" | "conclusion";

/** Types d'annotations en lecture seule */
export type ReadOnlyAnnotationType = "verbatim" | "resume" | "reference" | "cite" | "question";

// ---------------------------------------------------------------------------
// Block Interfaces
// ---------------------------------------------------------------------------

/** Bloc générique du document PEA */
export interface PEABlock {
  id: string;                          // UUID unique pour React key + tracking
  type: PEABlockType;
  paragraphIndex: number;              // position dans le .docx source
}

/** Bloc titre de section */
export interface HeadingBlock extends PEABlock {
  type: "heading";
  level: number;                       // 1-6 (H1-H6)
  number: string;                      // "2.1.3"
  text: string;                        // texte du titre
}

/** Bloc texte normal (lecture seule) */
export interface TextBlock extends PEABlock {
  type: "text";
  content: string;                     // texte brut
}

/** Bloc placeholder <<...>> (lecture seule, rouge gras) */
export interface PlaceholderBlock extends PEABlock {
  type: "placeholder";
  name: string;                        // nom du placeholder sans << >>
  fullText: string;                    // texte complet du paragraphe contenant le placeholder
}

/** Bloc annotation (modifiable ou lecture seule selon le type) */
export interface AnnotationBlock extends PEABlock {
  type: "annotation";
  annotationType: EditableAnnotationType | ReadOnlyAnnotationType;
  suffix: string;                      // "section_2.1.3" ou "date_entretien JJ/MM/AAAA"
  content: string;                     // contenu textuel modifiable
  isEditable: boolean;                 // true pour remplir, dires, analyse, conclusion
  fieldName?: string;                  // pour @remplir: nom du champ
  fieldFormat?: string;                // pour @remplir: format attendu
  sectionRef?: string;                 // pour @dires/@analyse: "2.1.3"
  insertedAnnotations?: InsertedAnnotation[];  // annotations insérées via palette
}

// ---------------------------------------------------------------------------
// Inserted Annotation (Palette)
// ---------------------------------------------------------------------------

/** Annotation insérée via la palette dans un textarea */
export interface InsertedAnnotation {
  id: string;                          // UUID
  type: "cite" | "reference" | "resume";
  target: string;                      // "@dires section_2.1.3"
  position: number;                    // position dans le texte du textarea
  displayText: string;                 // texte affiché (ex: "@cite @dires_2.1.3@")
}

// ---------------------------------------------------------------------------
// Section Info (Palette)
// ---------------------------------------------------------------------------

/** Info section pour la palette */
export interface SectionInfo {
  number: string;                      // "2.1.3"
  title: string;                       // texte du titre
  level: number;                       // niveau de profondeur
  annotationType: "dires" | "analyse"; // type d'annotation associé
}

// ---------------------------------------------------------------------------
// API Response & Request Types
// ---------------------------------------------------------------------------

/** Réponse du parsing */
export interface PEAParseResponse {
  blocks: PEABlock[];
  sections: SectionInfo[];
  metadata: {
    filename: string;
    totalAnnotations: number;
    editableAnnotations: number;
    totalParagraphs: number;
  };
  errors: string[];                    // erreurs de parsing non fatales
}

/** Requête de sauvegarde */
export interface PEASaveRequest {
  blocks: PEABlock[];                  // blocs avec contenu modifié
  sourceFile: string;                  // base64 du fichier source (pour préserver styles)
  dossierName: string;                 // nom du dossier actif
  outputFilename: string;              // nom du fichier de sortie (ex: "pea.docx")
}

/** Réponse de sauvegarde */
export interface PEASaveResponse {
  success: boolean;
  outputPath: string;                  // chemin complet du fichier écrit
  message: string;
}
