"""Service comptable — construction et validation des métadonnées pour Stripe.

Tous les experts sont traités en B2B dans les métadonnées Stripe.
Les métadonnées incluent les informations de l'expert et les informations d'achat.

Métadonnées à l'enregistrement (profil) :
    - nom, prénom, email
    - entreprise (si définie)
    - adresse-entreprise
    - email-facturation
    - SIRET (si existant, sinon "non attribué")

Métadonnées au paiement :
    - Informations expert (ci-dessus)
    - Informations achat : prix HT, TVA, TTC, date, service, abonnement, récurrence

Pour la facture :
    - date achat
    - description : application - service
    - nom/prénom expert
    - adresse, email client
    - SIRET (renseigné ou "non attribué")
    - prix HT, TVA et TTC
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from models.expert import Expert


class ComptaValidationError(Exception):
    """Erreur levée lorsque la validation des métadonnées comptables échoue.

    Attributes:
        message: Description lisible de l'erreur de validation.
        details: Détails supplémentaires fournis par la Compta_Library.
    """

    def __init__(self, message: str, details: Any = None) -> None:
        self.message = message
        self.details = details
        super().__init__(self.message)


# --- Constantes métier ---
APPLI = "judi-expert"
SERVICE = "ticket-expertise"
TVA_RATE = 0.20  # TVA à 20%


def _validate_with_compta_library(metadata: dict[str, str]) -> dict[str, str]:
    """Valide et formate les métadonnées via la Compta_Library.

    Args:
        metadata: Dictionnaire des métadonnées à valider.

    Returns:
        Métadonnées validées et formatées par la bibliothèque.

    Raises:
        ComptaValidationError: Si la validation échoue.
    """
    try:
        from compta_library import validate_and_format  # type: ignore[import-untyped]

        return validate_and_format(metadata)  # type: ignore[no-any-return]
    except ImportError:
        # Mode dégradé : bibliothèque non installée (dev local)
        return metadata
    except Exception as exc:
        raise ComptaValidationError(
            message=f"Échec de la validation Compta_Library : {exc}",
            details=str(exc),
        ) from exc


def build_metadata(expert: Expert, ticket_config: dict[str, Any]) -> dict[str, str]:
    """Construit les métadonnées comptables pour une transaction Stripe.

    Tous les experts sont marqués B2B. Les métadonnées incluent :
    - Informations expert : nom, prénom, email, entreprise, adresse, billing_email, SIRET
    - Informations achat : prix HT, TVA, TTC, date, service, récurrence

    Args:
        expert: Instance du modèle Expert.
        ticket_config: Dictionnaire de configuration contenant :
            - domaine (str) : domaine d'expertise
            - price_ht (str) : prix HT en euros
            - price_tva (str) : montant TVA en euros
            - price_ttc (str) : prix TTC en euros
            - date_achat (str, optionnel) : date d'achat ISO (défaut: maintenant)
            - service_type (str, optionnel) : type de service (défaut: "ticket-expertise")
            - abonnement (str, optionnel) : "oui" ou "non" (défaut: "non")
            - recurrence (str, optionnel) : fréquence (défaut: "ponctuel")

    Returns:
        Dictionnaire de métadonnées validées, prêt à être passé à Stripe.

    Raises:
        ComptaValidationError: Si la validation des métadonnées échoue.
    """
    # --- Informations expert ---
    metadata: dict[str, str] = {
        "appli": APPLI,
        "service": SERVICE,
        "type": "B2B",
        "domaine": ticket_config.get("domaine", expert.domaine),
        "expert_lastname": expert.nom,
        "expert_firstname": expert.prenom,
        "expert_email": expert.email,
        "entreprise": expert.entreprise or "",
        "expert_address": expert.company_address or expert.adresse,
        "billing_email": expert.billing_email or expert.email,
        "siret": expert.siret if expert.siret else "non attribué",
    }

    # --- Informations achat ---
    metadata["price_ht"] = str(ticket_config.get("price_ht", ""))
    metadata["price_tva"] = str(ticket_config.get("price_tva", ""))
    metadata["price_ttc"] = str(ticket_config.get("price_ttc", ""))
    metadata["date_achat"] = ticket_config.get(
        "date_achat", datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    metadata["service_type"] = ticket_config.get("service_type", SERVICE)
    metadata["abonnement"] = ticket_config.get("abonnement", "non")
    metadata["recurrence"] = ticket_config.get("recurrence", "ponctuel")

    # --- Description facture ---
    metadata["description"] = f"{APPLI} - {metadata['service_type']}"

    # --- Validation via Compta_Library ---
    validated_metadata = _validate_with_compta_library(metadata)

    return validated_metadata
