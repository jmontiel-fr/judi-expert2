# Requirements Document

## Introduction

Ce document spécifie les exigences pour la fonctionnalité "Outils d'édition PEA" (pea-editor-tools). Cette fonctionnalité réorganise la page "Révision" existante en une page "Outils" avec un sous-menu à trois onglets : "Mettre en forme", "Résumer" et "Editer PEA". Les deux premiers onglets reprennent et séparent les fonctionnalités actuelles de révision et résumé, tandis que le troisième onglet introduit un éditeur de formulaire pour les annotations PEA.

## Glossary

- **Outils_Page**: Page principale regroupant les sous-pages "Mettre en forme", "Résumer" et "Editer PEA" sous un menu de navigation par onglets
- **Formatter**: Sous-page "Mettre en forme" permettant la correction orthographique et grammaticale de texte via le LLM
- **Summarizer**: Sous-page "Résumer" permettant la génération de résumés de texte via le LLM
- **PEA_Editor**: Sous-page "Editer PEA" permettant l'édition des annotations dans un document TPE/PEA sous forme de formulaire
- **Annotation**: Marqueur structuré dans un document PEA délimité par `@type ... @` contenant du contenu modifiable par l'expert (types : @remplir, @dire, @analyse, @conclusion)
- **Placeholder**: Champ de fusion `<<...>>` dans un document TPE/PEA qui reste non modifiable dans l'éditeur
- **Section_Heading**: Titre de section numéroté (x.x.x.x) dans le document TPE/PEA, mappé vers les niveaux HTML H1-Hn
- **Annotation_Palette**: Barre d'outils composée de deux listes déroulantes et d'un bouton "Insérer" permettant d'insérer des annotations dans les zones de texte
- **Work_Directory**: Répertoire de sortie `c:\judi-expert\<dossier>\travail` où les fichiers produits sont enregistrés
- **Processing_Timer**: Indicateur visuel (sablier animé + chronomètre) affiché pendant le traitement LLM

## Requirements

### Requirement 1: Navigation par onglets de la page Outils

**User Story:** En tant qu'expert judiciaire, je veux accéder aux outils d'édition via une page unique avec un sous-menu à onglets, afin de naviguer facilement entre les fonctionnalités de mise en forme, résumé et édition PEA.

#### Acceptance Criteria

1. WHEN l'utilisateur accède à la route `/outils`, THE Outils_Page SHALL afficher un menu de navigation avec exactement trois onglets libellés "Mettre en forme", "Résumer" et "Editer PEA", dans cet ordre de gauche à droite
2. WHEN l'utilisateur clique sur un onglet, THE Outils_Page SHALL afficher le contenu de la sous-page correspondante sans rechargement complet de la page et SHALL appliquer un indicateur visuel distinctif (style différencié) sur l'onglet actif par rapport aux onglets inactifs
3. THE Outils_Page SHALL conserver l'onglet actif dans l'URL (ex: `/outils/mettre-en-forme`, `/outils/resumer`, `/outils/editer-pea`) pour permettre le partage de liens et la navigation par historique du navigateur (boutons précédent/suivant)
4. WHEN l'utilisateur accède à `/outils` sans sous-route, THE Outils_Page SHALL afficher l'onglet "Mettre en forme" par défaut et SHALL mettre à jour l'URL vers `/outils/mettre-en-forme`
5. IF l'utilisateur accède à une sous-route invalide sous `/outils` (ex: `/outils/inexistant`), THEN THE Outils_Page SHALL rediriger vers `/outils/mettre-en-forme`

### Requirement 2: Mode fichier pour Mettre en forme

**User Story:** En tant qu'expert judiciaire, je veux soumettre un fichier (.txt, .docx ou .md) pour correction orthographique et grammaticale, afin d'obtenir un fichier corrigé enregistré dans mon répertoire de travail.

#### Acceptance Criteria

1. WHEN l'utilisateur sélectionne le mode fichier dans la sous-page Formatter, THE Formatter SHALL afficher une zone de sélection de fichier acceptant les formats .txt, .docx et .md
2. WHEN un fichier valide est sélectionné et soumis, THE Formatter SHALL envoyer le fichier au backend pour traitement par le LLM
3. WHILE le traitement est en cours, THE Processing_Timer SHALL afficher un sablier animé accompagné d'un chronomètre indiquant la durée écoulée en secondes
4. WHEN le traitement est terminé, THE Formatter SHALL proposer un bouton de téléchargement permettant de récupérer le fichier corrigé
5. WHEN l'utilisateur choisit d'enregistrer le fichier, THE Formatter SHALL placer le fichier produit dans le Work_Directory sous le nom spécifié par l'utilisateur
6. IF le fichier soumis dépasse 20 Mo, THEN THE Formatter SHALL afficher un message d'erreur indiquant la limite de taille
7. IF le format du fichier soumis ne correspond pas à .txt, .docx ou .md, THEN THE Formatter SHALL afficher un message d'erreur indiquant les formats acceptés

### Requirement 3: Mode texte pour Mettre en forme

**User Story:** En tant qu'expert judiciaire, je veux soumettre du texte par copier-coller pour correction orthographique et grammaticale, afin d'obtenir le texte corrigé directement dans l'interface.

#### Acceptance Criteria

1. WHEN l'utilisateur sélectionne le mode texte dans la sous-page Formatter, THE Formatter SHALL afficher une zone de saisie (textarea) pour le texte d'entrée et une zone de lecture pour le texte de sortie
2. WHEN l'utilisateur soumet du texte via le bouton "Réviser", THE Formatter SHALL envoyer le texte au backend pour traitement par le LLM
3. WHILE le traitement est en cours, THE Processing_Timer SHALL afficher un sablier animé accompagné d'un chronomètre indiquant la durée écoulée en secondes
4. WHEN le traitement est terminé, THE Formatter SHALL afficher le texte corrigé dans la zone de sortie
5. IF le texte soumis est vide, THEN THE Formatter SHALL désactiver le bouton de soumission

### Requirement 4: Mode fichier pour Résumer

**User Story:** En tant qu'expert judiciaire, je veux soumettre un fichier (.txt, .docx ou .md) pour en obtenir un résumé, afin de synthétiser rapidement le contenu d'un document.

#### Acceptance Criteria

1. WHEN l'utilisateur sélectionne le mode fichier dans la sous-page Summarizer, THE Summarizer SHALL afficher une zone de sélection de fichier acceptant les formats .txt, .docx et .md
2. WHEN un fichier valide est sélectionné et soumis, THE Summarizer SHALL envoyer le fichier au backend pour résumé par le LLM
3. WHILE le traitement est en cours, THE Processing_Timer SHALL afficher un sablier animé accompagné d'un chronomètre indiquant la durée écoulée en secondes
4. WHEN le traitement est terminé, THE Summarizer SHALL proposer un bouton de téléchargement permettant de récupérer le fichier résumé
5. WHEN l'utilisateur choisit d'enregistrer le fichier, THE Summarizer SHALL placer le fichier produit dans le Work_Directory sous le nom spécifié par l'utilisateur
6. IF le fichier soumis dépasse 20 Mo, THEN THE Summarizer SHALL afficher un message d'erreur indiquant la limite de taille

### Requirement 5: Mode texte pour Résumer

**User Story:** En tant qu'expert judiciaire, je veux soumettre du texte par copier-coller pour en obtenir un résumé, afin de synthétiser rapidement un contenu textuel.

#### Acceptance Criteria

1. WHEN l'utilisateur sélectionne le mode texte dans la sous-page Summarizer, THE Summarizer SHALL afficher une zone de saisie (textarea) pour le texte d'entrée et une zone de lecture pour le texte de sortie
2. WHEN l'utilisateur soumet du texte via le bouton "Résumer", THE Summarizer SHALL envoyer le texte au backend pour résumé par le LLM
3. WHILE le traitement est en cours, THE Processing_Timer SHALL afficher un sablier animé accompagné d'un chronomètre indiquant la durée écoulée en secondes
4. WHEN le traitement est terminé, THE Summarizer SHALL afficher le résumé dans la zone de sortie
5. IF le texte soumis est vide, THEN THE Summarizer SHALL désactiver le bouton de soumission

### Requirement 6: Chargement de document dans l'éditeur PEA

**User Story:** En tant qu'expert judiciaire, je veux charger un fichier tpe.docx ou pea.docx dans l'éditeur PEA, afin de visualiser et compléter les annotations sous forme de formulaire.

#### Acceptance Criteria

1. THE PEA_Editor SHALL afficher en haut de page la note explicative : "Cette page permet de générer un pea.docx à partir d'un tpe.docx ou d'un pea.docx en cours de préparation, en faisant apparaître les @annotations sous forme de champs de formulaires à compléter."
2. WHEN l'utilisateur sélectionne un fichier .docx, THE PEA_Editor SHALL parser le document pour extraire la structure (sections, placeholders, annotations)
3. WHEN le parsing est terminé, THE PEA_Editor SHALL afficher le contenu du document sous forme de formulaire HTML
4. IF le fichier sélectionné ne contient aucune annotation reconnue (@remplir, @dire, @analyse, @conclusion), THEN THE PEA_Editor SHALL afficher un message indiquant qu'aucune annotation modifiable n'a été trouvée

### Requirement 7: Affichage du formulaire PEA

**User Story:** En tant qu'expert judiciaire, je veux visualiser le document PEA sous forme de formulaire structuré, afin de distinguer clairement les zones modifiables des zones en lecture seule.

#### Acceptance Criteria

1. THE PEA_Editor SHALL afficher les titres de sections avec leur numérotation (x.x.x.x) mappés vers les niveaux HTML correspondants (Titre Principal → H1, Titre1 → H2, Titre2 → H3, etc.)
2. THE PEA_Editor SHALL afficher les Placeholder en rouge gras et en lecture seule
3. THE PEA_Editor SHALL afficher le texte hors annotations en texte normal sans formatage supplémentaire et en lecture seule
4. THE PEA_Editor SHALL afficher les marqueurs d'Annotation (@remplir, @dire, @analyse, @conclusion) en rouge gras
5. WHEN une Annotation est affichée, THE PEA_Editor SHALL présenter son contenu dans une zone de texte modifiable (input text ou textarea selon la longueur attendue)
6. THE PEA_Editor SHALL conserver la numérotation des sections du document source dans l'affichage du formulaire

### Requirement 8: Édition des annotations PEA

**User Story:** En tant qu'expert judiciaire, je veux modifier le contenu des annotations @remplir, @dire, @analyse et @conclusion, afin de compléter mon rapport d'expertise.

#### Acceptance Criteria

1. WHEN l'utilisateur modifie le contenu d'une zone de texte associée à une Annotation, THE PEA_Editor SHALL conserver la modification en mémoire
2. THE PEA_Editor SHALL permettre la modification uniquement des contenus des annotations @remplir, @dire, @analyse et @conclusion
3. THE PEA_Editor SHALL empêcher la modification du texte hors annotations, des Placeholder et des titres de sections

### Requirement 9: Palette d'insertion d'annotations

**User Story:** En tant qu'expert judiciaire, je veux insérer des annotations prédéfinies (cite, référence, résumé) dans les zones de texte via une palette, afin d'enrichir le contenu de mes annotations avec des références structurées.

#### Acceptance Criteria

1. THE Annotation_Palette SHALL afficher deux listes déroulantes : la première contenant les types d'annotation (cite, référence, résumé) et la seconde contenant les cibles disponibles dans le document courant (au format @dires section_x.x.x ou @analyse_x.x.x), peuplées dynamiquement à partir des sections présentes dans le fichier édité
2. THE Annotation_Palette SHALL afficher un bouton "Insérer" à côté des listes déroulantes
3. WHEN le curseur est positionné dans une zone de texte (textarea) et l'utilisateur clique sur "Insérer", THE Annotation_Palette SHALL insérer à la position du curseur une balise au format `@<type> @<cible>@` correspondant au type sélectionné (colonne 1) et à la cible sélectionnée (colonne 2)
4. IF le curseur n'est positionné dans aucune zone de texte (textarea) lorsque l'utilisateur clique sur "Insérer", THEN THE Annotation_Palette SHALL ne pas effectuer d'insertion et ne pas modifier le contenu du formulaire
5. WHEN une annotation est insérée dans une zone de texte, THE PEA_Editor SHALL afficher cette annotation comme un élément en ligne rouge, en lecture seule, non modifiable par saisie clavier directe
6. WHEN l'utilisateur clique sur une annotation insérée dans une zone de texte puis modifie les sélections des listes déroulantes et clique "Insérer", THE PEA_Editor SHALL remplacer le contenu de l'annotation sélectionnée par la nouvelle balise correspondant aux nouvelles sélections

### Requirement 10: Sauvegarde du document PEA

**User Story:** En tant qu'expert judiciaire, je veux enregistrer le document PEA complété avec mes annotations, afin de produire un fichier pea.docx final exploitable.

#### Acceptance Criteria

1. THE PEA_Editor SHALL afficher en haut de page un bouton "Enregistrer" et un bouton "Annuler"
2. WHEN l'utilisateur clique sur "Enregistrer", THE PEA_Editor SHALL générer un fichier pea.docx contenant le texte du tpe.docx avec son style d'origine, les Placeholder inchangés et les Annotation avec leur contenu modifié
3. WHEN l'utilisateur clique sur "Annuler", THE PEA_Editor SHALL réinitialiser le formulaire à l'état initial du document chargé sans sauvegarder les modifications
4. IF une erreur survient lors de la génération du fichier pea.docx, THEN THE PEA_Editor SHALL afficher un message d'erreur descriptif sans perdre les données saisies dans le formulaire

### Requirement 11: Parsing des annotations du document PEA

**User Story:** En tant que développeur, je veux un parser robuste pour les annotations PEA, afin d'extraire correctement la structure du document pour l'affichage en formulaire.

#### Acceptance Criteria

1. THE PEA_Editor SHALL parser les annotations au format `@type contenu@` (annotation mono-ligne) ou `@type contenu` suivi de lignes de contenu et fermé par un `@` seul en fin de ligne (annotation multi-paragraphe), où type est l'un de : remplir, dires, analyse, conclusion, verbatim, resume, reference, cite, question
2. WHEN le parser rencontre une annotation `@remplir champ_name format :`, THE PEA_Editor SHALL extraire le nom du champ (identifiant snake_case, 1 à 64 caractères) et le format attendu (texte après le nom de champ et avant le `:`) comme métadonnée associée à la zone de saisie correspondante
3. WHEN le parser rencontre une annotation `@dires section_x.x.x` ou `@analyse section_x.x.x`, THE PEA_Editor SHALL extraire la référence de section (format numérique x.x.x avec 1 à 4 niveaux de profondeur) comme métadonnée de l'annotation et le contenu textuel entre l'ouverture et le marqueur `@` de fermeture
4. WHEN le parser rencontre une annotation `@conclusion`, THE PEA_Editor SHALL créer une zone de texte multiligne (textarea) pour le contenu de la conclusion, délimité entre le marqueur d'ouverture `@conclusion` et le marqueur de fermeture `@`
5. WHEN le parser effectue un parsing suivi d'une sérialisation puis d'un re-parsing sur un document PEA valide, THE PEA_Editor SHALL produire un résultat identique en nombre d'annotations, types, contenus textuels et références de section (propriété round-trip)
6. IF le parser rencontre une annotation dont le marqueur de fermeture `@` est absent en fin de document, THEN THE PEA_Editor SHALL signaler une erreur indiquant le numéro de paragraphe d'ouverture et le type de l'annotation non fermée
7. IF le parser rencontre un type d'annotation non reconnu (hors de la liste définie au critère 1), THEN THE PEA_Editor SHALL parser l'annotation sans erreur en la marquant comme annotation de type inconnu, et inclure le type brut dans les métadonnées extraites

### Requirement 12: Sérialisation du document PEA en .docx

**User Story:** En tant que développeur, je veux un sérialiseur qui produit un fichier .docx valide à partir du formulaire édité, afin de préserver le style d'origine du document source.

#### Acceptance Criteria

1. WHEN le PEA_Editor sérialise le document, THE PEA_Editor SHALL préserver les styles d'origine du fichier tpe.docx source (polices, tailles, marges, en-têtes)
2. WHEN le PEA_Editor sérialise le document, THE PEA_Editor SHALL conserver les Placeholder `<<...>>` inchangés dans le fichier de sortie
3. WHEN le PEA_Editor sérialise le document, THE PEA_Editor SHALL intégrer le contenu modifié des annotations dans le format `@type paramètres : contenu @`
4. FOR ALL formulaires PEA complétés, la sérialisation SHALL produire un fichier .docx valide et lisible par Microsoft Word

### Requirement 13: Enregistrement des fichiers dans le répertoire de travail

**User Story:** En tant qu'expert judiciaire, je veux que les fichiers produits soient enregistrés dans mon répertoire de travail local, afin de les retrouver facilement dans l'arborescence de mon dossier.

#### Acceptance Criteria

1. WHEN l'utilisateur demande l'enregistrement d'un fichier produit, THE Outils_Page SHALL permettre à l'utilisateur de spécifier le nom du fichier de sortie
2. WHEN l'utilisateur confirme l'enregistrement, THE Outils_Page SHALL placer le fichier dans le répertoire `c:\judi-expert\<dossier>\travail` correspondant au dossier actif
3. IF le répertoire de travail n'existe pas, THEN THE Outils_Page SHALL créer le répertoire avant d'y enregistrer le fichier
4. IF un fichier du même nom existe déjà dans le répertoire de travail, THEN THE Outils_Page SHALL demander confirmation à l'utilisateur avant d'écraser le fichier existant
