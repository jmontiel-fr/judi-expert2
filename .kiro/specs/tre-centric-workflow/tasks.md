# Tasks — Workflow TRE-Centré

## Task 1: Créer `services/tre_parser.py` — Parser et validateur de TRE

- [x] Créer le fichier `local-site/web/backend/services/tre_parser.py`
- [x] Implémenter les dataclasses `Placeholder`, `Annotation`, `TREParseResult`
- [x] Implémenter `TREParser.parse()` : itérer sur les paragraphes du .docx avec `python-docx`, extraire les placeholders `<<...>>` et les annotations `@...@` (y compris multi-paragraphes)
- [x] Implémenter `TREParser.validate()` : vérifier présence de `@debut_tpe@`, appariement des balises ouvrantes/fermantes, format snake_case des placeholders
- [x] Implémenter `TREParser.extract_pe()` : extraire la portion du TRE depuis `@debut_tpe@` jusqu'à la fin, ajouter les questions en section conclusion, retourner un .docx
- [x] Implémenter `TREParser.extract_header()` : extraire la partie du TRE avant `@debut_tpe@`, retourner un .docx
- [x] Gérer les annotations personnalisées `@/mon_annotation contenu@`
- [x] Gérer les annotations spéciales : `@verbatim`, `@question n`, `@reference @dires_x.y.z@`, `@cite @dires_x.y.z@`

## Task 2: Créer `services/annotation_formatter.py` — Formatage des annotations

- [x] Créer le fichier `local-site/web/backend/services/annotation_formatter.py`
- [x] Implémenter la dataclass `SectionIndex` (number, title, content)
- [x] Implémenter `AnnotationFormatter.format_dires()` : retourne "Dires : contenu"
- [x] Implémenter `AnnotationFormatter.format_analyse()` : retourne "Analyse : contenu"
- [x] Implémenter `AnnotationFormatter.format_verbatim()` : retourne le contenu entre guillemets sans modification
- [x] Implémenter `AnnotationFormatter.format_custom()` : capitalise le nom d'annotation, remplace underscores par espaces
- [x] Implémenter `AnnotationFormatter.resolve_reference()` : résout `@reference @dires_x.y.z@` → "cf section X.Y.Z - titre"
- [x] Implémenter `AnnotationFormatter.resolve_cite()` : résout `@cite @dires_x.y.z@` → "citation section X.Y.Z - titre ... texte"
- [x] Construire l'index des sections à partir du document parsé (numérotation hiérarchique des headings)

## Task 3: Créer `services/revision_service.py` — Service de révision linguistique

- [x] Créer le fichier `local-site/web/backend/services/revision_service.py`
- [x] Implémenter la dataclass `RevisionResult` (corrected_text, corrections)
- [x] Implémenter `RevisionService.revise()` : identifier les verbatim (textes entre guillemets), les remplacer par des tokens, appeler le LLM pour correction, restaurer les verbatim
- [x] Ajouter la gestion d'erreur (LLM indisponible → retourner le texte original)

## Task 4: Modifier `services/llm_service.py` — Nouveaux prompts et méthodes

- [x] Ajouter le prompt `PROMPT_REFORMULATION_DIRES` (reformulation notes télégraphiques → texte rédigé 3e personne)
- [x] Ajouter le prompt `PROMPT_REFORMULATION_ANALYSE` (reformulation notes d'analyse → texte professionnel)
- [x] Ajouter le prompt `PROMPT_REVISION` (correction linguistique français juridique, préservation verbatim)
- [x] Implémenter `LLMService.reformuler_dires(texte_abrege: str) -> str`
- [x] Implémenter `LLMService.reformuler_analyse(texte_abrege: str) -> str`
- [x] Implémenter `LLMService.reviser_texte(texte: str) -> str`

## Task 5: Modifier `services/file_paths.py` — Nouveaux chemins

- [x] Ajouter `archive_dir(dossier_name: str) -> str` : retourne `<DATA_DIR>/<nom-dossier>/archive/`
- [x] Ajouter `tre_path(dossier_name: str, domaine: str) -> str` : résolution par priorité (step2/in/tre.docx → data/config/tre.docx → corpus/{domaine}/tre.docx)
- [x] Ajouter `create_archive_dir(dossier_name: str) -> str` : crée le répertoire archive si inexistant

## Task 6: Refonte Step 1 dans `routers/steps.py`

- [x] Renommer la sortie `ordonnance.md` → `demande.md` dans `step1_execute()`
- [x] Modifier l'extraction des questions pour les stocker dans `placeholders.csv` au format `question_1;texte de la question 1` (en plus du fichier `questions.md`)
- [x] Mettre à jour les StepFile en base (filename `demande.md` au lieu de `ordonnance.md`)
- [x] Conserver la rétrocompatibilité : si `ordonnance.md` existe déjà, ne pas casser les dossiers en cours

## Task 7: Refonte Step 2 dans `routers/steps.py`

- [x] Supprimer l'ancien flux (RAG + LLM génération PE)
- [x] Implémenter la résolution du TRE : charger depuis `step2/in/tre.docx` ou TRE par défaut via `file_paths.tre_path()`
- [x] Copier le TRE résolu dans `step2/in/tre.docx` (figer la version)
- [x] Appeler `TREParser.parse()` pour valider le TRE
- [x] Appeler `TREParser.extract_pe()` avec les questions du `placeholders.csv`
- [x] Sauvegarder le PE en `step2/out/pe.docx`
- [x] Implémenter la vérification : le PE contient des annotations et les questions en conclusion
- [x] Mettre à jour les StepFile en base
- [x] Ajouter un endpoint `POST /{dossier_id}/step2/upload-tre` pour permettre l'upload d'un TRE personnalisé

## Task 8: Refonte Step 4 dans `routers/steps.py`

- [x] Remplacer le parsing regex sur bytes bruts par `TREParser.parse()` sur le PEA .docx
- [x] Charger le TRE original depuis `step2/in/tre.docx`
- [x] Appeler `TREParser.extract_header()` pour obtenir l'en-tête du rapport
- [x] Reconstituer le document complet : en-tête + contenu PEA
- [x] Charger `placeholders.csv` du Step 1 et substituer les `<<placeholder>>`
- [x] Pour chaque annotation `@dires` : appeler `LLMService.reformuler_dires()`
- [x] Pour chaque annotation `@analyse` : appeler `LLMService.reformuler_analyse()`
- [x] Préserver les `@verbatim` entre guillemets sans appel LLM
- [x] Résoudre les `@reference` et `@cite` via `AnnotationFormatter`
- [x] Formater les annotations personnalisées `@/custom` via `AnnotationFormatter.format_custom()`
- [x] Générer le PRE en .docx (utiliser `python-docx` ou `docxtpl`)
- [x] Générer le DAC via `LLMService.generer_dac()` (existant, à adapter)
- [x] Sauvegarder `step4/out/pre.docx` et `step4/out/dac.docx`
- [x] Mettre à jour les StepFile en base
- [x] Signaler les placeholders manquants à l'expert (warning, pas bloquant)

## Task 9: Refonte Step 5 dans `routers/steps.py`

- [x] Ajouter l'appel au `RevisionService.revise()` sur le PRE ajusté
- [x] Présenter les corrections en mode "track changes" (liste des corrections dans la réponse API)
- [x] Préserver les verbatim intacts pendant la révision
- [x] Modifier la génération du ZIP : inclure tous les fichiers de `c:\judi-expert\<nom-dossier>` sauf `archive\`
- [x] Générer `<nom-dossier>-timbre.txt` avec les métadonnées : demandeur_nom, demandeur_prenom, demandeur_adresse, demande_date, tribunal_nom, tribunal_adresse, demande_reference, mec_nom, mec_prenom, mec_adresse, expert_nom, expert_prenom, expert_adresse, nom du fichier .zip, log d'archive (date + hash SHA-256)
- [x] Placer le .zip et le timbre.txt dans `<nom-dossier>/archive/`
- [x] Mettre à jour les StepFile en base (filenames: `<nom-dossier>.zip`, `<nom-dossier>-timbre.txt`)

## Task 10: Mise à jour `docs/glossaire-workflow.md`

- [x] Réécrire la section "Vue d'ensemble" pour décrire le workflow TRE-centré
- [x] Ajouter la description du TRE comme document central (placeholders + annotations)
- [x] Documenter les 2 types de méta-instructions (placeholders `<<...>>` et annotations `@...@`)
- [x] Documenter les annotations prédéfinies : `@dires`, `@analyse`, `@verbatim`, `@question`, `@reference`, `@cite`, `@debut_tpe`
- [x] Documenter les annotations personnalisées : `@/mon_annotation`
- [x] Mettre à jour le tableau récapitulatif Entrées/Opération/Sorties pour chaque step
- [x] Mettre à jour le détail de chaque step (Step 1 → demande.md, Step 2 → extraction PE depuis TRE, Step 4 → reconstitution, Step 5 → révision + timbre)
- [x] Ajouter MEC dans le glossaire des termes métier
- [x] Mettre à jour la section 7 (Conventions d'annotation) pour refléter la nouvelle syntaxe

## Task 11: Mise à jour `docs/methodologie.md`

- [x] Mettre à jour la section "Workflow d'expertise assisté par l'IA" : Step 2 = extraction mécanique du PE depuis le TRE (pas de génération LLM libre)
- [x] Mettre à jour Step 4 : reformulation LLM des annotations (pas de génération libre du rapport)
- [x] Ajouter Step 5 : service de révision linguistique
- [x] Mettre à jour le tableau "Rôle de l'IA" pour chaque étape
- [x] Vérifier la cohérence avec le nouveau glossaire-workflow.md

## Task 12: Tests unitaires pour `tre_parser.py`

- [x] Créer `tests/unit/test_tre_parser.py`
- [x] Test : parse un TRE valide avec placeholders et annotations → résultat correct
- [x] Test : validate détecte l'absence de `@debut_tpe@`
- [x] Test : validate détecte les annotations mal fermées
- [x] Test : extract_pe retourne la portion après `@debut_tpe@` avec questions en conclusion
- [x] Test : extract_header retourne la portion avant `@debut_tpe@`
- [x] Test : parsing des annotations personnalisées `@/custom`
- [x] Test : parsing des annotations multi-paragraphes
- [x] Test : propriété round-trip (parse → format → re-parse = équivalent)

## Task 13: Tests unitaires pour `annotation_formatter.py`

- [x] Créer `tests/unit/test_annotation_formatter.py`
- [x] Test : format_dires produit "Dires : contenu"
- [x] Test : format_analyse produit "Analyse : contenu"
- [x] Test : format_verbatim préserve le contenu entre guillemets
- [x] Test : format_custom capitalise et remplace les underscores
- [x] Test : resolve_reference produit "cf section X.Y.Z - titre"
- [x] Test : resolve_cite produit "citation section X.Y.Z - titre ... texte"
- [x] Test : resolve_reference avec section inexistante → erreur signalée

## Task 14: Tests unitaires pour `revision_service.py`

- [x] Créer `tests/unit/test_revision_service.py`
- [x] Test : les verbatim sont préservés après révision
- [x] Test : les tokens de remplacement sont correctement restaurés
- [x] Test : en cas d'erreur LLM, le texte original est retourné
