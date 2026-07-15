# Signature électronique — Universign

**Judi-Expert — ITechSource**
**Dernière mise à jour : juillet 2026**

Ce document décrit la procédure interne pour **acheter un pack de signatures** sur Universign et **envoyer un contrat partenaire référent** à signer. Il complète l’article 17.6 de la [convention type](contrat-partenaire-referent.md).

**Référence officielle Universign :** [Guide utilisateur](https://apps.universign.com/docs/webapp/fr)

---

## Le partenaire doit-il payer pour signer ?

**Non.** Le partenaire référent (expert judiciaire invité) **ne paie rien** pour signer électroniquement :

- **pas de compte Universign** à créer ;
- **pas d’abonnement** ni de pack de signatures à acheter ;
- **pas de frais** demandés sur le parcours de signature.

C’est **ITechSource** (l’expéditeur) qui supporte le coût via son **abonnement** et ses **packs de signatures**.

Le partenaire reçoit un **e-mail d’invitation** avec un lien sécurisé, ouvre le document dans son navigateur, s’authentifie (souvent par **code SMS** si vous l’avez configuré) et signe. Le SMS d’authentification est **inclus dans le service** côté expéditeur : le signataire n’est pas débité.

> **À retenir :** seul l’**expéditeur** (ITechSource) consomme des crédits de signature. Le signataire invité signe gratuitement.

---

## Vue d’ensemble des coûts (côté ITechSource)

| Élément | Qui paie | Commentaire |
|---------|----------|-------------|
| Abonnement Universign (plan Business ou Business+) | ITechSource | Requis pour acheter des packs AES/QES |
| Pack de 25 signatures | ITechSource | Environ **49 € HT** (tarif indicatif — vérifier sur la plateforme) |
| Signature du partenaire | — | **Gratuit** pour le partenaire |
| Signature ITechSource | — | Décomptée du pack ITechSource |
| Authentification SMS du partenaire | — | Incluse dans la transaction (coût côté ITechSource) |

### Consommation d’un contrat partenaire

Universign compte **une signature par participant et par document** (pas par transaction globale).

Pour une convention partenaire en **un seul PDF** signée par **ITechSource** puis par le **partenaire** :

| Action | Signatures consommées |
|--------|----------------------|
| Signature du représentant ITechSource | 1 |
| Signature du partenaire référent | 1 |
| **Total par contrat** | **2** |

Un **pack de 25 signatures** permet donc d’environ **12 conventions** complètes (25 ÷ 2), hors tests ou avenants.

Les **signatures simples** sont disponibles par défaut sur l’espace de travail ; les **packs achetés** donnent accès aux signatures **avancées (AES)** ou **qualifiées (QES)**, plus adaptées à un contrat B2B. Voir [Acheter des packs de signatures](https://apps.universign.com/docs/webapp/fr/manage_workspace/subscription/).

---

## Prérequis

1. **Compte Universign** avec un espace de travail ITechSource (propriétaire = personne habilitée à gérer l’abonnement).
2. **Forfait Business ou Business+** (nécessaire pour acheter des packs AES/QES).
3. **Contrat préparé en PDF** :
   - modèle : `docs/contrat-partenaire-referent.md` ;
   - tous les placeholders `<<...>>` complétés ;
   - section **« Annexe — Placeholders à compléter »** retirée avant signature ;
   - export **PDF** (Word ou autre outil d’export propre).
4. **Coordonnées du partenaire** : e-mail professionnel, numéro de mobile (si authentification SMS).

### Contraintes sur le PDF (Universign)

Avant envoi, le PDF doit :

- ne contenir **aucune signature tierce** préexistante ;
- être **original** (pas modifié par un éditeur PDF qui invalide la structure) ;
- ne pas contenir de **champs de formulaire dynamiques** ;
- faire moins de **25 Mo**.

Source : [Gérer les documents](https://apps.universign.com/docs/webapp/fr/basic_parameters/manage_documents/).

---

## Procédure 1 — Acheter un pack de 25 signatures

### Étape 1 — Accéder à l’abonnement

1. Connectez-vous à [Universign](https://www.universign.com/fr/).
2. Ouvrez votre **espace de travail** ITechSource.
3. Menu **Administration** → **Abonnement et Factures**.

Seul le **propriétaire** de l’espace de travail peut gérer l’abonnement.

### Étape 2 — Vérifier ou activer le forfait Business

Si l’espace est encore en essai gratuit ou sur un plan inférieur :

1. Cliquez sur **Mettre à niveau**.
2. Choisissez le forfait **Business** (ou **Business+** selon vos besoins).
3. Finalisez le paiement de l’abonnement.

Les packs AES/QES ne sont disponibles que sur ces forfaits.

### Étape 3 — Acheter le pack de 25 signatures

1. Dans **Abonnement et Factures**, cliquez sur **Acheter des signatures**.
2. Sélectionnez le **pack de 25 signatures** (ou le volume adapté).
3. Réglez par carte bancaire.

Le pack est **disponible immédiatement**. Le compteur de signatures s’affiche dans le tableau de bord.

**Validité :** chaque pack a une **durée de validité** à compter de la date d’achat (souvent **1 an** pour les packs standards — confirmer sur l’écran d’achat). Les signatures non utilisées à expiration sont perdues, sauf celles déjà engagées dans des transactions en cours.

Source : [Abonnement & Factures](https://apps.universign.com/docs/webapp/fr/manage_workspace/subscription/).

---

## Procédure 2 — Envoyer un contrat partenaire à signer

### Étape 1 — Préparer le document

1. Compléter `docs/contrat-partenaire-referent.md`.
2. Retirer l’annexe glossaire (non signée).
3. Exporter en **PDF** (ex. `convention-partenariat-referent-<domaine>-<nom>.pdf`).
4. Relire le PDF : aucun `<<placeholder>>` restant.

### Étape 2 — Créer une transaction

1. Depuis le tableau de bord Universign, **créer une nouvelle transaction**.
2. **Importer** le PDF (glisser-déposer ou parcourir).
3. Vérifier l’aperçu (pagination, lisibilité).

Une transaction non démarrée reste en **brouillon 7 jours** avant suppression automatique.

Source : [Faire signer un premier document](https://apps.universign.com/docs/webapp/fr/getting_started/simple_transaction/).

### Étape 3 — Placer les champs de signature

1. Ouvrir l’éditeur de la transaction.
2. Pour chaque signataire, faire glisser un **champ Signature** depuis le panneau **Champs** vers le bloc signatures du PDF (dernière page).
3. Positionner :
   - un champ pour **ITechSource** (`<<representant_legal>>`) ;
   - un champ pour le **partenaire référent**.

### Étape 4 — Renseigner les participants

| Participant | Rôle | E-mail | Téléphone (si SMS) |
|-------------|------|--------|---------------------|
| Représentant ITechSource | Signataire 1 | e-mail professionnel ITechSource | selon politique interne |
| Partenaire référent | Signataire 2 | `<<email_partenaire>>` | mobile du partenaire |

Attribuer chaque champ de signature au bon e-mail.

**Ordre recommandé :** faire signer **ITechSource en premier**, puis le **partenaire** (paramètre *Ordonnancer les participants* si besoin).

### Étape 5 — Niveau de signature et authentification

Pour un contrat de partenariat B2B :

| Paramètre | Recommandation |
|-----------|----------------|
| Niveau de signature | **Avancée (AES)** — via le pack acheté |
| Authentification partenaire | **Code SMS** (valeur probante, usage courant) |
| Authentification ITechSource | Selon politique interne (certificat ou SMS) |

Configurer dans **Paramètres avancés** → [Gérer les moyens d’authentification](https://apps.universign.com/docs/webapp/fr/advanced_parameters/authentication_means/).

Le partenaire **ne choisit pas** le mode de paiement : il suit le parcours imposé par la transaction (lecture → SMS → signature).

### Étape 6 — Démarrer la transaction

1. Vérifier le récapitulatif (document, participants, ordre, niveau AES).
2. Cliquer sur **Démarrer** / **Envoyer**.

Chaque signataire reçoit un **e-mail Universign** avec un lien personnel. ITechSource signe en premier si l’ordre l’exige ; le partenaire reçoit ensuite sa demande.

### Étape 7 — Après signature

1. Télécharger le **PDF signé** et le **dossier de preuve** (journal d’audit, certificats).
2. Archiver les deux côtés ITechSource (GED, dossier partenaire).
3. Reporter la **date de signature** figurant sur le certificat Universign si vous mettez à jour une copie interne.
4. Envoyer au partenaire une copie du PDF signé si ce n’est pas déjà fait automatiquement par Universign.

---

## Parcours côté partenaire (résumé)

Ce que vit l’expert invité — **sans frais** :

1. Réception d’un e-mail **« Demande de signature »** (expéditeur : Universign / ITechSource).
2. Clic sur le lien sécurisé → ouverture du contrat dans le **navigateur** (PC ou mobile).
3. Lecture du document.
4. Saisie d’un **code SMS** reçu sur son mobile (si authentification SMS activée).
5. Validation de la signature électronique.
6. Réception éventuelle d’une copie du document signé par e-mail.

**Le partenaire n’a pas besoin :**

- d’installer une application ;
- de créer un compte Universign ;
- de payer un abonnement ou un pack ;
- de posséder un certificat de signature préalable (Universign crée le certificat de session si nécessaire).

---

## Checklist rapide — Contrat partenaire référent

- [ ] Pack de signatures disponible (≥ 2 crédits AES pour un contrat à 2 signataires)
- [ ] PDF final sans placeholders ni annexe glossaire
- [ ] E-mail et mobile du partenaire vérifiés
- [ ] Niveau **AES** sélectionné
- [ ] Ordre de signature : ITechSource → partenaire
- [ ] Transaction démarrée et suivie jusqu’à statut **Terminée**
- [ ] PDF signé + dossier de preuve archivés

---

## Essai gratuit et tarifs indicatifs

- À la création du premier espace de travail, Universign propose en général un **essai gratuit** pour tester l’envoi (durée et quotas variables — vérifier à l’inscription).
- **Pack 25 signatures :** environ **49 € HT** (tarif public courant, juillet 2026 — **à confirmer** sur [universign.com](https://www.universign.com/fr/) au moment de l’achat).
- L’**abonnement Business** est facturé **en plus** du pack (modèle SaaS Signaturit/Universign).

---

## Liens utiles

| Sujet | URL |
|-------|-----|
| Guide utilisateur (FR) | https://apps.universign.com/docs/webapp/fr |
| Première transaction | https://apps.universign.com/docs/webapp/fr/getting_started/simple_transaction/ |
| Abonnement & packs | https://apps.universign.com/docs/webapp/fr/manage_workspace/subscription/ |
| Authentification (SMS) | https://apps.universign.com/docs/webapp/fr/advanced_parameters/authentication_means/ |
| Contrat type Judi-Expert | [contrat-partenaire-referent.md](contrat-partenaire-referent.md) |

---

## Support

- **Universign :** support via le site [universign.com](https://www.universign.com/fr/)
- **Interne ITechSource :** préciser ici le contact responsable des conventions partenaires (à compléter).
