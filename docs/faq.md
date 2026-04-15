# Questions Fréquentes (FAQ)

**Judi-Expert — ITechSource**
**Dernière mise à jour : 1er janvier 2026**

> Pour la définition des termes et acronymes, consultez le [Glossaire & Workflow](glossaire-workflow.md).

---

## Général

### Qu'est-ce que Judi-Expert ?

Judi-Expert est une solution d'assistance aux experts judiciaires multi-domaines. Elle se compose de deux parties :

- Une **Application Locale** installée sur votre PC, qui gère le workflow d'expertise en 4 étapes (extraction OCR, plan d'entretien, collecte de données, génération de rapport final) en s'appuyant sur un LLM local et une base de connaissances RAG spécifique à votre domaine ;
- Un **Site Central** (judi-expert.fr) qui gère votre inscription, la distribution des modules domaine, la vente de tickets d'expertise et la documentation.

Toutes vos données d'expertise restent exclusivement sur votre PC.

### Quels domaines d'expertise sont couverts ?

Judi-Expert couvre actuellement les domaines suivants :

- **Santé** : psychologie, psychiatrie, médecine légale
- **Bâtiment**
- **Comptabilité**

Le domaine psychologie est le premier domaine pleinement opérationnel avec un corpus documentaire complet. Les autres domaines seront progressivement complétés.

### Combien coûte Judi-Expert ?

L'Application Locale est gratuite à télécharger et à installer. Pour créer un dossier d'expertise, vous devez acheter un **Ticket** sur le Site Central via Stripe. Chaque Ticket est à usage unique et correspond à un dossier d'expertise. Le tarif des tickets est affiché sur le Site Central lors de l'achat.

### Judi-Expert remplace-t-il l'expert judiciaire ?

Non. Judi-Expert est un outil d'assistance à la rédaction. Les rapports générés constituent une aide et doivent être vérifiés, validés et signés par l'expert judiciaire qui en assume l'entière responsabilité professionnelle.

---

## Installation

### Quels sont les prérequis pour installer l'Application Locale ?

Votre PC doit satisfaire les conditions minimales suivantes :

- **CPU** : processeur multi-cœurs récent (recommandé : 8 cœurs ou plus)
- **RAM** : 16 Go minimum (recommandé : 32 Go pour le LLM)
- **Espace disque** : 50 Go minimum disponibles
- **Chiffrement du disque** : BitLocker (Windows) ou équivalent activé (obligatoire)
- **Système d'exploitation** : Windows 10/11, macOS ou Linux

Le programme d'installation vérifie automatiquement ces prérequis.

### Comment installer l'Application Locale ?

1. Inscrivez-vous sur [judi-expert.fr](https://judi-expert.fr) ;
2. Connectez-vous et accédez à la page **Téléchargements** (`/downloads`) ;
3. Téléchargez le package d'installation correspondant à votre système d'exploitation ;
4. Lancez l'installateur qui vérifiera les prérequis, installera Docker et déploiera les conteneurs ;
5. L'Application Locale sera accessible comme une application standard via l'Amorce.

### Que fait le premier lancement ?

Au premier lancement, l'Application Locale vous demande de :

1. Définir un **mot de passe local** pour protéger l'accès ;
2. Sélectionner votre **domaine d'expertise** ;
3. Télécharger et installer le **module RAG** correspondant à votre domaine ;
4. Optionnellement, fournir votre propre trame d'entretien (TPE) et template de rapport, ou utiliser les fichiers par défaut proposés.

---

## Utilisation

### Comment créer un nouveau dossier d'expertise ?

1. Depuis la page d'accueil de l'Application Locale, cliquez sur **Créer un dossier** ;
2. Saisissez un **nom de dossier** ;
3. Fournissez un **Ticket valide** acheté sur le Site Central ;
4. Le ticket est vérifié auprès du Site Central. Si valide, le dossier est créé avec les 4 étapes au statut « initial ».

### Quel est le workflow d'expertise ?

Le workflow suit 4 étapes séquentielles obligatoires :

1. **Step0 — Extraction** : uploadez le PDF-scan de la réquisition. Le système extrait le texte via OCR et le structure en Markdown. Vous pouvez visualiser et modifier le résultat ;
2. **Step1 — PEMEC** : cliquez sur « Execute » pour générer le plan d'entretien (QMEC). Téléchargez-le, puis validez pour passer à l'étape suivante ;
3. **Step2 — Upload** : uploadez vos notes d'entretien (NE) et votre rapport d'expertise brut (REB) au format .docx. Validez pour continuer ;
4. **Step3 — REF** : cliquez sur « Execute » pour générer le rapport final (REF) et le rapport auxiliaire (RAUX). Téléchargez les documents, puis validez pour archiver le dossier.

Chaque étape doit être validée avant de pouvoir accéder à la suivante. Une étape validée ne peut plus être modifiée.

### Qu'est-ce qu'un Ticket ?

Un Ticket est un fichier électronique à usage unique acheté sur le Site Central. Il est nécessaire pour créer un dossier d'expertise. Chaque Ticket est associé à votre domaine d'expertise et ne peut être utilisé qu'une seule fois.

### Comment fonctionne le ChatBot ?

Le ChatBot est accessible depuis l'interface principale de l'Application Locale. Il utilise le LLM local (Mistral 7B) avec la base de connaissances RAG de votre domaine pour répondre à vos questions sur le contenu du domaine et l'utilisation du système.

---

## Sécurité et données

### Où sont stockées mes données d'expertise ?

Toutes vos données d'expertise (réquisitions, notes d'entretien, rapports) sont stockées **exclusivement sur votre PC**, dans les conteneurs Docker de l'Application Locale. Aucune donnée d'expertise n'est transmise au Site Central ni à un serveur tiers.

### Mes données sont-elles chiffrées ?

- **Sur votre PC** : vos données sont protégées par le chiffrement du disque (BitLocker ou équivalent) que vous vous engagez à activer lors de votre inscription ;
- **Sur le Site Central** : les communications sont chiffrées via HTTPS/TLS, les mots de passe sont hachés avec bcrypt, et l'infrastructure AWS utilise des sous-réseaux privés et des groupes de sécurité.

### Judi-Expert est-il conforme au RGPD ?

Oui. Judi-Expert est conçu dans le respect du RGPD :

- Les données d'expertise restent sur le PC de l'expert (pas de transfert) ;
- Les données personnelles du Site Central sont hébergées dans la région AWS eu-west-3 (Paris), sans transfert hors de l'UE ;
- Les utilisateurs disposent de tous les droits prévus par le RGPD (accès, rectification, effacement, portabilité, opposition) ;
- La Politique de Confidentialité détaille l'ensemble des traitements.

### Que se passe-t-il si je supprime mon compte ?

La suppression de votre compte sur le Site Central entraîne la suppression de vos données personnelles (nom, prénom, email, adresse), sous réserve des obligations légales de conservation (données de transaction conservées 10 ans). Vos données d'expertise locales ne sont pas affectées.

---

## Site Central

### Comment m'inscrire ?

Rendez-vous sur [judi-expert.fr/inscription](https://judi-expert.fr/inscription) et remplissez le formulaire avec vos informations (Nom, Prénom, adresse, Domaine d'expertise). Vous devez accepter les Mentions légales, les CGU et vous engager à chiffrer le disque de votre PC.

### Comment me connecter ?

Rendez-vous sur [judi-expert.fr/connexion](https://judi-expert.fr/connexion), saisissez votre email et votre mot de passe, puis résolvez le Captcha. L'authentification est gérée par AWS Cognito.

### Comment acheter des Tickets ?

1. Connectez-vous au Site Central ;
2. Accédez à **Mon Espace** > **Tickets** ;
3. Cliquez sur **Acheter un Ticket** ;
4. Procédez au paiement via Stripe ;
5. Le Ticket est généré et envoyé à votre adresse email.

### Quels sont les horaires d'ouverture du Site Central ?

Le Site Central est disponible de **8h à 20h** (heure de Paris), du lundi au vendredi. En dehors de ces horaires, une page de maintenance vous informe de l'indisponibilité temporaire. L'Application Locale continue de fonctionner normalement pour les étapes d'expertise locales.

---

## Technique

### Comment mettre à jour le module RAG ?

1. Ouvrez l'Application Locale et accédez à la page **Configuration** ;
2. Consultez la liste des versions RAG disponibles pour votre domaine ;
3. Sélectionnez la nouvelle version souhaitée ;
4. Le module RAG est téléchargé depuis le Site Central et remplace la version précédente.

La mise à jour nécessite que le Site Central soit accessible (horaires d'ouverture).

### Quelle est la qualité de l'OCR ?

L'OCR utilise Tesseract, un moteur open-source reconnu, configuré pour le français. La qualité dépend de la résolution du scan :

- **Bonne qualité** (300 DPI ou plus) : extraction fiable ;
- **Qualité moyenne** (150-300 DPI) : extraction correcte avec possibles erreurs mineures ;
- **Faible qualité** (moins de 150 DPI) : résultats dégradés, vérification manuelle recommandée.

Le système indique un score de confiance après l'extraction. Vous pouvez toujours modifier manuellement le fichier Markdown généré.

### Quel LLM est utilisé ?

L'Application Locale utilise **Mistral 7B Instruct v0.3**, un modèle de langage open-source (licence Apache 2.0) optimisé pour le français. Il fonctionne entièrement en local via Ollama, sans appel à un service cloud. Le modèle nécessite environ 8 Go de RAM dédiée.

### Pourquoi Docker ?

Docker permet d'isoler les différents composants (site web, LLM, base RAG, OCR) dans des conteneurs indépendants, garantissant :

- La portabilité : fonctionne sur Windows, macOS et Linux ;
- L'isolation : chaque composant a son propre environnement ;
- La simplicité : installation et mise à jour automatisées via l'Amorce ;
- La sécurité : les données restent dans les volumes Docker locaux.
