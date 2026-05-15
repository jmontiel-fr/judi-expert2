# Implementation Plan: Integration Compta

## Overview

Intégration du système de paiement Stripe avec l'application comptable externe (compta-appli) pour la plateforme Judi-Expert. L'implémentation couvre : les métadonnées comptables dans les transactions Stripe, les profils B2B/B2C, l'intégration de la Compta_Library, le bouton de remboursement admin, le cron de relance des abonnements, et la résiliation d'abonnement.

## Tasks

- [x] 1. Modèles de données et migration Alembic
  - [x] 1.1 Ajouter les colonnes B2B/B2C au modèle Expert
    - Modifier `central-site/web/backend/models/expert.py` pour ajouter : `profile_type` (String(3), default "B2C"), `company_address` (Text, nullable), `billing_email` (String(255), nullable), `siret` (String(14), nullable), `rcs` (String(50), nullable)
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 1.2 Créer le modèle Subscription
    - Créer `central-site/web/backend/models/subscription.py` avec les champs : `id`, `expert_id` (FK unique), `stripe_subscription_id`, `status` (active/blocked/terminating/terminated), `current_period_end`, `termination_scheduled_at`, `termination_effective_at`, `payment_failed_at`, `first_rejection_notified_at`, `blocked_at`, `created_at`, `updated_at`
    - Ajouter la relation `subscription` dans le modèle Expert
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 6.1_

  - [x] 1.3 Créer le modèle SubscriptionLog
    - Créer `central-site/web/backend/models/subscription_log.py` avec : `id`, `expert_id` (FK), `action` (String(50)), `details` (Text, nullable), `created_at`
    - _Requirements: 5.5_

  - [x] 1.4 Ajouter les colonnes de remboursement au modèle Ticket
    - Modifier `central-site/web/backend/models/ticket.py` pour ajouter : `refunded_at` (DateTime, nullable), `stripe_refund_id` (String(255), nullable)
    - _Requirements: 4.3_

  - [x] 1.5 Créer la migration Alembic
    - Créer `central-site/web/backend/alembic/versions/XXX_add_compta_integration.py` avec `upgrade()` et `downgrade()` couvrant toutes les modifications de schéma (colonnes Expert, table subscriptions, table subscription_logs, colonnes Ticket)
    - _Requirements: 2.1, 2.2, 4.3, 5.1, 5.5_

- [x] 2. Schémas Pydantic et validation
  - [x] 2.1 Étendre les schémas de profil Expert
    - Modifier `central-site/web/backend/schemas/profile.py` pour ajouter les champs B2B/B2C : `profile_type`, `company_address`, `billing_email`, `siret`, `rcs`
    - Ajouter les validateurs Pydantic : SIRET = exactement 14 chiffres, RCS = format français valide
    - Rendre les champs B2B obligatoires conditionnellement quand `profile_type == "B2B"`
    - _Requirements: 2.1, 2.2, 2.4, 2.5_

  - [x] 2.2 Créer les schémas Subscription
    - Créer `central-site/web/backend/schemas/subscription.py` avec : `SubscriptionStatus`, `SubscriptionResponse`, `TerminationRequest`, `TerminationResponse`, `CronCheckResponse`
    - _Requirements: 5.1, 6.1_

  - [x] 2.3 Écrire les tests de propriété pour la validation SIRET/RCS
    - **Property 3: SIRET and RCS validation**
    - **Validates: Requirements 2.4, 2.5**

- [x] 3. Intégration Compta_Library et service comptable
  - [x] 3.1 Ajouter la dépendance Compta_Library
    - Ajouter `git+https://github.com/jmontiel.fr/itechsource` dans `requirements.txt` (ou `pyproject.toml`) du backend central
    - _Requirements: 3.1_

  - [x] 3.2 Créer le service compta_service
    - Créer `central-site/web/backend/services/compta_service.py` avec la fonction `build_metadata(expert, ticket_config)` qui :
      - Construit les champs communs : `appli="judi-expert"`, `service="ticket-expertise"`, `type` (B2B/B2C), `domaine`
      - Ajoute les champs B2B (`company_address`, `billing_email`, `expert_firstname`, `expert_lastname`, `siret`, `rcs`, `price_ht`) ou B2C (`expert_firstname`, `expert_lastname`, `expert_address`, `price_ttc`)
      - Appelle la Compta_Library pour valider/formater les métadonnées
      - Lève une exception descriptive si la validation échoue
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 3.2, 3.3, 3.4_

  - [x] 3.3 Écrire les tests de propriété pour la construction des métadonnées
    - **Property 1: Metadata correctness by profile type**
    - **Validates: Requirements 1.1, 1.2, 1.3**

  - [x] 3.4 Écrire les tests de propriété pour la validation round-trip
    - **Property 2: Metadata format validation round-trip**
    - **Validates: Requirements 1.4, 3.2**

- [~] 4. Checkpoint — Vérifier les fondations
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Modification du Stripe Service pour les métadonnées
  - [x] 5.1 Intégrer les métadonnées comptables dans la création de session Checkout
    - Modifier `central-site/web/backend/services/stripe_service.py` pour :
      - Charger le profil Expert (B2B/B2C) avant la création de session
      - Appeler `compta_service.build_metadata()` pour obtenir les métadonnées
      - Passer les métadonnées à `stripe.checkout.Session.create(metadata=...)`
      - Gérer les erreurs de validation Compta_Library (HTTP 422)
      - Gérer les erreurs Stripe (HTTP 500, nettoyage du ticket)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 3.2, 3.3_

- [ ] 6. Bouton de remboursement (Admin)
  - [x] 6.1 Créer l'endpoint de remboursement admin
    - Ajouter `POST /api/admin/tickets/{ticket_id}/refund` dans `central-site/web/backend/routers/admin.py`
    - Vérifier que le ticket est "actif" avec un `stripe_payment_id` valide (non "pending-")
    - Appeler `stripe.Refund.create(payment_intent=stripe_payment_id)`
    - En cas de succès : mettre à jour le statut du ticket à "rembourse", enregistrer `refunded_at` et `stripe_refund_id`
    - En cas d'échec Stripe : retourner HTTP 502 avec description de l'erreur
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 6.2 Créer le composant frontend RefundButton
    - Créer `central-site/web/frontend/src/components/RefundButton.tsx`
    - Afficher le bouton "Re-créditer" uniquement si ticket.status === "actif" ET ticket.stripe_payment_id existe ET ne commence pas par "pending-"
    - Appeler l'endpoint `/api/admin/tickets/{ticket_id}/refund` au clic
    - Afficher un message de succès ou d'erreur
    - Ajouter une confirmation avant l'action (modal ou dialog)
    - _Requirements: 4.1, 4.2, 4.4, 4.5_

  - [x] 6.3 Intégrer le RefundButton dans la page admin tickets
    - Modifier `central-site/web/frontend/src/app/admin/page.tsx` pour afficher le `RefundButton` sur chaque ligne de ticket éligible
    - _Requirements: 4.1, 4.5_

  - [x] 6.4 Écrire les tests de propriété pour la visibilité du bouton refund
    - **Property 4: Refund button visibility**
    - **Validates: Requirements 4.1, 4.5**

  - [x] 6.5 Écrire les tests de propriété pour la transition d'état refund
    - **Property 5: Refund state transition**
    - **Validates: Requirements 4.3**

- [~] 7. Checkpoint — Vérifier métadonnées et remboursement
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Service d'abonnement et cron
  - [x] 8.1 Créer le service subscription_service
    - Créer `central-site/web/backend/services/subscription_service.py` avec :
      - `process_payment_failures()` : logique du cron (premier rejet → email relance, 5+ jours → blocage + email suspension)
      - `check_access(expert_id)` : vérifier si l'expert a accès (status != "blocked")
      - `schedule_termination(expert_id)` : programmer la résiliation en fin de mois billing
      - `execute_termination(subscription)` : annuler le paiement Stripe récurrent, envoyer email confirmation
      - Chaque action produit un log dans `subscription_logs`
    - _Requirements: 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 6.4_

  - [x] 8.2 Créer le router internal pour le cron
    - Créer `central-site/web/backend/routers/internal.py` avec :
      - `POST /api/internal/cron/subscription-check` protégé par `X-Cron-Token`
      - Appeler `subscription_service.process_payment_failures()`
      - Retourner `{ "processed": N, "emails_sent": M, "blocked": K }`
    - _Requirements: 5.1, 5.2, 5.3, 5.5_

  - [x] 8.3 Créer le router subscription pour l'expert
    - Créer `central-site/web/backend/routers/subscription.py` avec :
      - `POST /api/subscription/terminate` : programmer la résiliation
      - `GET /api/subscription/status` : retourner le statut de l'abonnement
    - _Requirements: 6.1, 6.4_

  - [x] 8.4 Écrire les tests de propriété pour la machine d'état du cron
    - **Property 6: Cron payment failure state machine**
    - **Validates: Requirements 5.2, 5.3, 5.5**

  - [x] 8.5 Écrire les tests de propriété pour le contrôle d'accès abonnement
    - **Property 7: Subscription access control**
    - **Validates: Requirements 5.4, 6.4**

  - [x] 8.6 Écrire les tests de propriété pour le calcul de date de résiliation
    - **Property 8: Termination date calculation**
    - **Validates: Requirements 6.1**

- [ ] 9. Frontend — Profil facturation et abonnement
  - [x] 9.1 Créer le formulaire de profil facturation
    - Créer `central-site/web/frontend/src/components/ProfileBillingForm.tsx`
    - Sélecteur B2B/B2C avec affichage conditionnel des champs B2B (adresse société, email facturation, SIRET, RCS)
    - Validation côté client : SIRET = 14 chiffres, champs B2B requis si B2B sélectionné
    - Appeler l'API de mise à jour du profil
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [-] 9.2 Intégrer le formulaire dans la page profil
    - Modifier `central-site/web/frontend/src/app/monespace/profil/page.tsx` pour inclure le `ProfileBillingForm`
    - _Requirements: 2.1_

  - [-] 9.3 Créer la page gestion d'abonnement
    - Créer `central-site/web/frontend/src/app/monespace/abonnement/page.tsx`
    - Afficher le statut de l'abonnement (actif, bloqué, en cours de résiliation)
    - Bouton "Résilier mon abonnement" avec confirmation
    - Afficher la date de fin effective si résiliation programmée
    - _Requirements: 6.1, 6.4_

- [ ] 10. Infrastructure — EventBridge + Lambda
  - [-] 10.1 Créer les ressources Terraform pour le cron
    - Ajouter dans `central-site/terraform/` :
      - `aws_cloudwatch_event_rule.cron_abonnement` : `cron(0 8 * * ? *)`
      - `aws_cloudwatch_event_target.cron_lambda` : target vers la Lambda
      - `aws_lambda_function.cron_abonnement` : Lambda Python invoquant `POST /api/internal/cron/subscription-check`
      - `aws_iam_role.cron_lambda_role` : rôle IAM avec permissions minimales
      - `aws_secretsmanager_secret.cron_token` : token d'authentification
    - _Requirements: 5.1_

  - [-] 10.2 Créer le code de la Lambda cron
    - Créer le handler Lambda Python qui :
      - Récupère le token depuis Secrets Manager
      - Appelle l'endpoint interne avec le header `X-Cron-Token`
      - Gère les erreurs (timeout, réponse non-200)
    - _Requirements: 5.1_

- [~] 11. Checkpoint — Vérifier l'ensemble
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. Intégration finale et câblage
  - [x] 12.1 Enregistrer les nouveaux routers dans l'application FastAPI
    - Modifier `central-site/web/backend/main.py` pour inclure les routers : `internal`, `subscription`
    - Vérifier que le router `admin` est bien mis à jour avec le nouvel endpoint refund
    - _Requirements: 4.2, 5.1, 6.1_

  - [x] 12.2 Mettre à jour l'endpoint de mise à jour du profil Expert
    - Modifier le router/service de profil existant pour accepter et persister les champs B2B/B2C
    - Appliquer les validations SIRET/RCS lors de la sauvegarde
    - _Requirements: 2.1, 2.2, 2.4, 2.5_

  - [~] 12.3 Écrire les tests unitaires pour les services
    - Tests unitaires pour `compta_service.build_metadata()` (cas B2B complet, cas B2C complet)
    - Tests unitaires pour `subscription_service.process_payment_failures()` (pas d'échec, déjà bloqué)
    - Tests unitaires pour l'endpoint refund (erreur Stripe mockée, ticket déjà remboursé)
    - _Requirements: 1.1, 1.2, 1.3, 4.3, 4.4, 5.2, 5.3_

  - [~] 12.4 Écrire les tests d'intégration
    - Test création session Checkout avec metadata (Stripe test mode)
    - Test refund via Stripe API (test mode)
    - Test import et validation Compta_Library
    - _Requirements: 1.4, 3.1, 3.2, 4.2_

- [~] 13. Checkpoint final
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- All database changes pass through Alembic migrations (never modify schema directly)
- Compta_Library is installed via `pip install git+https://github.com/jmontiel.fr/itechsource`
- Lambda cron uses a secret token stored in AWS Secrets Manager for authentication
- Frontend components use functional React with hooks (no class components)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3", "1.4", "3.1"] },
    { "id": 1, "tasks": ["1.5", "2.1", "2.2"] },
    { "id": 2, "tasks": ["2.3", "3.2"] },
    { "id": 3, "tasks": ["3.3", "3.4", "5.1"] },
    { "id": 4, "tasks": ["6.1", "8.1"] },
    { "id": 5, "tasks": ["6.2", "6.4", "6.5", "8.2", "8.3"] },
    { "id": 6, "tasks": ["6.3", "8.4", "8.5", "8.6", "9.1"] },
    { "id": 7, "tasks": ["9.2", "9.3", "10.1", "10.2"] },
    { "id": 8, "tasks": ["12.1", "12.2"] },
    { "id": 9, "tasks": ["12.3", "12.4"] }
  ]
}
```
