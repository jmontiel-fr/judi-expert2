# Conditions Générales d'Utilisation (CGU)

**Judi-Expert — ITechSource**
**Dernière mise à jour : 1er janvier 2026**

---

## 1. Objet et champ d'application

Les présentes Conditions Générales d'Utilisation (ci-après « CGU ») définissent les modalités et conditions d'accès et d'utilisation des services proposés par la société ITechSource (ci-après « l'Éditeur ») à travers :

- Le **Site Central** accessible à l'adresse [https://judi-expert.fr](https://judi-expert.fr), déployé sur l'infrastructure AWS (région eu-west-3, Paris) ;
- L'**Application Locale** installée sur le poste de travail de l'utilisateur, fonctionnant via des conteneurs Docker en environnement local.

L'ensemble de ces deux composants constitue la solution **Judi-Expert**, destinée à assister les experts judiciaires dans la production de leurs rapports d'expertise.

En accédant ou en utilisant les services Judi-Expert, l'utilisateur reconnaît avoir pris connaissance des présentes CGU et les accepte sans réserve.

---

## 2. Conditions d'accès et d'inscription

### 2.1 Accès au Site Central

L'accès au Site Central est ouvert à tout visiteur. Certaines fonctionnalités (achat de tickets, téléchargement de l'Application Locale, accès à l'espace personnel) nécessitent une inscription préalable et une connexion authentifiée.

Le Site Central est disponible pendant les horaires bureau, de 8h à 20h (heure de Paris), du lundi au vendredi. En dehors de ces horaires, une page de maintenance informe les visiteurs de l'indisponibilité temporaire du service.

### 2.2 Inscription

Pour s'inscrire, l'utilisateur doit remplir le formulaire d'inscription comprenant les champs obligatoires suivants : Nom, Prénom, adresse, Domaine d'expertise. L'utilisateur doit également cocher les cases obligatoires suivantes :

- Acceptation des Mentions légales ;
- Acceptation des présentes CGU ;
- Engagement de responsabilité de protection des données sur son PC (chiffrement du disque via BitLocker ou équivalent).

Une case optionnelle permet d'accepter la réception d'emails et de newsletters.

L'authentification est gérée par AWS Cognito.

### 2.3 Accès à l'Application Locale

L'Application Locale est téléchargeable depuis la page `/downloads` du Site Central après inscription. Son utilisation nécessite un poste de travail satisfaisant les prérequis techniques (CPU, RAM, espace disque, chiffrement du disque) et la création d'un dossier d'expertise requiert un Ticket valide acheté sur le Site Central.

---

## 3. Description des services

### 3.1 Application Locale

L'Application Locale permet à l'expert judiciaire de gérer ses dossiers d'expertise selon un workflow en 4 étapes séquentielles :

1. **Step0 — Extraction** : conversion d'un document PDF-scan de réquisition en fichier Markdown exploitable via OCR (Tesseract) et structuration par un LLM local (Mistral 7B) ;
2. **Step1 — PEMEC** : génération d'un plan d'entretien (QMEC) à partir des questions du tribunal et de la trame d'entretien configurée par l'expert ;
3. **Step2 — Upload** : collecte des notes d'entretien (NE) et du rapport d'expertise brut (REB) au format .docx ;
4. **Step3 — REF** : génération du rapport d'expertise final (REF) et du rapport auxiliaire (RAUX) comprenant une analyse de contestations et une version révisée.

L'Application Locale intègre également un ChatBot conversationnel utilisant le LLM local et la base RAG du domaine d'expertise.

### 3.2 Site Central

Le Site Central propose les services suivants :

- Inscription et gestion du compte expert ;
- Achat de tickets d'expertise via Stripe ;
- Téléchargement de l'Application Locale et des modules RAG par domaine ;
- Consultation des corpus disponibles par domaine ;
- Accès à la documentation (FAQ, méthodologie, mentions légales, CGU) ;
- Formulaire de contact.

### 3.3 Tickets d'expertise

Un Ticket est un fichier électronique à usage unique, acheté sur le Site Central via Stripe, nécessaire à la création d'un dossier d'expertise dans l'Application Locale. Chaque Ticket est associé au domaine d'expertise de l'expert. Une fois utilisé, le Ticket ne peut être réutilisé.

### 3.4 Modules RAG

Les modules RAG contiennent le corpus documentaire spécifique à chaque domaine d'expertise (psychologie, psychiatrie, médecine légale, bâtiment, comptabilité). Ils sont distribués sous forme d'images Docker depuis le registre ECR du Site Central.

---

## 4. Obligations de l'utilisateur

L'utilisateur (expert judiciaire) s'engage à :

- Fournir des informations exactes et à jour lors de son inscription ;
- Maintenir la confidentialité de ses identifiants de connexion ;
- Assurer le chiffrement du disque dur de son poste de travail (BitLocker ou équivalent) conformément à son engagement lors de l'inscription ;
- Utiliser les services Judi-Expert exclusivement dans le cadre de ses missions d'expertise judiciaire ;
- Ne pas tenter de contourner les mécanismes de sécurité ou de protection des données ;
- Ne pas reproduire, distribuer ou commercialiser tout ou partie des services sans autorisation préalable de l'Éditeur ;
- Vérifier et valider les documents générés par le système avant toute utilisation dans le cadre judiciaire ;
- Respecter les lois et réglementations en vigueur, notamment en matière de protection des données personnelles.

L'utilisateur reconnaît que les rapports générés par Judi-Expert constituent une assistance à la rédaction et ne se substituent pas à son expertise professionnelle et à sa responsabilité d'expert judiciaire.

---

## 5. Propriété intellectuelle

### 5.1 Droits de l'Éditeur

L'ensemble des éléments constituant la solution Judi-Expert (code source, interfaces, documentation, logos, textes, graphismes) est la propriété exclusive d'ITechSource ou de ses concédants de licence, et est protégé par les lois relatives à la propriété intellectuelle.

### 5.2 Droits de l'utilisateur

L'utilisateur conserve l'intégralité des droits de propriété intellectuelle sur les documents qu'il produit, importe ou génère via l'Application Locale (réquisitions, notes d'entretien, rapports d'expertise).

### 5.3 Composants open-source

La solution Judi-Expert utilise exclusivement des composants sous licences open-source ou gratuites compatibles avec un usage commercial. L'inventaire complet des dépendances est disponible dans le fichier `docs/licences.md`.

---

## 6. Responsabilité et limitation

### 6.1 Responsabilité de l'Éditeur

L'Éditeur s'engage à fournir les services avec diligence et selon les règles de l'art. Toutefois, l'Éditeur ne saurait être tenu responsable :

- Des interruptions de service du Site Central en dehors des horaires d'ouverture (8h-20h) ou pour maintenance ;
- De la qualité des documents générés par le LLM, qui constituent une aide à la rédaction et non un avis professionnel ;
- Des dommages résultant d'une utilisation non conforme aux présentes CGU ;
- De la perte de données locales résultant d'une défaillance du poste de travail de l'utilisateur ;
- Des conséquences liées à l'utilisation des rapports générés dans le cadre judiciaire.

### 6.2 Limitation de responsabilité

En tout état de cause, la responsabilité totale de l'Éditeur est limitée au montant des sommes effectivement versées par l'utilisateur au cours des douze (12) derniers mois précédant l'événement donnant lieu à responsabilité.

---

## 7. Protection des données

La collecte et le traitement des données personnelles sont régis par la Politique de Confidentialité de Judi-Expert, accessible à l'adresse [/politique-confidentialite](/politique-confidentialite).

L'utilisateur est informé que :

- Les données d'expertise restent exclusivement sur le poste local de l'expert et ne sont jamais transmises au Site Central ;
- Seuls les tickets transitent entre l'Application Locale et le Site Central pour vérification ;
- Les données personnelles collectées lors de l'inscription sont hébergées sur AWS dans la région eu-west-3 (Paris), sans transfert hors de l'Union Européenne.

---

## 8. Modification des CGU

L'Éditeur se réserve le droit de modifier les présentes CGU à tout moment. Les modifications entrent en vigueur dès leur publication sur le Site Central. L'utilisateur sera informé de toute modification substantielle par email ou par notification lors de sa prochaine connexion.

L'utilisation continue des services après modification des CGU vaut acceptation des nouvelles conditions.

---

## 9. Droit applicable et juridiction compétente

Les présentes CGU sont régies par le droit français.

En cas de litige relatif à l'interprétation ou à l'exécution des présentes CGU, les parties s'efforceront de trouver une solution amiable. À défaut, le litige sera soumis aux tribunaux compétents du ressort du siège social d'ITechSource.

---

## 10. Contact

Pour toute question relative aux présentes CGU, vous pouvez nous contacter :

- Par le formulaire de contact : [https://judi-expert.fr/contact](https://judi-expert.fr/contact)
- Par email : contact@judi-expert.fr
