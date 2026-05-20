# Implementation Plan: PEA Editor Tools

## Overview

Cette implémentation réorganise la page "Révision" en une page "Outils" avec navigation par onglets (Mettre en forme, Résumer, Editer PEA) et introduit l'éditeur PEA complet : parsing de documents .docx, affichage en formulaire, édition des annotations, palette d'insertion, et sérialisation en .docx.

## Tasks

- [ ] 1. Mise en place de la structure backend PEA Editor
  - [x] 1.1 Créer les modèles de données PEA (dataclasses + Pydantic schemas)
    - Créer le fichier `local-site/web/backend/services/pea_editor_models.py`
    - Implémenter les dataclasses internes : `PEABlock`, `HeadingBlock`, `TextBlock`, `PlaceholderBlock`, `AnnotationBlock`, `SectionInfo`, `PEADocument`
    - Implémenter les schémas Pydantic : `PEABlockSchema`, `SectionInfoSchema`, `PEAParseResponseSchema`, `PEASaveRequestSchema`, `PEASaveResponseSchema`
    - Configurer les alias camelCase pour la sérialisation JSON frontend
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 12.3_

  - [-] 1.2 Implémenter le service PEAEditorService (parser)
    - Créer le fichier `local-site/web/backend/services/pea_editor_service.py`
    - Implémenter `parse(file_bytes) -> PEADocument` avec python-docx
    - Implémenter `_extract_blocks()` : détection headings (styles Heading1-6 + numérotation x.x.x), placeholders `<<...>>`, annotations `@type...@`
    - Implémenter `_parse_annotation()` : extraction type, suffix, content pour mono-ligne et multi-paragraphe
    - Implémenter `_detect_heading()` : détection par style Word et regex de numérotation
    - Gérer les annotations multi-paragraphes (ouverture sans fermeture sur la même ligne)
    - Construire la liste `sections` pour la palette d'annotations
    - Signaler les erreurs (annotations non fermées, types inconnus) dans `PEADocument.errors`
    - Classifier `is_editable` : True pour remplir, dires, analyse, conclusion ; False pour les autres
    - _Requirements: 6.2, 6.3, 11.1, 11.2, 11.3, 11.4, 11.6, 11.7, 8.2, 8.3_

  - [~] 1.3 Implémenter le service PEASerializer
    - Créer le fichier `local-site/web/backend/services/pea_serializer.py`
    - Implémenter `serialize(source_bytes, blocks) -> bytes` : ouvrir le .docx source, mapper paragraph_index → bloc modifié, reconstruire les paragraphes d'annotations modifiées en préservant les runs/styles
    - Implémenter `_rebuild_paragraph()` : reconstruire le texte au format `@type params : contenu @`
    - Implémenter `_write_to_work_dir()` : écriture dans `c:\judi-expert\<dossier>\travail`
    - Préserver les placeholders et le texte non modifié
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 13.2, 13.3_

  - [~] 1.4 Créer le router FastAPI pea_editor
    - Créer le fichier `local-site/web/backend/routers/pea_editor.py`
    - Implémenter `POST /api/pea-editor/parse` : accepte multipart file, valide .docx, appelle PEAEditorService.parse(), retourne PEAParseResponseSchema
    - Implémenter `POST /api/pea-editor/save` : accepte PEASaveRequestSchema, décode base64, appelle PEASerializer, gère les erreurs filesystem
    - Gérer les erreurs HTTP : 400 (format invalide, .docx corrompu), 409 (fichier existant), 500 (erreur filesystem/sérialisation)
    - Enregistrer le router dans `main.py`
    - _Requirements: 6.2, 10.2, 10.4, 13.1, 13.2, 13.3, 13.4_

- [~] 2. Checkpoint — Vérifier le backend PEA Editor
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 3. Tests property-based du parser et sérialiseur
  - [~] 3.1 Écrire le test property pour le round-trip parsing-sérialisation
    - **Property 1: Parsing-Serialization Round-Trip**
    - Créer `tests/property/test_prop_pea_parser.py`
    - Implémenter la stratégie Hypothesis `valid_pea_documents()` générant des .docx avec annotations variées
    - Vérifier que parse → serialize → parse produit une structure identique (nombre d'annotations, types, contenus, références de section)
    - **Validates: Requirements 11.5**

  - [~] 3.2 Écrire le test property pour l'extraction des annotations
    - **Property 2: Annotation Parsing Extraction**
    - Implémenter la stratégie `valid_annotations()` générant des annotations mono-ligne et multi-paragraphe de tous types
    - Vérifier l'extraction correcte du type, suffix/paramètres, et contenu textuel
    - Vérifier pour @remplir : extraction field_name (snake_case, 1-64 chars) et format
    - Vérifier pour @dires/@analyse : extraction section reference (1-4 niveaux)
    - Vérifier pour @conclusion : extraction contenu multi-ligne
    - **Validates: Requirements 11.1, 11.2, 11.3, 11.4**

  - [~] 3.3 Écrire le test property pour la classification d'éditabilité
    - **Property 3: Editability Classification**
    - Créer `tests/property/test_prop_pea_editability.py`
    - Implémenter la stratégie `pea_blocks()` générant des blocs de tous types
    - Vérifier que `isEditable = True` ssi type annotation ∈ {remplir, dires, analyse, conclusion}
    - **Validates: Requirements 8.2, 8.3**

  - [~] 3.4 Écrire le test property pour la validité de la sérialisation
    - **Property 5: Serialization Produces Valid .docx**
    - Créer `tests/property/test_prop_pea_serializer.py`
    - Générer des blocs avec contenu modifié aléatoire, sérialiser, vérifier que le résultat est un ZIP valide contenant `word/document.xml` bien formé
    - **Validates: Requirements 12.4**

  - [~] 3.5 Écrire le test property pour la préservation des placeholders
    - **Property 6: Placeholder Preservation Through Serialization**
    - Générer des documents avec placeholders, modifier les annotations, sérialiser, vérifier que les placeholders sont identiques (noms, positions)
    - **Validates: Requirements 12.2, 10.2**

  - [~] 3.6 Écrire le test property pour la détection d'annotations non fermées
    - **Property 7: Unclosed Annotation Error Detection**
    - Générer des documents avec annotations tronquées (pas de `@` de fermeture), vérifier que le parser signale l'erreur avec paragraph_index et type
    - **Validates: Requirements 11.6**

  - [~] 3.7 Écrire le test property pour la tolérance aux types inconnus
    - **Property 8: Unknown Annotation Type Tolerance**
    - Générer des annotations avec des types aléatoires hors du set prédéfini, vérifier : pas d'exception, inclusion dans la liste de blocs, `is_editable = False`
    - **Validates: Requirements 11.7**

  - [~] 3.8 Écrire le test property pour l'insertion via la palette
    - **Property 9: Palette Insertion Format and Position**
    - Créer `tests/property/test_prop_pea_palette.py`
    - Générer texte aléatoire, position curseur, type annotation (cite, référence, résumé), cible (@dires section_x.x.x)
    - Vérifier que `@<type> @<cible>@` est inséré exactement à la position du curseur, contenu avant/après inchangé
    - **Validates: Requirements 9.3, 9.6**

- [ ] 4. Mise en place de la structure frontend — Layout Outils et navigation par onglets
  - [x] 4.1 Créer le layout Outils avec navigation par onglets
    - Créer `local-site/web/frontend/src/app/outils/layout.tsx`
    - Implémenter le composant `OutilsTabs` avec les trois onglets : "Mettre en forme", "Résumer", "Editer PEA"
    - Déterminer l'onglet actif via `usePathname()`
    - Rediriger `/outils` vers `/outils/mettre-en-forme` (via `redirect()` Next.js)
    - Rediriger les sous-routes invalides vers `/outils/mettre-en-forme`
    - Appliquer un style distinctif sur l'onglet actif vs inactifs
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [-] 4.2 Créer la page Mettre en forme (migration depuis Révision)
    - Créer `local-site/web/frontend/src/app/outils/mettre-en-forme/page.tsx`
    - Migrer la logique de correction orthographique/grammaticale depuis la page Révision existante
    - Conserver les modes fichier (.txt, .docx, .md) et texte avec `ProcessingTimer`
    - Conserver les appels aux endpoints existants `/api/revision/text` et `/api/revision/upload`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 3.1, 3.2, 3.3, 3.4, 3.5_

  - [-] 4.3 Créer la page Résumer (migration depuis Révision)
    - Créer `local-site/web/frontend/src/app/outils/resumer/page.tsx`
    - Migrer la logique de résumé depuis la page Révision existante
    - Conserver les modes fichier et texte avec `ProcessingTimer`
    - Conserver les appels aux endpoints existants `/api/revision/summarize` et `/api/revision/extract-text`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 5.1, 5.2, 5.3, 5.4, 5.5_

- [~] 5. Checkpoint — Vérifier la navigation par onglets
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Implémenter l'éditeur PEA frontend
  - [x] 6.1 Créer les types TypeScript PEA
    - Créer `local-site/web/frontend/src/types/pea.ts`
    - Définir tous les types : `PEABlockType`, `PEABlock`, `HeadingBlock`, `TextBlock`, `PlaceholderBlock`, `AnnotationBlock`, `InsertedAnnotation`, `SectionInfo`, `PEAParseResponse`, `PEASaveRequest`, `PEASaveResponse`
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 8.1, 8.2_

  - [-] 6.2 Créer le client API PEA Editor
    - Ajouter dans `local-site/web/frontend/src/lib/api.ts` les fonctions `peaEditorApi.parse()` et `peaEditorApi.save()`
    - Configurer les appels multipart pour le parse et JSON pour le save avec timeout 60s
    - _Requirements: 6.2, 10.2_

  - [~] 6.3 Implémenter la page PEA Editor principale
    - Créer `local-site/web/frontend/src/app/outils/editer-pea/page.tsx`
    - Implémenter le state machine : idle → loading → editing → saving → error
    - Afficher la note explicative en haut de page
    - Intégrer `PEAFileSelector`, `PEAFormRenderer`, `PEAAnnotationPalette`, `PEAToolbar`
    - Gérer le bouton "Enregistrer" et "Annuler"
    - Préserver les données du formulaire en cas d'erreur de sauvegarde
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 10.1, 10.2, 10.3, 10.4_

  - [~] 6.4 Implémenter le composant PEAFormRenderer
    - Créer `local-site/web/frontend/src/components/PEAFormRenderer.tsx`
    - Implémenter `PEABlockRenderer` avec switch sur block.type
    - `HeadingBlock` : rendu en `<hN>` avec numérotation
    - `TextBlock` : texte normal en lecture seule
    - `PlaceholderBlock` : rouge gras, lecture seule
    - `AnnotationBlock` éditable : marqueur rouge gras + textarea/input modifiable
    - `AnnotationBlock` non-éditable : marqueur rouge gras + contenu en lecture seule
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 8.1, 8.2, 8.3_

  - [~] 6.5 Implémenter le composant PEAAnnotationPalette
    - Créer `local-site/web/frontend/src/components/PEAAnnotationPalette.tsx`
    - Implémenter deux listes déroulantes : types (cite, référence, résumé) et cibles (sections du document)
    - Implémenter le bouton "Insérer" : insertion de `@<type> @<cible>@` à la position du curseur dans le textarea actif
    - Ne rien faire si aucun textarea n'est actif
    - Afficher les annotations insérées comme éléments inline rouges en lecture seule
    - Permettre la modification d'une annotation insérée par re-sélection + "Insérer"
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

- [~] 7. Checkpoint — Vérifier l'éditeur PEA complet
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Tests unitaires et intégration
  - [~] 8.1 Écrire les tests unitaires du parser PEA
    - Créer `tests/unit/test_pea_editor_service.py`
    - Tester chaque type d'annotation avec des exemples spécifiques
    - Tester les cas limites : contenu vide, caractères spéciaux, annotations imbriquées
    - Tester la détection de headings par style et par numérotation
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.6, 11.7_

  - [~] 8.2 Écrire les tests unitaires du sérialiseur PEA
    - Créer `tests/unit/test_pea_serializer.py`
    - Tester la préservation des styles avec des fixtures .docx connues
    - Tester la reconstruction des paragraphes d'annotations
    - Tester l'écriture dans le répertoire de travail
    - _Requirements: 12.1, 12.2, 12.3, 12.4_

  - [~] 8.3 Écrire les tests unitaires du router PEA Editor
    - Créer `tests/unit/test_pea_editor_router.py`
    - Tester les endpoints /parse et /save avec FastAPI TestClient
    - Tester les codes d'erreur HTTP (400, 409, 500)
    - _Requirements: 6.2, 10.2, 13.4_

  - [~] 8.4 Écrire les tests d'intégration du workflow PEA
    - Créer `tests/integration/test_pea_editor_workflow.py`
    - Tester le flux complet : upload .docx → parse → modifier annotations → save → vérifier output .docx
    - Tester la création du répertoire de travail
    - _Requirements: 11.5, 12.4, 13.2, 13.3_

- [~] 9. Final checkpoint — Vérifier l'ensemble de la fonctionnalité
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Le backend utilise Python (FastAPI + python-docx), le frontend utilise TypeScript (Next.js 14 + React 18)
- Les endpoints existants `/api/revision/*` ne sont pas modifiés, seul le frontend est réorganisé pour les onglets Formatter et Summarizer

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "4.1", "6.1"] },
    { "id": 1, "tasks": ["1.2", "4.2", "4.3", "6.2"] },
    { "id": 2, "tasks": ["1.3", "6.3"] },
    { "id": 3, "tasks": ["1.4", "6.4"] },
    { "id": 4, "tasks": ["3.1", "3.2", "3.3", "6.5"] },
    { "id": 5, "tasks": ["3.4", "3.5", "3.6", "3.7", "3.8"] },
    { "id": 6, "tasks": ["8.1", "8.2", "8.3"] },
    { "id": 7, "tasks": ["8.4"] }
  ]
}
```
