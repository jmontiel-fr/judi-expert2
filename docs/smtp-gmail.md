# Configuration SMTP Gmail pour Judi-Expert

## Vue d'ensemble

Judi-Expert utilise un compte Gmail comme serveur SMTP pour l'envoi de tous les emails (tickets, notifications). La même configuration est utilisée en développement local et en production.

## Prérequis

1. Un compte Google (Gmail)
2. L'authentification à deux facteurs (2FA) activée sur le compte
3. Un "Mot de passe d'application" généré (pas le mot de passe du compte)

## Étape 1 : Activer l'authentification à deux facteurs

1. Aller sur https://myaccount.google.com/security
2. Dans la section "Comment vous connecter à Google", cliquer sur "Validation en deux étapes"
3. Suivre les instructions pour activer la 2FA (SMS, application Authenticator, etc.)

## Étape 2 : Générer un mot de passe d'application

Le mot de passe d'application est un code de 16 caractères qui permet à Judi-Expert d'envoyer des emails via votre compte Gmail sans utiliser votre mot de passe principal.

1. Aller sur https://myaccount.google.com/apppasswords
   - Si le lien ne fonctionne pas : Google Account → Sécurité → Validation en deux étapes → Mots de passe des applications
2. Dans le champ "Nom de l'application", saisir : `Judi-Expert`
3. Cliquer sur "Créer"
4. Google affiche un mot de passe de 16 caractères (ex: `abcd efgh ijkl mnop`)
5. **Copier ce mot de passe** — il ne sera plus affiché

> **Important** : Ne pas confondre le mot de passe d'application avec le mot de passe du compte Google. Le mot de passe d'application est spécifique à Judi-Expert et peut être révoqué à tout moment.

## Étape 3 : Configurer les variables d'environnement

### Variables requises

| Variable | Description | Exemple |
|----------|-------------|---------|
| `SMTP_HOST` | Serveur SMTP Gmail | `smtp.gmail.com` |
| `SMTP_PORT` | Port SMTP (TLS) | `587` |
| `SMTP_USER` | Adresse Gmail complète | `judi-expert@gmail.com` |
| `SMTP_PASSWORD` | Mot de passe d'application (16 car.) | `abcd efgh ijkl mnop` |
| `SMTP_FROM_NAME` | Nom affiché dans l'email | `Judi-Expert` |

### Configuration en développement local

Dans `central-site/docker-compose.dev.yml`, section `backend > environment` :

```yaml
SMTP_HOST: "smtp.gmail.com"
SMTP_PORT: "587"
SMTP_USER: "votre-email@gmail.com"
SMTP_PASSWORD: "abcd efgh ijkl mnop"
SMTP_FROM_NAME: "Judi-Expert"
```

### Configuration en production

Dans le fichier `.env` de production (ou AWS Systems Manager Parameter Store) :

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=votre-email@gmail.com
SMTP_PASSWORD=abcdefghijklmnop
SMTP_FROM_NAME=Judi-Expert
```

## Limites Gmail

- **500 emails/jour** pour un compte Gmail standard
- **2000 emails/jour** pour un compte Google Workspace
- Suffisant pour un usage Judi-Expert (quelques dizaines de tickets/jour max)

## Vérification

Pour vérifier que la configuration fonctionne, démarrer le site central et acheter un ticket de test. L'email doit arriver dans la boîte de réception de l'expert.

En cas d'erreur, vérifier les logs du backend :

```bash
docker logs judi-central-backend 2>&1 | grep -i smtp
```

### Erreurs courantes

| Erreur | Cause | Solution |
|--------|-------|----------|
| `Authentication failed` | Mot de passe incorrect | Régénérer un mot de passe d'application |
| `Less secure app access` | 2FA non activée | Activer la 2FA puis générer un mot de passe d'application |
| `Connection timed out` | Port bloqué | Vérifier que le port 587 est ouvert (firewall, Docker) |
| `Daily limit exceeded` | Quota Gmail dépassé | Attendre 24h ou passer à Google Workspace |

## Sécurité

- Le mot de passe d'application est stocké uniquement dans les variables d'environnement (jamais dans le code source ni dans Git)
- En production, il sera extrait depuis AWS Systems Manager Parameter Store
- Le mot de passe d'application peut être révoqué à tout moment depuis https://myaccount.google.com/apppasswords
- Les emails sont envoyés via TLS (chiffrement en transit)
