# Requirements Document — Workflow TRE-Centré

## Introduction

Refonte du workflow d'expertise pour le centrer sur le TRE (Template de Rapport d'Expertise). Le TRE est un document `.docx` au format Word du rapport final, enrichi de méta-instructions (placeholders et annotations) qui pilotent l'ensemble du workflow. Le workflow produit le rapport final d'expertise (REF) à partir de ce document central en 5 étapes séquentielles.

## Glossaire

- **TRE** : Template de Rapport d'Expertise — document `.docx` central contenant des placeholders `<<...>>` et des annotations `@...@` servant de modèle au rapport final.
- **Placeholder** : Méta-instruction de substitution au format `<<nom_placeholder>>` dans le TRE, remplacée par une valeur extraite ou saisie.
- **Annotation** : Méta-instruction au format `@type contenu@` dans le TRE, destinée à être complétée par l'expert pendant l'entretien.
- **Annotation_Prédéfinie** : Annotation utilisant un type reconnu par le système (`@dires`, `@analyse`, `@verbatim`, `@question`, `@reference`, `@cite`, `@debut_tpe`).
- **Annotation_Personnalisée** : Annotation définie par l'expert au format `@/mon_annotation contenu@`, retranscrite en "Mon Annotation : contenu".
- **PE** : Plan d'Entretien — partie du TRE extraite à partir de `@debut_tpe@` jusqu'à la fin du document, contenant les annotations à compléter en entretien.
- **PEA** : Plan d'Entretien Annoté — PE complété par l'expert avec ses notes en texte abrégé dans les annotations.
- **PRE** : Pré-Rapport d'Expertise — rapport généré à partir du PEA avec mise en forme des annotations et substitution des placeholders.
- **DAC** : Document d'Analyse Contradictoire — document d'analyse généré à partir du PRE.
- **REF** : Rapport d'Expertise Final — PRE ajusté et révisé, version finale du rapport.
- **Placeholders_CSV** : Fichier `placeholders.csv` contenant les paires clé/valeur des placeholders extraits de la demande.
- **Demande** : Document de réquisition ou d'ordonnance du tribunal (fichier PDF en entrée).
- **Workflow_Engine** : Moteur de workflow séquentiel gérant les transitions d'étapes et les validations.
- **Service_Révision** : Service de correction linguistique appliqué au PRE pour produire le REF.
- **Texte_Abrégé** : Style télégraphique utilisé par l'expert pour annoter rapidement pendant l'entretien.
- **Verbatim** : Texte à restituer sans modification, encadré par des guillemets dans le rapport final.
- **MEC** : Mis(e) En Cause — personne évaluée en expertise psychologique (la personne faisant l'objet de l'expertise).

## Requirements

### Requirement 1 : Extraction OCR et identification des placeholders (Step 1)

**User Story:** En tant qu'expert judiciaire, je veux importer un fichier PDF de réquisition et obtenir automatiquement un fichier structuré et un fichier de placeholders, afin de disposer des données de base pour le workflow.

#### Acceptance Criteria

1. WHEN un fichier PDF de réquisition est importé, THE Workflow_Engine SHALL extraire le texte par OCR et produire un fichier `demande.md` structuré en Markdown.
2. WHEN le texte de la réquisition est extrait, THE Workflow_Engine SHALL identifier les placeholders principaux et les stocker dans un fichier `placeholders.csv` au format clé/valeur.
3. WHEN des questions sont identifiées dans la réquisition, THE Workflow_Engine SHALL les extraire et les enregistrer comme placeholders `question_1` à `question_n` dans le fichier `placeholders.csv`.
4. WHEN le fichier `placeholders.csv` est généré, THE Workflow_Engine SHALL présenter les valeurs extraites à l'expert pour vérification avant validation.
5. IF l'extraction OCR échoue ou produit un résultat illisible, THEN THE Workflow_Engine SHALL signaler l'erreur à l'expert avec un message descriptif et permettre un nouvel essai.

---

### Requirement 2 : Extraction du PE depuis le TRE (Step 2)

**User Story:** En tant qu'expert judiciaire, je veux que le système extraie automatiquement le Plan d'Entretien depuis mon TRE et y intègre les questions de la réquisition, afin de disposer d'un document prêt pour l'entretien.

#### Acceptance Criteria

1. WHEN le TRE et le fichier `placeholders.csv` sont fournis en entrée, THE Workflow_Engine SHALL extraire la portion du TRE comprise entre l'annotation `@debut_tpe@` et la fin du document pour constituer le PE.
2. WHEN le PE est extrait, THE Workflow_Engine SHALL compléter la section conclusion du PE avec des sous-sections correspondant à chaque question extraite (`question_1` à `question_n` présentes dans `placeholders.csv`).
3. WHEN le PE est généré, THE Workflow_Engine SHALL conserver toutes les annotations présentes dans la portion extraite du TRE.
4. WHEN le PE est généré, THE Workflow_Engine SHALL substituer les annotations `@question n@` par le texte de la question correspondante issue de `placeholders.csv`.
5. THE Workflow_Engine SHALL vérifier que le PE contient les annotations attendues et les questions en section conclusion avant de le présenter à l'expert.
6. IF l'annotation `@debut_tpe@` est absente du TRE, THEN THE Workflow_Engine SHALL signaler l'erreur à l'expert et indiquer que le TRE est invalide.

---

### Requirement 3 : Parsing des annotations du TRE

**User Story:** En tant qu'expert judiciaire, je veux que le système reconnaisse et interprète correctement toutes les méta-instructions de mon TRE, afin que le workflow produise un rapport fidèle à mes annotations.

#### Acceptance Criteria

1. THE Workflow_Engine SHALL reconnaître les placeholders au format `<<nom_placeholder>>` dans le TRE et les substituer par les valeurs correspondantes du fichier `placeholders.csv`.
2. THE Workflow_Engine SHALL reconnaître les annotations prédéfinies au format `@type contenu@` où type est l'un de : `dires`, `analyse`, `verbatim`, `question`, `reference`, `cite`, `debut_tpe`.
3. THE Workflow_Engine SHALL reconnaître les annotations personnalisées au format `@/mon_annotation contenu@` et les retranscrire en "Mon Annotation : contenu" dans le rapport.
4. WHEN une annotation `@dires contenu@` est rencontrée, THE Workflow_Engine SHALL la retranscrire en "Dires : contenu" dans le rapport.
5. WHEN une annotation `@verbatim contenu@` est rencontrée, THE Workflow_Engine SHALL restituer le contenu sans modification, encadré par des guillemets dans le rapport.
6. WHEN une annotation `@question n@` est rencontrée, THE Workflow_Engine SHALL substituer le placeholder `question_n` par le texte de la question correspondante.
7. FOR ALL annotations valides dans le TRE, le parsing puis la restitution en texte puis le re-parsing SHALL produire un résultat équivalent à l'annotation originale (propriété round-trip).
8. IF une annotation a un format invalide (balise ouvrante sans balise fermante), THEN THE Workflow_Engine SHALL signaler l'erreur avec la position dans le document.

---

### Requirement 4 : Génération du PRE depuis le PEA (Step 4)

**User Story:** En tant qu'expert judiciaire, je veux que le système transforme mon PEA annoté en un pré-rapport d'expertise structuré, afin de disposer d'un document professionnel prêt à être finalisé.

#### Acceptance Criteria

1. WHEN le PEA est fourni en entrée, THE Workflow_Engine SHALL reconstituer le rapport complet en ajoutant la partie du TRE précédant `@debut_tpe@` au début du document.
2. WHEN le PEA contient des annotations `@dires contenu@`, THE Workflow_Engine SHALL mettre en forme le contenu en texte rédigé à partir du texte abrégé de l'expert.
3. WHEN le PEA contient des annotations `@analyse contenu@`, THE Workflow_Engine SHALL mettre en forme le contenu en texte rédigé à partir du texte abrégé de l'expert.
4. WHEN le PEA contient des annotations `@verbatim contenu@`, THE Workflow_Engine SHALL restituer le contenu entre guillemets sans aucune modification.
5. WHEN le PEA contient des annotations `@reference @dires_xxx@` ou `@reference @analyse_xxx@`, THE Workflow_Engine SHALL substituer l'annotation par le numéro de section et le chemin titre correspondant (ex: "cf section 2.1.3 - biographie/education/primaire").
6. WHEN le PEA contient des annotations `@cite @dires_xxx@`, THE Workflow_Engine SHALL substituer l'annotation par "citation section X.Y.Z - chemin/titre ... texte de la citation".
7. WHEN le PRE est généré, THE Workflow_Engine SHALL construire le DAC (Document d'Analyse Contradictoire) sur la base de l'analyse du PRE.
8. THE Workflow_Engine SHALL substituer tous les placeholders `<<...>>` restants dans le PRE par les valeurs du fichier `placeholders.csv`.
9. IF un placeholder référencé dans le TRE n'a pas de valeur dans `placeholders.csv`, THEN THE Workflow_Engine SHALL conserver le placeholder non substitué et signaler les placeholders manquants à l'expert.

---

### Requirement 5 : Finalisation et archivage (Step 5)

**User Story:** En tant qu'expert judiciaire, je veux que le système finalise mon rapport avec une révision linguistique et archive l'ensemble du dossier de manière sécurisée, afin de disposer d'un rapport sans faute et d'une archive immuable.

#### Acceptance Criteria

1. WHEN le PRE ajusté est soumis au Service_Révision, THE Workflow_Engine SHALL produire une version corrigée avec les corrections de langue en mode correction pour validation par l'expert.
2. WHILE le Service_Révision corrige le texte, THE Workflow_Engine SHALL préserver intacts les textes entre guillemets (les verbatim).
3. WHEN le REF est validé par l'expert, THE Workflow_Engine SHALL générer un fichier `<nom-dossier>.zip` contenant tous les fichiers du répertoire `c:\judi-expert\<nom-dossier>` en excluant le sous-répertoire `archive\`.
4. WHEN le REF est validé par l'expert, THE Workflow_Engine SHALL générer un fichier `<nom-dossier>-timbre.txt` contenant les données en clair : contexte expertise (demandeur, demandeur_nom, demandeur_prenom, demandeur_adresse, demande_date, tribunal_nom, tribunal_adresse, demande_reference, demande_date, mec_nom, mec_prenom, mec_adresse, expert_nom, expert_prenom, expert_adresse), le nom du fichier zip, et le log d'archive.
5. WHEN les fichiers d'archive sont générés, THE Workflow_Engine SHALL placer le fichier `.zip` et le fichier `-timbre.txt` dans le répertoire `c:\judi-expert\<nom-dossier>\archive`.
6. IF la génération de l'archive échoue (erreur d'écriture disque, fichier verrouillé), THEN THE Workflow_Engine SHALL signaler l'erreur à l'expert et permettre un nouvel essai sans perte de données.

---

### Requirement 6 : Gestion des annotations @reference et @cite dans la conclusion

**User Story:** En tant qu'expert judiciaire, je veux pouvoir référencer et citer des sections de mon entretien dans la conclusion, afin de produire des réponses aux questions du tribunal étayées par les éléments recueillis.

#### Acceptance Criteria

1. WHEN l'expert utilise `@reference @dires_x.y.z@` dans la conclusion du PEA, THE Workflow_Engine SHALL substituer l'annotation par "cf section X.Y.Z - chemin/titre" correspondant à la section référencée.
2. WHEN l'expert utilise `@reference @analyse_x.y.z@` dans la conclusion du PEA, THE Workflow_Engine SHALL substituer l'annotation par "cf section X.Y.Z - chemin/titre" correspondant à la section référencée.
3. WHEN l'expert utilise `@cite @dires_x.y.z@` dans la conclusion du PEA, THE Workflow_Engine SHALL substituer l'annotation par le contenu textuel de la section citée, précédé de "citation section X.Y.Z - chemin/titre".
4. IF une annotation `@reference` ou `@cite` fait référence à une section inexistante, THEN THE Workflow_Engine SHALL signaler l'erreur à l'expert avec l'identifiant de section non trouvé.

---

### Requirement 7 : Validation structurelle du TRE

**User Story:** En tant qu'expert judiciaire, je veux que le système valide la structure de mon TRE avant de l'utiliser dans le workflow, afin d'éviter des erreurs en cours de traitement.

#### Acceptance Criteria

1. WHEN un TRE est chargé dans le système, THE Workflow_Engine SHALL vérifier la présence de l'annotation `@debut_tpe@` dans le document.
2. WHEN un TRE est chargé dans le système, THE Workflow_Engine SHALL vérifier que toutes les annotations ont une balise ouvrante et une balise fermante correctement appariées.
3. WHEN un TRE est chargé dans le système, THE Workflow_Engine SHALL vérifier que les placeholders utilisent le format `<<nom_placeholder>>` avec un nom en snake_case.
4. WHEN un TRE est validé, THE Workflow_Engine SHALL extraire la liste de tous les placeholders et annotations présents et la présenter à l'expert pour confirmation.
5. IF le TRE contient des erreurs structurelles, THEN THE Workflow_Engine SHALL lister toutes les erreurs détectées avec leur position dans le document et refuser le traitement.

---

### Requirement 8 : Pretty-printer des annotations

**User Story:** En tant qu'expert judiciaire, je veux que le système puisse restituer les annotations dans un format lisible et cohérent, afin de garantir la fidélité du rendu dans le rapport.

#### Acceptance Criteria

1. THE Workflow_Engine SHALL formater les annotations `@dires contenu@` en "Dires : contenu" dans le rapport final.
2. THE Workflow_Engine SHALL formater les annotations `@analyse contenu@` en "Analyse : contenu" dans le rapport final.
3. THE Workflow_Engine SHALL formater les annotations `@verbatim contenu@` en restituant le contenu entre guillemets sans modification.
4. THE Workflow_Engine SHALL formater les annotations personnalisées `@/mon_annotation contenu@` en "Mon Annotation : contenu" (avec capitalisation du nom d'annotation et remplacement des underscores par des espaces).
5. FOR ALL annotations valides, le parsing d'une annotation suivi de son formatage puis d'un re-parsing SHALL produire une annotation sémantiquement équivalente à l'originale (propriété round-trip).

---

### Requirement 9 : Intégration du workflow TRE-centré dans le moteur existant

**User Story:** En tant que développeur, je veux que le moteur de workflow existant supporte le nouveau flux TRE-centré, afin de maintenir la cohérence du système tout en intégrant les nouvelles fonctionnalités.

#### Acceptance Criteria

1. THE Workflow_Engine SHALL conserver le mécanisme séquentiel à 5 étapes avec transitions de statut (initial → en_cours → fait → validé).
2. THE Workflow_Engine SHALL adapter le Step 1 pour produire `demande.md` et `placeholders.csv` avec les questions extraites.
3. THE Workflow_Engine SHALL adapter le Step 2 pour extraire le PE depuis le TRE à partir de `@debut_tpe@` et intégrer les questions en conclusion.
4. THE Workflow_Engine SHALL conserver le Step 3 inchangé (consolidation documentaire, non utilisé pour le domaine psychologie).
5. THE Workflow_Engine SHALL adapter le Step 4 pour traiter le PEA, reconstituer le rapport complet, mettre en forme les annotations, et générer le PRE et le DAC.
6. THE Workflow_Engine SHALL adapter le Step 5 pour intégrer le Service_Révision et l'archivage avec génération du zip et du timbre.
7. WHILE le workflow est en cours d'exécution, THE Workflow_Engine SHALL maintenir le verrouillage des étapes validées (une étape validée ne peut plus être modifiée).
