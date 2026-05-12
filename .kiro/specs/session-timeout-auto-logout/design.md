# Session Timeout Auto-Logout Bugfix Design

## Overview

L'application Judi-Expert (site local et site central) ne déconnecte pas automatiquement l'utilisateur lorsque son token JWT expire après 1 heure d'inactivité. L'utilisateur reste sur la page courante avec un token expiré, provoquant des erreurs 401 silencieuses. Le correctif consiste à :
1. Intercepter les réponses 401 pour déclencher la déconnexion automatique
2. Vérifier proactivement l'expiration du token côté client (au retour d'inactivité et périodiquement)
3. Nettoyer le token et rediriger vers la page d'accueil appropriée

## Glossary

- **Bug_Condition (C)** : L'état où le token JWT est expiré (`currentTime > token.exp`) mais l'utilisateur reste authentifié dans l'interface sans redirection
- **Property (P)** : Le comportement attendu — déconnexion automatique, suppression du token, et redirection vers la page d'accueil
- **Preservation** : Le comportement existant qui doit rester inchangé — navigation normale avec token valide, déconnexion manuelle, pages publiques
- **apiClient** : L'instance axios dans `local-site/web/frontend/src/lib/api.ts` qui gère toutes les communications HTTP du site local
- **AuthContext** : Le contexte React dans `central-site/web/frontend/src/contexts/AuthContext.tsx` qui gère l'état d'authentification du site central
- **TOKEN_KEY** : Clé localStorage — `"token"` (site local) ou `"judi_access_token"` (site central)

## Bug Details

### Bug Condition

Le bug se manifeste lorsque le token JWT expire après 1 heure d'inactivité. Ni le site local ni le site central ne vérifient l'expiration du token côté client, et aucun des deux n'intercepte les réponses HTTP 401 pour déclencher une déconnexion automatique.

**Site local** : L'intercepteur de réponse axios ne gère que l'extraction du message d'erreur, sans traitement spécifique du statut 401.

**Site central** : Les appels API utilisent `fetch` natif sans wrapper centralisé pour la gestion des 401. Le `AuthContext.restoreSession()` appelle `apiGetProfile` au montage mais ne vérifie pas l'expiration du token avant l'appel.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type SessionState { token: string | null, currentTime: number }
  OUTPUT: boolean
  
  IF input.token IS NULL THEN
    RETURN FALSE  // Pas de session active, pas de bug
  END IF
  
  decoded ← decodeJwtPayload(input.token)
  
  RETURN decoded.exp IS NOT NULL
         AND input.currentTime > decoded.exp
         AND userIsStillOnAuthenticatedPage()
         AND tokenIsStillInLocalStorage()
END FUNCTION
```

### Examples

- **Site local — Appel API après expiration** : L'utilisateur est sur `/dossiers/1` avec un token expiré depuis 5 minutes. Il clique sur "Valider l'étape" → l'API retourne 401 → le message d'erreur "Session expirée" s'affiche brièvement mais l'utilisateur reste sur la page sans redirection.
- **Site central — Retour après inactivité** : L'utilisateur laisse l'onglet ouvert 2 heures sur `/tickets`. Il revient et clique sur "Acheter un ticket" → erreur 401 silencieuse, pas de redirection vers `/`.
- **Site local — Navigation après expiration** : L'utilisateur navigue entre les pages du dossier avec un token expiré → les données ne se chargent pas, aucune indication claire que la session est expirée.
- **Site central — Restauration de session** : L'utilisateur recharge la page après 1h30 → `restoreSession()` appelle `apiGetProfile` qui échoue en 401 → le token est supprimé mais sans redirection explicite vers `/`.

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- La navigation et les appels API avec un token valide (non expiré) doivent continuer à fonctionner normalement
- La déconnexion manuelle via le bouton "Déconnexion" doit continuer à fonctionner comme avant
- Les pages publiques (login, accueil non-authentifié) doivent rester accessibles sans déclencher de déconnexion
- L'utilisateur actif dans la période de validité du token ne doit subir aucune interruption
- Le flux d'authentification (login, register, setup) doit rester inchangé

**Scope:**
Toutes les interactions qui n'impliquent PAS un token expiré doivent être complètement non affectées par ce correctif. Cela inclut :
- Les appels API avec un token valide
- La navigation côté client sans appel API
- Les clics sur le bouton de déconnexion manuelle
- L'accès aux pages publiques sans token
- Le rafraîchissement de page avec un token valide

## Hypothesized Root Cause

Based on the code analysis, the root causes are:

1. **Absence d'intercepteur 401 (site local)** : L'intercepteur de réponse axios dans `local-site/web/frontend/src/lib/api.ts` ne traite que l'extraction du message d'erreur (`error.response.data.detail`). Il n'y a aucune logique pour détecter un statut 401 et déclencher la déconnexion/redirection.

2. **Absence de gestion centralisée des 401 (site central)** : Le site central utilise `fetch` natif dans chaque fonction API. La fonction `handleResponse` lance une `ApiError` sur les erreurs mais ne déclenche aucune action de déconnexion. Le `AuthContext` n'a pas de mécanisme pour intercepter les 401 provenant des appels API.

3. **Pas de vérification proactive de l'expiration** : Aucun des deux sites ne décode le JWT côté client pour vérifier `exp` avant d'effectuer un appel API ou lorsque l'utilisateur revient après une période d'inactivité (événements `visibilitychange`, `focus`).

4. **Pas de timer d'expiration** : Aucun mécanisme ne programme un logout automatique basé sur le champ `exp` du token au moment du login.

## Correctness Properties

Property 1: Bug Condition - Auto-déconnexion sur token expiré

_For any_ état de session où le token JWT est expiré (isBugCondition retourne true), le système corrigé SHALL supprimer le token du localStorage, déconnecter l'utilisateur, et le rediriger vers la page d'accueil appropriée (/accueil pour le site local, / pour le site central).

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

Property 2: Preservation - Sessions valides non affectées

_For any_ état de session où le token JWT est valide et non expiré (isBugCondition retourne false), le système corrigé SHALL produire exactement le même comportement que le système original, préservant la navigation normale, les appels API réussis, et l'absence d'interruption de session.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `local-site/web/frontend/src/lib/api.ts`

**Function**: Response interceptor + new utility functions

**Specific Changes**:
1. **Ajouter une fonction `isTokenExpired()`** : Décoder le payload JWT (base64) et comparer `exp` avec `Date.now() / 1000`. Retourne `true` si expiré ou invalide.
   - Utiliser `atob()` pour décoder le payload (partie 2 du JWT)
   - Ajouter une marge de sécurité de 30 secondes (`exp - 30`)

2. **Modifier l'intercepteur de réponse axios** : Ajouter la détection du statut 401 → appeler `clearToken()` → rediriger vers `/accueil` via `window.location.href`.
   - Ne pas rediriger si déjà sur `/login` ou `/accueil`
   - Éviter les redirections multiples simultanées (flag `isRedirecting`)

3. **Ajouter un listener `visibilitychange`** : Quand l'onglet redevient visible, vérifier `isTokenExpired()` et déclencher la déconnexion si nécessaire.

4. **Ajouter un composant/hook `useSessionGuard`** : Vérifie périodiquement (toutes les 60 secondes) la validité du token et déclenche la déconnexion si expiré.

---

**File**: `central-site/web/frontend/src/contexts/AuthContext.tsx`

**Function**: `AuthProvider` + new utility

**Specific Changes**:
1. **Ajouter une fonction `isTokenExpired()`** : Même logique que le site local — décoder le JWT et vérifier `exp`.

2. **Ajouter un wrapper `fetchWithAuth`** ou modifier `handleResponse` dans `api.ts` : Détecter les réponses 401 et appeler `logout()` du contexte + rediriger vers `/`.

3. **Ajouter la vérification au retour d'inactivité** : Listener `visibilitychange` dans le `AuthProvider` qui vérifie l'expiration du token quand l'onglet redevient actif.

4. **Ajouter un timer d'expiration** : Au login, calculer le temps restant avant expiration et programmer un `setTimeout` pour déclencher le logout automatique.

5. **Améliorer `restoreSession()`** : Vérifier `isTokenExpired()` AVANT d'appeler `apiGetProfile()`. Si expiré, supprimer le token et rediriger immédiatement.

---

**File**: `central-site/web/frontend/src/lib/api.ts`

**Function**: `handleResponse`

**Specific Changes**:
1. **Ajouter la gestion du 401 dans `handleResponse`** : Quand le statut est 401, supprimer le token du localStorage et déclencher une redirection vers `/` avant de lancer l'erreur.

## Testing Strategy

### Validation Approach

La stratégie de test suit une approche en deux phases : d'abord, démontrer le bug sur le code non corrigé via des contre-exemples, puis vérifier que le correctif fonctionne et préserve le comportement existant.

### Exploratory Bug Condition Checking

**Goal**: Démontrer le bug AVANT d'implémenter le correctif. Confirmer ou réfuter l'analyse de la cause racine.

**Test Plan**: Écrire des tests unitaires qui simulent des appels API avec un token expiré et vérifient que le système NE déclenche PAS de déconnexion/redirection. Exécuter ces tests sur le code NON corrigé pour observer les échecs.

**Test Cases**:
1. **Local — 401 sans redirection** : Simuler une réponse 401 de l'API → vérifier que le token reste dans localStorage et qu'aucune redirection n'a lieu (échouera sur le code non corrigé car c'est le comportement actuel — le test vérifie l'absence de correction)
2. **Central — 401 sans logout** : Simuler un appel `apiGetProfile` qui retourne 401 → vérifier que `logout()` n'est pas appelé automatiquement
3. **Local — Token expiré sans vérification** : Mettre un token expiré dans localStorage → vérifier qu'aucune vérification proactive ne se déclenche
4. **Central — Visibilité sans check** : Simuler un événement `visibilitychange` avec token expiré → vérifier qu'aucune action n'est prise

**Expected Counterexamples**:
- Le token expiré reste dans localStorage après une réponse 401
- Aucune redirection ne se produit malgré l'expiration du token
- Causes confirmées : absence d'intercepteur 401, absence de vérification proactive

### Fix Checking

**Goal**: Vérifier que pour tous les inputs où la condition de bug est vraie, le système corrigé produit le comportement attendu.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := handleSession_fixed(input)
  ASSERT result.tokenCleared = TRUE
  ASSERT result.redirectedToHome = TRUE
  ASSERT result.userLoggedOut = TRUE
END FOR
```

### Preservation Checking

**Goal**: Vérifier que pour tous les inputs où la condition de bug n'est PAS vraie, le système corrigé produit le même résultat que le système original.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT handleSession_original(input) = handleSession_fixed(input)
END FOR
```

**Testing Approach**: Les tests property-based sont recommandés pour la vérification de préservation car :
- Ils génèrent automatiquement de nombreux cas de test sur le domaine d'entrée
- Ils détectent les cas limites que les tests unitaires manuels pourraient manquer
- Ils fournissent des garanties fortes que le comportement est inchangé pour tous les inputs non-buggy

**Test Plan**: Observer le comportement sur le code NON corrigé pour les tokens valides et les interactions normales, puis écrire des tests property-based capturant ce comportement.

**Test Cases**:
1. **Préservation des appels API valides** : Vérifier que les appels avec un token valide continuent à retourner les données normalement après le correctif
2. **Préservation de la déconnexion manuelle** : Vérifier que le bouton "Déconnexion" continue à fonctionner identiquement
3. **Préservation des pages publiques** : Vérifier que les pages sans authentification ne déclenchent pas de redirection
4. **Préservation du flux de login** : Vérifier que le processus de connexion fonctionne identiquement

### Unit Tests

- Test de `isTokenExpired()` avec différents tokens (valide, expiré, malformé, null)
- Test de l'intercepteur 401 axios (site local) — vérifie clearToken + redirection
- Test de `handleResponse` modifié (site central) — vérifie clearToken + redirection sur 401
- Test du listener `visibilitychange` — vérifie la détection d'expiration au retour
- Test du timer d'expiration — vérifie le déclenchement du logout au bon moment
- Test des cas limites : token sans champ `exp`, token avec `exp` dans le passé immédiat, token expirant pendant un appel long

### Property-Based Tests

- Générer des timestamps aléatoires et des tokens avec différentes valeurs `exp` → vérifier que `isTokenExpired()` retourne le bon résultat pour toute combinaison
- Générer des séquences d'appels API aléatoires avec tokens valides → vérifier qu'aucune déconnexion intempestive ne se produit
- Générer des scénarios d'inactivité aléatoires (durées variées) → vérifier que seuls les cas avec token expiré déclenchent la déconnexion

### Integration Tests

- Test du flux complet : login → attente d'expiration → vérification de la redirection automatique
- Test du flux : login → appel API avec token expiré → vérification de l'interception 401 et redirection
- Test du flux : login → mise en arrière-plan → retour après expiration → vérification de la déconnexion
- Test de non-régression : login → navigation normale avec token valide → aucune interruption
