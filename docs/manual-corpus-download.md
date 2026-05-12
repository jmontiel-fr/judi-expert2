# Corpus — Guide de téléchargement manuel

Ce document explique comment alimenter le corpus de chaque domaine en documents PDF et en contenu textuel pour le RAG.

---

## Principe général

Le corpus est composé de 3 types de ressources :

| Type | Source | Traitement |
|------|--------|-----------|
| **Templates** (TPE, TRE) | Fichiers `.tpl` / `.docx` dans le repo | Automatique (montés dans le conteneur) |
| **Documents PDF** | Fichiers dans `corpus/{domaine}/documents/` | **Manuel** — upload par l'admin |
| **URLs de référence** | Listées dans `corpus/{domaine}/urls/urls.yaml` | Crawl automatique |

### Philosophie

- Les URLs dans `urls.yaml` doivent être **crawlables automatiquement**. Si un site bloque les robots (403), son contenu doit être traité comme un document à uploader manuellement (PDF ou `.txt`).
- Les URLs Cairn.info ont été retirées (contenu payant, résumés non exploitables pour le RAG).
- Les textes Légifrance (bloqués en 403) doivent être uploadés manuellement comme documents texte.

---

## Procédure d'upload des documents (Admin — Site Central)

### Option A — Via l'interface admin (dynamique)

1. Se connecter à l'admin du Site Central (`/admin`, onglet **Corpus**)
2. Sélectionner le domaine (ex: `psychologie`)
3. Cliquer **"Uploader un PDF"** ou **"📁 Uploader plusieurs PDFs"**
4. Sélectionner le(s) fichier(s) (PDF, `.txt` ou `.md`)
5. Le fichier est stocké dans `corpus/{domaine}/documents/` et `contenu.yaml` est mis à jour
6. L'indicateur passe de ⚠ à ✔ dans la liste

> **Important** : le nom du fichier uploadé doit correspondre exactement au nom dans `contenu.yaml` (sans le préfixe `documents/`).

---

### Option B — Directement dans le repo (recommandé pour le setup initial)

1. Placer les fichiers dans `corpus/{domaine}/documents/` avec les noms exacts du `contenu.yaml`
2. Commit et redéployer le Site Central

Les fichiers seront automatiquement détectés comme "présents sur disque" (indicateur ✔) sans aucune action dans l'interface.

```
corpus/psychologie/documents/
├── guide_methodologique_expertise_psychologique_penale.pdf
├── code_deontologie_psychologues.pdf
├── referentiel_has_evaluation_psychologique.pdf
├── textes_reglementaires_expertise_judiciaire.pdf
└── guide_bonnes_pratiques_expertise_personnalite.pdf
```

> **Quand utiliser quelle option ?**
> - **Option B** (repo) : pour le setup initial ou quand on prépare le corpus en amont du déploiement
> - **Option A** (interface) : pour ajouter un document après déploiement sans redéployer

---

## Procédure pour le contenu Légifrance (non crawlable)

Légifrance bloque les robots (protection Cloudflare). Pour intégrer ces textes de loi dans le RAG :

### Constitution des fichiers `.txt`

1. Ouvrir l'URL dans un navigateur
2. Sélectionner et copier le texte des articles pertinents (copier-coller brut, sans réécriture)
3. Coller dans un fichier `.txt` nommé clairement (voir tableau ci-dessous)
4. Pas besoin de reformater : le texte brut tel que copié depuis Légifrance est suffisant pour le RAG

### Où placer les fichiers

**Option A — Dans le repo (recommandé)** : placer les `.txt` dans `corpus/{domaine}/documents/` puis commit et redéployer.

```
corpus/psychologie/documents/
├── legifrance_cpp_art156-169_expertise.txt
├── legifrance_decret_2004_experts_judiciaires.txt
├── legifrance_cpc_art232-284_mesures_instruction.txt
└── legifrance_loi_1985_titre_psychologue.txt
```

**Option B — Via l'interface** : uploader via l'admin (bouton "Uploader un PDF" accepte aussi `.txt`).

### Exemple de contenu d'un fichier `.txt`

```
Article 156
Toute juridiction d'instruction ou de jugement, dans le cas où se pose
une question d'ordre technique, peut, soit à la demande du ministère
public, soit d'office, ou à la demande des parties, ordonner une expertise.
[...]

Article 157
Les experts sont choisis parmi les personnes physiques ou morales qui
figurent sur la liste nationale dressée par la Cour de cassation ou sur
une des listes dressées par les cours d'appel [...]
```

> **Note** : c'est l'administrateur du Site Central qui prépare ces fichiers une seule fois. Les experts n'ont pas à le faire — ils reçoivent le contenu automatiquement via "Télécharger le corpus".

> Les URLs Légifrance restent dans `urls.yaml` comme **liens de consultation** pour l'expert (il peut les ouvrir dans son navigateur), mais leur contenu n'est pas indexé automatiquement dans le RAG.

---

## Domaine : Psychologie

---

### Templates — Automatiques ✔

| Fichier | Statut |
|---------|--------|
| `TPE_psychologie.tpl` | ✔ Présent dans le repo |
| `template_rapport_psychologie.docx` | ✔ Présent dans le repo |

---

### Documents à constituer manuellement (copier-coller `.txt`)

Les contenus ci-dessous proviennent de sites qui bloquent le crawl automatique (Légifrance).
L'admin copie-colle le texte brut depuis le navigateur et place les fichiers dans `corpus/psychologie/documents/`.

#### Présent dans le repo ✔

| Fichier | Source | Contenu |
|---------|--------|---------|
| `apa_apls_specialty_guidelines_forensic_psychology_2013.txt` | [ap-ls.org](https://ap-ls.org/resources/guidelines/) | Référentiel international de bonnes pratiques pour la psychologie légale (APA/AP-LS, 2013). Méthodologie d'évaluation, impartialité, assessment. En anglais. |

---

#### Essentiels ⚠

| Fichier à créer | Source | Contenu |
|-----------------|--------|---------|
| `legifrance_cpp_art156-169_expertise.txt` | [Légifrance — CPP art. 156-169](https://www.legifrance.gouv.fr/codes/section_lc/LEGITEXT000006071154/LEGISCTA000006167469) | Cadre légal de l'expertise judiciaire (désignation, mission, obligations) |
| `legifrance_decret_2004_experts_judiciaires.txt` | [Légifrance — Décret 2004-1463](https://www.legifrance.gouv.fr/loda/id/JORFTEXT000000464648) | Conditions d'inscription sur les listes d'experts |

---

#### Optionnels (enrichissement)

| Fichier à créer | Source | Contenu |
|-----------------|--------|---------|
| `legifrance_cpc_art232-284_mesures_instruction.txt` | [Légifrance — CPC art. 232-284](https://www.legifrance.gouv.fr/codes/section_lc/LEGITEXT000006070716/LEGISCTA000006149642) | Mesures d'instruction en procédure civile |
| `legifrance_loi_1985_titre_psychologue.txt` | [Légifrance — Loi 85-772](https://www.legifrance.gouv.fr/loda/id/JORFTEXT000000521846) | Protection du titre de psychologue |

---

### URLs de référence — Crawl automatique ✔

Ces URLs sont crawlées automatiquement par le Site Central. Leur contenu textuel est extrait et distribué aux sites locaux. Aucune action manuelle requise.

| URL | Statut |
|-----|--------|
| Service-Public.fr — Experts judiciaires | ✔ Crawlé |
| HAS — Recommandations | ✔ Crawlé |
| CNCDP (Code de déontologie) | ✔ Crawlé |
| FFPP (Fédération Française des Psychologues) | ✔ Crawlé |
| SFP (Société Française de Psychologie) | ✔ Crawlé |
| HAL — Archives ouvertes | ✔ Crawlé |
| Persée — Revues en psychologie | ✔ Crawlé |
| OpenEdition — Revues sciences humaines | ✔ Crawlé |

> **Note** : le contenu du code de déontologie (CNCDP) et des recommandations HAS/SFP est déjà récupéré via le crawl de ces URLs. Il n'est pas nécessaire de les dupliquer en PDF.

---

### Résumé du domaine psychologie

| Catégorie | Auto | Dans le repo | Manuel |
|-----------|------|-------------|--------|
| Templates (TPE, TRE) | 2/2 ✔ | — | — |
| URLs crawlées | 9/9 ✔ | — | — |
| Référentiel APA (psycho légale) | — | 1/1 ✔ | — |
| Documents Légifrance `.txt` | — | — | 2 essentiels + 2 optionnels |

---

## Autres domaines

Les domaines `psychiatrie`, `medecine_legale`, `batiment` et `comptabilite` sont marqués **inactifs** dans `domaines.yaml`. Leur corpus sera à constituer selon le même modèle quand ils seront activés.

---

## Après l'upload

Une fois les documents uploadés sur le Site Central :

1. **Site Central** : vérifier les indicateurs ✔ dans l'onglet Corpus
2. **Site Local** : dans la page Configuration, cliquer **"⬇ Télécharger le corpus"** pour récupérer les PDFs et contenus pré-crawlés
3. **Site Local** : cliquer **"🧠 Build RAG"** pour indexer le tout dans la base vectorielle

Le Build RAG indexera :
- Les documents PDF téléchargés depuis le Site Central
- Les contenus textuels pré-crawlés des URLs
- Les documents custom ajoutés localement par l'expert
