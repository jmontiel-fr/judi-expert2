# Sécurité — Judi-Expert

## 1. Architecture de sécurité

### Isolation réseau des conteneurs

L'application locale utilise deux réseaux Docker distincts :

- **Réseau interne** (`internal: true`) : LLM, OCR, RAG, frontend. Ces conteneurs n'ont **aucun accès à Internet**. Les données d'expertise ne peuvent pas fuiter vers l'extérieur.
- **Réseau externe** : seul le backend y est connecté, exclusivement pour communiquer avec le Site Central (vérification de tickets, mises à jour).

```
[Internet] ←→ [Backend] ←→ [Réseau interne Docker]
                              ├── judi-llm (Mistral 7B) — pas d'Internet
                              ├── judi-ocr (Tesseract) — pas d'Internet
                              ├── judi-rag (Qdrant) — pas d'Internet
                              ├── judi-web-frontend — pas d'Internet
                              └── volumes chiffrés (BitLocker)
```

### Intégrité des conteneurs

- Les images Docker sont épinglées par version (pas de tag `latest` en production)
- Les images personnalisées (backend, frontend, OCR) sont construites localement à partir du code source signé
- Les images tierces (Ollama, Qdrant) proviennent de registres officiels Docker Hub
- En production AWS, les images sont stockées dans ECR privé avec scan de vulnérabilités

### Communications sortantes

Le backend ne communique qu'avec :
- `site-central.judi-expert.fr` — vérification de tickets et mises à jour
- Aucune autre communication sortante n'est autorisée
- Les conteneurs internes (LLM, OCR, RAG) ne peuvent physiquement pas accéder à Internet

## 2. Protection des données

### Chiffrement du disque

- **Windows** : BitLocker obligatoire (Windows 11 Pro requis)
- **macOS** : FileVault obligatoire
- Le chiffrement protège les données au repos contre le vol physique du PC

### Données en transit

- Communications backend ↔ site central : HTTPS/TLS 1.3
- Communications internes Docker : réseau isolé, pas de chiffrement nécessaire (même machine)

### Stockage des données

- Toutes les données d'expertise restent sur le PC de l'expert
- Les volumes Docker sont stockés dans le répertoire Docker local
- Aucune donnée d'expertise n'est transmise au cloud
- Seuls les tokens de tickets transitent entre l'application locale et le site central

## 3. Authentification

### Application locale

- JWT local (HS256) avec expiration configurable (24h par défaut)
- Vérification des credentials via le Site Central (Cognito)
- Pas de stockage de mot de passe en local

### Site Central

- AWS Cognito (OAuth 2.0 / OpenID Connect)
- MFA recommandé
- Tokens JWT signés par Cognito

## 4. Conformité

### RGPD

- Données d'expertise traitées uniquement en local (pas de transfert cloud)
- Droit à l'effacement : suppression complète via "Reset complet" du dossier
- Minimisation des données : seul le token ticket transite vers le cloud
- Chiffrement au repos (BitLocker/FileVault)

### AI Act européen

- L'IA est utilisée comme outil d'assistance, pas de décision autonome
- L'expert valide chaque étape du workflow
- Modèle open-source (Mistral 7B, licence Apache 2.0)
- Inférence 100% locale, pas d'appel à des API cloud d'IA

### Expertise judiciaire

- Intégrité des documents : hash SHA-256 de l'archive finale
- Traçabilité : horodatage de chaque étape du workflow
- Non-répudiation : archive ZIP signée avec hash stocké
