# Requirements Document

## Introduction

Fonctionnalité de révision documentaire autonome permettant à l'expert judiciaire de soumettre un document ou un texte pour correction automatique par le LLM. Le système accepte les fichiers .docx, .txt et .md, ainsi que du texte copié-collé directement dans une zone de saisie. Il corrige les fautes d'orthographe et de grammaire, développe les abréviations en phrases complètes, et améliore la lisibilité pour un lecteur psychologue non-expert. Le résultat est soit un fichier révisé avec suivi des modifications (track changes) pour les fichiers .docx, soit un texte corrigé affiché dans une zone de sortie (pour .txt, .md ou texte copié-collé) permettant à l'utilisateur de le copier ou télécharger.

Cette fonctionnalité est indépendante du workflow d'expertise en 4 étapes et accessible via un lien "Révision" dans le menu de navigation principal.

## Glossary

- **Revision_Service**: Service backend (FastAPI) responsable de l'orchestration du processus de révision documentaire (upload, appel LLM, génération du fichier révisé)
- **Revision_Page**: Page frontend Next.js accessible via le menu de navigation, permettant l'upload du fichier et le téléchargement du résultat
- **LLM_Service**: Service existant encapsulant les appels au modèle Mistral 7B via Ollama pour le traitement du langage naturel
- **Document_Parser**: Composant responsable de l'extraction du contenu textuel d'un fichier (.docx, .txt ou .md) tout en préservant la structure et le formatage
- **Track_Changes_Generator**: Composant responsable de la production du fichier .docx de sortie avec les marques de révision (insertions/suppressions) au format Word track changes
- **Input_File**: Fichier .docx, .txt ou .md soumis par l'utilisateur pour révision
- **Input_Text**: Texte copié-collé par l'utilisateur dans la zone de saisie de la page Révision
- **Output_File**: Fichier révisé nommé `fichier-revu.{ext}` contenant les corrections (track changes pour .docx, texte corrigé pour .txt/.md)
- **Output_Zone**: Zone de texte en lecture seule affichant le résultat de la révision lorsque l'entrée est du texte copié-collé ou un fichier .txt/.md

## Requirements

### Requirement 1: Navigation et accès à la page Révision

**User Story:** En tant qu'expert judiciaire, je veux accéder à la fonctionnalité de révision depuis le menu principal, afin de pouvoir réviser un document à tout moment sans dépendre d'un dossier d'expertise.

#### Acceptance Criteria

1. THE Revision_Page SHALL be accessible via a navigation link labeled "Révision" in the main header menu
2. WHEN the user navigates to the Révision route, THE Revision_Page SHALL display two input modes: a file upload zone and a text input zone
3. THE Revision_Page SHALL be accessible independently from any active expertise dossier
4. THE Revision_Page SHALL display an Output_Zone below the input area for displaying text results

### Requirement 2: Upload du fichier d'entrée

**User Story:** En tant qu'expert judiciaire, je veux uploader un fichier .docx, .txt ou .md, afin que le système puisse le réviser automatiquement.

#### Acceptance Criteria

1. THE Revision_Page SHALL provide a file upload control accepting files with `.docx`, `.txt`, or `.md` extensions
2. WHEN the user selects a file that is not a valid .docx, .txt, or .md file, THE Revision_Page SHALL display an error message indicating the accepted formats
3. WHEN the user uploads a valid file, THE Revision_Service SHALL receive the file via a multipart form data request
4. IF the uploaded file exceeds 20 MB, THEN THE Revision_Service SHALL reject the request and return an error indicating the file size limit

### Requirement 2b: Saisie de texte directe

**User Story:** En tant qu'expert judiciaire, je veux pouvoir coller du texte directement dans une zone de saisie, afin de réviser rapidement un extrait sans créer de fichier.

#### Acceptance Criteria

1. THE Revision_Page SHALL provide a text input area (textarea) where the user can paste or type text directly
2. WHEN the user submits text via the input area, THE Revision_Service SHALL receive the text content via a JSON request body
3. IF the submitted text is empty, THEN THE Revision_Page SHALL display an error message indicating that text content is required
4. IF the submitted text exceeds 100 000 characters, THEN THE Revision_Service SHALL reject the request and return an error indicating the text size limit

### Requirement 3: Extraction du contenu textuel avec préservation du formatage

**User Story:** En tant qu'expert judiciaire, je veux que le formatage de mon document soit strictement préservé, afin de ne pas avoir à reformater le document après révision.

#### Acceptance Criteria

1. WHEN a valid .docx file is received, THE Document_Parser SHALL extract the textual content while preserving the document structure (paragraphs, headings, tables, lists)
2. THE Document_Parser SHALL preserve all Word formatting attributes (bold, italic, underline, font size, font color, styles, heading levels)
3. THE Document_Parser SHALL preserve table structures including cell content, merged cells, and table formatting
4. THE Document_Parser SHALL preserve images, headers, footers, and page layout without modification
5. WHEN a .txt file is received, THE Document_Parser SHALL read the content as plain text (UTF-8)
6. WHEN a .md file is received, THE Document_Parser SHALL read the content as Markdown text (UTF-8) preserving the Markdown structure
7. WHEN text is submitted via the input area (Input_Text), THE Revision_Service SHALL use the text content directly without file parsing

### Requirement 4: Correction par le LLM

**User Story:** En tant qu'expert judiciaire, je veux que le LLM corrige les erreurs et améliore la lisibilité de mon document, afin de produire un texte professionnel adapté à un lecteur psychologue non-expert.

#### Acceptance Criteria

1. WHEN textual content is extracted, THE LLM_Service SHALL correct all spelling and grammar errors in the text
2. WHEN textual content is extracted, THE LLM_Service SHALL expand abbreviated phrases into full proper sentences
3. WHEN textual content is extracted, THE LLM_Service SHALL improve readability for a non-expert psychologist reader
4. THE LLM_Service SHALL process the text without altering the semantic meaning of the original content
5. THE LLM_Service SHALL preserve all domain-specific terminology (legal, medical, psychological terms) without modification

### Requirement 5: Génération du fichier de sortie avec suivi des modifications

**User Story:** En tant qu'expert judiciaire, je veux recevoir un fichier Word avec le suivi des modifications activé, afin de pouvoir accepter ou rejeter chaque correction individuellement.

#### Acceptance Criteria

1. WHEN the LLM has produced corrected text from a .docx Input_File, THE Track_Changes_Generator SHALL produce an Output_File in .docx format with revision marks
2. THE Track_Changes_Generator SHALL encode all corrections as Word track changes (revision marks) with insertions and deletions visible
3. THE Track_Changes_Generator SHALL name the Output_File `fichier-revu.docx`
4. THE Track_Changes_Generator SHALL preserve the original formatting of the Input_File in the Output_File
5. WHEN the user opens the Output_File in Microsoft Word, THE Output_File SHALL display revision marks that the user can accept or reject individually

### Requirement 5b: Affichage du résultat pour texte et fichiers .txt/.md

**User Story:** En tant qu'expert judiciaire, je veux voir le texte corrigé directement dans la page lorsque j'ai soumis du texte ou un fichier .txt/.md, afin de pouvoir le copier rapidement.

#### Acceptance Criteria

1. WHEN the LLM has produced corrected text from an Input_Text or a .txt/.md Input_File, THE Revision_Page SHALL display the corrected text in the Output_Zone below the input area
2. THE Output_Zone SHALL be a read-only text area with a "Copier" button allowing the user to copy the content to the clipboard
3. WHEN the input was a .txt file, THE Revision_Page SHALL also offer a download button for `fichier-revu.txt`
4. WHEN the input was a .md file, THE Revision_Page SHALL also offer a download button for `fichier-revu.md`
5. WHEN the input was text copié-collé, THE Revision_Page SHALL display the result only in the Output_Zone (no file download)

### Requirement 6: Téléchargement du fichier révisé

**User Story:** En tant qu'expert judiciaire, je veux télécharger le fichier révisé facilement, afin de l'utiliser dans mon travail.

#### Acceptance Criteria

1. WHEN the revision process completes successfully for a file input, THE Revision_Page SHALL display a download button for the Output_File
2. WHEN the user clicks the download button, THE Revision_Page SHALL trigger a browser download of the file named `fichier-revu.{ext}` (where ext matches the input format)
3. WHILE the revision process is in progress, THE Revision_Page SHALL display a progress indicator informing the user that processing is underway
4. WHEN the revision process completes successfully for a text input, THE Revision_Page SHALL display the corrected text in the Output_Zone without a download button

### Requirement 7: Gestion des erreurs

**User Story:** En tant qu'expert judiciaire, je veux être informé clairement en cas de problème, afin de comprendre ce qui s'est passé et pouvoir réessayer.

#### Acceptance Criteria

1. IF the LLM service is unavailable or times out, THEN THE Revision_Service SHALL return an error message indicating that the revision service is temporarily unavailable
2. IF the uploaded file is corrupted or cannot be parsed, THEN THE Revision_Service SHALL return an error message indicating that the file could not be read
3. IF an error occurs during the revision process, THEN THE Revision_Page SHALL display the error message to the user and offer the option to retry
4. IF the document content exceeds the LLM context window capacity, THEN THE Revision_Service SHALL process the document in sequential chunks and reassemble the results
5. IF a .txt or .md file cannot be decoded as UTF-8, THEN THE Revision_Service SHALL return an error message indicating the encoding issue

### Requirement 8: Indépendance du workflow d'expertise

**User Story:** En tant qu'expert judiciaire, je veux que la révision soit totalement indépendante du workflow d'expertise, afin de pouvoir réviser n'importe quel document sans créer de dossier.

#### Acceptance Criteria

1. THE Revision_Service SHALL operate without requiring an active expertise dossier
2. THE Revision_Service SHALL not persist the Input_File or Output_File in the application database
3. WHEN the revision process is complete and the user has downloaded the Output_File, THE Revision_Service SHALL delete any temporary files created during processing
