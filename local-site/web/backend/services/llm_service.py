"""
Judi-Expert — Service LLM (client Ollama)

Client asynchrone pour l'API Ollama hébergeant Mistral 7B Instruct v0.3.
Fournit les méthodes de haut niveau pour chaque étape du workflow d'expertise
et les prompts système spécialisés pour le domaine judiciaire (psychologie).

Valide : Exigences 6.4, 7.2, 9.2, 9.3, 11.2
"""

import os
import logging

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (variables d'environnement avec valeurs par défaut)
# ---------------------------------------------------------------------------

OLLAMA_URL: str = os.environ.get("OLLAMA_URL", "http://judi-llm:11434")
LLM_MODEL: str = os.environ.get("LLM_MODEL", "mistral:7b-instruct-v0.3-q4_0")

# Timeout élevé : l'inférence locale sur CPU peut être lente
LLM_TIMEOUT: float = float(os.environ.get("LLM_TIMEOUT", "1800"))

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

PROMPT_GENERATION_QMEC: str = (
    "Tu es un expert psychologue judiciaire expérimenté. Tu dois générer un plan "
    "d'entretien structuré (QMEC — Questionnaire pour le Mis En Cause) à partir des "
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
    "6. Termine par une section « Synthèse et éléments de réponse aux QT » rappelant "
    "les points clés à couvrir pour répondre à chaque question du tribunal.\n\n"
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
    "dans le NEA.\n\n"
    "Réponds uniquement avec le contenu du rapport structuré selon le template."
)

PROMPT_GENERATION_RE_PROJET_AUXILIAIRE: str = (
    "Tu es un avocat spécialisé en droit de l'expertise judiciaire et en psychologie "
    "légale. Tu dois analyser le RE-Projet (Rapport d'Expertise Projet) ci-dessous et "
    "produire un document auxiliaire d'analyse.\n\n"
    "Tu disposes également du **NEA** (Notes d'Entretien et Analyse) de l'expert.\n\n"
    "Consignes :\n"
    "1. Examine chaque section du RE-Projet et identifie les points faibles, les "
    "affirmations insuffisamment étayées, les biais méthodologiques potentiels et les "
    "conclusions contestables.\n"
    "2. Pour chaque point identifié, indique :\n"
    "   - La section du RE-Projet concernée\n"
    "   - La nature de l'observation (méthodologique, factuelle, déontologique, juridique)\n"
    "   - L'argumentation détaillée\n"
    "3. Propose des améliorations concrètes pour renforcer le rapport.\n"
    "4. Évalue le niveau de priorité de chaque observation (élevé, moyen, faible).\n"
    "5. Sois exhaustif et rigoureux.\n\n"
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
        model: str = LLM_MODEL,
        timeout: float = LLM_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Méthodes de bas niveau
    # ------------------------------------------------------------------

    async def chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> str:
        """Appelle ``POST /api/chat`` avec une liste de messages.

        Parameters
        ----------
        messages:
            Liste de dicts ``{"role": "user"|"assistant", "content": "..."}``.
        system_prompt:
            Prompt système optionnel injecté en premier message.

        Returns
        -------
        str
            Contenu de la réponse de l'assistant.
        """
        full_messages: list[dict[str, str]] = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": full_messages,
            "stream": False,
            "options": {
                "num_ctx": 16384,
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

    async def generate(self, prompt: str) -> str:
        """Appelle ``POST /api/generate`` avec un prompt simple.

        Parameters
        ----------
        prompt:
            Texte du prompt à envoyer au LLM.

        Returns
        -------
        str
            Texte de la réponse générée.
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_ctx": 16384,
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

    async def generer_qmec(
        self, qt: str, tpe: str, contexte_rag: str
    ) -> str:
        """Step1 — Génère le plan d'entretien (QMEC).

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
        return await self.chat(messages, system_prompt=PROMPT_GENERATION_QMEC)

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
        self, nea_content: str, requisition_md: str, template: str
    ) -> str:
        """Step2 — Génère le RE-Projet à partir du NEA, de la réquisition et du template.

        Valide : Exigence 3.4
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
        return await self.chat(messages, system_prompt=PROMPT_GENERATION_RE_PROJET)

    async def generer_re_projet_auxiliaire(
        self, nea_content: str, re_projet: str
    ) -> str:
        """Step2 — Génère le RE-Projet-Auxiliaire en complément du RE-Projet.

        Valide : Exigence 3.5
        """
        contenu = (
            "## NEA (Notes d'Entretien et Analyse)\n\n"
            f"{nea_content}\n\n"
            "## RE-Projet (Rapport d'Expertise Projet)\n\n"
            f"{re_projet}"
        )
        messages = [{"role": "user", "content": contenu}]
        return await self.chat(
            messages, system_prompt=PROMPT_GENERATION_RE_PROJET_AUXILIAIRE
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

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ):
        """Appelle ``POST /api/chat`` en mode streaming.

        Yields des chunks de texte au fur et à mesure de la génération.
        """
        full_messages: list[dict[str, str]] = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": full_messages,
            "stream": True,
            "options": {
                "num_ctx": 16384,
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


# ---------------------------------------------------------------------------
# Exceptions personnalisées
# ---------------------------------------------------------------------------


class LLMError(Exception):
    """Erreur de base pour le service LLM."""


class LLMTimeoutError(LLMError):
    """Le LLM n'a pas répondu dans le délai imparti."""


class LLMConnectionError(LLMError):
    """Impossible de se connecter au serveur LLM."""
