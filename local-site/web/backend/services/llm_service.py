"""
Judi-Expert — Service LLM (client Ollama)

Client asynchrone pour l'API Ollama hébergeant Mistral 7B Instruct v0.3.
Fournit les méthodes de haut niveau pour chaque étape du workflow d'expertise
et les prompts système spécialisés pour le domaine judiciaire (psychologie).

Valide : Exigences 6.4, 7.2, 9.2, 9.3, 11.2
"""

import json
import os
import logging
import threading
from dataclasses import dataclass

import httpx

from services.hardware_service import HardwareInfo, PerformanceProfile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (variables d'environnement avec valeurs par défaut)
# ---------------------------------------------------------------------------

OLLAMA_URL: str = os.environ.get("OLLAMA_URL", "http://judi-llm:11434")

# Timeout élevé : l'inférence locale sur CPU peut être lente
LLM_TIMEOUT: float = float(os.environ.get("LLM_TIMEOUT", "1800"))

# ---------------------------------------------------------------------------
# Estimation de tokens et contexte dynamique
# ---------------------------------------------------------------------------
# Ratio moyen caractères → tokens pour du texte français
CHARS_PER_TOKEN: float = 3.5
# Marge de sécurité pour le contexte (prompt système + overhead)
CTX_OVERHEAD_TOKENS: int = 512
# Taille minimale de contexte
CTX_MIN: int = 4096
# Alignement du contexte (arrondi au multiple supérieur)
CTX_ALIGN: int = 2048


def estimate_tokens(text: str) -> int:
    """Estime le nombre de tokens pour un texte français."""
    return max(1, int(len(text) / CHARS_PER_TOKEN))


def compute_num_ctx(input_text: str, system_prompt: str = "", output_ratio: float = 1.0) -> int:
    """Calcule dynamiquement num_ctx en fonction de la taille de l'input.

    Args:
        input_text: Texte envoyé au LLM (contenu user).
        system_prompt: Prompt système.
        output_ratio: Ratio output/input estimé (1.0 = output ≈ input).

    Returns:
        num_ctx arrondi au multiple de CTX_ALIGN supérieur, avec 20% de marge.
    """
    input_tokens = estimate_tokens(input_text)
    prompt_tokens = estimate_tokens(system_prompt)
    output_tokens = max(int(input_tokens * output_ratio), 512)
    total = input_tokens + prompt_tokens + output_tokens + CTX_OVERHEAD_TOKENS

    # Ajouter 20% de marge de sécurité
    total = int(total * 1.2)

    # Arrondir au multiple de CTX_ALIGN supérieur
    aligned = ((total + CTX_ALIGN - 1) // CTX_ALIGN) * CTX_ALIGN
    # Hot-reload: read CTX_MAX from ActiveProfile on each call
    ctx_max = ActiveProfile.get_ctx_max()
    return max(CTX_MIN, min(aligned, ctx_max))


def estimate_duration_seconds(num_ctx: int, output_ratio: float = 0.5) -> int:
    """Estime la durée de génération en secondes.

    Args:
        num_ctx: Taille du contexte alloué.
        output_ratio: Part du contexte utilisée pour la génération.

    Returns:
        Durée estimée en secondes (arrondie).
    """
    output_tokens = int(num_ctx * output_ratio)
    # Hot-reload: read tokens_per_sec from ActiveProfile on each call
    tokens_per_sec = ActiveProfile.get_tokens_per_sec()
    return max(5, int(output_tokens / tokens_per_sec))

# ---------------------------------------------------------------------------
# Prompts système
# ---------------------------------------------------------------------------

PROMPT_STRUCTURATION_MD: str = (
    "Tu es un assistant spécialisé dans l'analyse de documents judiciaires français. "
    "Tu reçois le texte brut extrait par OCR d'une réquisition judiciaire (ordonnance de "
    "commission d'expert ou jugement avant dire droit).\n\n"
    "Ta tâche est de structurer ce texte en Markdown propre et lisible en respectant "
    "les consignes suivantes :\n"
    "1. Identifie et extrais les **Questions du Tribunal (QT)** — ce sont les missions "
    "confiées à l'expert. Présente-les dans une section dédiée « ## Questions du Tribunal » "
    "sous forme de liste numérotée.\n"
    "2. Identifie le **destinataire** de la réquisition (nom de l'expert, adresse, "
    "juridiction émettrice). Place ces informations dans une section « ## Destinataire ».\n"
    "3. Identifie les **parties** (demandeur, défendeur, mis en cause) et place-les dans "
    "une section « ## Parties ».\n"
    "4. Structure le reste du document en sections Markdown logiques avec des titres "
    "appropriés (## pour les sections principales, ### pour les sous-sections).\n"
    "5. Corrige les erreurs évidentes d'OCR (caractères mal reconnus, mots coupés) tout "
    "en préservant fidèlement le contenu juridique.\n"
    "6. Conserve les dates, numéros de dossier, références juridiques et montants exacts "
    "tels quels.\n"
    "7. Ne modifie pas le sens du texte. N'ajoute aucune information qui ne figure pas "
    "dans le texte original.\n\n"
    "Réponds uniquement avec le document Markdown structuré, sans commentaire ni explication."
)

PROMPT_EXTRACTION_QUESTIONS: str = (
    "Tu es un assistant juridique spécialisé dans l'analyse d'ordonnances judiciaires françaises.\n\n"
    "Tu reçois le texte structuré d'une ordonnance de commission d'expert (réquisition). "
    "Ta tâche est d'extraire UNIQUEMENT les questions d'expertise numérotées posées à l'expert.\n\n"
    "IMPORTANT — Distinction entre objet de mission et questions :\n"
    "- L'OBJET DE MISSION est le chapeau introductif (ex: « Réaliser une expertise psychologique sur... »). "
    "NE PAS l'inclure comme question.\n"
    "- Les QUESTIONS sont les points numérotés que l'expert doit traiter "
    "(ex: « 1. Relever les aspects de la personnalité... », « 2. Analyser les circonstances... »).\n\n"
    "Règles :\n"
    "1. Extrais UNIQUEMENT les questions numérotées (pas le chapeau introductif).\n"
    "2. Numérote-les Q1, Q2, Q3, etc. dans l'ordre où elles apparaissent.\n"
    "3. Conserve le texte exact de chaque question.\n"
    "4. Chaque point numéroté dans l'ordonnance = une question distincte.\n"
    "5. N'invente aucune question qui ne figure pas dans le texte.\n\n"
    "Format de sortie (Markdown) :\n"
    "```\n"
    "# Questions du Tribunal\n\n"
    "## Q1\n"
    "Texte de la première question\n\n"
    "## Q2\n"
    "Texte de la deuxième question\n"
    "```\n\n"
    "Réponds uniquement avec la liste des questions en Markdown, sans commentaire."
)

PROMPT_EXTRACTION_PLACEHOLDERS: str = (
    "Tu es un assistant juridique spécialisé dans l'analyse d'ordonnances judiciaires françaises.\n\n"
    "Tu reçois le texte structuré d'une ordonnance de commission d'expert. "
    "Ta tâche est d'extraire les informations factuelles pour remplir les champs d'un rapport d'expertise.\n\n"
    "Extrais les informations suivantes si elles sont présentes dans le texte. "
    "Si une information n'est pas trouvée, laisse la valeur vide.\n\n"
    "Format de sortie STRICT (CSV avec séparateur point-virgule, une ligne par champ) :\n"
    "```\n"
    "nom_placeholder;valeur\n"
    "nom_expert;...\n"
    "prenom_expert;...\n"
    "titre_expert;...\n"
    "date_mission;...\n"
    "tribunal;...\n"
    "reference_dossier;...\n"
    "nom_expertise;...\n"
    "nom_mec;...\n"
    "prenom_mec;...\n"
    "nom_requerant;...\n"
    "prenom_requerant;...\n"
    "titre_requerant;...\n"
    "objet_mission;...\n"
    "date_ordonnance;...\n"
    "juridiction;...\n"
    "ville_juridiction;...\n"
    "magistrat;...\n"
    "```\n\n"
    "Règles :\n"
    "1. Utilise EXACTEMENT les noms de champs ci-dessus (pas de modification).\n"
    "2. Les dates doivent être au format JJ/MM/AAAA.\n"
    "3. N'invente aucune information absente du texte — laisse le champ vide.\n"
    "4. La première ligne doit être l'en-tête : nom_placeholder;valeur\n\n"
    "Réponds UNIQUEMENT avec le CSV, sans commentaire ni bloc de code."
)

PROMPT_GENERATION_QMEC: str = (
    "Tu es un expert psychologue judiciaire expérimenté. Tu dois générer un plan "
    "d'entretien structuré (PE — Plan d'Entretien) à partir des "
    "éléments suivants :\n\n"
    "- Les **Questions du Tribunal (QT)** extraites de la réquisition judiciaire.\n"
    "- La **Trame de Plan d'Entretien (TPE)** fournie par l'expert, qui définit la "
    "structure et les sections de l'entretien.\n"
    "- Le **contexte RAG** issu du corpus du domaine (guides méthodologiques, "
    "référentiels de bonnes pratiques, textes réglementaires).\n\n"
    "Consignes :\n"
    "1. Reprends la structure de la TPE (sections, sous-sections) comme squelette du plan.\n"
    "2. Pour chaque section de la TPE, adapte et enrichis les questions en fonction des QT "
    "spécifiques de cette mission.\n"
    "3. Ajoute des questions complémentaires pertinentes issues du contexte RAG lorsque "
    "les QT le justifient (évaluation de dangerosité, accessibilité aux soins, etc.).\n"
    "4. Chaque question doit être formulée de manière ouverte, neutre et professionnelle.\n"
    "5. Indique pour chaque section l'objectif clinique visé.\n"
    "6. **Pour chaque section, prépare les emplacements d'annotation** que l'expert "
    "remplira lors de l'entretien. Utilise la syntaxe suivante :\n"
    "   - `@dires ... @` — pour les propos rapportés par l'interviewé\n"
    "   - `@analyse ... @` — pour les observations et interprétations de l'expert\n"
    "   - `@verbatim ... @` — pour les citations textuelles mot pour mot\n"
    "   Exemple dans une section :\n"
    "   ```\n"
    "   ### 3.1 Relation à la mère\n"
    "   Questions : ...\n"
    "   @dires @\n"
    "   @analyse @\n"
    "   ```\n"
    "7. Termine par une section « Conclusion » avec les questions du tribunal sous forme :\n"
    "   ```\n"
    "   @question 1 @\n"
    "   @reference section ... @\n"
    "   ```\n"
    "   pour chaque question QT, en indiquant les sections du plan dont les dires et "
    "analyses serviront à formuler la réponse.\n\n"
    "Réponds uniquement avec le plan d'entretien structuré en Markdown."
)

PROMPT_GENERATION_REF: str = (
    "Tu es un expert psychologue judiciaire expérimenté chargé de rédiger le Rapport "
    "d'Expertise Final (REF). Tu disposes des éléments suivants :\n\n"
    "- Le **Rapport d'Expertise Brut (REB)** rédigé par l'expert, contenant les réponses "
    "argumentées aux questions du tribunal.\n"
    "- Les **Questions du Tribunal (QT)** extraites de la réquisition.\n"
    "- Les **Notes d'Entretien (NE)** prises par l'expert lors de l'entretien.\n"
    "- Le **Template de Rapport** définissant la structure et la mise en forme attendues.\n\n"
    "Consignes :\n"
    "1. Respecte scrupuleusement la structure du Template de Rapport fourni.\n"
    "2. Intègre les informations du REB dans les sections correspondantes du template.\n"
    "3. Assure-toi que chaque Question du Tribunal (QT) reçoit une réponse argumentée, "
    "claire et étayée par les éléments cliniques des NE et du REB.\n"
    "4. Utilise un style rédactionnel professionnel, objectif et conforme aux normes de "
    "rédaction des rapports d'expertise judiciaire en psychologie.\n"
    "5. Les conclusions doivent être nuancées, fondées sur les données cliniques, et "
    "formulées avec la prudence déontologique requise.\n"
    "6. N'invente aucune donnée clinique. Utilise uniquement les informations fournies "
    "dans le REB et les NE.\n"
    "7. Remplis les champs de fusion du template (destinataire, QT, réponses, analyse, "
    "conclusions) avec les données appropriées.\n\n"
    "Réponds uniquement avec le contenu du rapport structuré selon le template."
)

PROMPT_GENERATION_RAUX_P1: str = (
    "Tu es un avocat spécialisé en droit de l'expertise judiciaire et en psychologie "
    "légale. Tu dois analyser le Rapport d'Expertise Final (REF) ci-dessous et identifier "
    "toutes les contestations possibles qu'un avocat de la partie adverse pourrait "
    "soulever.\n\n"
    "Tu disposes également du **corpus du domaine** (jurisprudence, guides méthodologiques, "
    "textes réglementaires) pour étayer ton analyse.\n\n"
    "Consignes :\n"
    "1. Examine chaque section du REF et identifie les points faibles, les affirmations "
    "insuffisamment étayées, les biais méthodologiques potentiels et les conclusions "
    "contestables.\n"
    "2. Pour chaque contestation identifiée, indique :\n"
    "   - La section du REF concernée\n"
    "   - La nature de la contestation (méthodologique, factuelle, déontologique, juridique)\n"
    "   - L'argumentation détaillée qu'un avocat pourrait développer\n"
    "   - Les références du corpus (jurisprudence, textes) qui appuient la contestation\n"
    "3. Évalue le niveau de risque de chaque contestation (élevé, moyen, faible).\n"
    "4. Sois exhaustif et rigoureux : un bon rapport d'expertise doit pouvoir résister "
    "à un examen contradictoire.\n\n"
    "Réponds uniquement avec l'analyse structurée des contestations en Markdown."
)

PROMPT_GENERATION_RAUX_P2: str = (
    "Tu es un expert psychologue judiciaire expérimenté. Tu as reçu une analyse des "
    "contestations possibles (Partie 1 du RAUX) concernant le Rapport d'Expertise "
    "Final (REF).\n\n"
    "Ta tâche est de produire une **version révisée du REF** qui prend en compte les "
    "contestations identifiées et renforce le rapport.\n\n"
    "Consignes :\n"
    "1. Pour chaque contestation de niveau « élevé » ou « moyen », apporte les "
    "modifications nécessaires au REF :\n"
    "   - Renforce l'argumentation avec des références méthodologiques ou scientifiques\n"
    "   - Nuance les conclusions si elles étaient trop catégoriques\n"
    "   - Ajoute les précautions déontologiques manquantes\n"
    "   - Corrige les éventuels biais méthodologiques identifiés\n"
    "2. Pour les contestations de niveau « faible », indique en note pourquoi elles ne "
    "nécessitent pas de modification.\n"
    "3. Conserve la structure du REF original.\n"
    "4. Marque clairement les passages modifiés avec la mention « [RÉVISÉ] » en début "
    "de paragraphe.\n"
    "5. Ajoute une section finale « Réponse aux contestations » résumant les "
    "améliorations apportées.\n\n"
    "Réponds uniquement avec le REF révisé en Markdown."
)

PROMPT_GENERATION_RE_PROJET: str = (
    "Tu es un expert psychologue judiciaire expérimenté chargé de rédiger le RE-Projet "
    "(Rapport d'Expertise Projet). Tu disposes des éléments suivants :\n\n"
    "- Les **Informations factuelles** extraites de l'ordonnance (nom de l'expert, "
    "juridiction, référence dossier, parties, dates, etc.).\n"
    "- Le **NEA** (Notes d'Entretien et Analyse) rédigé par l'expert.\n"
    "- La **Réquisition** structurée en Markdown (questions du tribunal, parties, contexte).\n"
    "- Le **Template de Rapport** définissant la structure et la mise en forme attendues.\n\n"
    "Consignes :\n"
    "1. Respecte scrupuleusement la structure du Template de Rapport fourni — "
    "reproduis TOUTES les sections dans l'ordre exact du template.\n"
    "2. Remplace TOUS les placeholders restants ({{...}}) par les valeurs concrètes "
    "fournies dans les « Informations factuelles ». Si un placeholder n'a pas de "
    "valeur correspondante, laisse la mention « [À compléter] ».\n"
    "3. Intègre les informations du NEA dans les sections correspondantes du template "
    "(anamnèse, examen clinique, tests, analyse, réponses aux questions).\n"
    "4. Assure-toi que chaque Question du Tribunal reçoit une réponse argumentée, "
    "claire et étayée par les éléments cliniques du NEA.\n"
    "5. Utilise un style rédactionnel professionnel, objectif et conforme aux normes de "
    "rédaction des rapports d'expertise judiciaire en psychologie.\n"
    "6. Les conclusions doivent être nuancées, fondées sur les données cliniques, et "
    "formulées avec la prudence déontologique requise.\n"
    "7. N'invente aucune donnée clinique. Utilise uniquement les informations fournies "
    "dans le NEA.\n\n"
    "Réponds uniquement avec le contenu du rapport structuré selon le template."
)

PROMPT_GENERATION_RE_PROJET_AUXILIAIRE: str = (
    "Tu es un contre-expert en psychologie judiciaire, spécialisé dans l'analyse "
    "contradictoire de rapports d'expertise psychologique. Tu dois analyser le "
    "RE-Projet (Rapport d'Expertise Projet) ci-dessous et produire un document "
    "auxiliaire d'analyse contradictoire.\n\n"
    "Tu disposes également du **NEA** (Notes d'Entretien et Analyse) de l'expert.\n\n"
    "## CADRE D'ANALYSE CONTRADICTOIRE EN PSYCHOLOGIE LÉGALE\n\n"
    "### A. Biais méthodologiques à rechercher\n"
    "- **Biais de confirmation** : l'expert a-t-il cherché uniquement les éléments "
    "confirmant son hypothèse initiale ? A-t-il testé des hypothèses rivales ?\n"
    "- **Biais d'ancrage** : les conclusions sont-elles influencées par les premières "
    "informations reçues (ex: motif de saisine, antécédents communiqués) ?\n"
    "- **Effet de halo** : une caractéristique saillante du sujet (apparence, "
    "éloquence, coopération) a-t-elle pu influencer l'évaluation globale ?\n"
    "- **Biais rétrospectif** : l'expert raisonne-t-il « après coup » en considérant "
    "un événement comme prévisible alors qu'il ne l'était pas ?\n"
    "- **Biais de l'évaluateur unique** : absence de double évaluation ou de "
    "supervision par un pair.\n\n"
    "### B. Validité des tests psychométriques\n"
    "- Le test utilisé est-il **validé scientifiquement** pour la population évaluée "
    "(âge, culture, langue) ?\n"
    "- Le test est-il **approprié au contexte forensique** (vs. contexte clinique "
    "thérapeutique) ? Les normes utilisées sont-elles adaptées ?\n"
    "- Les **conditions de passation** étaient-elles conformes (durée, environnement, "
    "état du sujet) ?\n"
    "- L'expert a-t-il pris en compte les **indices de validité** du protocole "
    "(échelles de mensonge, incohérence, simulation, dissimulation) ?\n"
    "- Les résultats sont-ils **interprétés dans leur contexte** ou de manière "
    "isolée et catégorique ?\n"
    "- Tests courants à évaluer : MMPI-2/MMPI-3, Rorschach (système Exner/R-PAS), "
    "WAIS-IV, TAT, PCL-R, HCR-20, MCMI-IV.\n\n"
    "### C. Qualité du raisonnement clinique\n"
    "- Les **données cliniques** (entretien, observation, anamnèse) sont-elles "
    "suffisantes et correctement rapportées ?\n"
    "- Le lien entre **données observées** et **conclusions** est-il explicite et "
    "logique (chaîne inférentielle) ?\n"
    "- L'expert distingue-t-il clairement les **faits**, les **interprétations** et "
    "les **hypothèses** ?\n"
    "- Les **diagnostics** sont-ils posés selon des critères reconnus (DSM-5, CIM-11) "
    "et étayés par des éléments cliniques suffisants ?\n"
    "- L'expert a-t-il envisagé des **diagnostics différentiels** ?\n"
    "- Les **limites** de l'évaluation sont-elles explicitement mentionnées ?\n\n"
    "### D. Conformité déontologique et procédurale\n"
    "- L'expert a-t-il respecté le **cadre de sa mission** (questions du tribunal) "
    "sans le dépasser ?\n"
    "- Le **consentement éclairé** du sujet a-t-il été recueilli ?\n"
    "- La **neutralité** et l'**impartialité** sont-elles maintenues tout au long "
    "du rapport ?\n"
    "- Les **sources d'information** sont-elles clairement identifiées et "
    "hiérarchisées ?\n"
    "- Le rapport respecte-t-il le **principe de proportionnalité** (conclusions "
    "proportionnées aux données disponibles) ?\n\n"
    "### E. Points de contestation fréquents\n"
    "- Conclusions catégoriques sans nuance ni réserve\n"
    "- Extrapolation au-delà des données (prédiction de comportement futur sans base)\n"
    "- Confusion entre corrélation et causalité\n"
    "- Absence de prise en compte du contexte situationnel\n"
    "- Utilisation de tests obsolètes ou non validés en français\n"
    "- Durée d'examen insuffisante pour la complexité du cas\n"
    "- Non-prise en compte de facteurs culturels ou linguistiques\n\n"
    "## CONSIGNES DE RÉDACTION\n\n"
    "1. Examine chaque section du RE-Projet en appliquant le cadre ci-dessus.\n"
    "2. Pour chaque point identifié, indique :\n"
    "   - La section du RE-Projet concernée\n"
    "   - La catégorie (A: biais, B: tests, C: raisonnement, D: déontologie, "
    "E: contestation)\n"
    "   - L'argumentation détaillée avec référence aux principes ci-dessus\n"
    "   - Une suggestion d'amélioration concrète\n"
    "3. Évalue le niveau de priorité de chaque observation (élevé, moyen, faible).\n"
    "4. Termine par une synthèse des forces et faiblesses du rapport.\n"
    "5. Sois exhaustif, rigoureux et constructif — l'objectif est d'améliorer le "
    "rapport, pas de le démolir.\n"
    "6. IMPORTANT : Rédige INTÉGRALEMENT en français.\n\n"
    "Réponds uniquement avec l'analyse structurée en Markdown."
)

PROMPT_GENERATION_REF_PROJET: str = (
    "Tu es un expert psychologue judiciaire expérimenté chargé de rédiger le REF-Projet "
    "(Rapport d'Expertise Final). Tu disposes des éléments suivants :\n\n"
    "- Le **NEA** (Notes d'Entretien et Analyse) rédigé par l'expert.\n"
    "- La **Réquisition** structurée en Markdown (questions du tribunal, parties, contexte).\n"
    "- Le **Template de Rapport** définissant la structure et la mise en forme attendues.\n\n"
    "Consignes :\n"
    "1. Respecte scrupuleusement la structure du Template de Rapport fourni.\n"
    "2. Intègre les informations du NEA dans les sections correspondantes du template.\n"
    "3. Assure-toi que chaque Question du Tribunal reçoit une réponse argumentée, "
    "claire et étayée par les éléments cliniques du NEA.\n"
    "4. Utilise un style rédactionnel professionnel, objectif et conforme aux normes de "
    "rédaction des rapports d'expertise judiciaire en psychologie.\n"
    "5. Les conclusions doivent être nuancées, fondées sur les données cliniques, et "
    "formulées avec la prudence déontologique requise.\n"
    "6. N'invente aucune donnée clinique. Utilise uniquement les informations fournies "
    "dans le NEA.\n"
    "7. Ce rapport est le rapport final d'expertise — il doit être complet, structuré "
    "et prêt pour soumission au tribunal.\n\n"
    "Réponds uniquement avec le contenu du rapport structuré selon le template."
)

# ---------------------------------------------------------------------------
# Prompts — Workflow TRE-centré (reformulation et révision)
# ---------------------------------------------------------------------------

PROMPT_REFORMULATION_DIRES: str = (
    "Tu es un assistant spécialisé dans la rédaction de rapports d'expertise "
    "judiciaire en psychologie.\n\n"
    "Tu reçois des notes télégraphiques prises par un expert judiciaire pendant "
    "un entretien avec la personne évaluée. Ces notes sont en style abrégé.\n\n"
    "Ta tâche est de reformuler ces notes en texte rédigé professionnel à la "
    "troisième personne, en conservant fidèlement le sens et les faits rapportés.\n\n"
    "Règles :\n"
    "1. Reformule en français soutenu, style rapport d'expertise.\n"
    "2. Utilise la troisième personne (« Le sujet rapporte que... », "
    "« L'intéressé(e) indique... »).\n"
    "3. Ne modifie PAS les citations entre guillemets — restitue-les telles quelles.\n"
    "4. N'ajoute aucune interprétation clinique — reste factuel.\n"
    "5. Conserve tous les faits, dates, noms et détails mentionnés.\n"
    "6. Ne commente pas, ne résume pas — reformule intégralement.\n\n"
    "Réponds uniquement avec le texte reformulé, sans commentaire."
)

PROMPT_REFORMULATION_ANALYSE: str = (
    "Tu es un assistant spécialisé dans la rédaction de rapports d'expertise "
    "judiciaire en psychologie.\n\n"
    "Tu reçois des notes d'analyse clinique prises par un expert psychologue "
    "judiciaire. Ces notes sont en style abrégé/télégraphique.\n\n"
    "Ta tâche est de reformuler ces notes en texte rédigé professionnel, en "
    "conservant la terminologie clinique et les observations factuelles.\n\n"
    "Règles :\n"
    "1. Reformule en français soutenu, style analyse clinique.\n"
    "2. Conserve la terminologie psychologique (mécanismes de défense, "
    "symptômes, diagnostics, etc.).\n"
    "3. Utilise la troisième personne (« L'expert observe que... », "
    "« L'analyse clinique révèle... »).\n"
    "4. Ne modifie PAS les citations entre guillemets.\n"
    "5. N'invente aucune observation — reste fidèle aux notes.\n"
    "6. Conserve les nuances et réserves exprimées par l'expert.\n\n"
    "Réponds uniquement avec le texte reformulé, sans commentaire."
)

PROMPT_REVISION: str = (
    "Tu es un correcteur linguistique spécialisé en français juridique et "
    "en rapports d'expertise judiciaire.\n\n"
    "Tu reçois un texte de rapport d'expertise à corriger.\n\n"
    "Ta tâche est de corriger les fautes d'orthographe, de grammaire et de "
    "syntaxe, tout en préservant le style et le contenu.\n\n"
    "Règles STRICTES :\n"
    "1. Corrige UNIQUEMENT les erreurs de langue (orthographe, grammaire, "
    "conjugaison, syntaxe, ponctuation).\n"
    "2. Ne modifie PAS le contenu sémantique ni la structure du texte.\n"
    "3. Ne modifie PAS les textes entre guillemets — ce sont des verbatim "
    "à préserver intacts.\n"
    "4. Ne modifie PAS les tokens __VERBATIM_NNN__ — ce sont des marqueurs "
    "techniques à conserver tels quels.\n"
    "5. Conserve le registre de langue (français juridique soutenu).\n"
    "6. Ne reformule pas, ne résume pas, ne réorganise pas.\n\n"
    "Réponds uniquement avec le texte corrigé, sans commentaire ni explication."
)

PROMPT_CHATBOT: str = (
    "Tu es l'assistant virtuel de Judi-Expert, une application d'aide à la rédaction "
    "de rapports d'expertise judiciaire en psychologie. Tu assistes l'expert dans "
    "l'utilisation de l'application et réponds à ses questions sur le domaine.\n\n"
    "Tu disposes du **contexte RAG** suivant, issu du corpus du domaine et de la "
    "documentation du système (user-guide, mentions légales, CGU) :\n\n"
    "{contexte_rag}\n\n"
    "Consignes :\n"
    "1. Réponds de manière claire, concise et professionnelle en français.\n"
    "2. Si la question porte sur l'utilisation de l'application, base ta réponse sur "
    "la documentation système (user-guide).\n"
    "3. Si la question porte sur le domaine de l'expertise psychologique judiciaire, "
    "base ta réponse sur le corpus du domaine.\n"
    "4. Si tu ne disposes pas d'information suffisante pour répondre, indique-le "
    "clairement et suggère à l'expert de consulter les ressources appropriées.\n"
    "5. Ne fournis jamais de conseil juridique. Rappelle que tu es un assistant "
    "technique et documentaire.\n"
    "6. Respecte la confidentialité : ne fais jamais référence à des données de "
    "dossiers d'expertise spécifiques."
)


# ---------------------------------------------------------------------------
# Active Performance Profile (singleton)
# ---------------------------------------------------------------------------


class ActiveProfile:
    """Thread-safe singleton holding the active performance profile.

    Provides class-level storage for the currently active PerformanceProfile
    and HardwareInfo. Getter methods implement a fallback chain:
    1. ActiveProfile values (if set)
    2. Environment variables (CTX_MAX, LLM_MODEL, LLM_TOKENS_PER_SEC)
    3. Hardcoded defaults (8192, "qwen2.5:7b-instruct-q3_K_M", 8.0)
    """

    _profile: PerformanceProfile | None = None
    _hardware_info: HardwareInfo | None = None
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def set(cls, profile: PerformanceProfile, hw: HardwareInfo) -> None:
        """Set the active profile and hardware info (thread-safe).

        Args:
            profile: The performance profile to activate.
            hw: The detected hardware information.
        """
        with cls._lock:
            cls._profile = profile
            cls._hardware_info = hw

    @classmethod
    def get_ctx_max(cls) -> int:
        """Return the active context max size.

        Fallback chain: profile → env var CTX_MAX → 8192.

        Returns:
            Maximum context window size in tokens.
        """
        if cls._profile is not None:
            return cls._profile.ctx_max
        return int(os.environ.get("CTX_MAX", "8192"))

    @classmethod
    def get_model(cls) -> str:
        """Return the active LLM model identifier.

        Fallback chain: profile → env var LLM_MODEL →
        "qwen2.5:7b-instruct-q3_K_M".

        Returns:
            Ollama model identifier string.
        """
        if cls._profile is not None:
            return cls._profile.model
        return os.environ.get("LLM_MODEL", "mistral:7b-instruct-v0.3-q4_0")

    @classmethod
    def get_tokens_per_sec(cls) -> float:
        """Return the active tokens-per-second estimate.

        Fallback chain: profile → env var LLM_TOKENS_PER_SEC → 8.0.

        Returns:
            Estimated token generation speed.
        """
        if cls._profile is not None:
            return cls._profile.tokens_per_sec
        return float(os.environ.get("LLM_TOKENS_PER_SEC", "8.0"))

    @classmethod
    def get_profile(cls) -> PerformanceProfile | None:
        """Return the full active PerformanceProfile, or None if not set.

        Returns:
            The active PerformanceProfile or None.
        """
        return cls._profile

    @classmethod
    def get_hardware_info(cls) -> HardwareInfo | None:
        """Return the stored HardwareInfo, or None if not set.

        Returns:
            The detected HardwareInfo or None.
        """
        return cls._hardware_info


# ---------------------------------------------------------------------------
# Step Duration Estimation
# ---------------------------------------------------------------------------

# Step-specific output ratios (how much output relative to input)
STEP_OUTPUT_RATIOS: dict[str, float] = {
    "step1": 1.5,   # PEMEC generation — moderate output
    "step2": 0.5,   # Upload processing — minimal output
    "step3": 2.0,   # REF report — heavy output
    "step4": 1.0,   # RAUX analysis — moderate output
    "step5": 0.3,   # Final validation — minimal output
}

# Estimated input tokens per step (average case)
STEP_INPUT_TOKENS: dict[str, int] = {
    "step1": 3000,
    "step2": 2000,
    "step3": 5000,
    "step4": 4000,
    "step5": 1500,
}


def compute_step_duration(
    estimated_input_tokens: int,
    output_ratio: float,
    tokens_per_sec: float,
) -> float:
    """Compute estimated step duration in seconds.

    Formula: (estimated_input_tokens × output_ratio) / tokens_per_sec

    Args:
        estimated_input_tokens: Number of input tokens for the step.
        output_ratio: Step-specific output ratio multiplier.
        tokens_per_sec: Estimated token generation speed.

    Returns:
        Estimated duration in seconds.
    """
    return (estimated_input_tokens * output_ratio) / tokens_per_sec


def get_all_step_durations(tokens_per_sec: float | None = None) -> dict[str, str]:
    """Compute duration estimates for all steps.

    Args:
        tokens_per_sec: Override tokens/sec value. If None, uses ActiveProfile.

    Returns:
        Dict mapping step names to formatted duration strings (e.g. "~3 min ±1").
    """
    if tokens_per_sec is None:
        tokens_per_sec = ActiveProfile.get_tokens_per_sec()

    durations: dict[str, str] = {}
    for step, input_tokens in STEP_INPUT_TOKENS.items():
        ratio = STEP_OUTPUT_RATIOS[step]
        seconds = compute_step_duration(input_tokens, ratio, tokens_per_sec)
        minutes = seconds / 60.0
        durations[step] = f"~{max(1, round(minutes))} min ±1"
    return durations


# ---------------------------------------------------------------------------
# Model Download Manager
# ---------------------------------------------------------------------------


@dataclass
class ModelDownloadStatus:
    """Status of a model download operation."""

    needed: bool = False
    in_progress: bool = False
    progress_percent: float | None = None
    error: str | None = None


class ModelDownloadManager:
    """Manages LLM model downloads via Ollama.

    Checks model availability and triggers downloads when the active
    profile requires a different model than what's currently available.
    Uses the Ollama REST API (GET /api/tags, POST /api/pull).
    """

    def __init__(self, ollama_base_url: str | None = None) -> None:
        """Initialize the download manager.

        Args:
            ollama_base_url: Base URL for the Ollama API. Falls back to
                env var OLLAMA_URL, then to "http://judi-llm:11434".
        """
        self._status = ModelDownloadStatus()
        self._ollama_base_url = (
            ollama_base_url
            or os.environ.get("OLLAMA_URL", "http://judi-llm:11434")
        ).rstrip("/")

    @property
    def status(self) -> ModelDownloadStatus:
        """Return current download status."""
        return self._status

    async def check_and_pull_if_needed(self, target_model: str) -> None:
        """Check if target model is available, pull if not.

        If the model is not locally available, triggers an async download.
        On failure, keeps the previous model available and logs the error.

        Args:
            target_model: The model identifier to ensure is available.
        """
        self._status = ModelDownloadStatus()

        try:
            available = await self._is_model_available(target_model)
        except Exception as exc:
            logger.warning(
                "Cannot check model availability (Ollama may not be running): %s",
                exc,
            )
            self._status.error = f"Cannot reach Ollama: {exc}"
            return

        if available:
            logger.info("Model '%s' is already available locally.", target_model)
            return

        # Model not available — trigger download
        self._status.needed = True
        logger.info(
            "Model '%s' not found locally. Triggering download.", target_model
        )
        await self._pull_model(target_model)

    async def _is_model_available(self, model_name: str) -> bool:
        """Check if a model is available locally via Ollama API.

        Calls GET /api/tags and checks if the model name appears in the
        list of locally available models.

        Args:
            model_name: The model identifier to check.

        Returns:
            True if the model is available locally, False otherwise.

        Raises:
            httpx.ConnectError: If Ollama is unreachable.
            httpx.HTTPStatusError: If the API returns an error status.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self._ollama_base_url}/api/tags")
            response.raise_for_status()
            data = response.json()

        models = data.get("models", [])
        for model in models:
            name = model.get("name", "")
            # Exact match
            if name == model_name:
                return True
            # Ollama often stores models with ":latest" suffix
            if name == f"{model_name}:latest":
                return True
            # Match when model_name includes a tag (e.g. "qwen2.5:7b-instruct-q3_K_M")
            if name.startswith(f"{model_name}:"):
                return True

        return False

    async def _pull_model(self, model_name: str) -> None:
        """Pull a model from Ollama registry.

        Streams the download response to track progress. On failure,
        sets the error status and logs the error without raising.

        Args:
            model_name: The model identifier to download.
        """
        self._status.in_progress = True
        self._status.progress_percent = 0.0
        self._status.error = None

        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST",
                    f"{self._ollama_base_url}/api/pull",
                    json={"name": model_name, "stream": True},
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        # Track progress from Ollama streaming response
                        total = chunk.get("total", 0)
                        completed = chunk.get("completed", 0)
                        if total and total > 0:
                            self._status.progress_percent = (
                                completed / total
                            ) * 100.0

                        # Check for error in stream
                        if "error" in chunk:
                            raise RuntimeError(chunk["error"])

            # Download successful
            self._status = ModelDownloadStatus(needed=False)
            logger.info("Model '%s' downloaded successfully.", model_name)

        except Exception as exc:
            # Download failed — keep previous model, log error
            self._status.in_progress = False
            self._status.progress_percent = None
            self._status.error = str(exc)
            logger.error(
                "Failed to download model '%s': %s. "
                "Keeping previous model available.",
                model_name,
                exc,
            )

    def get_status(self) -> ModelDownloadStatus:
        """Return current download status.

        Returns:
            The current ModelDownloadStatus instance.
        """
        return self._status


# ---------------------------------------------------------------------------
# Client LLM
# ---------------------------------------------------------------------------


class LLMService:
    """Client asynchrone pour l'API Ollama (Mistral 7B Instruct v0.3).

    Fournit deux méthodes de bas niveau (``chat``, ``generate``) et des
    méthodes de haut niveau pour chaque étape du workflow d'expertise.
    """

    def __init__(
        self,
        base_url: str = OLLAMA_URL,
        timeout: float = LLM_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Méthodes de bas niveau
    # ------------------------------------------------------------------

    async def chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        num_ctx: int | None = None,
    ) -> str:
        """Appelle ``POST /api/chat`` avec une liste de messages.

        Parameters
        ----------
        messages:
            Liste de dicts ``{"role": "user"|"assistant", "content": "..."}``.
        system_prompt:
            Prompt système optionnel injecté en premier message.
        num_ctx:
            Taille de la fenêtre de contexte en tokens.
            Si None, calculée automatiquement à partir de l'input (+20% marge).

        Returns
        -------
        str
            Contenu de la réponse de l'assistant.
        """
        full_messages: list[dict[str, str]] = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        if num_ctx is None:
            user_content = " ".join(m["content"] for m in messages)
            num_ctx = compute_num_ctx(user_content, system_prompt or "")

        logger.info(
            "LLM chat — num_ctx=%d, input≈%d tokens, durée estimée≈%ds",
            num_ctx,
            estimate_tokens(" ".join(m["content"] for m in full_messages)),
            estimate_duration_seconds(num_ctx),
        )

        payload = {
            "model": ActiveProfile.get_model(),
            "messages": full_messages,
            "stream": False,
            "options": {
                "num_ctx": num_ctx,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["message"]["content"]
        except httpx.TimeoutException:
            logger.error("LLM timeout lors de l'appel /api/chat")
            raise LLMTimeoutError(
                "Le LLM n'a pas répondu dans le délai imparti. "
                "Essayez de redémarrer le conteneur judi-llm."
            )
        except httpx.HTTPStatusError as exc:
            logger.error("Erreur HTTP LLM /api/chat : %s", exc.response.status_code)
            raise LLMConnectionError(
                f"Erreur du serveur LLM (HTTP {exc.response.status_code})."
            )
        except httpx.ConnectError:
            logger.error("Impossible de se connecter au LLM à %s", self.base_url)
            raise LLMConnectionError(
                "Impossible de se connecter au LLM. "
                "Vérifiez que le conteneur judi-llm est démarré."
            )

    async def generate(self, prompt: str, num_ctx: int | None = None) -> str:
        """Appelle ``POST /api/generate`` avec un prompt simple.

        Parameters
        ----------
        prompt:
            Texte du prompt à envoyer au LLM.
        num_ctx:
            Taille de la fenêtre de contexte en tokens.
            Si None, calculée automatiquement à partir de l'input (+20% marge).

        Returns
        -------
        str
            Texte de la réponse générée.
        """
        if num_ctx is None:
            num_ctx = compute_num_ctx(prompt)

        payload = {
            "model": ActiveProfile.get_model(),
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_ctx": num_ctx,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["response"]
        except httpx.TimeoutException:
            logger.error("LLM timeout lors de l'appel /api/generate")
            raise LLMTimeoutError(
                "Le LLM n'a pas répondu dans le délai imparti. "
                "Essayez de redémarrer le conteneur judi-llm."
            )
        except httpx.HTTPStatusError as exc:
            logger.error("Erreur HTTP LLM /api/generate : %s", exc.response.status_code)
            raise LLMConnectionError(
                f"Erreur du serveur LLM (HTTP {exc.response.status_code})."
            )
        except httpx.ConnectError:
            logger.error("Impossible de se connecter au LLM à %s", self.base_url)
            raise LLMConnectionError(
                "Impossible de se connecter au LLM. "
                "Vérifiez que le conteneur judi-llm est démarré."
            )

    # ------------------------------------------------------------------
    # Méthodes de haut niveau (workflow d'expertise)
    # ------------------------------------------------------------------

    async def structurer_markdown(self, texte_brut: str) -> str:
        """Step0 — Structure le texte OCR brut en Markdown.

        Valide : Exigence 6.4
        """
        messages = [{"role": "user", "content": texte_brut}]
        return await self.chat(messages, system_prompt=PROMPT_STRUCTURATION_MD)

    async def extraire_questions(self, ordonnance_md: str) -> str:
        """Step 1 — Extrait les questions du tribunal depuis l'ordonnance structurée.

        Retourne un Markdown avec les questions numérotées Q1, Q2, etc.
        """
        messages = [{"role": "user", "content": ordonnance_md}]
        return await self.chat(messages, system_prompt=PROMPT_EXTRACTION_QUESTIONS)

    async def extraire_placeholders(self, ordonnance_md: str) -> str:
        """Step 1 — Extrait les valeurs des placeholders depuis l'ordonnance structurée.

        Retourne un CSV (séparateur ;) avec les champs nom_placeholder;valeur.
        """
        messages = [{"role": "user", "content": ordonnance_md}]
        return await self.chat(messages, system_prompt=PROMPT_EXTRACTION_PLACEHOLDERS)

    async def generer_qmec(
        self, qt: str, tpe: str, contexte_rag: str
    ) -> str:
        """Step 2 — Génère le plan d'entretien (PE) à partir de QT + TPE + contexte RAG.

        Valide : Exigence 7.2
        """
        contenu = (
            "## Questions du Tribunal (QT)\n\n"
            f"{qt}\n\n"
            "## Trame de Plan d'Entretien (TPE)\n\n"
            f"{tpe}\n\n"
            "## Contexte du domaine (RAG)\n\n"
            f"{contexte_rag}"
        )
        messages = [{"role": "user", "content": contenu}]
        # Limiter le num_ctx pour éviter un contexte de 32K sur CPU
        num_ctx = compute_num_ctx(contenu, PROMPT_GENERATION_QMEC, output_ratio=0.7)
        return await self.chat(messages, system_prompt=PROMPT_GENERATION_QMEC, num_ctx=num_ctx)

    # Alias pour la nouvelle terminologie
    generer_pe = generer_qmec

    async def generer_ref(
        self, reb: str, qt: str, ne: str, template: str
    ) -> str:
        """Step3 — Génère le Rapport d'Expertise Final (REF).

        Valide : Exigence 9.2
        """
        contenu = (
            "## Rapport d'Expertise Brut (REB)\n\n"
            f"{reb}\n\n"
            "## Questions du Tribunal (QT)\n\n"
            f"{qt}\n\n"
            "## Notes d'Entretien (NE)\n\n"
            f"{ne}\n\n"
            "## Template de Rapport\n\n"
            f"{template}"
        )
        messages = [{"role": "user", "content": contenu}]
        return await self.chat(messages, system_prompt=PROMPT_GENERATION_REF)

    async def generer_raux_p1(self, ref: str, corpus: str) -> str:
        """Step3 — Analyse des contestations possibles du REF (RAUX Partie 1).

        Valide : Exigence 9.3
        """
        contenu = (
            "## Rapport d'Expertise Final (REF)\n\n"
            f"{ref}\n\n"
            "## Corpus du domaine\n\n"
            f"{corpus}"
        )
        messages = [{"role": "user", "content": contenu}]
        return await self.chat(messages, system_prompt=PROMPT_GENERATION_RAUX_P1)

    async def generer_raux_p2(self, ref: str, raux_p1: str) -> str:
        """Step3 — Révision du REF tenant compte des contestations (RAUX Partie 2).

        Valide : Exigence 9.3
        """
        contenu = (
            "## Rapport d'Expertise Final (REF)\n\n"
            f"{ref}\n\n"
            "## Analyse des contestations (RAUX Partie 1)\n\n"
            f"{raux_p1}"
        )
        messages = [{"role": "user", "content": contenu}]
        return await self.chat(messages, system_prompt=PROMPT_GENERATION_RAUX_P2)

    async def generer_re_projet(
        self, nea_content: str, requisition_md: str, template: str,
        placeholders_context: str = "",
    ) -> str:
        """Step2 — Génère le RE-Projet à partir du NEA, de la réquisition et du template.

        Args:
            nea_content: Contenu du NEA (Notes d'Entretien et Analyse).
            requisition_md: Réquisition structurée en Markdown.
            template: Template de rapport (TRE) avec placeholders substitués.
            placeholders_context: Résumé des informations factuelles extraites
                de l'ordonnance (nom expert, juridiction, etc.).

        Valide : Exigence 3.4
        """
        contenu = ""
        if placeholders_context:
            contenu += placeholders_context
        contenu += (
            "## NEA (Notes d'Entretien et Analyse)\n\n"
            f"{nea_content}\n\n"
            "## Réquisition (Markdown structuré)\n\n"
            f"{requisition_md}\n\n"
            "## Template de Rapport\n\n"
            f"{template}"
        )
        messages = [{"role": "user", "content": contenu}]
        return await self.chat(messages, system_prompt=PROMPT_GENERATION_RE_PROJET)

    async def generer_re_projet_auxiliaire(
        self, nea_content: str, re_projet: str, rag_context: str = "",
    ) -> str:
        """Step2 — Génère le RE-Projet-Auxiliaire (analyse contradictoire).

        Args:
            nea_content: Contenu du NEA (Notes d'Entretien et Analyse).
            re_projet: Contenu du RE-Projet généré.
            rag_context: Contexte RAG du domaine (jurisprudence, guides
                méthodologiques, textes réglementaires) pour étayer
                l'analyse contradictoire.

        Valide : Exigence 3.5
        """
        contenu = (
            "## NEA (Notes d'Entretien et Analyse)\n\n"
            f"{nea_content}\n\n"
            "## RE-Projet (Rapport d'Expertise Projet)\n\n"
            f"{re_projet}"
        )
        if rag_context:
            contenu += (
                "\n\n## Corpus du domaine (jurisprudence, guides méthodologiques, "
                "textes réglementaires)\n\n"
                f"{rag_context}"
            )
        messages = [{"role": "user", "content": contenu}]
        return await self.chat(
            messages, system_prompt=PROMPT_GENERATION_RE_PROJET_AUXILIAIRE,
        )

    async def generer_ref_projet(
        self, nea_content: str, requisition_md: str, template: str
    ) -> str:
        """Step3 — Génère le REF-Projet (rapport d'expertise final) à partir du NEA.

        Valide : Exigence 4.3
        """
        contenu = (
            "## NEA (Notes d'Entretien et Analyse)\n\n"
            f"{nea_content}\n\n"
            "## Réquisition (Markdown structuré)\n\n"
            f"{requisition_md}\n\n"
            "## Template de Rapport\n\n"
            f"{template}"
        )
        messages = [{"role": "user", "content": contenu}]
        return await self.chat(messages, system_prompt=PROMPT_GENERATION_REF_PROJET)

    async def generer_pre_rapport(
        self, pea_content: str, requisition_md: str, template: str
    ) -> str:
        """Step 4 — Génère le Pré-Rapport d'Expertise (PRE) à partir du PEA annoté.

        Interprète les annotations balisées (@dires, @analyse, @verbatim,
        @question, @reference) et produit le rapport structuré.
        """
        contenu = (
            "## PEA (Plan d'Entretien Annoté)\n\n"
            f"{pea_content}\n\n"
            "## Réquisition (Markdown structuré)\n\n"
            f"{requisition_md}\n\n"
            "## Template de Rapport\n\n"
            f"{template}"
        )
        messages = [{"role": "user", "content": contenu}]
        return await self.chat(messages, system_prompt=PROMPT_GENERATION_RE_PROJET)

    async def generer_dac(
        self, pea_content: str, pre_rapport: str, rag_context: str = "",
    ) -> str:
        """Step 4 — Génère le Document d'Analyse Contradictoire (DAC).

        Analyse le PRE pour identifier les points faibles et proposer
        des améliorations, en s'appuyant sur le corpus du domaine.

        Args:
            pea_content: Contenu du PEA (Plan d'Entretien Annoté).
            pre_rapport: Contenu du PRE (Pré-Rapport d'Expertise).
            rag_context: Contexte RAG du domaine (jurisprudence, guides
                méthodologiques) pour étayer l'analyse contradictoire.
        """
        contenu = (
            "## PEA (Plan d'Entretien Annoté)\n\n"
            f"{pea_content}\n\n"
            "## Pré-Rapport d'Expertise (PRE)\n\n"
            f"{pre_rapport}"
        )
        if rag_context:
            contenu += (
                "\n\n## Corpus du domaine (jurisprudence, guides méthodologiques, "
                "textes réglementaires)\n\n"
                f"{rag_context}"
            )
        messages = [{"role": "user", "content": contenu}]
        return await self.chat(
            messages, system_prompt=PROMPT_GENERATION_RE_PROJET_AUXILIAIRE,
        )

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        num_ctx: int | None = None,
    ):
        """Appelle ``POST /api/chat`` en mode streaming.

        Yields des chunks de texte au fur et à mesure de la génération.
        """
        full_messages: list[dict[str, str]] = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        if num_ctx is None:
            user_content = " ".join(m["content"] for m in messages)
            num_ctx = compute_num_ctx(user_content, system_prompt or "", output_ratio=0.5)

        payload = {
            "model": ActiveProfile.get_model(),
            "messages": full_messages,
            "stream": True,
            "options": {
                "num_ctx": num_ctx,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        import json as _json
                        try:
                            chunk = _json.loads(line)
                        except _json.JSONDecodeError:
                            continue
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
        except httpx.TimeoutException:
            raise LLMTimeoutError("Le LLM n'a pas répondu dans le délai imparti.")
        except httpx.ConnectError:
            raise LLMConnectionError("Impossible de se connecter au LLM.")

    async def chatbot_stream(
        self, messages: list[dict[str, str]], contexte_rag: str
    ):
        """ChatBot streaming — Yields des chunks de réponse."""
        system_prompt = PROMPT_CHATBOT.replace("{contexte_rag}", contexte_rag)
        async for chunk in self.chat_stream(messages, system_prompt=system_prompt):
            yield chunk

    async def chatbot(
        self, messages: list[dict[str, str]], contexte_rag: str
    ) -> str:
        """ChatBot — Répond à une question avec le contexte RAG.

        Valide : Exigence 11.2
        """
        system_prompt = PROMPT_CHATBOT.replace("{contexte_rag}", contexte_rag)
        return await self.chat(messages, system_prompt=system_prompt)

    # ------------------------------------------------------------------
    # Méthodes workflow TRE-centré (reformulation et révision)
    # ------------------------------------------------------------------

    async def reformuler_dires(self, texte_abrege: str) -> str:
        """Reformule des notes @dires en texte rédigé professionnel.

        Args:
            texte_abrege: Notes télégraphiques de l'expert (style abrégé).

        Returns:
            Texte reformulé à la troisième personne, style rapport.
        """
        messages = [{"role": "user", "content": texte_abrege}]
        return await self.chat(messages, system_prompt=PROMPT_REFORMULATION_DIRES)

    async def reformuler_analyse(self, texte_abrege: str) -> str:
        """Reformule des notes @analyse en texte rédigé professionnel.

        Args:
            texte_abrege: Notes d'analyse clinique de l'expert (style abrégé).

        Returns:
            Texte reformulé en style analyse clinique professionnelle.
        """
        messages = [{"role": "user", "content": texte_abrege}]
        return await self.chat(messages, system_prompt=PROMPT_REFORMULATION_ANALYSE)

    async def reviser_texte(self, texte: str) -> str:
        """Corrige le texte linguistiquement en préservant les verbatim.

        Args:
            texte: Texte du rapport à corriger (peut contenir des tokens
                __VERBATIM_NNN__ à ne pas modifier).

        Returns:
            Texte corrigé (orthographe, grammaire, syntaxe).
        """
        messages = [{"role": "user", "content": texte}]
        return await self.chat(messages, system_prompt=PROMPT_REVISION)


# ---------------------------------------------------------------------------
# Exceptions personnalisées
# ---------------------------------------------------------------------------


class LLMError(Exception):
    """Erreur de base pour le service LLM."""


class LLMTimeoutError(LLMError):
    """Le LLM n'a pas répondu dans le délai imparti."""


class LLMConnectionError(LLMError):
    """Impossible de se connecter au serveur LLM."""
