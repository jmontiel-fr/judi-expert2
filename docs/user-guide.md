# Guide Utilisateur — Application Locale Judi-Expert

## Introduction

Ce guide décrit l'utilisation complète de l'Application Locale Judi-Expert, destinée aux experts judiciaires. L'application vous accompagne dans la production de vos rapports d'expertise en 4 étapes, en s'appuyant sur l'intelligence artificielle et une base de connaissances spécialisée dans votre domaine.

Toutes vos données d'expertise restent exclusivement sur votre PC. Seuls les tickets d'expertise transitent entre votre application et le Site Central.

---

## 1. Installation et premier lancement (Amorce)

### Prérequis PC

Avant l'installation, vérifiez que votre PC satisfait les conditions suivantes :

- **Processeur** : CPU multi-cœurs récent (Intel i5/i7 ou AMD Ryzen 5/7)
- **Mémoire RAM** : 16 Go minimum (32 Go recommandé)
- **Espace disque** : 50 Go minimum disponibles
- **Chiffrement du disque** : BitLocker (Windows) ou FileVault (macOS) activé
- **Système d'exploitation** : Windows 10/11, macOS 12+ ou Linux (Ubuntu 22.04+)

### Installation

1. Téléchargez le package d'installation depuis la page **Téléchargements** du Site Central (https://judi-expert.fr/downloads)
2. Lancez l'installateur :
   - **Windows** : double-cliquez sur le fichier `.exe`
   - **macOS/Linux** : exécutez le script d'installation
3. L'installateur vérifie automatiquement les prérequis de votre PC
4. Si toutes les conditions sont remplies, l'installation se déroule automatiquement (Docker, images Docker, configuration)

### Premier lancement

1. Lancez l'application via l'**Amorce** (icône "Judi-Expert" sur votre bureau ou dans vos applications)
2. L'Amorce démarre Docker puis lance les 4 conteneurs de l'application
3. Votre navigateur s'ouvre automatiquement sur http://localhost:3000

---

## 2. Configuration initiale

Au premier lancement, l'application vous guide à travers la configuration initiale.

### Définition du mot de passe

1. Accédez à la page de configuration initiale (`/setup`)
2. Définissez un **mot de passe local** pour protéger l'accès à votre application
3. Ce mot de passe est stocké localement (haché avec bcrypt) et n'est jamais transmis

### Sélection du domaine d'expertise

1. Choisissez votre **domaine d'expertise** dans le menu déroulant :
   - Psychologie
   - Psychiatrie
   - Médecine légale
   - Bâtiment
   - Comptabilité
2. Le domaine détermine le corpus de connaissances utilisé par l'IA

### Installation du module RAG

Le module RAG contient la base de connaissances spécialisée pour votre domaine. Son installation est **obligatoire** avant de pouvoir créer des dossiers.

1. Accédez au menu **Configuration**
2. Consultez la liste des **versions RAG disponibles** avec leur contenu détaillé
3. Sélectionnez la version souhaitée et cliquez sur **Installer**
4. L'application télécharge et installe le module depuis le Site Central

### Configuration du TPE (Trame d'entretien)

1. Dans le menu **Configuration**, section **TPE**
2. Cliquez sur **Charger un TPE** pour téléverser votre trame d'entretien personnelle
3. Pour le domaine psychologie, un TPE par défaut est proposé (`TPE_psychologie.tpl`)
4. Le TPE est indexé dans la base RAG pour être utilisé lors de la génération du plan d'entretien

### Configuration du Template Rapport

1. Dans le menu **Configuration**, section **Template Rapport**
2. Cliquez sur **Charger un template** pour téléverser votre modèle de rapport au format `.docx`
3. Pour le domaine psychologie, un template par défaut est proposé (`template_rapport_psychologie.docx`)
4. Le template contient des champs de fusion (placeholders) qui seront remplis automatiquement lors de la génération du rapport final

---

## 3. Création d'un dossier

### Prérequis

- Un **ticket d'expertise** valide, acheté sur le Site Central
- Le module RAG installé et configuré

### Procédure

1. Depuis la page d'accueil (liste des dossiers), cliquez sur **Nouveau dossier**
2. Saisissez le **nom du dossier** (ex: "Expertise Dupont - TGI Paris")
3. Saisissez le **code du ticket** reçu par email après achat
4. Cliquez sur **Créer**

L'application vérifie le ticket auprès du Site Central :
- Si le ticket est **valide** : le dossier est créé avec 4 étapes au statut "initial"
- Si le ticket est **invalide** : un message d'erreur indique la raison (ticket invalide ou déjà utilisé)
- Si le Site Central est **indisponible** (hors heures ouvrables 8h-20h) : un message vous invite à réessayer pendant les heures ouvrables

Le dossier créé apparaît en tête de la liste des dossiers (tri chronologique inverse).

---

## 4. Workflow d'expertise

Le workflow d'expertise se déroule en 4 étapes séquentielles. Chaque étape doit être validée avant de passer à la suivante. Une étape validée est verrouillée et ne peut plus être modifiée.

### Step0 — Extraction de la réquisition

**Objectif** : convertir le PDF-scan de la réquisition du tribunal en fichier Markdown exploitable.

1. Accédez au dossier, puis cliquez sur **Step0 — Extraction**
2. Cliquez sur **Choisir un fichier** et sélectionnez le PDF-scan de la réquisition
3. Cliquez sur le bouton **Extraction**
4. L'application :
   - Envoie le PDF au moteur OCR pour extraire le texte brut
   - Utilise l'IA pour structurer le texte en Markdown (identification des QT, du destinataire, des sections)
5. Une fois l'extraction terminée :
   - Cliquez sur **Visualiser** pour consulter le Markdown généré
   - Vous pouvez **modifier manuellement** le Markdown si nécessaire (corrections OCR, ajustements)
6. Cliquez sur **Valider** pour verrouiller l'étape et passer au Step1

### Step1 — PEMEC (Plan d'entretien)

**Objectif** : générer un plan d'entretien structuré (QMEC) à partir de la réquisition et de votre trame d'entretien.

1. Accédez au **Step1 — PEMEC**
2. Cliquez sur le bouton **Execute**
3. L'application :
   - Récupère les QT extraites au Step0
   - Récupère votre TPE et le contexte du domaine depuis la base RAG
   - Génère le QMEC via l'IA
4. Une fois la génération terminée :
   - Cliquez sur **Download** pour télécharger le QMEC
   - Consultez le plan d'entretien et utilisez-le pour vos entretiens
5. Cliquez sur **Valider** pour verrouiller l'étape et passer au Step2

### Step2 — Upload des notes et du rapport brut

**Objectif** : soumettre vos notes d'entretien (NE) et votre rapport d'expertise brut (REB) rédigés hors application.

1. Accédez au **Step2 — Upload**
2. Téléversez vos deux fichiers au format `.docx` :
   - **NE** (Notes d'Entretien) : vos notes sous forme télégraphique
   - **REB** (Rapport d'Expertise Brut) : vos réponses argumentées aux QT
3. Seul le format `.docx` est accepté. Tout autre format sera refusé avec un message d'erreur
4. Cliquez sur **Valider** pour verrouiller l'étape et passer au Step3

### Step3 — Génération du rapport final (REF + RAUX)

**Objectif** : générer le rapport d'expertise final et le rapport auxiliaire.

1. Accédez au **Step3 — REF**
2. Cliquez sur le bouton **Execute**
3. L'application génère deux documents :
   - **REF** (Rapport d'Expertise Final) : rapport professionnel généré à partir du REB, des QT, des NE et de votre Template Rapport
   - **RAUX** (Rapport Auxiliaire) en deux parties :
     - **Partie 1** : analyse des contestations possibles du REF sur la base du corpus domaine
     - **Partie 2** : version révisée du REF tenant compte des contestations identifiées
4. Une fois la génération terminée :
   - Cliquez sur **Download REF** pour télécharger le rapport final (.docx)
   - Cliquez sur **Download RAUX** pour télécharger le rapport auxiliaire (.docx)
5. Cliquez sur **Valider** pour :
   - Verrouiller définitivement le dossier
   - Archiver automatiquement tous les fichiers dans un ZIP (réquisition, Markdown, QMEC, NE, REB, REF, RAUX)

---

## 5. Utilisation du ChatBot

L'Application Locale intègre un assistant conversationnel (ChatBot) accessible depuis le menu principal.

### Fonctionnalités

- Réponses basées sur le **corpus de votre domaine** et la **documentation du système**
- Historique des conversations conservé localement
- Utilisation du LLM local (aucune donnée transmise à l'extérieur)

### Utilisation

1. Cliquez sur **ChatBot** dans le menu principal
2. Saisissez votre question dans le champ de texte
3. L'assistant répond en s'appuyant sur la base de connaissances RAG
4. L'historique de la conversation est affiché et conservé

### Exemples de questions

- "Quels sont les tests psychométriques recommandés pour une expertise de garde d'enfant ?"
- "Comment structurer la section conclusions de mon rapport ?"
- "Quelles sont les obligations légales de l'expert judiciaire en matière de confidentialité ?"

---

## 6. FAQ utilisateur

### Comment obtenir un ticket d'expertise ?

Connectez-vous au Site Central (https://judi-expert.fr), accédez à **Mon Espace → Tickets** et cliquez sur **Acheter un ticket**. Le paiement se fait par carte bancaire via Stripe. Le ticket est envoyé par email après confirmation du paiement.

### Puis-je utiliser l'application hors connexion ?

Oui. L'Application Locale fonctionne entièrement en local. Seules deux opérations nécessitent une connexion internet :
- La création d'un dossier (vérification du ticket auprès du Site Central)
- Le téléchargement ou la mise à jour du module RAG

Les étapes d'expertise (Step0 à Step3) et le ChatBot fonctionnent sans connexion.

### Mes données sont-elles sécurisées ?

Toutes vos données d'expertise restent exclusivement sur votre PC. Aucun document, rapport ou note n'est transmis au Site Central ou à un service cloud. Seul le code du ticket transite entre votre application et le Site Central.

Il est recommandé d'activer le chiffrement du disque (BitLocker ou FileVault) pour protéger vos données.

### Comment mettre à jour le module RAG ?

Accédez au menu **Configuration**, consultez les versions disponibles et installez la nouvelle version. L'ancienne version est automatiquement remplacée.

### Que faire si l'extraction OCR est de mauvaise qualité ?

- Vérifiez la qualité du PDF-scan (résolution minimale 300 DPI recommandée)
- Après l'extraction, vous pouvez modifier manuellement le Markdown généré
- Si le PDF contient déjà du texte extractible, l'application l'utilise directement (meilleure qualité)

### Que faire si le Site Central est indisponible ?

Le Site Central fonctionne aux heures ouvrables (8h-20h, heure de Paris). En dehors de ces horaires, la création de dossier et l'achat de tickets ne sont pas disponibles. Toutes les autres fonctionnalités de l'Application Locale restent opérationnelles.

### Comment sauvegarder mes dossiers ?

Les dossiers finalisés sont automatiquement archivés en ZIP. Pour une sauvegarde complète, copiez le répertoire de données de l'application (accessible via les volumes Docker).

### Puis-je modifier un dossier après validation ?

Non. Une fois une étape validée, elle est verrouillée et ne peut plus être modifiée. La validation du Step3 verrouille définitivement l'ensemble du dossier. Cette immutabilité garantit l'intégrité du processus d'expertise.

### Comment contacter le support ?

Utilisez le formulaire de contact sur le Site Central (https://judi-expert.fr/contact) en sélectionnant votre domaine et le type de demande (Problème, Demande d'amélioration, Autre).
