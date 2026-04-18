# Requirements Document

## Introduction

Refactoring du workflow d'expertise et de la page dossier dans l'Application Locale Judi-Expert. Ce document couvre le renommage des étapes du workflow (frontend local + site central), la refonte du Step 2 (upload NEA → production RE-Projet + RE-Projet-Auxiliaire), la refonte du Step 3 (utilisation du NEA → production REF-Projet), l'ajout d'un mécanisme de fermeture de dossier avec téléchargement ZIP, et l'affichage enrichi des fichiers par étape avec prévisualisation, téléchargement et remplacement.

## Glossary

- **Application_Locale**: Application Next.js 14 + FastAPI installée sur le PC de l'expert, composée du frontend (`local-site/web/frontend`) et du backend (`local-site/web/backend`)
- **Site_Central**: Site web hébergé sur AWS (`central-site/web/frontend`) présentant le workflow d'expertise sur la page d'accueil
- **Dossier_Page**: Page de détail d'un dossier dans l'Application_Locale (`/dossier/[id]`)
- **Step_Page**: Page de détail d'une étape dans l'Application_Locale (`/dossier/[id]/step/[n]`)
- **WorkflowEngine**: Service backend (`services/workflow_engine.py`) gérant les transitions de statut des étapes
- **StepFile**: Modèle SQLAlchemy représentant un fichier associé à une étape (table `step_files`)
- **NEA**: Notes d'Entretien et Analyse — fichier .docx uploadé par l'expert au Step 2
- **RE_Projet**: Rapport d'expertise projet — document .docx produit au Step 2 à partir du NEA et du template de rapport
- **RE_Projet_Auxiliaire**: Document auxiliaire d'analyse — document .docx produit au Step 2 en complément du RE_Projet
- **REF_Projet**: Rapport d'expertise final — document .docx produit au Step 3 à partir du NEA
- **STEP_NAMES**: Dictionnaire de correspondance entre numéro d'étape et libellé affiché dans l'interface
- **Dossier_Statut**: Statut d'un dossier, valeurs possibles : "actif", "fermé", "archive"
- **ZIP_Archive**: Archive ZIP contenant tous les fichiers uploadés et produits par les 4 étapes d'un dossier

## Requirements

### Requirement 1: Renommage des étapes du workflow dans l'Application Locale

**User Story:** As an expert judiciaire, I want the workflow steps to have clear, descriptive names, so that I understand what each step does at a glance.

#### Acceptance Criteria

1. THE Application_Locale SHALL display the following STEP_NAMES mapping on the Dossier_Page and Step_Page: Step 0 = "Extraction", Step 1 = "Préparation entretien", Step 2 = "Mise en forme RE-Projet", Step 3 = "Génération rapport expertise"
2. WHEN the Dossier_Page renders the list of steps, THE Application_Locale SHALL display each step with its updated label from the STEP_NAMES mapping
3. WHEN the Step_Page renders the header for a given step, THE Application_Locale SHALL display the updated label from the STEP_NAMES mapping

### Requirement 2: Renommage des étapes du workflow sur le Site Central

**User Story:** As a visitor of the Site Central, I want the workflow section on the homepage to reflect the current step names, so that the public documentation is consistent with the application.

#### Acceptance Criteria

1. THE Site_Central SHALL display the following step labels in the "Workflow d'expertise" section of the homepage: Step 0 = "Extraction", Step 1 = "Préparation entretien", Step 2 = "Mise en forme RE-Projet", Step 3 = "Génération rapport expertise"
2. THE Site_Central SHALL display an updated description for each step matching its new purpose: Step 2 describes the upload of the NEA and the production of the RE_Projet and RE_Projet_Auxiliaire, Step 3 describes the generation of the REF_Projet from the NEA

### Requirement 3: Refonte du Step 2 — Mise en forme RE-Projet

**User Story:** As an expert judiciaire, I want to upload a single NEA file and receive the RE-Projet and RE-Projet-Auxiliaire as output, so that the system produces the formatted expertise report from my interview notes.

#### Acceptance Criteria

1. WHEN the expert uploads a file at Step 2, THE Application_Locale SHALL accept a single .docx file named NEA (Notes d'Entretien et Analyse)
2. IF the uploaded file is not in .docx format, THEN THE Application_Locale SHALL return an HTTP 400 error with the message "Seul le format .docx est accepté"
3. WHEN the NEA file is uploaded, THE Application_Locale SHALL save the file as `nea.docx` in the directory `data/dossiers/{id}/step2/`
4. WHEN the NEA file is saved, THE Application_Locale SHALL call the LLM service to generate the RE_Projet document using the NEA content, the requisition Markdown from Step 0, and the report template from the RAG corpus
5. WHEN the RE_Projet is generated, THE Application_Locale SHALL call the LLM service to generate the RE_Projet_Auxiliaire document
6. THE Application_Locale SHALL save the RE_Projet as `re_projet.docx` and the RE_Projet_Auxiliaire as `re_projet_auxiliaire.docx` in the directory `data/dossiers/{id}/step2/`
7. THE Application_Locale SHALL create StepFile entries in the database for the three files: `nea.docx` (type "nea"), `re_projet.docx` (type "re_projet"), and `re_projet_auxiliaire.docx` (type "re_projet_auxiliaire")
8. WHEN Step 2 execution completes, THE WorkflowEngine SHALL mark the step as "réalisé"

### Requirement 4: Refonte du Step 3 — Génération rapport expertise

**User Story:** As an expert judiciaire, I want Step 3 to use the NEA uploaded at Step 2 to generate the final expertise report, so that I get a polished REF-Projet document.

#### Acceptance Criteria

1. WHEN Step 3 is executed, THE Application_Locale SHALL read the NEA file (`nea.docx`) from the directory `data/dossiers/{id}/step2/`
2. IF the NEA file is not found in the Step 2 directory, THEN THE Application_Locale SHALL return an HTTP 404 error with the message "Fichier NEA non trouvé — complétez d'abord le Step 2"
3. WHEN the NEA file is read, THE Application_Locale SHALL call the LLM service to generate the REF_Projet document using the NEA content, the requisition Markdown from Step 0, and the report template from the RAG corpus
4. THE Application_Locale SHALL save the REF_Projet as `ref_projet.docx` in the directory `data/dossiers/{id}/step3/`
5. THE Application_Locale SHALL create a StepFile entry in the database for `ref_projet.docx` (type "ref_projet")
6. WHEN Step 3 execution completes, THE WorkflowEngine SHALL mark the step as "réalisé"

### Requirement 5: Fermeture de dossier

**User Story:** As an expert judiciaire, I want to close a dossier when all steps are complete, so that no further modifications can be made and I can download the complete archive.

#### Acceptance Criteria

1. WHEN all four steps of a dossier have statut "validé", THE Dossier_Page SHALL display a "Fermer le dossier" button
2. WHEN the expert clicks "Fermer le dossier", THE Application_Locale SHALL send a POST request to the backend endpoint `POST /api/dossiers/{id}/close`
3. WHEN the close endpoint is called, THE WorkflowEngine SHALL verify that all four steps have statut "validé" before proceeding
4. IF any step does not have statut "validé", THEN THE Application_Locale SHALL return an HTTP 403 error with the message "Toutes les étapes doivent être validées pour fermer le dossier"
5. WHEN the dossier is closed, THE Application_Locale SHALL set the Dossier_Statut to "fermé"
6. WHILE a dossier has Dossier_Statut "fermé", THE Application_Locale SHALL block all modification operations on the dossier and display the dossier in read-only mode
7. WHEN a dossier has Dossier_Statut "fermé", THE Dossier_Page SHALL display a "Télécharger le dossier" button

### Requirement 6: Génération et téléchargement de l'archive ZIP

**User Story:** As an expert judiciaire, I want to download a ZIP archive of all documents in a closed dossier, so that I have a complete backup of the expertise.

#### Acceptance Criteria

1. WHEN the expert clicks "Télécharger le dossier", THE Application_Locale SHALL send a GET request to the backend endpoint `GET /api/dossiers/{id}/download`
2. WHEN the download endpoint is called, THE Application_Locale SHALL generate a ZIP_Archive containing all files from directories `data/dossiers/{id}/step0/`, `data/dossiers/{id}/step1/`, `data/dossiers/{id}/step2/`, and `data/dossiers/{id}/step3/`
3. THE ZIP_Archive SHALL preserve the step directory structure inside the archive (e.g., `step0/requisition.pdf`, `step2/nea.docx`)
4. IF the dossier does not have Dossier_Statut "fermé", THEN THE Application_Locale SHALL return an HTTP 403 error with the message "Le dossier doit être fermé pour télécharger l'archive"
5. THE Application_Locale SHALL return the ZIP_Archive as a file download response with content type `application/zip` and filename `dossier_{id}_archive.zip`

### Requirement 7: Affichage des fichiers par étape

**User Story:** As an expert judiciaire, I want to see all files (input and output) for each step on the Dossier Page, so that I can track what has been uploaded and produced.

#### Acceptance Criteria

1. WHEN the Dossier_Page renders a step section, THE Application_Locale SHALL display the list of StepFile entries associated with that step
2. THE Application_Locale SHALL display for each StepFile: the filename, the file type (input or output), and the file size formatted in human-readable units (KB, MB)
3. WHEN a step has no associated StepFile entries, THE Application_Locale SHALL display the message "Aucun fichier pour cette étape"

### Requirement 8: Prévisualisation et téléchargement de fichiers individuels

**User Story:** As an expert judiciaire, I want to preview or download any file produced or uploaded during the workflow, so that I can review documents without leaving the application.

#### Acceptance Criteria

1. THE Application_Locale SHALL provide a backend endpoint `GET /api/dossiers/{id}/files/{file_id}/download` that returns the file content as a download response
2. WHEN the expert clicks the download button for a StepFile, THE Application_Locale SHALL trigger a file download using the download endpoint
3. THE Application_Locale SHALL provide a backend endpoint `GET /api/dossiers/{id}/files/{file_id}/preview` that returns the file content for inline display
4. WHEN the expert clicks the preview button for a Markdown StepFile, THE Application_Locale SHALL display the file content in a modal or inline viewer
5. WHEN the expert clicks the preview button for a PDF StepFile, THE Application_Locale SHALL open the file in a new browser tab
6. WHEN the expert clicks the preview button for a .docx StepFile, THE Application_Locale SHALL trigger a file download (no inline preview for .docx)

### Requirement 9: Remplacement de fichier par l'expert

**User Story:** As an expert judiciaire, I want to upload a modified version of a file to replace the original, so that subsequent steps use my corrected version.

#### Acceptance Criteria

1. WHILE a step has statut "réalisé" and the dossier has Dossier_Statut "actif", THE Step_Page SHALL display an "Upload version modifiée" button next to each StepFile
2. WHEN the expert uploads a replacement file, THE Application_Locale SHALL send a PUT request to the backend endpoint `PUT /api/dossiers/{id}/files/{file_id}/replace` with the new file content
3. WHEN the replace endpoint is called, THE Application_Locale SHALL overwrite the original file on disk at the same file_path
4. WHEN the file is replaced, THE Application_Locale SHALL update the StepFile entry in the database with the new file_size
5. IF the step has statut "validé", THEN THE Application_Locale SHALL return an HTTP 403 error with the message "Étape verrouillée, modification impossible"
6. IF the dossier has Dossier_Statut "fermé", THEN THE Application_Locale SHALL return an HTTP 403 error with the message "Le dossier est fermé, aucune modification n'est possible"
