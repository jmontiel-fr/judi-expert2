# Poste Expert — Guide de configuration du PC

Ce document décrit la configuration matérielle et logicielle recommandée
pour le poste de travail de l'expert judiciaire utilisant Judi-Expert.

## 1. Configuration matérielle

### Minimale (CPU uniquement)

| Composant | Minimum | Recommandé |
|-----------|---------|------------|
| Processeur | 4 cœurs / 8 threads (Intel i5 11e gen+) | 6+ cœurs (Intel i7 12e gen+) |
| RAM | 8 Go | 16 Go DDR4/DDR5 |
| Stockage | SSD 256 Go (50 Go libres) | SSD NVMe 512 Go |
| Écran | 14" Full HD | 15.6" Full HD+ |
| OS | Windows 10/11 Famille ou Pro | Windows 11 Pro |

Avec cette configuration, le traitement LLM s'effectue sur le CPU.
Temps estimés par étape :

| Étape | Durée estimée (CPU) |
|-------|---------------------|
| Step 0 — Extraction OCR + structuration | 3-5 min |
| Step 1 — Génération QMEC | 5-8 min |
| Step 2 — RE-Projet + Auxiliaire | 15-25 min |
| Step 3 — REF-Projet | 8-12 min |
| **Total workflow** | **~35-55 min** |

### Optimale (avec GPU NVIDIA)

L'ajout d'un GPU NVIDIA dédié accélère considérablement l'inférence LLM.
Le modèle Mistral 7B Q4 utilisé par Judi-Expert occupe environ 4,1 Go
de VRAM. Le GPU est détecté et activé automatiquement au démarrage.

| GPU (VRAM) | Gain estimé | Workflow complet |
|------------|-------------|------------------|
| RTX 3050 (4 Go) | ~3x | ~12-18 min |
| RTX 4050 (6 Go) | ~6x | ~7-10 min |
| RTX 4060 (8 Go) | ~8-10x | ~5-9 min |
| RTX 3060 (12 Go) | ~10-12x | ~4-7 min |

**Recommandation** : un PC portable avec GPU RTX 4060 (8 Go VRAM) offre
le meilleur rapport performance/prix pour Judi-Expert. Le modèle tient
entièrement en mémoire GPU, ce qui maximise le gain de vitesse.

Exemple de configuration recommandée :
- Lenovo LOQ 15 — i7-13650HX, RTX 4060 8 Go, 16 Go DDR5, 512 Go SSD
- Budget : environ 1 000-1 100 €

### Prérequis réseau

- Connexion Internet requise uniquement pour :
  - L'installation initiale (téléchargement Docker Desktop, modèle LLM)
  - La vérification des tickets auprès du Site Central
  - Les mises à jour de l'application
- L'inférence LLM fonctionne 100% hors ligne après l'installation

## 2. Système d'exploitation

### Windows 11 Pro (recommandé)

- BitLocker intégré pour le chiffrement du disque
- Pas de logiciel tiers nécessaire pour le chiffrement

### Windows 10/11 Famille

- BitLocker n'est pas disponible
- **VeraCrypt** est requis pour le chiffrement du disque (voir section 3)
- Le "Chiffrement de l'appareil" Windows peut être disponible si le PC
  dispose d'un TPM 2.0 et d'un compte Microsoft (vérifier dans
  Paramètres → Confidentialité et sécurité → Chiffrement de l'appareil)

### Paramètres Windows importants

- **Mises à jour Windows** : activer les mises à jour automatiques
- **Pare-feu Windows** : laisser activé (Docker gère ses propres règles)
- **OneDrive / synchronisation cloud** : voir section 5

## 3. Chiffrement du disque

Le chiffrement du disque est **obligatoire**. Il protège les données
d'expertise en cas de perte ou de vol du PC. Sans chiffrement, toute
personne ayant accès physique au disque peut lire les dossiers.

### Option A — BitLocker (Windows Pro uniquement)

1. Ouvrir Paramètres → Confidentialité et sécurité → Chiffrement de l'appareil
2. Activer BitLocker sur le lecteur C:
3. Sauvegarder la clé de récupération (compte Microsoft ou clé USB)
4. Le chiffrement s'effectue en arrière-plan, le PC reste utilisable

### Option B — VeraCrypt (Windows Famille et Pro)

VeraCrypt est un logiciel libre et gratuit de chiffrement de disque.
Il offre un niveau de sécurité équivalent à BitLocker avec l'avantage
d'être indépendant de Microsoft (aucune clé stockée chez un tiers).

**Installation :**

1. Télécharger VeraCrypt depuis le site officiel : https://veracrypt.eu/en/downloads/
2. Installer avec les options par défaut
3. Lancer VeraCrypt → Système → Chiffrer la partition/le disque système
4. Choisir "Normal" → "Chiffrer la partition système Windows"
5. Algorithme : AES (par défaut, le plus rapide)
6. Définir un mot de passe fort (12+ caractères, majuscules, chiffres, symboles)
7. Créer le disque de secours VeraCrypt (clé USB ou ISO)
8. Mode de nettoyage : "Aucun" (suffisant pour un SSD)
9. Lancer le test de pré-amorçage (le PC redémarre pour vérifier le mot de passe)
10. Si le test réussit, lancer le chiffrement complet

**Impact sur les performances** : négligeable (~1-3% sur SSD).
Le chiffrement/déchiffrement est accéléré par les instructions AES-NI
du processeur, présentes sur tous les CPU Intel/AMD récents.

**Important** : le mot de passe VeraCrypt est demandé à chaque démarrage
du PC, avant le chargement de Windows. Ne pas oublier ce mot de passe.
Conserver le disque de secours en lieu sûr.

## 4. Logiciels à installer

### Obligatoires

| Logiciel | Version | Téléchargement | Rôle |
|----------|---------|----------------|------|
| VeraCrypt | 1.26+ | https://veracrypt.eu/en/downloads/ | Chiffrement du disque (si Windows Famille) |
| Google Chrome | Dernière stable | https://www.google.com/chrome/ | Navigateur pour l'interface Judi-Expert |
| Antivirus | Voir section 6 | Voir section 6 | Protection contre les malwares |

> **Note** : Docker Desktop est installé automatiquement par le package
> Judi-Expert si absent. L'expert n'a pas besoin de l'installer
> manuellement.

### Optionnels

| Logiciel | Rôle |
|----------|------|
| Firefox | Navigateur alternatif (compatible) |
| 7-Zip | Gestion des archives ZIP |
| Adobe Acrobat Reader | Lecture des PDF (le navigateur suffit généralement) |

### À ne pas installer

- **VPN personnel** : peut interférer avec Docker et la communication
  avec le Site Central
- **Logiciels de nettoyage** (CCleaner, etc.) : risque de supprimer
  des fichiers Docker ou des données d'expertise

## 5. Synchronisation cloud — ATTENTION

**Les données d'expertise ne doivent JAMAIS être synchronisées dans le
cloud** (RGPD, secret professionnel, AI Act).

Judi-Expert est installé dans `C:\judi-expert\`, un répertoire hors de
tout dossier synchronisé. Cependant, il faut vérifier que :

### OneDrive

OneDrive synchronise par défaut les dossiers Bureau, Documents et Images.
Judi-Expert n'est pas dans ces dossiers, mais par précaution :

1. Clic droit sur l'icône OneDrive (barre des tâches) → Paramètres
2. Onglet "Synchronisation et sauvegarde"
3. Vérifier que `C:\judi-expert` n'apparaît pas dans les dossiers synchronisés
4. Optionnel : désactiver la sauvegarde des dossiers Bureau/Documents
   si l'expert y stocke des documents liés aux expertises

### Dropbox / Google Drive

Si installés, vérifier que leur dossier de synchronisation ne contient
pas `C:\judi-expert\` ni de lien symbolique vers ce répertoire.

### Vérification automatique

L'installateur Judi-Expert vérifie automatiquement si le répertoire
d'installation se trouve dans un dossier synchronisé (OneDrive, Dropbox,
Google Drive, iCloud, MEGA, pCloud) et affiche un avertissement le cas
échéant.

## 6. Antivirus

### Windows Defender (intégré) — Recommandé

Windows Defender (Microsoft Defender Antivirus) est intégré à Windows 10/11
et offre une protection suffisante pour un poste Judi-Expert :

- Protection en temps réel contre les virus, malwares et ransomwares
- Mises à jour automatiques via Windows Update
- Pare-feu intégré
- Aucun coût supplémentaire
- Faible impact sur les performances
- Scores AV-TEST régulièrement à 6/6 en protection
- Aucune collecte de données de navigation
- Aucun conflit avec Docker

**C'est la solution recommandée pour Judi-Expert.** Aucun antivirus tiers
n'est nécessaire si Windows Defender est activé et à jour.

### Options payantes (protection complémentaire)

Si l'expert souhaite une couche de protection supplémentaire au-delà de
Windows Defender (anti-ransomware avancé, protection réseau, sandbox) :

| Antivirus | Prix/an | Avantages complémentaires |
|-----------|---------|--------------------------|
| Bitdefender Total Security | ~40 € | Anti-ransomware multicouche, sandbox automatique, faible impact perf |
| ESET NOD32 Antivirus | ~30 € | Très léger, excellente compatibilité Docker, peu de faux positifs |
| Kaspersky Standard | ~30 € | Protection réseau avancée, mode "ne pas déranger" pour Docker |

**Si un antivirus tiers est choisi**, ajouter une exclusion pour le
répertoire `C:\judi-expert\` et pour les processus Docker afin d'éviter
les faux positifs et les ralentissements lors de l'inférence LLM.

## 7. Vérifications de sécurité

Checklist à vérifier avant la première utilisation de Judi-Expert :

### Chiffrement

- [ ] Le disque est chiffré (BitLocker ou VeraCrypt)
- [ ] La clé de récupération / disque de secours est sauvegardée en lieu sûr
- [ ] Le mot de passe de chiffrement est différent du mot de passe Windows

### Antivirus

- [ ] Windows Defender est activé et à jour (ou antivirus tiers installé)
- [ ] Les mises à jour automatiques de l'antivirus sont activées
- [ ] Exclusion ajoutée pour `C:\judi-expert\` (si antivirus tiers)

### Système

- [ ] Windows Update est activé (mises à jour automatiques)
- [ ] Le pare-feu Windows est activé
- [ ] Le compte Windows a un mot de passe fort
- [ ] Le verrouillage automatique de session est activé (5 min recommandé)

### Cloud et réseau

- [ ] `C:\judi-expert\` n'est PAS dans un dossier synchronisé (OneDrive, Dropbox, etc.)
- [ ] Aucun VPN personnel n'interfère avec Docker
- [ ] La connexion au Site Central fonctionne (test via l'application)

### Docker (installé automatiquement par Judi-Expert)

- [ ] Docker Desktop est installé et démarre correctement
- [ ] Les conteneurs Judi-Expert démarrent sans erreur
- [ ] Le modèle LLM (Mistral 7B) est téléchargé et fonctionnel

## 8. Maintenance

### Mises à jour régulières

- **Windows** : mises à jour automatiques (ne pas reporter au-delà de 7 jours)
- **Docker Desktop** : mettre à jour quand une notification apparaît
- **VeraCrypt** : vérifier les mises à jour trimestriellement sur https://veracrypt.eu
- **Navigateur** : mises à jour automatiques (Chrome se met à jour seul)
- **Judi-Expert** : les mises à jour sont distribuées via le Site Central

### Sauvegarde

Les données d'expertise sont stockées localement dans `C:\judi-expert\`.
Pour les sauvegarder sans compromettre la sécurité :

- **Disque externe chiffré** : copier `C:\judi-expert\data\` sur un
  disque externe lui-même chiffré (VeraCrypt ou BitLocker To Go)
- **Ne jamais** sauvegarder sur un cloud non chiffré (OneDrive, Google Drive, Dropbox)
- Fréquence recommandée : après chaque dossier validé
