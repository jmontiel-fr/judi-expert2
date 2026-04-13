# Politique de Confidentialité

**Judi-Expert — ITechSource**
**Dernière mise à jour : 1er janvier 2026**

---

## 1. Responsable du traitement

Le responsable du traitement des données personnelles est :

**ITechSource**
Adresse : [À compléter]
Email : contact@judi-expert.fr
SIRET : [À compléter]

---

## 2. Données collectées

### 2.1 Site Central (judi-expert.fr)

Dans le cadre de l'utilisation du Site Central, les données personnelles suivantes sont collectées :

| Donnée | Finalité | Obligatoire |
|---|---|---|
| Nom | Identification de l'expert | Oui |
| Prénom | Identification de l'expert | Oui |
| Adresse email | Authentification, communication | Oui |
| Adresse postale | Identification professionnelle | Oui |
| Ville | Identification professionnelle | Oui |
| Code postal | Identification professionnelle | Oui |
| Téléphone | Contact professionnel | Oui |
| Domaine d'expertise | Personnalisation du service | Oui |
| Acceptation newsletter | Communication marketing | Non |

Les données de paiement (numéro de carte bancaire, etc.) sont traitées directement par Stripe et ne sont jamais stockées sur les serveurs de Judi-Expert.

### 2.2 Application Locale

L'Application Locale fonctionne entièrement sur le poste de travail de l'expert. **Aucune donnée d'expertise n'est transmise au Site Central ni à un serveur tiers.** Les seules communications entre l'Application Locale et le Site Central concernent :

- La vérification des tickets d'expertise (transmission du code du ticket uniquement) ;
- Le téléchargement des modules RAG (images Docker).

Les données d'expertise (réquisitions, notes d'entretien, rapports) restent exclusivement stockées sur le disque local de l'expert.

---

## 3. Finalités du traitement

Les données personnelles collectées sur le Site Central sont traitées pour les finalités suivantes :

1. **Gestion des comptes utilisateurs** : création, authentification et administration des comptes experts ;
2. **Fourniture du service** : achat et gestion des tickets d'expertise, distribution des modules RAG ;
3. **Communication** : réponse aux demandes de contact, envoi de notifications relatives au service ;
4. **Newsletter** (si consentement) : envoi d'informations et d'actualités relatives à Judi-Expert ;
5. **Administration** : gestion des experts inscrits, statistiques d'utilisation agrégées ;
6. **Conformité légale** : respect des obligations légales et réglementaires.

---

## 4. Base légale du traitement

Les traitements de données personnelles reposent sur les bases légales suivantes :

| Finalité | Base légale |
|---|---|
| Gestion des comptes et fourniture du service | Exécution du contrat (article 6.1.b du RGPD) |
| Newsletter et communications marketing | Consentement de l'utilisateur (article 6.1.a du RGPD) |
| Conformité légale | Obligation légale (article 6.1.c du RGPD) |
| Statistiques agrégées | Intérêt légitime (article 6.1.f du RGPD) |

---

## 5. Destinataires des données

Les données personnelles peuvent être communiquées aux destinataires suivants :

- **ITechSource** : personnel habilité pour la gestion du service et le support ;
- **Amazon Web Services (AWS)** : hébergeur de l'infrastructure (sous-traitant, région eu-west-3 Paris) ;
- **AWS Cognito** : service d'authentification (sous-traitant) ;
- **Stripe** : prestataire de paiement (sous-traitant, pour les données de transaction uniquement).

Les données personnelles ne sont en aucun cas vendues, louées ou cédées à des tiers à des fins commerciales.

---

## 6. Durée de conservation

Les données personnelles sont conservées pour les durées suivantes :

| Donnée | Durée de conservation |
|---|---|
| Données de compte (nom, prénom, email, adresse, ville, code postal, téléphone, domaine) | Durée de la relation contractuelle + 2 ans. En fin de chaque année, les comptes inactifs sont avertis par email et disposent de 30 jours pour se reconnecter. Sans connexion dans ce délai, le compte est supprimé automatiquement avec toutes les données associées. |
| Données de transaction (tickets, paiements) | 10 ans (obligation comptable) |
| Messages de contact | 2 ans à compter de la réception |
| Données de newsletter | Jusqu'au retrait du consentement |
| Logs de connexion | 1 an (obligation légale) |

À l'expiration de ces durées, les données sont supprimées ou anonymisées de manière irréversible.

---

## 7. Droits des utilisateurs

Conformément au RGPD et à la loi Informatique et Libertés, vous disposez des droits suivants sur vos données personnelles :

- **Droit d'accès** (article 15 du RGPD) : obtenir la confirmation que vos données sont traitées et en recevoir une copie ;
- **Droit de rectification** (article 16 du RGPD) : demander la correction de données inexactes ou incomplètes ;
- **Droit à l'effacement** (article 17 du RGPD) : demander la suppression de vos données, sous réserve des obligations légales de conservation ;
- **Droit à la portabilité** (article 20 du RGPD) : recevoir vos données dans un format structuré, couramment utilisé et lisible par machine ;
- **Droit d'opposition** (article 21 du RGPD) : vous opposer au traitement de vos données pour des motifs légitimes ;
- **Droit à la limitation du traitement** (article 18 du RGPD) : demander la suspension du traitement dans certains cas.

Pour exercer ces droits, vous pouvez :

- Accéder à votre espace personnel sur le Site Central (page `/monespace/profil`) pour modifier ou supprimer votre compte ;
- Nous contacter par email à l'adresse : dpo@judi-expert.fr ;
- Nous contacter via le formulaire de contact : [https://judi-expert.fr/contact](https://judi-expert.fr/contact).

Nous nous engageons à répondre à votre demande dans un délai d'un (1) mois à compter de sa réception.

En cas de désaccord persistant, vous avez le droit d'introduire une réclamation auprès de la CNIL (Commission Nationale de l'Informatique et des Libertés) : [https://www.cnil.fr](https://www.cnil.fr).

---

## 8. Transferts de données

Les données personnelles collectées par le Site Central sont hébergées exclusivement dans la région AWS **eu-west-3 (Paris, France)**.

**Aucun transfert de données personnelles n'est effectué en dehors de l'Union Européenne.**

Les sous-traitants (AWS, Stripe) sont soumis à des clauses contractuelles garantissant un niveau de protection conforme au RGPD.

---

## 9. Sécurité

ITechSource met en œuvre les mesures techniques et organisationnelles appropriées pour protéger les données personnelles :

- **Chiffrement** : les communications sont chiffrées via HTTPS/TLS. Les mots de passe sont hachés avec bcrypt ;
- **Authentification** : gestion sécurisée via AWS Cognito avec politique de mots de passe robuste ;
- **Isolation des données d'expertise** : les données d'expertise restent exclusivement sur le poste local de l'expert et ne transitent jamais par le Site Central ;
- **Engagement de l'utilisateur** : l'expert s'engage lors de son inscription à chiffrer le disque dur de son poste de travail (BitLocker ou équivalent) ;
- **Infrastructure sécurisée** : VPC AWS avec sous-réseaux privés, groupes de sécurité, accès restreint aux bases de données ;
- **Conteneurisation** : isolation des services via Docker (ECS Fargate en production) ;
- **Accès restreint** : seul le personnel habilité d'ITechSource a accès aux données personnelles.

---

## 10. Cookies

Le site Judi-Expert utilise uniquement des cookies strictement nécessaires au fonctionnement du service :

- **Cookies de session** : gestion de l'authentification via AWS Cognito ;
- **Cookies de préférences** : mémorisation des choix de l'utilisateur (domaine, langue).

Aucun cookie publicitaire, analytique ou de suivi tiers n'est déposé. Conformément à la directive ePrivacy, les cookies strictement nécessaires ne requièrent pas le consentement préalable de l'utilisateur.

---

## 11. Modification de la politique

ITechSource se réserve le droit de modifier la présente Politique de Confidentialité à tout moment. Toute modification substantielle sera notifiée aux utilisateurs par email ou par notification lors de la prochaine connexion au Site Central.

La version en vigueur est celle publiée sur le Site Central à la date de consultation.

---

## 12. Contact DPO

Pour toute question relative à la protection de vos données personnelles, vous pouvez contacter notre Délégué à la Protection des Données (DPO) :

- Email : dpo@judi-expert.fr
- Formulaire de contact : [https://judi-expert.fr/contact](https://judi-expert.fr/contact)
- Adresse postale : ITechSource — DPO, [adresse à compléter]
