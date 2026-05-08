"""Service d'authentification AWS Cognito via boto3."""

import os
from typing import Any

import boto3
from botocore.exceptions import ClientError

AWS_REGION = os.environ.get("AWS_REGION", "eu-west-3")
COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID", "")
COGNITO_APP_CLIENT_ID = os.environ.get("COGNITO_APP_CLIENT_ID", "")


def _get_cognito_client():
    """Retourne un client boto3 cognito-idp."""
    return boto3.client("cognito-idp", region_name=AWS_REGION)


def register_user(
    email: str,
    password: str,
    attributes: dict[str, str],
) -> dict[str, Any]:
    """Inscrit un utilisateur dans le User Pool Cognito.

    Args:
        email: Adresse email de l'utilisateur.
        password: Mot de passe choisi.
        attributes: Attributs supplémentaires (nom, prenom, adresse, domaine, etc.).

    Returns:
        Réponse Cognito sign_up.

    Raises:
        ClientError: En cas d'erreur Cognito.
    """
    client = _get_cognito_client()

    user_attributes = [
        {"Name": "email", "Value": email},
    ]
    for key, value in attributes.items():
        user_attributes.append({"Name": f"custom:{key}", "Value": value})

    return client.sign_up(
        ClientId=COGNITO_APP_CLIENT_ID,
        Username=email,
        Password=password,
        UserAttributes=user_attributes,
    )


def confirm_sign_up(email: str, confirmation_code: str) -> dict[str, Any]:
    """Confirme l'inscription d'un utilisateur avec le code reçu par email.

    Args:
        email: Adresse email de l'utilisateur.
        confirmation_code: Code de confirmation reçu par email.

    Returns:
        Réponse Cognito confirm_sign_up.

    Raises:
        ClientError: En cas de code invalide ou expiré.
    """
    client = _get_cognito_client()
    return client.confirm_sign_up(
        ClientId=COGNITO_APP_CLIENT_ID,
        Username=email,
        ConfirmationCode=confirmation_code,
    )


def resend_confirmation_code(email: str) -> dict[str, Any]:
    """Renvoie le code de confirmation par email.

    Args:
        email: Adresse email de l'utilisateur.

    Returns:
        Réponse Cognito resend_confirmation_code.
    """
    client = _get_cognito_client()
    return client.resend_confirmation_code(
        ClientId=COGNITO_APP_CLIENT_ID,
        Username=email,
    )


def login_user(email: str, password: str) -> dict[str, Any]:
    """Authentifie un utilisateur et retourne les tokens Cognito.

    Args:
        email: Adresse email.
        password: Mot de passe.

    Returns:
        Dict contenant AccessToken, IdToken, RefreshToken.

    Raises:
        ClientError: En cas d'identifiants invalides ou d'erreur Cognito.
        NewPasswordRequiredError: Si Cognito exige un changement de mot de passe.
    """
    client = _get_cognito_client()

    response = client.initiate_auth(
        ClientId=COGNITO_APP_CLIENT_ID,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={
            "USERNAME": email,
            "PASSWORD": password,
        },
    )

    # Handle NEW_PASSWORD_REQUIRED challenge (admin first login)
    if response.get("ChallengeName") == "NEW_PASSWORD_REQUIRED":
        raise NewPasswordRequiredError(
            session=response["Session"],
            email=email,
        )

    return response["AuthenticationResult"]


class NewPasswordRequiredError(Exception):
    """Raised when Cognito requires a password change at first login."""

    def __init__(self, session: str, email: str):
        self.session = session
        self.email = email
        super().__init__("New password required")


def respond_to_new_password_challenge(
    email: str, new_password: str, session: str
) -> dict[str, Any]:
    """Répond au challenge NEW_PASSWORD_REQUIRED de Cognito.

    Args:
        email: Adresse email de l'utilisateur.
        new_password: Nouveau mot de passe choisi.
        session: Session du challenge Cognito.

    Returns:
        Dict contenant AccessToken, IdToken, RefreshToken.
    """
    client = _get_cognito_client()

    response = client.respond_to_auth_challenge(
        ClientId=COGNITO_APP_CLIENT_ID,
        ChallengeName="NEW_PASSWORD_REQUIRED",
        Session=session,
        ChallengeResponses={
            "USERNAME": email,
            "NEW_PASSWORD": new_password,
        },
    )
    return response["AuthenticationResult"]


def logout_user(access_token: str) -> dict[str, Any]:
    """Déconnecte globalement un utilisateur (invalide tous les tokens).

    Args:
        access_token: Token d'accès Cognito de l'utilisateur.

    Returns:
        Réponse Cognito global_sign_out.
    """
    client = _get_cognito_client()
    return client.global_sign_out(AccessToken=access_token)


def get_user(access_token: str) -> dict[str, Any]:
    """Récupère les informations de l'utilisateur connecté via son access token.

    Args:
        access_token: Token d'accès Cognito.

    Returns:
        Réponse Cognito get_user contenant Username et UserAttributes.

    Raises:
        ClientError: En cas de token invalide ou d'erreur Cognito.
    """
    client = _get_cognito_client()
    return client.get_user(AccessToken=access_token)


def delete_user(access_token: str) -> dict[str, Any]:
    """Supprime le compte utilisateur de Cognito.

    Args:
        access_token: Token d'accès Cognito de l'utilisateur.

    Returns:
        Réponse Cognito delete_user.
    """
    client = _get_cognito_client()
    return client.delete_user(AccessToken=access_token)


def change_password(
    access_token: str,
    old_password: str,
    new_password: str,
) -> dict[str, Any]:
    """Change le mot de passe d'un utilisateur.

    Args:
        access_token: Token d'accès Cognito.
        old_password: Ancien mot de passe.
        new_password: Nouveau mot de passe.

    Returns:
        Réponse Cognito change_password.
    """
    client = _get_cognito_client()
    return client.change_password(
        AccessToken=access_token,
        PreviousPassword=old_password,
        ProposedPassword=new_password,
    )
