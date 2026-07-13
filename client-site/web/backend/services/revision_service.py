"""Service de révision linguistique pour le PRE.

Corrige les fautes d'orthographe, grammaire et syntaxe du pré-rapport
tout en préservant intacts les textes entre guillemets (verbatim).

Valide : Requirement 5 (Finalisation et archivage)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes (compatibilité avec l'ancien service de révision documentaire)
# ---------------------------------------------------------------------------
CHARS_PER_TOKEN: float = 3.5
CTX_USAGE_RATIO: float = 0.6
PROMPT_REVISION: str = (
    "Tu es un correcteur linguistique spécialisé en français juridique. "
    "Corrige les fautes d'orthographe, de grammaire et de syntaxe. "
    "Ne modifie PAS le contenu sémantique ni les textes entre guillemets. "
    "Retourne le texte corrigé."
)


@dataclass
class Correction:
    """Une correction linguistique appliquée."""

    original: str
    corrected: str
    position: int  # approximate character position


@dataclass
class RevisionResult:
    """Résultat de la révision linguistique."""

    corrected_text: str
    corrections: list[Correction] = field(default_factory=list)
    verbatim_count: int = 0  # number of verbatim sections preserved


class RevisionService:
    """Service de révision linguistique via LLM.

    Préserve les textes entre guillemets (verbatim) en les remplaçant
    par des tokens avant l'envoi au LLM, puis les restaure après.
    """

    # Pattern to match quoted text (French guillemets and standard quotes)
    VERBATIM_PATTERN = re.compile(r'\u201c[^\u201d]*\u201d|"[^"]*"')
    TOKEN_PREFIX = "__VERBATIM_"
    TOKEN_SUFFIX = "__"

    def _extract_verbatim(self, text: str) -> tuple[str, dict[str, str]]:
        """Extract verbatim sections and replace with tokens.

        Args:
            text: Input text containing quoted sections.

        Returns:
            Tuple of (text with tokens, mapping of token → original text).
        """
        verbatim_map: dict[str, str] = {}
        counter = 0

        def replacer(match: re.Match) -> str:
            nonlocal counter
            counter += 1
            token = f"{self.TOKEN_PREFIX}{counter:03d}{self.TOKEN_SUFFIX}"
            verbatim_map[token] = match.group(0)
            return token

        tokenized_text = self.VERBATIM_PATTERN.sub(replacer, text)
        return tokenized_text, verbatim_map

    def _restore_verbatim(self, text: str, verbatim_map: dict[str, str]) -> str:
        """Restore verbatim sections from tokens.

        Args:
            text: Text with tokens.
            verbatim_map: Mapping of token → original text.

        Returns:
            Text with verbatim sections restored.
        """
        result = text
        for token, original in verbatim_map.items():
            result = result.replace(token, original)
        return result

    async def revise(self, text: str) -> RevisionResult:
        """Corrige le texte en préservant les verbatim.

        Args:
            text: Text to revise (PRE content).

        Returns:
            RevisionResult with corrected text and list of corrections.
        """
        from services.llm_service import LLMService

        # 1. Extract and protect verbatim sections
        tokenized_text, verbatim_map = self._extract_verbatim(text)
        verbatim_count = len(verbatim_map)

        logger.info(
            "Révision linguistique — %d sections verbatim protégées",
            verbatim_count,
        )

        # 2. Call LLM for linguistic correction
        llm = LLMService()
        try:
            corrected_tokenized = await llm.reviser_texte(tokenized_text)
        except Exception as exc:
            logger.error(
                "Erreur LLM lors de la révision : %s — retour du texte original",
                exc,
            )
            return RevisionResult(
                corrected_text=text,
                corrections=[],
                verbatim_count=verbatim_count,
            )

        # 3. Restore verbatim sections
        corrected_text = self._restore_verbatim(corrected_tokenized, verbatim_map)

        # 4. Identify corrections (simple diff)
        corrections = self._identify_corrections(text, corrected_text)

        logger.info(
            "Révision terminée — %d corrections identifiées",
            len(corrections),
        )

        return RevisionResult(
            corrected_text=corrected_text,
            corrections=corrections,
            verbatim_count=verbatim_count,
        )

    def _identify_corrections(
        self, original: str, corrected: str
    ) -> list[Correction]:
        """Identify differences between original and corrected text.

        Simple word-level diff to identify corrections.
        Not exhaustive but gives a useful summary.
        """
        corrections: list[Correction] = []

        orig_words = original.split()
        corr_words = corrected.split()

        # Simple comparison — find changed words
        min_len = min(len(orig_words), len(corr_words))
        position = 0

        for i in range(min_len):
            if orig_words[i] != corr_words[i]:
                corrections.append(
                    Correction(
                        original=orig_words[i],
                        corrected=corr_words[i],
                        position=position,
                    )
                )
            position += len(orig_words[i]) + 1  # +1 for space

        return corrections
