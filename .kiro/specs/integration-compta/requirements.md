# Requirements Document

## Introduction

Intégration du système de paiement Stripe de Judi-Expert avec une application comptable externe (compta-appli). Cette fonctionnalité enrichit les transactions Stripe avec des métadonnées comptables (profil B2B/B2C, données de facturation), ajoute un bouton de remboursement sur la page tickets, et prépare l'infrastructure pour la gestion future des abonnements (cron de relance, suspension, résiliation).

## Glossaire

- **Site_Central**: Application web AWS (FastAPI + Next.js) gérant l'inscription des experts, les paiements Stripe et l'administration
- **Stripe_Service**: Service backend responsable de la création des sessions Checkout et de la vérification des webhooks Stripe
- **Compta_Library**: Bibliothèque partagée fournie par l'application comptable externe (github.com/jmontiel.fr/itechsource) pour la transmission des données de facturation
- **Expert**: Utilisateur inscrit sur le Site Central, expert judiciaire
- **Profil_B2B**: Expert exerçant en société (personne morale), identifié par un numéro SIRET et RCS
- **Profil_B2C**: Expert exerçant en individuel (personne physique), sans structure juridique
- **Ticket**: Droit d'usage unique acheté par un expert pour créer un dossier d'expertise
- **Metadata_Comptable**: Ensemble de champs transmis à Stripe dans les métadonnées de la session Checkout pour exploitation par l'application comptable
- **Cron_Abonnement**: Tâche planifiée quotidienne (AWS EventBridge) pour la gestion des incidents de paiement d'abonnements
- **Refund_Action**: Action de remboursement Stripe déclenchée depuis l'interface d'administration

## Requirements

### Requirement 1: Métadonnées comptables dans les transactions Stripe

**User Story:** As an administrator of the accounting system, I want Stripe transactions to contain structured accounting metadata, so that invoices can be generated automatically by the external accounting application.

#### Acceptance Criteria

1. WHEN a Checkout session is created, THE Stripe_Service SHALL include the following Metadata_Comptable fields: `appli` (value: "judi-expert"), `service` (value: "ticket-expertise"), `type` (value: "B2B" or "B2C" based on Expert profile), `price_ht` (price excluding tax for B2B) or `price_ttc` (price including tax for B2C), and `domaine` (expertise domain of the Expert)
2. WHEN a Checkout session is created for a Profil_B2B Expert, THE Stripe_Service SHALL include in Metadata_Comptable: `company_address`, `billing_email`, `expert_firstname`, `expert_lastname`, `siret`, and `rcs`
3. WHEN a Checkout session is created for a Profil_B2C Expert, THE Stripe_Service SHALL include in Metadata_Comptable: `expert_firstname`, `expert_lastname`, and `expert_address`
4. THE Stripe_Service SHALL transmit Metadata_Comptable using the format specified by the Compta_Library integration guide

### Requirement 2: Profil B2B/B2C de l'expert

**User Story:** As an expert, I want to declare my billing profile (company or individual), so that my invoices are generated with the correct legal information.

#### Acceptance Criteria

1. THE Site_Central SHALL store for each Expert a profile type field with value "B2B" or "B2C"
2. WHEN an Expert has Profil_B2B, THE Site_Central SHALL store: company address, billing email, SIRET number (14 digits), and RCS number
3. WHEN an Expert has Profil_B2C, THE Site_Central SHALL store: expert address (already present in the Expert model)
4. WHEN an Expert registers or updates their profile, THE Site_Central SHALL validate that SIRET contains exactly 14 digits for Profil_B2B
5. WHEN an Expert registers or updates their profile, THE Site_Central SHALL validate that RCS follows the format of a valid French RCS number for Profil_B2B

### Requirement 3: Intégration de la bibliothèque comptable partagée

**User Story:** As a developer, I want to integrate the shared accounting library, so that payment data is transmitted in the format expected by the external accounting application.

#### Acceptance Criteria

1. THE Site_Central SHALL include the Compta_Library as a dependency in the backend
2. THE Stripe_Service SHALL use the Compta_Library to format and validate Metadata_Comptable before passing it to Stripe
3. IF the Compta_Library returns a validation error, THEN THE Stripe_Service SHALL reject the payment creation and return a descriptive error message to the caller
4. THE Compta_Library configuration SHALL specify `appli` as "judi-expert" and `service` as "ticket-expertise"

### Requirement 4: Bouton de remboursement (Re-créditer)

**User Story:** As an administrator, I want a refund button on the ticket display page, so that I can issue Stripe refunds when needed.

#### Acceptance Criteria

1. WHEN the ticket display page is rendered, THE Site_Central SHALL display a "Re-créditer" button for each Ticket with status "actif" that has a valid `stripe_payment_id`
2. WHEN an administrator clicks the "Re-créditer" button, THE Site_Central SHALL initiate a full refund via the Stripe API using the Ticket's `stripe_payment_id`
3. WHEN the Stripe refund succeeds, THE Site_Central SHALL update the Ticket status to "rembourse" and record the refund timestamp
4. IF the Stripe refund fails, THEN THE Site_Central SHALL display an error message with the Stripe error description and keep the Ticket status unchanged
5. WHEN a Ticket has status "rembourse" or "utilise", THE Site_Central SHALL hide the "Re-créditer" button for that Ticket

### Requirement 5: Cron de relance des incidents de paiement d'abonnement

**User Story:** As a platform operator, I want automated handling of subscription payment failures, so that experts are notified and subscriptions are suspended after non-payment.

#### Acceptance Criteria

1. THE Cron_Abonnement SHALL execute daily via AWS EventBridge at a configured time
2. WHEN a subscription payment is rejected for the first time, THE Cron_Abonnement SHALL send an email to the Expert requesting payment regularization within 5 calendar days
3. WHEN 5 calendar days have elapsed since the first rejection email and the payment remains unresolved, THE Cron_Abonnement SHALL block the subscription and send an immediate suspension notification email to the Expert
4. WHEN a subscription is blocked, THE Site_Central SHALL prevent the Expert from using subscription-based services until payment is regularized
5. THE Cron_Abonnement SHALL log each action (email sent, subscription blocked) with timestamp and Expert identifier

### Requirement 6: Résiliation d'abonnement par l'expert

**User Story:** As an expert, I want to close my subscription, so that I stop being billed at the end of the current billing period.

#### Acceptance Criteria

1. WHEN an Expert requests subscription termination, THE Site_Central SHALL schedule the termination for the end of the current billing month
2. WHEN the end of the billing month is reached after a termination request, THE Site_Central SHALL send a subscription termination confirmation email to the Expert
3. WHEN the end of the billing month is reached after a termination request, THE Site_Central SHALL cancel the Stripe recurring payment for that Expert
4. WHILE a termination is scheduled but not yet effective, THE Site_Central SHALL allow the Expert to continue using subscription-based services until the end of the billing month

