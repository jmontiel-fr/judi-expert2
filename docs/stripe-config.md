# Configuration Stripe pour Judi-Expert

## Vue d'ensemble

Judi-Expert utilise Stripe Checkout pour le paiement des tickets d'expertise. Le flux est identique en dev et en prod — seules les clés changent (clés de test vs clés live).

## Étape 1 : Créer un compte Stripe

1. Aller sur https://dashboard.stripe.com/register
2. Créer un compte avec une adresse email professionnelle
3. Confirmer l'email

En mode test, aucune vérification d'identité n'est requise. Pour passer en production, Stripe demandera des informations sur l'entreprise.

## Étape 2 : Récupérer les clés API

### Clés de test (développement)

1. Aller sur https://dashboard.stripe.com/test/apikeys
2. Vérifier que le toggle "Mode test" est activé (bandeau orange en haut)
3. Copier les deux clés :
   - **Clé publiable** (Publishable key) : commence par `pk_test_...`
   - **Clé secrète** (Secret key) : commence par `sk_test_...`

### Clés live (production)

1. Aller sur https://dashboard.stripe.com/apikeys (sans `/test/`)
2. Vérifier que le mode test est désactivé
3. Copier les deux clés :
   - **Clé publiable** : commence par `pk_live_...`
   - **Clé secrète** : commence par `sk_live_...`

> La clé secrète n'est affichée qu'une seule fois à la création. Si elle est perdue, il faut en générer une nouvelle (bouton "Créer une clé secrète").

## Étape 3 : Configurer le webhook (production uniquement)

Le webhook permet à Stripe de notifier le backend quand un paiement est confirmé.

1. Aller sur https://dashboard.stripe.com/webhooks
2. Cliquer "Ajouter un endpoint"
3. URL de l'endpoint : `https://www.judi-expert.fr/api/webhooks/stripe`
4. Événements à écouter : `checkout.session.completed`
5. Cliquer "Ajouter l'endpoint"
6. Copier le **Signing secret** (commence par `whsec_...`)

En dev, le webhook n'est pas nécessaire — les tickets sont générés directement après le paiement Stripe test.

## Étape 4 : Configurer les variables d'environnement

### Variables requises

| Variable | Description | Exemple |
|----------|-------------|---------|
| `STRIPE_SECRET_KEY` | Clé secrète API (backend) | `sk_test_...` ou `sk_live_...` |
| `STRIPE_PUBLISHABLE_KEY` | Clé publiable (frontend) | `pk_test_...` ou `pk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | Secret du webhook | `whsec_...` |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | Clé publiable exposée au frontend Next.js | `pk_test_...` |

### Configuration en développement local

Dans `central-site/docker-compose.dev.yml`, section `backend > environment` :

```yaml
STRIPE_SECRET_KEY: "sk_test_VOTRE_CLE_SECRETE"
STRIPE_PUBLISHABLE_KEY: "pk_test_VOTRE_CLE_PUBLIABLE"
STRIPE_WEBHOOK_SECRET: "whsec_NON_REQUIS_EN_DEV"
```

Section `frontend > args` et `frontend > environment` :

```yaml
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY: "pk_test_VOTRE_CLE_PUBLIABLE"
```

### Configuration en production

Dans le fichier `.env` (ou AWS Systems Manager Parameter Store) :

```env
STRIPE_SECRET_KEY=sk_live_VOTRE_CLE_SECRETE
STRIPE_PUBLISHABLE_KEY=pk_live_VOTRE_CLE_PUBLIABLE
STRIPE_WEBHOOK_SECRET=whsec_VOTRE_SECRET_WEBHOOK
```

## Carte de test pour le développement

En mode test, Stripe accepte des numéros de carte fictifs. Utiliser :

| Scénario | Numéro de carte | Expiration | CVC | Code postal |
|----------|----------------|------------|-----|-------------|
| Paiement réussi | `4242 4242 4242 4242` | N'importe quelle date future (ex: `12/30`) | N'importe quel CVC à 3 chiffres (ex: `123`) | N'importe quel code (ex: `75001`) |
| Paiement refusé | `4000 0000 0000 0002` | Idem | Idem | Idem |
| Authentification 3D Secure requise | `4000 0025 0000 3155` | Idem | Idem | Idem |
| Fonds insuffisants | `4000 0000 0000 9995` | Idem | Idem | Idem |

La carte `4242 4242 4242 4242` est la plus couramment utilisée pour les tests.

> Toutes les cartes de test sont documentées sur https://docs.stripe.com/testing

## Flux de paiement Judi-Expert

```
Expert                    Frontend              Backend               Stripe
  |                          |                     |                    |
  |-- Clic "Acheter" ------>|                     |                    |
  |                          |-- POST /purchase ->|                    |
  |                          |                     |-- Create Session ->|
  |                          |                     |<- checkout_url ----|
  |                          |<- checkout_url -----|                    |
  |<- Redirect Stripe -------|                     |                    |
  |                          |                     |                    |
  |-- Paiement carte ------->|                     |                    |
  |                          |                     |<-- Webhook --------|
  |                          |                     |   (session.completed)
  |                          |                     |-- Génère ticket    |
  |                          |                     |-- Envoie email     |
  |<- Redirect success ------|                     |                    |
  |                          |                     |                    |
```

En mode dev (`APP_ENV=development`), le backend génère directement le ticket sans passer par le webhook Stripe. Le paiement Stripe test est quand même effectué pour valider le flux complet.

## Vérification

1. Démarrer le site central : `bash scripts-dev/dev-central-restart.sh --build`
2. Se connecter avec un compte expert
3. Aller dans Mon Espace > Tickets
4. Cliquer "Acheter un ticket"
5. Remplir le formulaire Stripe avec la carte test `4242 4242 4242 4242`
6. Vérifier que le ticket apparaît dans la liste

Les paiements de test sont visibles sur https://dashboard.stripe.com/test/payments

## Sécurité

- La clé secrète (`sk_...`) ne doit jamais être exposée côté frontend ni commitée dans Git
- Seule la clé publiable (`pk_...`) est exposée au navigateur via `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`
- Le webhook secret (`whsec_...`) protège contre les faux événements
- En production, les clés seront extraites depuis AWS Systems Manager Parameter Store
