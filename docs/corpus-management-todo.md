# Corpus Management — Fonctionnalités restantes

## Site Central (Admin)

### 1. Auto-download des PDFs
- Ajouter champ `download_url` dans `contenu.yaml` pour chaque PDF ayant une URL directe
- Endpoint `POST /api/corpus/{domaine}/documents/download-all` qui tente le téléchargement automatique
- Bouton "Télécharger auto" dans l'admin (onglet Corpus)
- Indicateur dans la liste : ✔ téléchargé / * non disponible (upload manuel requis)

### 2. Indicateur de statut dans la liste admin
- Chaque document affiche son statut : présent sur disque ou non
- Les documents non téléchargés sont marqués pour upload manuel

## Site Local (Expert — page Configuration)

### 3. Affichage post-téléchargement
- Après "Télécharger le corpus" ou "Reset" : afficher clairement ✔ téléchargé / ⚠ manquant pour chaque élément
- Distinguer : PDFs, URLs pré-crawlées, documents custom

### 4. Ajout/suppression custom
- ✅ Déjà implémenté : bouton "+ Doc" pour ajouter un PDF custom
- ✅ Déjà implémenté : bouton "+ URL" pour ajouter une URL custom
- ✅ Déjà implémenté : bouton ✕ pour supprimer un élément custom

### 5. Pré-crawl d'une URL custom (côté local)
- Quand l'expert ajoute une URL, proposer un bouton "Pré-crawler" à côté
- Le backend local fait le fetch HTTP + extraction texte + stockage dans le cache custom
- Le texte extrait sera indexé au prochain "Build RAG"

### 6. Téléchargement d'un PDF depuis une URL custom
- L'expert peut fournir une URL pointant vers un PDF
- Le backend local télécharge le PDF et le stocke dans le corpus custom
- Sera indexé au prochain "Build RAG"

### 7. Build RAG amélioré
- ✅ Déjà implémenté : indexe les fichiers locaux + cache + custom
- À améliorer : afficher le détail de ce qui est indexé (nombre de chunks par document)
- À améliorer : ne pas ré-indexer ce qui n'a pas changé (hash de contenu)

## Priorités

1. Auto-download PDFs (admin) — rapide si les URLs sont stables
2. Pré-crawl URL custom (local) — utile pour l'expert
3. Indicateurs visuels de statut — UX
4. Optimisation Build RAG (hash) — performance
