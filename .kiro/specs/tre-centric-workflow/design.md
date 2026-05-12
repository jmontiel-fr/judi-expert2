# Design Document — Workflow TRE-Centré

## Introduction

Ce document décrit la conception technique pour la refonte du workflow d'expertise centré sur le TRE (Template de Rapport d'Expertise). Le TRE devient le document pivot du workflow : il contient à la fois le modèle du rapport final et les méta-instructions (placeholders et annotations) qui pilotent la génération du PE, du PRE et du DAC.

## Architecture actuelle (résumé)

### Composants impactés

| Composant | Fichier | Rôle actuel |
|-----------|---------|-------------|
| Workflow Engine | `services/workflow_engine.py` | Transitions de statut (inchangé) |
| Steps Router | `routers/steps.py` | Logique métier des 5 steps |
| LLM Service | `services/llm_service.py` | Appels Ollama (prompts spécialisés) |
| RAG Service | `services/rag_service.py` | Recherche vectorielle corpus/config |
| File Paths | `services/file_paths.py` | Gestion des chemins disque |
| Docs | `docs/glossaire-workflow.md`, `docs/methodologie.md` | Documentation |

### Problèmes identifiés dans l'implémentation actuelle

1. **TRE chargé depuis le RAG** (recherche textuelle "template rapport") — fragile et non déterministe
2. **Parsing des annotations PEA** fait sur les bytes bruts du .docx (pas de parsing Word réel) — ne fonctionne pas correctement
3. **Pas de validation structurelle du TRE** avant utilisation
4. **Step 2 ne connaît pas le TRE** — le PE est généré par le LLM sans lien avec le template
5. **Step 5 ne génère pas de timbre.txt** avec les métadonnées d'expertise

---

## Design proposé

### Vue d'ensemble du nouveau flux

```
TRE (.docx)
    │
    ├── Validation structurelle (annotations + placeholders)
    │
    ├── Step 1 : PDF → OCR → demande.md + placeholders.csv
    │
    ├── Step 2 : TRE[@debut_tpe@ → fin] + questions → PE (.docx)
    │
    ├── Step E/A : Expert annote PE → PEA (.docx)
    │
    ├── Step 3 : (inchangé, optionnel)
    │
    ├── Step 4 : TRE[début → @debut_tpe@] + PEA annoté → PRE + DAC
    │
    └── Step 5 : PRE → Service Révision → REF → ZIP + timbre.txt
```

---

## Composant 1 : `services/tre_parser.py` (nouveau)

### Responsabilité

Parser et valider un document TRE (.docx). Extraire les méta-instructions (placeholders et annotations). Fournir les méthodes d'extraction du PE et de reconstitution du rapport.

### Interface

```python
@dataclass
class Placeholder:
    name: str          # ex: "nom_expert", "question_1"
    position: int      # index du paragraphe dans le docx

@dataclass
class Annotation:
    type: str          # "dires", "analyse", "verbatim", "question", "reference", "cite", "debut_tpe"
    suffix: str        # ex: "fratrie", "2.1.3", "" (pour debut_tpe)
    content: str       # contenu entre @...@
    position: int      # index du paragraphe
    is_custom: bool    # True si @/mon_annotation

@dataclass
class TREParseResult:
    placeholders: list[Placeholder]
    annotations: list[Annotation]
    debut_tpe_position: int | None  # index du paragraphe @debut_tpe@
    errors: list[str]               # erreurs de validation

class TREParser:
    """Parser de documents TRE (.docx)."""

    def parse(self, docx_path: str) -> TREParseResult:
        """Parse le TRE et extrait toutes les méta-instructions."""

    def validate(self, result: TREParseResult) -> list[str]:
        """Valide la structure du TRE. Retourne la liste des erreurs."""

    def extract_pe(self, docx_path: str, questions: dict[str, str]) -> bytes:
        """Extrait le PE depuis @debut_tpe@ jusqu'à la fin.
        
        Ajoute les questions en section conclusion.
        Retourne le contenu .docx du PE.
        """

    def extract_header(self, docx_path: str) -> bytes:
        """Extrait la partie du TRE avant @debut_tpe@.
        
        Retourne le contenu .docx de l'en-tête.
        """
```

### Règles de parsing

| Pattern | Type | Exemple |
|---------|------|---------|
| `<<nom>>` | Placeholder | `<<tribunal>>`, `<<question_1>>` |
| `@type contenu@` | Annotation prédéfinie | `@dires père agressif@` |
| `@/custom contenu@` | Annotation personnalisée | `@/observation agité@` |
| `@debut_tpe@` | Marqueur structurel | (sans contenu) |
| `@verbatim texte@` | Verbatim (pas de reformulation) | `@verbatim "sale morveuse"@` |
| `@question n@` | Référence question | `@question 3@` |
| `@reference @dires_x.y.z@` | Référence section | `@reference @dires_2.1.3@` |
| `@cite @dires_x.y.z@` | Citation section | `@cite @dires_2.1.3@` |

### Parsing Word (.docx)

Utiliser `python-docx` pour itérer sur les paragraphes du document. Les annotations peuvent s'étendre sur plusieurs paragraphes — le parser doit gérer les annotations multi-paragraphes (ouverture `@type` dans un paragraphe, fermeture `@` dans un autre).

```python
# Regex pour détecter le début d'une annotation
ANNOTATION_OPEN = re.compile(r"@(/?\w+)\s")
# Regex pour détecter la fin d'une annotation
ANNOTATION_CLOSE = re.compile(r"\s*@\s*$")
# Regex pour les placeholders
PLACEHOLDER = re.compile(r"<<(\w+)>>")
# Regex pour @debut_tpe@ (marqueur seul)
DEBUT_TPE = re.compile(r"^@debut_tpe@$")
```

---

## Composant 2 : `services/annotation_formatter.py` (nouveau)

### Responsabilité

Formater les annotations extraites du PEA en texte rédigé pour le PRE. Gérer les @reference et @cite.

### Interface

```python
@dataclass
class SectionIndex:
    """Index d'une section du rapport avec son numéro et titre."""
    number: str       # "2.1.3"
    title: str        # "biographie/education/primaire"
    content: str      # contenu textuel de la section

class AnnotationFormatter:
    """Formate les annotations PEA en texte pour le PRE."""

    def format_dires(self, content: str) -> str:
        """Formate @dires → 'Dires : contenu reformulé'"""

    def format_analyse(self, content: str) -> str:
        """Formate @analyse → 'Analyse : contenu reformulé'"""

    def format_verbatim(self, content: str) -> str:
        """Formate @verbatim → '"contenu"' (sans modification)"""

    def format_custom(self, annotation_name: str, content: str) -> str:
        """Formate @/custom → 'Custom : contenu'"""

    def resolve_reference(self, ref: str, sections: dict[str, SectionIndex]) -> str:
        """Résout @reference @dires_x.y.z@ → 'cf section X.Y.Z - titre'"""

    def resolve_cite(self, ref: str, sections: dict[str, SectionIndex]) -> str:
        """Résout @cite @dires_x.y.z@ → 'citation section X.Y.Z - titre ... texte'"""
```

### Règles de formatage

| Annotation | Sortie PRE |
|-----------|-----------|
| `@dires contenu@` | `Dires : <contenu reformulé par LLM>` |
| `@analyse contenu@` | `Analyse : <contenu reformulé par LLM>` |
| `@verbatim texte@` | `"texte"` (inchangé) |
| `@/mon_annot contenu@` | `Mon Annot : <contenu reformulé>` |
| `@reference @dires_2.1.3@` | `cf section 2.1.3 - biographie/education/primaire` |
| `@cite @dires_2.1.3@` | `citation section 2.1.3 - biographie/education/primaire "texte de la section"` |

---

## Composant 3 : Modifications de `routers/steps.py`

### Step 1 — Modifications mineures

- Renommer la sortie `ordonnance.md` → `demande.md` (fichier banalisé)
- Ajouter les questions extraites dans `placeholders.csv` comme `question_1;texte question 1`
- Conserver le reste du flux (OCR → LLM structuration → LLM extraction)

### Step 2 — Refonte complète

**Ancien flux** : RAG(TPE) + RAG(corpus) + ordonnance.md → LLM → pe.md/pe.docx

**Nouveau flux** :
1. Charger le TRE depuis le disque (pas le RAG) : `step2/in/tre.docx` ou TRE par défaut du domaine
2. Parser le TRE avec `TREParser`
3. Extraire le PE : portion `@debut_tpe@` → fin du document
4. Charger `placeholders.csv` du Step 1
5. Injecter les questions (`question_1` à `question_n`) en section conclusion du PE
6. Substituer les `@question n@` par le texte des questions
7. Sauvegarder le PE en `.docx`
8. Valider : vérifier que le PE contient des annotations et les questions en conclusion

**Entrées** : `step2/in/tre.docx` (ou TRE par défaut), `step1/out/placeholders.csv`
**Sorties** : `step2/out/pe.docx`

### Step 3 — Inchangé

Consolidation documentaire optionnelle (skip pour psychologie).

### Step 4 — Refonte majeure

**Ancien flux** : PEA bytes → regex annotations → RAG(TRE) → substitution → LLM PRE → LLM DAC

**Nouveau flux** :
1. Charger le PEA (`step4/in/pea.docx`) avec `python-docx`
2. Parser les annotations du PEA avec `TREParser` (même logique de parsing)
3. Charger le TRE original (`step2/in/tre.docx`)
4. Extraire l'en-tête du TRE (avant `@debut_tpe@`)
5. Reconstituer le document complet : en-tête + PEA
6. Charger `placeholders.csv` du Step 1
7. Substituer tous les `<<placeholder>>` par leurs valeurs
8. Pour chaque annotation `@dires` et `@analyse` : appeler LLM pour reformuler le texte abrégé
9. Résoudre les `@reference` et `@cite` avec l'index des sections
10. Préserver les `@verbatim` entre guillemets sans modification
11. Générer le PRE (.docx)
12. Générer le DAC (.docx) via LLM (analyse contradictoire du PRE)

**Entrées** : `step4/in/pea.docx`, `step2/in/tre.docx`, `step1/out/placeholders.csv`
**Sorties** : `step4/out/pre.docx`, `step4/out/dac.docx`

### Step 5 — Ajout service révision + timbre

**Ancien flux** : Upload projet_final → ZIP → SHA-256

**Nouveau flux** :
1. Charger le PRE ajusté par l'expert (REF candidat)
2. Appeler le Service Révision (LLM) : correction linguistique en mode "track changes"
3. Préserver les verbatim (textes entre guillemets) intacts
4. Présenter les corrections à l'expert pour validation
5. Générer `<nom-dossier>.zip` : tous les fichiers de `c:\judi-expert\<nom-dossier>` sauf `archive\`
6. Générer `<nom-dossier>-timbre.txt` avec :
   - Contexte expertise : demandeur_nom, demandeur_prenom, demandeur_adresse, demande_date, tribunal_nom, tribunal_adresse, demande_reference, mec_nom, mec_prenom, mec_adresse, expert_nom, expert_prenom, expert_adresse
   - Nom du fichier .zip
   - Log d'archive (date, hash SHA-256)
7. Placer zip et timbre dans `c:\judi-expert\<nom-dossier>\archive\`

---

## Composant 4 : `services/revision_service.py` (nouveau)

### Responsabilité

Correction linguistique du PRE pour produire le REF. Préserve les verbatim.

### Interface

```python
@dataclass
class RevisionResult:
    corrected_text: str
    corrections: list[dict]  # [{"original": ..., "corrected": ..., "position": ...}]

class RevisionService:
    """Service de révision linguistique via LLM."""

    async def revise(self, text: str) -> RevisionResult:
        """Corrige le texte en préservant les verbatim (entre guillemets).
        
        Retourne le texte corrigé et la liste des corrections appliquées.
        """
```

### Stratégie de préservation des verbatim

1. Identifier tous les textes entre guillemets (`"..."`)
2. Les remplacer par des tokens uniques (`__VERBATIM_001__`)
3. Envoyer le texte au LLM pour correction
4. Restaurer les verbatim originaux à la place des tokens

---

## Composant 5 : Stockage du TRE

### Problème actuel

Le TRE est stocké dans le RAG (base vectorielle Qdrant) et récupéré par recherche textuelle. C'est non déterministe et fragile.

### Solution

Le TRE est un fichier `.docx` stocké sur disque :
- **TRE par défaut** : `corpus/{domaine}/tre.docx` (fourni avec le corpus du domaine)
- **TRE personnalisé** : uploadé par l'expert dans la configuration locale, stocké dans `data/config/tre.docx`
- **TRE par dossier** : copié dans `step2/in/tre.docx` au début du Step 2 (permet de figer la version utilisée)

Priorité de résolution :
1. `step2/in/tre.docx` (si déjà copié pour ce dossier)
2. `data/config/tre.docx` (TRE personnalisé de l'expert)
3. `corpus/{domaine}/tre.docx` (TRE par défaut du domaine)

---

## Composant 6 : Modifications de `services/llm_service.py`

### Nouveaux prompts système

```python
PROMPT_REFORMULATION_DIRES: str = (
    "Tu reçois des notes télégraphiques prises par un expert judiciaire "
    "pendant un entretien. Reformule ces notes en texte rédigé professionnel "
    "à la troisième personne, en conservant fidèlement le sens et les faits. "
    "Ne modifie pas les citations entre guillemets."
)

PROMPT_REFORMULATION_ANALYSE: str = (
    "Tu reçois des notes d'analyse d'un expert judiciaire en psychologie. "
    "Reformule ces notes en texte rédigé professionnel, en conservant "
    "la terminologie clinique et les observations factuelles."
)

PROMPT_REVISION: str = (
    "Tu es un correcteur linguistique spécialisé en français juridique. "
    "Corrige les fautes d'orthographe, de grammaire et de syntaxe. "
    "Ne modifie PAS le contenu sémantique ni les textes entre guillemets. "
    "Retourne le texte corrigé."
)
```

### Nouvelles méthodes

```python
async def reformuler_dires(self, texte_abrege: str) -> str:
    """Reformule des notes @dires en texte rédigé."""

async def reformuler_analyse(self, texte_abrege: str) -> str:
    """Reformule des notes @analyse en texte rédigé."""

async def reviser_texte(self, texte: str) -> str:
    """Corrige le texte en préservant les verbatim."""
```

---

## Composant 7 : Documentation

### `docs/glossaire-workflow.md`

Réécriture de la section 1 (Workflow fonctionnel) pour refléter le flux TRE-centré :
- Le TRE est le document central
- Step 2 extrait le PE depuis le TRE (pas de génération LLM)
- Step 4 reconstitue le rapport à partir du TRE + PEA
- Step 5 inclut le service révision et le timbre

Ajout dans le glossaire :
- **MEC** : Mis(e) En Cause — personne évaluée en expertise psychologique

### `docs/methodologie.md`

Mise à jour de la section 2 (Workflow d'expertise assisté par l'IA) :
- Step 2 : extraction mécanique du PE depuis le TRE (pas de génération LLM)
- Step 4 : reformulation LLM des annotations (pas de génération libre)
- Step 5 : ajout du service révision

---

## Diagramme de séquence — Step 4

```
Expert          API (steps.py)       TREParser       AnnotFormatter    LLM
  │                  │                   │                │              │
  │─── upload PEA ──►│                   │                │              │
  │                  │                   │                │              │
  │─── execute ─────►│                   │                │              │
  │                  │── parse PEA ─────►│                │              │
  │                  │◄── annotations ───│                │              │
  │                  │                   │                │              │
  │                  │── extract_header ─►│                │              │
  │                  │◄── header docx ───│                │              │
  │                  │                   │                │              │
  │                  │── load placeholders.csv            │              │
  │                  │                   │                │              │
  │                  │── format @dires ──────────────────►│              │
  │                  │                   │                │── reformuler►│
  │                  │                   │                │◄── texte ────│
  │                  │◄── formatted ─────────────────────│              │
  │                  │                   │                │              │
  │                  │── resolve @ref ───────────────────►│              │
  │                  │◄── "cf section..." ───────────────│              │
  │                  │                   │                │              │
  │                  │── substitute <<placeholders>>      │              │
  │                  │                   │                │              │
  │                  │── assemble PRE ───►│                │              │
  │                  │                   │                │              │
  │                  │── generer_dac ────────────────────────────────────►│
  │                  │◄── dac content ──────────────────────────────────│
  │                  │                   │                │              │
  │◄── pre.docx + dac.docx ─────────────│                │              │
```

---

## Migration et compatibilité

### Stratégie

1. **Ajout des nouveaux services** (`tre_parser.py`, `annotation_formatter.py`, `revision_service.py`) sans casser l'existant
2. **Refactoring progressif** des steps dans `routers/steps.py` — un step à la fois
3. **Feature flag** optionnel : `USE_TRE_CENTRIC_WORKFLOW=true` pour basculer (si nécessaire pendant la transition)
4. **Tests** : ajouter des tests unitaires pour le parser et le formatter avant de modifier les steps

### Fichiers à créer

| Fichier | Description |
|---------|-------------|
| `services/tre_parser.py` | Parser et validateur de TRE |
| `services/annotation_formatter.py` | Formatage des annotations pour le PRE |
| `services/revision_service.py` | Service de révision linguistique |

### Fichiers à modifier

| Fichier | Modifications |
|---------|--------------|
| `routers/steps.py` | Refonte Step 2, Step 4, Step 5 |
| `services/llm_service.py` | Ajout prompts reformulation + révision |
| `services/file_paths.py` | Ajout `archive_dir()`, `tre_path()` |
| `docs/glossaire-workflow.md` | Réécriture workflow TRE-centré |
| `docs/methodologie.md` | Mise à jour méthodologie |

### Dépendances Python (déjà présentes)

- `python-docx` : parsing et génération .docx
- `docxtpl` : substitution de placeholders dans les templates .docx (à utiliser au lieu de string replace)

---

## Considérations de performance

- **Reformulation LLM par annotation** : chaque `@dires` et `@analyse` nécessite un appel LLM. Pour un PEA typique (20-30 annotations), cela représente 20-30 appels séquentiels. Optimisation possible : batching des annotations courtes en un seul appel.
- **Taille du contexte** : le TRE complet peut être volumineux (50+ pages). Le `compute_num_ctx` dynamique existant gère déjà ce cas.
- **Step 5 révision** : un seul appel LLM sur le PRE complet. Peut nécessiter un `num_ctx` élevé.
