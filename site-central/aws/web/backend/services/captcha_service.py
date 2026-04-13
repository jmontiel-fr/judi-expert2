"""Service de vérification Google reCAPTCHA V2."""

import os

import httpx

RECAPTCHA_SECRET_KEY = os.environ.get("RECAPTCHA_SECRET_KEY", "")
RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"


async def verify_captcha(captcha_token: str) -> bool:
    """Vérifie un token reCAPTCHA V2 auprès de l'API Google.

    Args:
        captcha_token: Token reCAPTCHA envoyé par le frontend.

    Returns:
        True si le captcha est valide, False sinon.
    """
    if not RECAPTCHA_SECRET_KEY:
        # En développement sans clé configurée, on accepte tout
        return True

    async with httpx.AsyncClient() as client:
        response = await client.post(
            RECAPTCHA_VERIFY_URL,
            data={
                "secret": RECAPTCHA_SECRET_KEY,
                "response": captcha_token,
            },
        )
        result = response.json()
        return result.get("success", False)
