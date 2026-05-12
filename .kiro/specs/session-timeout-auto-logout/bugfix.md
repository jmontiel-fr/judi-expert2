# Bugfix Requirements Document

## Introduction

L'application Judi-Expert (site local et site central) ne déconnecte pas automatiquement l'utilisateur lorsque son token JWT expire après 1 heure d'inactivité. L'utilisateur reste sur la page courante avec un token expiré, ce qui provoque des erreurs 401 silencieuses lors des appels API. Ce bug affecte la sécurité de la session et l'expérience utilisateur sur les deux composants du système.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN le token JWT expire après 1 heure d'inactivité sur le site local THEN le système ne détecte pas l'expiration et l'utilisateur reste sur la page courante avec un token invalide

1.2 WHEN le token JWT expire après 1 heure d'inactivité sur le site central THEN le système ne détecte pas l'expiration et l'utilisateur reste sur la page courante avec un token invalide

1.3 WHEN l'utilisateur effectue une action API avec un token expiré THEN le système reçoit une erreur 401 silencieuse sans notification ni redirection

1.4 WHEN l'utilisateur est inactif pendant plus d'une heure et revient interagir avec l'interface THEN le système ne vérifie pas la validité du token avant d'autoriser la navigation

### Expected Behavior (Correct)

2.1 WHEN le token JWT expire après 1 heure d'inactivité sur le site local THEN le système SHALL déconnecter automatiquement l'utilisateur et le rediriger vers la page d'accueil (/accueil)

2.2 WHEN le token JWT expire après 1 heure d'inactivité sur le site central THEN le système SHALL déconnecter automatiquement l'utilisateur et le rediriger vers la page d'accueil (/)

2.3 WHEN l'utilisateur effectue une action API avec un token expiré THEN le système SHALL intercepter la réponse 401, supprimer le token, et rediriger l'utilisateur vers la page d'accueil correspondante

2.4 WHEN l'utilisateur est inactif pendant plus d'une heure et revient interagir avec l'interface THEN le système SHALL vérifier la validité du token et déclencher la déconnexion automatique si le token est expiré

### Unchanged Behavior (Regression Prevention)

3.1 WHEN le token JWT est valide (non expiré) THEN le système SHALL CONTINUE TO permettre la navigation et les appels API normalement sans interruption

3.2 WHEN l'utilisateur se déconnecte manuellement via le bouton "Déconnexion" THEN le système SHALL CONTINUE TO supprimer le token et rediriger vers la page de login (/login pour local)

3.3 WHEN l'utilisateur n'est pas authentifié (pas de token) THEN le système SHALL CONTINUE TO afficher les pages publiques normalement sans déclencher de déconnexion automatique

3.4 WHEN l'utilisateur est actif et utilise l'application dans la période de validité du token THEN le système SHALL CONTINUE TO maintenir la session sans interruption

---

## Bug Condition (Formal)

```pascal
FUNCTION isBugCondition(X)
  INPUT: X of type SessionState { token: JWT, currentTime: Timestamp }
  OUTPUT: boolean
  
  // Returns true when the token is expired (current time > token expiration)
  RETURN X.token IS NOT NULL AND X.currentTime > X.token.exp
END FUNCTION
```

### Property: Fix Checking

```pascal
// Property: Fix Checking — Auto-logout on token expiration
FOR ALL X WHERE isBugCondition(X) DO
  result ← handleSession'(X)
  ASSERT result.tokenCleared = TRUE
    AND result.redirectedToHome = TRUE
    AND result.userLoggedOut = TRUE
END FOR
```

### Property: Preservation Checking

```pascal
// Property: Preservation Checking — Valid sessions unaffected
FOR ALL X WHERE NOT isBugCondition(X) DO
  ASSERT handleSession(X) = handleSession'(X)
END FOR
```
