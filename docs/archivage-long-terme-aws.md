# Archivage long terme des dossiers d'expertise — AWS S3 Glacier

## Objectif

Permettre à l'expert judiciaire de sauvegarder ses archives de dossiers d'expertise (.zip chiffrés) sur un stockage cloud sécurisé, durable et économique, en dehors de son PC local.

Les archives contiennent des **données de santé** (rapports d'expertise psychologique, observations cliniques, tests psychométriques). Le stockage doit être conforme au RGPD et aux obligations HDS (Hébergement de Données de Santé).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  PC Expert (Application Locale)                             │
│                                                             │
│  1. Génération du ZIP (Step 5)                              │
│  2. Chiffrement AES-256-GCM côté client                    │
│     (clé dérivée du mot de passe expert + sel unique)       │
│  3. Upload vers S3 Glacier Deep Archive (eu-west-3 Paris)   │
│                                                             │
│  Restauration :                                             │
│  4. Demande de restauration S3 Glacier (délai 12-48h)       │
│  5. Download du fichier chiffré                             │
│  6. Déchiffrement local avec le mot de passe expert         │
└─────────────────────────────────────────────────────────────┘
         │
         │ HTTPS (TLS 1.3)
         ▼
┌─────────────────────────────────────────────────────────────┐
│  AWS S3 — Région eu-west-3 (Paris) — Certification HDS     │
│                                                             │
│  Bucket : judi-expert-archives-{expert-id}                  │
│  Classe : S3 Glacier Deep Archive                           │
│  Chiffrement serveur : SSE-KMS (double chiffrement)         │
│  Versioning : activé                                        │
│  Object Lock : COMPLIANCE mode (immuabilité)                │
│  Lifecycle : aucune suppression automatique                 │
│                                                             │
│  Structure :                                                │
│  s3://judi-expert-archives-{id}/                            │
│  ├── {dossier-nom}-{date}.zip.enc                           │
│  ├── {dossier-nom}-{date}.zip.enc.meta                      │
│  └── ...                                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Conformité RGPD et HDS

### Pourquoi c'est conforme sans certifier l'application

| Exigence | Comment c'est couvert |
|----------|----------------------|
| **HDS** (art. L.1111-8 CSP) | AWS eu-west-3 est **certifié HDS** — l'hébergeur porte la certification, pas l'application |
| **RGPD — Localisation** | Données stockées en France (région Paris eu-west-3) |
| **RGPD — Chiffrement** | Double chiffrement : côté client (AES-256-GCM) + côté serveur (SSE-KMS) |
| **RGPD — Minimisation** | Seules les archives finales sont stockées (pas de données intermédiaires) |
| **RGPD — Sous-traitance** | DPA (Data Processing Agreement) inclus dans les conditions AWS |
| **Immuabilité** | S3 Object Lock en mode COMPLIANCE — impossible de supprimer ou modifier |
| **Durabilité** | S3 garantit 99,999999999% (11 neufs) de durabilité |

### Ce que l'expert doit faire

- Documenter le traitement dans son **registre CNIL**
- Réaliser une **AIPD** (Analyse d'Impact relative à la Protection des Données) si > 100 dossiers
- Conserver sa **clé de chiffrement** (mot de passe) de manière sécurisée (gestionnaire de mots de passe)

### Ce que l'expert n'a PAS besoin de faire

- Certifier son application (c'est AWS qui est certifié HDS)
- Obtenir un agrément CNIL spécifique
- Déclarer un transfert hors UE (les données restent en France)

---

## Sécurité

### Chiffrement côté client (avant upload)

```python
# Algorithme : AES-256-GCM
# Dérivation de clé : PBKDF2-HMAC-SHA256 (600 000 itérations)
# Sel : 32 octets aléatoires (unique par fichier)
# Nonce : 12 octets aléatoires (unique par opération)

import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

def encrypt_archive(zip_path: str, password: str) -> tuple[bytes, bytes]:
    """Chiffre un fichier ZIP avec un mot de passe.
    
    Returns:
        (données_chiffrées, sel) — le sel doit être stocké dans le .meta
    """
    salt = os.urandom(32)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32,
                     salt=salt, iterations=600_000)
    key = kdf.derive(password.encode())
    
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    
    with open(zip_path, "rb") as f:
        plaintext = f.read()
    
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext, salt
```

### Fichier .meta (non chiffré, stocké à côté du .enc)

```json
{
  "dossier_nom": "Expertise Dupont 2026",
  "reference_dossier": "RG 24/12345",
  "date_archivage": "2026-05-12T14:30:00Z",
  "hash_sha256_zip": "a1b2c3d4...",
  "hash_sha256_enc": "e5f6g7h8...",
  "salt_hex": "...",
  "kdf": "PBKDF2-HMAC-SHA256",
  "kdf_iterations": 600000,
  "cipher": "AES-256-GCM",
  "taille_zip_octets": 1234567,
  "taille_enc_octets": 1234599,
  "expert_email": "expert@example.com",
  "domaine": "psychologie"
}
```

Le fichier .meta ne contient **aucune donnée de santé** — uniquement des métadonnées techniques pour la restauration.

---

## Coûts estimés

| Élément | Coût |
|---------|------|
| Stockage S3 Glacier Deep Archive | ~0,002 €/Go/mois |
| 1 dossier archivé (~5 Mo chiffré) | ~0,00001 €/mois |
| 100 dossiers archivés | ~0,001 €/mois |
| 1000 dossiers archivés | ~0,01 €/mois |
| Restauration (par fichier) | ~0,03 € + transfert |
| Transfert sortant (download) | ~0,09 €/Go |

**Coût annuel pour un expert typique (50 dossiers/an)** : < 1 €/an

---

## Flux utilisateur

### Archivage (automatique après validation Step 5)

1. L'expert valide le Step 5 → le ZIP est généré localement
2. L'application propose : "Archiver sur le cloud ?" (optionnel)
3. Si oui : chiffrement local → upload S3 Glacier → confirmation
4. Le fichier local reste sur le PC (l'archive cloud est une sauvegarde)

### Restauration (depuis la page "Mes archives")

1. L'expert consulte la liste de ses archives cloud
2. Il demande la restauration d'un dossier
3. Délai : 12 à 48h (contrainte S3 Glacier Deep Archive)
4. Notification quand le fichier est disponible
5. Download + déchiffrement local avec le mot de passe

---

## Implémentation technique

### Backend (Application Locale)

- **Service** : `services/archive_cloud_service.py`
- **Dépendances** : `boto3`, `cryptography`
- **Configuration** : clés AWS via le Site Central (token temporaire STS)
- **Endpoint** : `POST /api/dossiers/{id}/archive-cloud` (déclenche chiffrement + upload)
- **Endpoint** : `GET /api/archives` (liste les archives cloud de l'expert)
- **Endpoint** : `POST /api/archives/{id}/restore` (demande de restauration)

### Authentification AWS

L'Application Locale n'a pas de clés AWS permanentes. Le flux est :
1. L'app locale demande un token temporaire au Site Central
2. Le Site Central génère des credentials STS (durée 1h, scope limité au bucket de l'expert)
3. L'app locale utilise ces credentials pour l'upload/download

### Infrastructure (Terraform)

```hcl
resource "aws_s3_bucket" "archives" {
  bucket = "judi-expert-archives"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "archives" {
  bucket = aws_s3_bucket.archives.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.archives.arn
    }
  }
}

resource "aws_s3_bucket_object_lock_configuration" "archives" {
  bucket              = aws_s3_bucket.archives.id
  object_lock_enabled = "Enabled"
  rule {
    default_retention {
      mode = "COMPLIANCE"
      years = 30
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "archives" {
  bucket = aws_s3_bucket.archives.id
  rule {
    id     = "glacier-immediate"
    status = "Enabled"
    transition {
      days          = 0
      storage_class = "DEEP_ARCHIVE"
    }
  }
}
```

---

## Durée de conservation

### Cadre juridique

L'expert judiciaire a une **obligation déontologique de conservation** de ses dossiers (décret n°2004-1463 relatif aux experts judiciaires, art. 24). Il doit pouvoir justifier de son travail en cas de contestation, récusation ou action en responsabilité.

Il n'existe pas de durée légale unique imposée. La durée dépend du type de contentieux :

| Contentieux | Prescription | Durée de conservation recommandée |
|---|---|---|
| Pénal — crimes | 20 ans | **20 ans** minimum |
| Pénal — délits | 6 ans | **10 ans** recommandé |
| Civil (droit commun) | 5 ans | **10 ans** recommandé |
| Responsabilité civile de l'expert | 10 ans | **10 ans** minimum |
| Mineur victime | majorité + 10 ans | **28 ans** (cas le plus long) |

**Recommandation CNCEJ** (Conseil National des Compagnies d'Experts de Justice) : **10 ans minimum**, 20 ans pour le pénal.

### Ce qui doit être conservé

L'expert doit conserver les éléments permettant de **justifier ses conclusions** et de **répondre à une contestation** :

| Document | Obligatoire | Justification |
|----------|:-----------:|---------------|
| **Rapport d'expertise final** (REF) | ✅ Oui | Document remis au tribunal — preuve du travail réalisé |
| **Ordonnance / réquisition** | ✅ Oui | Cadre de la mission (questions posées, parties, dates) |
| **Notes d'entretien** (PEA annoté) | ✅ Oui | Justifie les observations cliniques et les dires rapportés |
| **Pièces consultées** (diligences) | ✅ Oui | Justifie les éléments factuels utilisés dans le rapport |
| **Correspondances** (courriers de diligence) | ✅ Oui | Preuve du respect du contradictoire |
| **Tests psychométriques** (protocoles bruts) | ✅ Oui | Justifie les résultats et interprétations |
| **Consentement éclairé** (si recueilli par écrit) | ✅ Oui | Preuve déontologique |
| Fichiers intermédiaires (demande.md, brouillons) | ❌ Non | Documents de travail sans valeur probante |
| Fichiers techniques (placeholders.csv, pe.docx) | ❌ Non | Artefacts de l'application, pas du dossier d'expertise |

### Contenu de l'archive ZIP

L'archive générée au Step 5 contient **tout le dossier** (fichiers d'entrée + sorties de chaque step). Pour l'archivage long terme, les éléments essentiels sont :

- `ref.docx` — Rapport d'Expertise Final
- `demande.pdf` — Ordonnance/réquisition originale
- `pea.docx` — Notes d'entretien annotées
- `diligence-*.pdf` — Pièces consultées
- `timbre.txt` — Horodatage technique (intégrité)

Les autres fichiers (demande.md, placeholders.csv, pre.docx, dac.docx) sont conservés par commodité mais ne sont pas juridiquement nécessaires.

### Configuration S3 Object Lock

- **Mode** : COMPLIANCE (immuabilité — impossible de supprimer avant l'échéance)
- **Durée par défaut** : 20 ans (couvre la majorité des cas)
- **Configurable par l'expert** : 10, 20 ou 30 ans selon le type de contentieux
- **Après échéance** : l'expert peut choisir de supprimer ou prolonger

---

## Limitations et risques

| Risque | Mitigation |
|--------|-----------|
| Perte du mot de passe | L'expert doit utiliser un gestionnaire de mots de passe. Pas de récupération possible (chiffrement côté client). |
| Délai de restauration (12-48h) | Acceptable pour des archives long terme. Utiliser S3 Glacier Instant Retrieval si besoin d'accès rapide (+coût). |
| Coût AWS si volume important | Négligeable (< 1€/an pour un expert typique) |
| Fermeture du service Judi-Expert | Les archives restent accessibles tant que le compte AWS existe. L'expert peut télécharger ses archives à tout moment. |
| Évolution des algorithmes crypto | AES-256 est considéré sûr pour > 50 ans. Si nécessaire, re-chiffrement possible. |
