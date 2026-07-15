# Prompt — Contrat « Partenaire référent Judi-Expert »

Rédige un **contrat type** intitulé **« Convention de partenariat référent Judi-Expert »**.

## Fichier de sortie

- Chemin cible : `docs/contrat-partenaire-referent.md`
- Format : **Markdown** (`.md`)

## Format de sortie

- **Table des matières** cliquable en tête de document, avec liens vers des **ancres HTML explicites** (`<a id="art-N-slug"></a>` placé juste avant chaque titre `##`), en **ASCII sans accents** (ex. `#art-7-pass-referent`, `#art-14-conflits-interets`). Ne pas s'appuyer sur les ancres auto-générées par le rendu Markdown (accents, em dash « — », apostrophes : incohérents entre outils).
- Style **juridique français formel**, sections numérotées avec sous-articles (ex. 4.1, 4.2).
- En-tête document : titre, mention « Judi-Expert — ITechSource », ligne « Modèle à compléter — Dernière mise à jour : `<<date_mise_a_jour>>` ».
- Utiliser des placeholders **`<<nom_placeholder>>`** (double chevron, snake_case en minuscules) pour toute information à compléter ultérieurement.
- **Dans le corps du contrat**, entourer chaque placeholder de **backticks** (ex. `` `<<domaine>>` ``) : sans cela, le rendu Markdown masque le nom et n'affiche que `<>` .
- **Ne pas utiliser** de marqueurs `[...]` dans le contrat généré : chaque zone à compléter doit porter un placeholder nommé explicite.
- Les placeholders volontairement laissés ouverts dans ce prompt doivent être reproduits tels quels ou développés de façon générique, **sans inventer** de données (SIRET, capital, représentant légal, montants catalogue, etc.).
- Terminer par un bloc **Signatures**, puis une section **Annexe — Placeholders à compléter** (tableau de glossaire, non signé).

## Nature de la relation

- Contrat de **partenariat utilisateur – éditeur**.
- **Pas** de lien de subordination, **pas** de contrat de travail, **pas** de mandat.
- Parties :
  - **ITechSource** (l'Éditeur) — `<<forme_juridique>>`, `<<adresse_siege>>`, `<<ville_rcs>>`, `<<RCS>>`, `<<capital_social>>`, `<<representant_legal>>`, `<<fonction_representant>>`
  - **Le Partenaire référent** — `<<civilite>>` `<<prenom>>` `<<nom>>`, expert judiciaire spécialisé en `<<domaine>>`, `<<adresse_partenaire>>`, `<<email_partenaire>>`

## Contexte produit (à intégrer au préambule)

**Le Partenaire référent :**
- est expert du domaine `<<domaine>>` auprès d'un tribunal ;
- souhaite utiliser des outils d'IA pour accélérer son travail, dans le respect des exigences réglementaires applicables à la solution (RGPD, AI Act) ;
- déclare disposer d'un poste de travail Windows **au moins équivalent à la configuration plancher** définie à l'article 5 ;
- assure, sous sa seule responsabilité, la sécurisation de son matériel et de sa protection réseau conformément à l'article 5.

**Configurations matérielles du poste de travail (article 5) :**
- système d'exploitation **Windows 10 ou Windows 11** ;
- **Configuration plancher (minimum acceptable)** : processeur équivalent **Intel Core i5 10e gen+** ou Ryzen 5, **16 Go RAM** (plancher absolu), SSD 50 Go libres min., GPU non requis — temps IA : **5 à 10 min/étape** ;
- **Configuration recommandée A (GPU)** : NVIDIA min. **4 Go VRAM** (recommandé 8 Go+), i5 11e gen+, **32 Go RAM**, SSD NVMe — temps IA : **10 à 30 s/étape**, gain typique **×10 à ×30** vs plancher ;
- **Configuration recommandée B (CPU)** : i7 12e gen+ (6 cœurs min.), **32 Go RAM**, SSD NVMe — temps IA : **2 à 5 min/étape** ;
- Les configs A et B sont **recommandées**, pas obligatoires ; seul le **plancher 16 Go** est le minimum contractuel pour le matériel.

**Obligations de sécurisation (responsabilité exclusive de l'expert) :**
- chiffrement intégral du disque : **BitLocker** (Windows Pro) ou **VeraCrypt** (ou équivalent) ;
- **antivirus** actif et à jour (**Windows Defender** ou équivalent) ;
- **pare-feu** activé (pare-feu Windows ou équivalent) ;
- **mises à jour de sécurité Windows** appliquées dans des délais raisonnables ;
- **mot de passe robuste** (distinct du mot de passe de déchiffrement si applicable) ;
- **sauvegardes** adaptées aux dossiers d'expertise ;
- **protection du réseau local** (Wi-Fi chiffré, box/router sécurisé) et **signalement** des incidents de sécurité à ITechSource.

**ITechSource :**
- développe la solution Judi-Expert, sécurisée et conforme à la réglementation française applicable (RGPD, AI Act et exigences applicables aux experts judiciaires) ;
- s'appuie sur un réseau de partenaires experts référents pour fournir un produit conforme aux attentes des experts judiciaires.

**Phases d'intervention du référent :**
- soit en phase **préliminaire / Beta** (avant ouverture officielle du service), puis pendant 6 mois à partir du lancement ;
- soit en phase **d'exploitation**.

Le rôle de référent d'un domaine **n'est pas exclusif** : ITechSource se réserve la possibilité de désigner **plusieurs référents** pour un même domaine.

---

## Structure du document à produire

La table des matières doit inclure, dans cet ordre :

1. Préambule
2. Objet
3. Définitions
4. Nature de la relation
5. Obligations du Partenaire référent
6. Poste de travail et sécurisation
7. Obligations d'ITechSource
8. Pass Référent — Contrepartie
9. Durée
10. Propriété intellectuelle
11. Témoignage publiable
12. Confidentialité
13. Données personnelles — RGPD et AI Act
14. Responsabilité
15. Conflits d'intérêts
16. Sanctions
17. Résiliation
18. Dispositions diverses
19. Droit applicable et juridiction compétente
20. Annexes
21. Signatures
22. Annexe — Placeholders à compléter

---

## Contenu des sections

### Préambule

- Bloc « Entre les soussignés » avec identité complète des deux Parties (placeholders).
- Appellations contractuelles : **l'Éditeur** / **ITechSource**, **le Partenaire référent**, **les Parties**.
- Bloc « Attendu que » reprenant le contexte produit ci-dessus.
- Clôture : « Il a été convenu ce qui suit : »

### 1. Objet

Cadre de collaboration entre ITechSource et le Partenaire référent pour contribuer à l'évolution de Judi-Expert dans le domaine `<<domaine>>`, notamment par des retours sur les workflows, fonctionnalités et usages métier, en contrepartie d'un **Pass Référent** (renvoi à l'article 7).

### 2. Définitions

Définir au minimum, avec renvois aux articles pertinents :

| Terme | Contenu |
|-------|---------|
| **Judi-Expert** | Solution d'assistance aux experts judiciaires (Site Central + Site Client) |
| **Site Central** | Application web https://judi-expert.fr (inscription, Tickets, téléchargement) |
| **Site Client** | Application locale Docker sur le Poste de travail |
| **Ticket** | Fichier électronique à usage unique pour créer un dossier d'expertise |
| **Pass Référent** | Avantage tarifaire (article 7) |
| **Poste de travail** | PC du Partenaire référent conforme à l'article 5 |
| **Phase Beta** | Période expérimentale avant Ouverture officielle |
| **Ouverture officielle** | Date de lancement commercial, fixée par ITechSource par écrit |
| **Retour d'expérience** | Compte rendu structuré de l'usage du produit |
| **Témoignage publiable** | Texte soumis à validation (article 10) |
| **CGU / CGV** | Conditions applicables, https://judi-expert.fr/cgu |

### 3. Nature de la relation

- Partenariat **utilisateur – éditeur** ; pas de subordination, travail ou mandat.
- Partenaire référent = expert judiciaire **indépendant**, seul responsable de son activité professionnelle.
- Les échanges = collaboration produit ; **pas** de conseil réglementaire ni de validation des choix d'ITechSource par le référent.

### 4. Obligations du Partenaire référent

Le Partenaire référent s'engage à :

- **4.1** Donner un avis professionnel sur les workflows et fonctionnalités du domaine `<<domaine>>` ;
- **4.2** Transmettre ses observations par **email** et participer à **2 à 4 réunions visio d'1 heure sur 1 mois**, sur proposition d'ITechSource ;
- **4.3** Suggérer des adaptations ou fonctionnalités utiles ;
- **4.4** Fournir un **retour d'expérience** dès qu'il commence à utiliser la solution ;
- **4.5** Proposer un **témoignage publiable** conforme à l'article 10 ;
- **4.6** Utiliser Judi-Expert conformément aux **CGU/CGV** ;
- **4.7** Maintenir un **Poste de travail adapté** : au minimum la **configuration plancher** et les **obligations de sécurisation** de l'article 5.

### 5. Poste de travail et sécurisation

Article structuré en sous-sections :

- **5.1 Déclaration et configurations matérielles** — trois niveaux : **plancher** (i5 + 16 Go RAM, acceptable avec perf dégradées), **recommandée A (GPU)**, **recommandée B (CPU 32 Go)** ; les configs A/B sont conseillées, seul le plancher est le minimum contractuel matériel.
- **5.2 Responsabilité exclusive** — choix matériel et conséquences sur les temps de traitement ; sécurisation ; ITechSource ne vérifie pas sur site.
- **5.3 Obligations de sécurisation du matériel** — BitLocker/VeraCrypt, antivirus, pare-feu, mises à jour Windows, mot de passe, sauvegardes (liste a–f).
- **5.4 Protection réseau** — Wi-Fi/box sécurisés, interdiction d'usage sur poste/réseau compromis, signalement d'incidents.
- **5.5 Maintien en condition** — obligation de maintenir la sécurité ; modifications matérielles/logicielles sans compromettre les données d'expertise.
- **5.6 Conséquences d'un manquement** — manquement = sécurisation (5.3–5.5) ou poste **sous le plancher** ; usage sous les configs recommandées (sans GPU, RAM inférieure à 32 Go) **n'est pas** un manquement seul.
- **5.7 Note sur les configurations matérielles** — (1) configs recommandées ; i5 + 16 Go acceptable (plancher), perf dégradées ; (2) GPU recommandé, gain **×10 à ×30** sur temps IA vs plancher CPU (10–30 s vs 5–10 min/étape, aligné FAQ produit).

### 6. Obligations d'ITechSource

- **6.1** Mettre Judi-Expert à disposition selon le Pass Référent (article 7) ;
- **6.2** Organiser les échanges (emails, visios) ;
- **6.3** Informer le Partenaire référent des éléments utiles à sa mission ;
- **Ne pas** inclure de paragraphe 6.4 optionnel.

### 7. Pass Référent — Contrepartie

- **Période 1 — 6 mois** : accès **illimité et gratuit** à la **création de tickets de procédures** (Tickets d'expertise Judi-Expert) ;
- **Période 2 — 12 mois** : Tickets à **50 % du prix catalogue** (`<<prix_catalogue_ticket>>` € HT par Ticket, sous réserve de modification CGU/CGV) ;
- Pass Référent **personnel** et **non transférable** ;
- Usage hors Pass ou après expiration = **CGU/CGV** en vigueur ;
- Pass Référent = **seule contrepartie** (pas de rémunération en numéraire).

### 8. Durée

À compter de `<<date_signature>>` :

- **Service déjà lancé** : **18 mois** (6 mois gratuits + 12 mois à tarif réduit) ;
- **Produit en version Beta** : **18 mois** à compter de `<<date_ouverture_officielle>>` (même répartition).

Préciser le début effectif de la Période 1 et la fin de plein droit à expiration, avec renvoi à l'article 16 pour les clauses survivantes.

### 9. Propriété intellectuelle

- **100 % ITechSource** : logiciel, documentation, marques, workflows, corpus, etc.
- Cession **gratuite et exclusive** des suggestions, retours et propositions du Partenaire référent, sans limitation de durée, territoire ou support.
- Seule contrepartie = Pass Référent.
- Aucune licence inverse au-delà des CGU/CGV et du Pass Référent.

### 10. Témoignage publiable

- Format indicatif : « **`<<prenom>>` X.**, expert en `<<domaine>>` — `<<corps_temoignage_publiable>>` » ;
- **Pas de droit à l'image** ;
- **Validation écrite préalable** d'ITechSource obligatoire ;
- **Droit de retrait** dans un délai de **15 jours ouvrés** ;
- **Anonymisation obligatoire** : prénom + « X. » (valeur fixe, jamais l'initiale du nom) — interdire tribunal, ville, numéro de dossier ou toute identification directe ;
- Proposition = obligation ; publication = subordonnée à validation et accord sur le texte final.

### 11. Confidentialité

**Partenaire référent :**
- Ne pas divulguer les informations non publiques sur Judi-Expert (roadmap, fonctionnalités non commercialisées, tarifs, documents internes, CR de réunions, etc.) ;
- **Sanctions** : renvoi à l'**article 15.2**.

**ITechSource :**
- Garder **confidentielle la liste des experts référents** (identité, domaine, statut), sauf accord écrit du référent ou obligation légale.

**Durée :**
- Confidentialité du Partenaire référent : **24 mois** après fin de convention ;
- Confidentialité d'ITechSource sur la liste : sans limitation (sous réserve des exceptions).

### 12. Données personnelles — RGPD et AI Act

- RGPD et AI Act = cadre **général de la solution** (CGU https://judi-expert.fr/cgu, politique https://judi-expert.fr/politique-confidentialite) ;
- **Pas** d'obligations spécifiques supplémentaires créées par la présente convention, sauf traitement des données du Partenaire référent pour la gestion du partenariat (Politique de confidentialité Judi-Expert).

### 13. Responsabilité

- Partenaire référent **ne porte aucune responsabilité** sur les **choix fonctionnels et réglementaires** d'ITechSource ;
- Avis et retours = **consultatifs** ; pas de validation réglementaire du produit ;
- Responsabilité d'ITechSource limitée **dans les limites prévues par les CGU/CGV en vigueur** ;
- Chaque Partie responsable de ses propres manquements ;
- **13.5** Partenaire référent **seul responsable** de la sécurisation de son Poste de travail, réseau et données d'expertise locales (article 5 + CGU).

### 14. Conflits d'intérêts

- Interdiction d'exercer un **rôle similaire** (référent produit, beta-testeur rémunéré en nature, conseil éditorial sur outil concurrent) auprès d'un **concurrent direct** d'ITechSource pendant **24 mois** après fin de convention ;
- « Concurrent direct » = solution logicielle d'assistance aux experts judiciaires par IA, substituable à Judi-Expert sur `<<domaine>>` (sans que cette définition soit limitative) ;
- **Sanctions** : renvoi à l'**article 15.3**.
- N'empêche pas l'exercice normal de l'expertise judiciaire ni l'usage d'outils généralistes non concurrents.

### 15. Sanctions (version modérée — article centralisé)

Regrouper **toutes** les sanctions dans cet article. Les articles 11, 14, 5 et 16 y renvoient.

**15.1 Dispositions communes :**
- Mise en demeure préalable (**15 jours**), sauf urgence manifeste ;
- Forme : email AR à `<<email_partenaire>>` ou lettre recommandée AR ;
- Mesures : résiliation (art. 16), suspension Pass Référent, remboursement avantage indu, dommages-intérêts (préjudice réel), mesures injonctives ;
- Clauses pénales (art. 1231-5 C. civ.) : cumul possible avec préjudice réel supérieur ;
- **Plafond global : 15 000 €** (toutes causes confondues).

**15.2 Violation confidentialité (renvoi art. 11) :**
- Indemnité forfaitaire **5 000 €** / manquement avéré ;
- Remboursement Pass Référent indu ;
- Action en cessation / retrait.

**15.3 Violation conflits d'intérêts (renvoi art. 14) :**
- Indemnité forfaitaire **10 000 €** / manquement avéré ;
- Dommages-intérêts complémentaires si préjudice réel supérieur.

**15.4 Autres manquements (art. 4, 5, 7, 10) :**
- Résiliation + préjudice réel uniquement, **sans forfait** (sauf faute lourde ou dolosive).

### 16. Résiliation

**16.1 Par ITechSource ou de plein droit :**
- **a) Arrêt du produit** — reconduction automatique en cas de cession (**30 jours** de notification) ;
- **b) Non-utilisation** — 1 mois consécutif sans usage ;
- **c) Manquement** — non régularisé conformément à l'**article 15.1**, ou urgence manifeste ;
- **d) Expiration** — fin de plein droit à l'article 8.

**16.2 Par le Partenaire référent :**
- Résiliation à tout moment, sans motif ;
- Libération sauf confidentialité (24 mois) et conflits d'intérêts (24 mois) ;
- Usage Judi-Expert continue sous CGU/CGV.

**16.3 Effets communs :**
- Articles PI, confidentialité, conflits d'intérêts, **sanctions**, responsabilité et droit applicable survivent.

### 17. Dispositions diverses

Inclure : force majeure (**60 jours** max avant résiliation), nullité partielle, modifications par avenant signé (y compris électroniquement), intégralité de l'accord, langue française (version française seule fait foi).

**17.6 Signature électronique (Universign) :**
- Plateforme **Universign** ;
- Valeur juridique = signature manuscrite (C. civ. 1366-1367, eIDAS) ;
- Satisfait toute exigence d'« écrit » ou de « signature » (y compris avenants art. 17.3) ;
- Date = certificat / dossier de preuve Universign ;
- Exemplaire électronique + dossier de preuve pour chaque Partie.

### 18. Droit applicable et juridiction compétente

- Droit **français** ;
- Tentative de règlement amiable (**30 jours**) ;
- Compétence exclusive du **Tribunal de commerce de Lyon**, nonobstant pluralité de défendeurs ou appel en garantie.

### 19. Annexes

- **Annexe 1** — CGU / CGV Judi-Expert : https://judi-expert.fr/cgu
- **Annexe 2** — Politique de confidentialité : https://judi-expert.fr/politique-confidentialite
- **Annexe 3** — Guide de configuration du poste expert : https://judi-expert.fr/securite
- **Ne pas** inclure d'Annexe 4 optionnelle.

### Signatures

- Signature **électronique via Universign** (art. 17.6) — pas d'exemplaires papier.
- Date : `<<date_signature>>` (certificat / dossier de preuve Universign).
- Tableau deux colonnes : ITechSource (`<<representant_legal>>`, `<<fonction_representant>>`) / Partenaire référent (`<<prenom>>` `<<nom>>`, expert en `<<domaine>>`).
- Mentionner que la version signée via Universign + dossier de preuve constitue l'original.

### Annexe — Placeholders à compléter

Section finale (après Signatures) : tableau Markdown à deux colonnes (**Placeholder** | **Signification**) listant **tous** les `<<nom_placeholder>>` du document, avec exemple de valeur. Inclure une note : guide de complétion du modèle, **non signé**, à retirer avant signature.

| Placeholder | Signification |
|-------------|---------------|
| `<<date_mise_a_jour>>` | Date de dernière révision du modèle. |
| `<<forme_juridique>>` | Forme juridique d'ITechSource (SAS, SARL…). |
| `<<capital_social>>` | Capital social d'ITechSource. |
| `<<ville_rcs>>` | Ville d'immatriculation RCS. |
| `<<RCS>>` | Numéro RCS d'ITechSource. |
| `<<adresse_siege>>` | Adresse du siège social d'ITechSource. |
| `<<representant_legal>>` | Nom du signataire ITechSource. |
| `<<fonction_representant>>` | Fonction du signataire ITechSource. |
| `<<civilite>>` | Civilité du Partenaire référent. |
| `<<prenom>>` | Prénom du Partenaire référent (témoignage anonymisé). |
| `<<nom>>` | Nom du Partenaire référent (absent du témoignage publié). |
| `<<domaine>>` | Domaine d'expertise Judi-Expert couvert. |
| `<<adresse_partenaire>>` | Adresse professionnelle du Partenaire référent. |
| `<<email_partenaire>>` | Email professionnel du Partenaire référent. |
| `<<prix_catalogue_ticket>>` | Prix catalogue HT d'un Ticket. |
| `<<date_signature>>` | Date de signature (certificat Universign). |
| `<<date_ouverture_officielle>>` | Date de lancement commercial (Beta uniquement). |
| `<<corps_temoignage_publiable>>` | Trame du texte de témoignage. |

**Valeurs déjà fixées dans le modèle (ne pas remettre en placeholder) :** sanctions modérées (art. 15), délais (15 jours mise en demeure, 15 jours ouvrés retrait témoignage, 30 jours médiation/cession, 60 jours force majeure), URLs Judi-Expert, contact@judi-expert.fr, anonymisation « X. ».

---

## Exigences rédactionnelles

- Orthographe et typographie soignées : **ITechSource**, **Judi-Expert**, experts judiciaires, fonctionnalités, visioconférence, etc.
- Ton neutre, précis, juridique, sans marketing.
- Chaque section = titre Markdown `##` compatible avec la table des matières.
- Sous-articles numérotés (X.1, X.2…) pour les sections détaillées.
- **Ne pas inventer** les mentions légales d'ITechSource : utiliser des placeholders nommés du type `` `<<domaine>>` ``, `` `<<forme_juridique>>` ``, etc.
- Les renvois entre articles doivent être **cohérents** avec la numérotation ci-dessus.
- Conserver les placeholders `` `<<nom_placeholder>>` `` (avec backticks) là où une information reste à compléter.

## Garde-fous

- Ne pas générer de SIRET, capital, RCS, adresse ou montants fictifs.
- Ne pas supprimer les clauses de non-exclusivité, de cession PI, ni la clause de reconduction en cas de cession d'activité.
- Ne pas disperser les sanctions dans les articles thématiques : **toutes** les sanctions (forfaits, mise en demeure, plafond) doivent figurer à l'**article 15**, avec renvois depuis les articles 5, 11 et 14.
- Ne pas transformer le Pass Référent en rémunération en numéraire.
- Ne pas attribuer au Partenaire référent une responsabilité sur les choix fonctionnels ou réglementaires d'ITechSource.
- Prévoir la **signature électronique via Universign** (art. 17.6) : pas de mention « exemplaires originaux » papier.
