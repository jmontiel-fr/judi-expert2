"use client";

import { useState, useCallback, useRef } from "react";
import { peaEditorApi } from "@/lib/api";
import type {
  PEABlock,
  PEAParseResponse,
  SectionInfo,
  AnnotationBlock,
} from "@/types/pea";
import styles from "./editer-pea.module.css";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type EditorState = "idle" | "loading" | "editing" | "saving" | "error";

// ---------------------------------------------------------------------------
// PEA Editor Page
// ---------------------------------------------------------------------------

export default function EditerPeaPage() {
  const [state, setState] = useState<EditorState>("idle");
  const [parseResponse, setParseResponse] = useState<PEAParseResponse | null>(null);
  const [blocks, setBlocks] = useState<PEABlock[]>([]);
  const [sections, setSections] = useState<SectionInfo[]>([]);
  const [errors, setErrors] = useState<string[]>([]);
  const [errorMessage, setErrorMessage] = useState("");
  const [sourceFileBase64, setSourceFileBase64] = useState("");
  const [filename, setFilename] = useState("");
  const [saveMessage, setSaveMessage] = useState("");

  // Ref pour le textarea actif (pour la palette d'insertion)
  const activeTextareaRef = useRef<HTMLTextAreaElement | null>(null);
  const [activeBlockId, setActiveBlockId] = useState<string | null>(null);
  const [activeBlockType, setActiveBlockType] = useState<string | null>(null);

  // --- File selection & parse ---
  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".docx")) {
      setErrorMessage("Seuls les fichiers .docx sont acceptés.");
      setState("error");
      return;
    }

    setState("loading");
    setErrorMessage("");
    setSaveMessage("");

    try {
      // Stocker le fichier source en base64 pour la sauvegarde
      const arrayBuffer = await file.arrayBuffer();
      const base64 = btoa(
        new Uint8Array(arrayBuffer).reduce((data, byte) => data + String.fromCharCode(byte), "")
      );
      setSourceFileBase64(base64);
      setFilename(file.name);

      // Parser le document
      const response = await peaEditorApi.parse(file);
      setParseResponse(response);
      setBlocks(response.blocks);
      setSections(response.sections);
      setErrors(response.errors);
      setState("editing");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erreur lors du parsing";
      setErrorMessage(msg);
      setState("error");
    }
  }, []);

  // --- Block content update ---
  const handleBlockChange = useCallback((blockId: string, newContent: string) => {
    setBlocks((prev) =>
      prev.map((b) => (b.id === blockId ? { ...b, content: newContent } : b))
    );
  }, []);

  // --- Save ---
  const handleSave = useCallback(async () => {
    if (!sourceFileBase64 || blocks.length === 0) return;

    setState("saving");
    setSaveMessage("");
    setErrorMessage("");

    try {
      const result = await peaEditorApi.save({
        blocks,
        sourceFile: sourceFileBase64,
        dossierName: "courant",
        outputFilename: filename.replace(".docx", "_modifie.docx"),
      });
      setSaveMessage(result.message || "Document sauvegardé avec succès.");
      setState("editing");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erreur lors de la sauvegarde";
      setErrorMessage(msg);
      setState("editing"); // Rester en mode édition pour ne pas perdre les données
    }
  }, [blocks, sourceFileBase64, filename]);

  // --- Cancel ---
  const handleCancel = useCallback(() => {
    setState("idle");
    setParseResponse(null);
    setBlocks([]);
    setSections([]);
    setErrors([]);
    setErrorMessage("");
    setSaveMessage("");
    setSourceFileBase64("");
    setFilename("");
  }, []);

  // --- Palette insertion ---
  const handleInsertAnnotation = useCallback((type: string, target: string) => {
    const textarea = activeTextareaRef.current;
    if (!textarea) return;

    // Construire le texte à insérer
    let insertion: string;
    if (type === "__placeholder__") {
      insertion = `<<${target}>>`;
    } else if (target) {
      insertion = `@${type} @${target}@`;
    } else {
      insertion = `@${type}@`;
    }

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const currentValue = textarea.value;
    const newValue = currentValue.slice(0, start) + insertion + currentValue.slice(end);

    // Mettre à jour le bloc correspondant
    const blockId = textarea.dataset.blockId;
    if (blockId) {
      handleBlockChange(blockId, newValue);
    }

    // Repositionner le curseur après l'insertion
    setTimeout(() => {
      textarea.focus();
      textarea.selectionStart = start + insertion.length;
      textarea.selectionEnd = start + insertion.length;
    }, 0);
  }, [handleBlockChange]);

  // --- Render ---
  return (
    <div className={styles.container}>
      <div className={styles.infoNote}>
        <strong>Éditeur PEA</strong> — Chargez un document PEA/TPE (.docx) pour
        visualiser et modifier les annotations. Les champs éditables (dires, analyse,
        remplir, conclusion) sont modifiables. Les autres éléments sont en lecture seule.
      </div>

      {/* File selector */}
      {state === "idle" && (
        <div className={styles.fileSelector}>
          <label htmlFor="pea-file" className={styles.fileLabel}>
            Sélectionner un fichier PEA/TPE (.docx)
          </label>
          <input
            id="pea-file"
            type="file"
            accept=".docx"
            onChange={handleFileSelect}
            className={styles.fileInput}
          />
        </div>
      )}

      {/* Loading */}
      {state === "loading" && (
        <div className={styles.loading}>
          <p>Analyse du document en cours...</p>
        </div>
      )}

      {/* Error */}
      {state === "error" && (
        <div className={styles.errorBox}>
          <p>{errorMessage}</p>
          <button onClick={handleCancel} className={styles.btnSecondary}>
            Réessayer
          </button>
        </div>
      )}

      {/* Editing */}
      {(state === "editing" || state === "saving") && (
        <>
          {/* Toolbar */}
          <div className={styles.toolbar}>
            <span className={styles.toolbarFilename}>{filename}</span>
            <div className={styles.toolbarActions}>
              <button
                onClick={handleSave}
                disabled={state === "saving"}
                className={styles.btnPrimary}
              >
                {state === "saving" ? "Enregistrement..." : "Enregistrer"}
              </button>
              <button
                onClick={handleCancel}
                disabled={state === "saving"}
                className={styles.btnSecondary}
              >
                Annuler
              </button>
            </div>
          </div>

          {/* Messages */}
          {saveMessage && <div className={styles.successMsg}>{saveMessage}</div>}
          {errorMessage && <div className={styles.errorMsg}>{errorMessage}</div>}
          {errors.length > 0 && (
            <div className={styles.warningBox}>
              <strong>Avertissements :</strong>
              <ul>
                {errors.map((err, i) => (
                  <li key={i}>{err}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Form Renderer */}
          <div
            className={styles.formContainer}
            onBlur={(e) => {
              // Masquer la palette si le focus quitte le formContainer
              if (!e.currentTarget.contains(e.relatedTarget as Node)) {
                setActiveBlockId(null);
                setActiveBlockType(null);
              }
            }}
          >
            {/* Annotation Palette — inside formContainer so clicking it doesn't trigger onBlur */}
            {activeBlockId && ["conclusion", "dires", "analyse", "remplir"].includes(activeBlockType || "") && (
              <AnnotationPalette
                sections={sections}
                blocks={blocks}
                onInsert={handleInsertAnnotation}
              />
            )}

            {blocks.map((block) => (
              <BlockRenderer
                key={block.id}
                block={block}
                onChange={handleBlockChange}
                onFocusTextarea={(el) => {
                  activeTextareaRef.current = el;
                  if (el) {
                    setActiveBlockId(el.dataset.blockId || null);
                    const b = blocks.find((bl) => bl.id === el.dataset.blockId);
                    setActiveBlockType(b ? (b as unknown as { annotationType?: string }).annotationType || null : null);
                  }
                }}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Block Renderer
// ---------------------------------------------------------------------------

interface BlockRendererProps {
  block: PEABlock;
  onChange: (blockId: string, content: string) => void;
  onFocusTextarea: (el: HTMLTextAreaElement | null) => void;
}

function BlockRenderer({ block, onChange, onFocusTextarea }: BlockRendererProps) {
  switch (block.type) {
    case "heading":
      return <HeadingRenderer block={block} />;
    case "text":
      return <TextRenderer block={block} />;
    case "placeholder":
      return <PlaceholderRenderer block={block} />;
    case "annotation":
      return (
        <AnnotationRenderer
          block={block as AnnotationBlock}
          onChange={onChange}
          onFocusTextarea={onFocusTextarea}
        />
      );
    default:
      return null;
  }
}

function HeadingRenderer({ block }: { block: PEABlock }) {
  const level = (block as unknown as { level: number }).level ?? 1;
  const number = (block as unknown as { number: string }).number ?? "";
  const text = (block as unknown as { text: string }).text ?? "";
  const Tag = `h${Math.min(level + 1, 6)}` as keyof JSX.IntrinsicElements;
  return (
    <Tag className={styles.heading}>
      {number && <span className={styles.headingNumber}>{number}</span>}
      {text}
    </Tag>
  );
}

function TextRenderer({ block }: { block: PEABlock }) {
  const content = (block as unknown as { content: string }).content ?? "";
  if (!content) return <div className={styles.emptyPara} />;

  // Mettre en évidence les <<placeholders>> dans le texte
  const parts = content.split(/(<<[^>]+>>)/g);
  if (parts.length === 1) {
    return <p className={styles.textBlock}>{content}</p>;
  }
  return (
    <p className={styles.textBlock}>
      {parts.map((part, i) =>
        part.startsWith("<<") && part.endsWith(">>") ? (
          <span key={i} className={styles.placeholderTag}>{part}</span>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </p>
  );
}

function PlaceholderRenderer({ block }: { block: PEABlock }) {
  const fullText = (block as unknown as { fullText?: string }).fullText ?? "";
  const name = (block as unknown as { name: string }).name ?? "";

  // Afficher le fullText complet avec les <<placeholders>> en rouge
  const displayText = fullText || `<<${name}>>`;

  // Séparer par \n pour respecter les sauts de ligne du document
  const lines = displayText.split("\n");

  return (
    <div className={styles.textBlock}>
      {lines.map((line, lineIdx) => {
        if (!line.trim()) return <br key={lineIdx} />;
        const parts = line.split(/(<<[^>]+>>)/g);
        return (
          <p key={lineIdx} className={styles.textBlock} style={{ margin: "0.15rem 0" }}>
            {parts.map((part, i) =>
              part.startsWith("<<") && part.endsWith(">>") ? (
                <span key={i} className={styles.placeholderTag}>{part}</span>
              ) : (
                <span key={i}>{part}</span>
              )
            )}
          </p>
        );
      })}
    </div>
  );
}

function AnnotationRenderer({
  block,
  onChange,
  onFocusTextarea,
}: {
  block: AnnotationBlock;
  onChange: (blockId: string, content: string) => void;
  onFocusTextarea: (el: HTMLTextAreaElement | null) => void;
}) {
  const isEditable = block.isEditable;
  const annType = block.annotationType || "";
  const suffix = block.suffix || "";
  const fieldName = (block as unknown as { fieldName?: string }).fieldName || "";
  const fieldFormat = (block as unknown as { fieldFormat?: string }).fieldFormat || "";

  // Construire le label
  let label = `@${annType}`;
  if (suffix && suffix !== annType) label += ` ${suffix}`;

  // Déterminer le mode de rendu
  const isInlineField = fieldFormat === "champ" && !["dires", "analyse", "conclusion"].includes(annType);

  // Rendu inline pour @remplir_champ et types inconnus (champ court)
  if (isInlineField && isEditable) {
    return (
      <div className={styles.annotationInlineRow}>
        <span className={styles.annotationLabel}>{label}</span>
        <input
          type="text"
          className={styles.annotationInput}
          value={block.content || ""}
          onChange={(e) => onChange(block.id, e.target.value)}
          onFocus={(e) => onFocusTextarea(e.target as unknown as HTMLTextAreaElement)}
          data-block-id={block.id}
          placeholder="…"
        />
      </div>
    );
  }

  // Rendu bloc pour tout le reste (dires, analyse, conclusion, remplir_bloc)
  return (
    <div className={`${styles.annotation} ${isEditable ? styles.annotationEditable : ""}`}>
      <span className={styles.annotationLabel}>{label}</span>
      {isEditable ? (
        <textarea
          className={styles.annotationTextarea}
          value={block.content || ""}
          onChange={(e) => onChange(block.id, e.target.value)}
          onFocus={(e) => onFocusTextarea(e.target)}
          data-block-id={block.id}
          placeholder="Saisir le contenu..."
          rows={Math.max(3, (block.content || "").split("\n").length + 1)}
        />
      ) : (
        block.content
          ? <span className={styles.annotationContent}>{block.content}</span>
          : null
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Annotation Palette
// ---------------------------------------------------------------------------

interface AnnotationPaletteProps {
  sections: SectionInfo[];
  blocks: PEABlock[];
  onInsert: (type: string, target: string) => void;
}

function AnnotationPalette({ sections, blocks, onInsert }: AnnotationPaletteProps) {
  const [selectedType, setSelectedType] = useState("cite");
  const [selectedTarget, setSelectedTarget] = useState("");
  const [selectedPlaceholder, setSelectedPlaceholder] = useState("");
  const [resumeTargets, setResumeTargets] = useState<string[]>([]);

  const types = [
    { value: "cite", label: "@cite" },
    { value: "reference", label: "@reference" },
    { value: "resume", label: "@resume" },
    { value: "question", label: "@question" },
  ];

  // Construire la liste des cibles : toutes les annotations @dires et @analyse avec leur section
  // Corréler avec le heading précédent pour afficher le titre de section
  const annotationTargets: { value: string; label: string }[] = [];
  let lastHeadingText = "";
  for (const block of blocks) {
    if (block.type === "heading") {
      const hText = (block as unknown as { text?: string }).text || "";
      if (hText) lastHeadingText = hText;
    }
    if (block.type === "annotation") {
      const ann = block as AnnotationBlock;
      if (["dires", "analyse"].includes(ann.annotationType || "") && ann.suffix) {
        const sectionRef = (ann as unknown as { sectionRef?: string }).sectionRef || ann.suffix.replace("section_", "");
        const val = `${ann.annotationType}_${sectionRef}`;
        const headingLabel = lastHeadingText ? ` — ${lastHeadingText}` : "";
        const label = `@${ann.annotationType}_${sectionRef}${headingLabel}`;
        // Éviter les doublons
        if (!annotationTargets.find((t) => t.value === val)) {
          annotationTargets.push({ value: val, label });
        }
      }
    }
  }

  // Construire la liste des placeholders existants dans le document
  const placeholders: string[] = [];
  for (const block of blocks) {
    if (block.type === "placeholder") {
      const name = (block as unknown as { name?: string }).name;
      if (name && !placeholders.includes(name)) {
        placeholders.push(name);
      }
    }
  }

  // Gestion @resume : toggle sélection multiple
  const toggleResumeTarget = (target: string) => {
    setResumeTargets((prev) =>
      prev.includes(target) ? prev.filter((t) => t !== target) : [...prev, target]
    );
  };

  const handleInsertAnnotation = () => {
    if (selectedType === "resume") {
      // @resume insère plusieurs références
      if (resumeTargets.length > 0) {
        const refs = resumeTargets.map((t) => `@reference @${t}@`).join(", ");
        onInsert("resume", refs);
      }
    } else {
      onInsert(selectedType, selectedTarget);
    }
  };

  const handleInsertPlaceholder = () => {
    if (selectedPlaceholder) {
      onInsert("__placeholder__", selectedPlaceholder);
    }
  };

  return (
    <div className={styles.palette}>
      {/* Ligne 1 : Annotations */}
      <div className={styles.paletteRow}>
        <span className={styles.paletteTitle}>Annotation :</span>
        <select
          value={selectedType}
          onChange={(e) => { setSelectedType(e.target.value); setResumeTargets([]); }}
          className={styles.paletteSelect}
          aria-label="Type d'annotation"
        >
          {types.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>

        {selectedType === "resume" ? (
          /* @resume : sélection multiple */
          <div className={styles.paletteMultiSelect}>
            {annotationTargets.map((t) => (
              <label key={t.value} className={styles.paletteCheckbox}>
                <input
                  type="checkbox"
                  checked={resumeTargets.includes(t.value)}
                  onChange={() => toggleResumeTarget(t.value)}
                />
                <span>{t.label}</span>
              </label>
            ))}
          </div>
        ) : (
          /* Autres types : sélection simple */
          annotationTargets.length > 0 && (
            <select
              value={selectedTarget}
              onChange={(e) => setSelectedTarget(e.target.value)}
              className={styles.paletteSelect}
              aria-label="Section cible"
            >
              <option value="">— Choisir —</option>
              {annotationTargets.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          )
        )}

        <button
          onClick={handleInsertAnnotation}
          className={styles.btnPalette}
          type="button"
          disabled={selectedType === "resume" ? resumeTargets.length === 0 : !selectedTarget}
        >
          Insérer
        </button>
      </div>

      {/* Ligne 2 : Placeholder */}
      <div className={styles.paletteRow}>
        <span className={styles.paletteTitle}>Placeholder :</span>
        <select
          value={selectedPlaceholder}
          onChange={(e) => setSelectedPlaceholder(e.target.value)}
          className={styles.paletteSelect}
          aria-label="Placeholder à insérer"
        >
          <option value="">— Choisir —</option>
          {placeholders.map((p) => (
            <option key={p} value={p}>&lt;&lt;{p}&gt;&gt;</option>
          ))}
        </select>
        <button
          onClick={handleInsertPlaceholder}
          className={styles.btnPalette}
          type="button"
          disabled={!selectedPlaceholder}
        >
          Insérer &lt;&lt;…&gt;&gt;
        </button>
      </div>
    </div>
  );
}
