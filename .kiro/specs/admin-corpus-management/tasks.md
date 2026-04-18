# Plan d'Implémentation : Gestion du Corpus Admin & Page Corpus Publique

## Vue d'ensemble

Implémentation incrémentale de l'enrichissement de la page Corpus publique et du refactoring de la page Admin avec gestion du corpus. Le backend Python (FastAPI) expose de nouveaux endpoints pour lire/écrire les fichiers YAML et gérer les PDF. Le frontend Next.js consomme ces endpoints. Les tâches suivent l'ordre : schémas → service → endpoints publics → endpoints admin → Docker → frontend public → frontend admin → tests.

## Tâches

- [x] 1. Créer les schémas Pydantic et le service corpus
  - [x] 1.1 Ajouter les schémas Pydantic dans `schemas/corpus.py`
    - Ajouter `ContenuItemResponse(BaseModel)` avec les champs `nom`, `description`, `type`, `date_ajout`
    - Ajouter `UrlItemResponse(BaseModel)` avec les champs `nom`, `url`, `description`, `type`, `date_ajout`
    - Ajouter `AddUrlRequest(BaseModel)` avec les champs `nom` (min_length=1), `url` (pattern `^https?://`), `description`, `type` (pattern `^(pdf_externe|site_web)$`)
    - _Exigences : 1.1, 1.2, 6.3, 7.3_

  - [x] 1.2 Créer le service `services/corpus_content_service.py`
    - Implémenter la classe `CorpusContentService` avec `corpus_base_path: Path` en paramètre
    - Méthode `load_contenu(domaine: str) -> list[dict]` : lit et parse `corpus/{domaine}/contenu.yaml`, retourne liste vide si fichier absent
    - Méthode `load_urls(domaine: str) -> list[dict]` : lit et parse `corpus/{domaine}/urls/urls.yaml`, retourne liste vide si fichier absent
    - Méthode `save_pdf(domaine: str, filename: str, content: bytes) -> dict` : enregistre le PDF dans `corpus/{domaine}/documents/`, met à jour `contenu.yaml` avec type `document` et date du jour, lève une erreur si fichier existant
    - Méthode `add_url(domaine: str, entry: dict) -> dict` : ajoute une entrée dans `urls/urls.yaml` avec la date d'ajout courante
    - Méthodes privées `_resolve_contenu_path` et `_resolve_urls_path`
    - Gestion des erreurs : YAML malformé → exception, fichier absent → liste vide
    - _Exigences : 1.1, 1.2, 1.4, 5.3, 5.5, 6.3, 7.3_

  - [x] 1.3 Écrire le test par propriété pour l'aller-retour contenu.yaml
    - **Propriété 1 : Aller-retour de parsing du contenu.yaml**
    - Pour tout ensemble valide d'éléments de contenu, sérialiser en YAML puis appeler `load_contenu()` doit retourner les mêmes éléments
    - Fichier : `tests/property/test_prop_corpus_contenu_roundtrip.py`
    - **Valide : Exigence 1.1**

  - [x] 1.4 Écrire le test par propriété pour l'aller-retour urls.yaml
    - **Propriété 2 : Aller-retour de parsing du urls.yaml**
    - Pour tout ensemble valide d'entrées URL, sérialiser en YAML puis appeler `load_urls()` doit retourner les mêmes entrées
    - Fichier : `tests/property/test_prop_corpus_urls_roundtrip.py`
    - **Valide : Exigence 1.2**

- [x] 2. Implémenter les endpoints publics de contenu corpus
  - [x] 2.1 Ajouter les endpoints `GET` dans `routers/corpus.py`
    - Endpoint `GET /api/corpus/{domaine}/contenu` : valider le domaine via `load_domaines()`, appeler `CorpusContentService.load_contenu()`, retourner `list[ContenuItemResponse]`
    - Endpoint `GET /api/corpus/{domaine}/urls` : valider le domaine via `load_domaines()`, appeler `CorpusContentService.load_urls()`, retourner `list[UrlItemResponse]`
    - Retourner HTTP 404 si le domaine n'existe pas dans `domaines.yaml`
    - Retourner une liste vide si le fichier YAML n'existe pas
    - Ces endpoints ne nécessitent pas d'authentification
    - _Exigences : 1.1, 1.2, 1.3, 1.4, 8.3_

  - [x] 2.2 Écrire les tests unitaires pour les endpoints publics
    - Fichier : `tests/unit/test_corpus_contenu_endpoints.py`
    - Tester : 404 domaine inexistant, liste vide si fichier absent, réponse correcte avec données
    - _Exigences : 1.1, 1.2, 1.3, 1.4_

- [x] 3. Implémenter les endpoints admin de gestion du corpus
  - [x] 3.1 Créer le router `routers/admin_corpus.py`
    - Endpoint `POST /api/admin/corpus/{domaine}/documents` : upload de fichier PDF via `UploadFile`, valider le domaine, vérifier que le fichier est un PDF, vérifier qu'aucun fichier du même nom n'existe, appeler `CorpusContentService.save_pdf()`
    - Endpoint `POST /api/admin/corpus/{domaine}/urls` : accepter `AddUrlRequest`, valider le domaine, appeler `CorpusContentService.add_url()`
    - Protéger les deux endpoints avec la dépendance `get_admin_expert` importée depuis `routers/admin.py`
    - Retourner HTTP 400 si fichier non-PDF, HTTP 409 si doublon, HTTP 404 si domaine inexistant
    - _Exigences : 5.3, 5.4, 5.5, 6.3, 7.3, 8.1, 8.2_

  - [x] 3.2 Enregistrer le nouveau router dans `main.py`
    - Ajouter `from routers.admin_corpus import router as admin_corpus_router`
    - Ajouter `app.include_router(admin_corpus_router, prefix="/api/admin/corpus", tags=["admin-corpus"])`
    - _Exigences : 8.1_

  - [x] 3.3 Écrire le test par propriété pour l'upload PDF
    - **Propriété 4 : Upload PDF persiste le fichier et met à jour contenu.yaml**
    - Pour tout nom de fichier PDF valide et contenu binaire non vide, `save_pdf()` doit créer le fichier et ajouter l'entrée dans `contenu.yaml`
    - Fichier : `tests/property/test_prop_corpus_pdf_upload.py`
    - **Valide : Exigence 5.3**

  - [x] 3.4 Écrire le test par propriété pour l'ajout d'URL
    - **Propriété 5 : Ajout d'URL persiste l'entrée dans urls.yaml**
    - Pour toute entrée URL valide, `add_url()` doit ajouter l'entrée dans `urls/urls.yaml` avec tous les champs préservés
    - Fichier : `tests/property/test_prop_corpus_url_addition.py`
    - **Valide : Exigences 6.3, 7.3**

  - [x] 3.5 Écrire les tests unitaires pour les endpoints admin
    - Fichier : `tests/unit/test_admin_corpus_endpoints.py`
    - Tester : auth requise (401), non-admin (403), non-PDF (400), doublon (409), succès upload, succès ajout URL
    - _Exigences : 5.3, 5.4, 5.5, 6.3, 7.3, 8.1, 8.2_

- [x] 4. Checkpoint — Vérifier le backend
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Modifier le montage Docker du volume corpus
  - [x] 5.1 Modifier `docker-compose.dev.yml` pour le volume corpus en lecture-écriture
    - Changer `../corpus:/data/corpus:ro` en `../corpus:/data/corpus:rw` dans le service `backend`
    - Conserver `../domaines:/data/domaines:ro` inchangé
    - _Exigences : 9.1, 9.2_

- [x] 6. Ajouter les fonctions API frontend et enrichir la page Corpus publique
  - [x] 6.1 Ajouter les nouvelles fonctions API dans `lib/api.ts`
    - Ajouter les interfaces TypeScript : `ContenuItem` (nom, description, type, date_ajout), `UrlItem` (nom, url, description, type, date_ajout), `AddUrlPayload` (nom, url, description, type)
    - Ajouter `apiGetCorpusContenu(domaine: string): Promise<ContenuItem[]>` — appel `GET /api/corpus/{domaine}/contenu`
    - Ajouter `apiGetCorpusUrls(domaine: string): Promise<UrlItem[]>` — appel `GET /api/corpus/{domaine}/urls`
    - Ajouter `apiAdminUploadDocument(token: string, domaine: string, file: File): Promise<ContenuItem>` — appel `POST /api/admin/corpus/{domaine}/documents` avec `FormData`
    - Ajouter `apiAdminAddUrl(token: string, domaine: string, data: AddUrlPayload): Promise<UrlItem>` — appel `POST /api/admin/corpus/{domaine}/urls`
    - _Exigences : 1.1, 1.2, 5.3, 6.3, 7.3_

  - [x] 6.2 Enrichir la page Corpus publique (`app/corpus/page.tsx`)
    - Pour chaque domaine actif, ajouter une section dépliable (accordéon) affichant les documents et les URLs
    - Appeler `apiGetCorpusContenu(domaine)` et `apiGetCorpusUrls(domaine)` pour chaque domaine actif
    - Afficher chaque document avec son nom, sa description et son type
    - Afficher chaque URL avec son nom, sa description et un lien cliquable
    - Pour les domaines inactifs, afficher un badge « Inactif » et le message « Corpus en cours de préparation »
    - Afficher un indicateur de chargement pendant le chargement des données
    - _Exigences : 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 7. Refactoriser la page Admin avec menu horizontal et section Corpus
  - [x] 7.1 Refactoriser la navigation de la page Admin (`app/admin/page.tsx`)
    - Remplacer les onglets actuels (`experts` / `stats`) par un menu horizontal `nav` avec 4 items : « Statistiques », « Experts », « News », « Corpus »
    - Le clic sur « Statistiques » affiche la section statistiques existante (inline)
    - Le clic sur « Experts » affiche la section experts enrichie (inline)
    - Le clic sur « News » navigue vers `/admin/news` (page existante)
    - Le clic sur « Corpus » affiche la nouvelle section corpus (inline)
    - _Exigences : 3.1, 3.2, 3.4, 3.5_

  - [x] 7.2 Enrichir la section Experts avec recherche et compteur
    - Ajouter un champ de recherche au-dessus de la table des experts
    - Filtrer la liste en temps réel par nom, prénom ou email (insensible à la casse)
    - Afficher le nombre d'experts correspondant au filtre à droite du champ de recherche sous la forme « N expert(s) »
    - _Exigences : 3.3, 3.6, 3.7_

  - [x] 7.3 Écrire le test par propriété pour le filtrage des experts
    - **Propriété 3 : Filtrage des experts par recherche**
    - Pour toute liste d'experts et toute chaîne de recherche, le filtrage doit retourner exactement les experts correspondants
    - Fichier : `tests/property/test_prop_expert_search_filter.py`
    - **Valide : Exigences 3.6, 3.7**

  - [x] 7.4 Implémenter la section Admin Corpus
    - Afficher la liste des domaines avec leur statut (actif/inactif)
    - Au clic sur un domaine, afficher le contenu réparti en « Documents » et « URLs » via `apiGetCorpusContenu` et `apiGetCorpusUrls`
    - Afficher chaque document avec nom, description, type et date d'ajout
    - Afficher chaque URL avec nom, URL cliquable, description, type et date d'ajout
    - Ajouter les boutons d'action : « Ajouter un document PDF », « Ajouter une URL de PDF », « Ajouter une URL de site web »
    - _Exigences : 4.1, 4.2, 4.3, 4.4, 5.1, 6.1, 7.1_

  - [x] 7.5 Implémenter les formulaires d'upload et d'ajout d'URLs
    - Formulaire upload PDF : sélecteur de fichier limité aux `.pdf`, appel `apiAdminUploadDocument`, notification de succès, rafraîchissement de la liste
    - Formulaire ajout URL de PDF : champs nom, URL, description, type fixé à `pdf_externe`, validation côté client (URL commence par `http://` ou `https://`, nom non vide), appel `apiAdminAddUrl`
    - Formulaire ajout URL de site web : champs nom, URL, description, type fixé à `site_web`, mêmes validations, appel `apiAdminAddUrl`
    - Afficher les messages d'erreur de validation inline
    - _Exigences : 5.2, 5.6, 6.2, 6.3, 6.4, 6.5, 7.2, 7.3, 7.4, 7.5_

- [x] 8. Checkpoint — Vérifier le frontend et l'intégration
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Tests unitaires du service corpus
  - [x] 9.1 Écrire les tests unitaires pour `corpus_content_service.py`
    - Fichier : `tests/unit/test_corpus_content_service.py`
    - Tester : YAML malformé, fichier absent retourne liste vide, chemins résolus correctement, save_pdf crée le fichier et met à jour le YAML, add_url ajoute l'entrée
    - _Exigences : 1.1, 1.2, 1.4, 5.3, 6.3, 7.3_

- [x] 10. Checkpoint final — Vérification complète
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Les tâches marquées avec `*` sont optionnelles et peuvent être ignorées pour un MVP plus rapide
- Chaque tâche référence les exigences spécifiques pour la traçabilité
- Les checkpoints permettent une validation incrémentale
- Les tests par propriétés valident les 5 propriétés de correction définies dans le document de conception
- Les tests unitaires valident les cas spécifiques et les cas limites
- Le volume Docker `corpus` passe en lecture-écriture pour permettre les uploads (Exigence 9)
