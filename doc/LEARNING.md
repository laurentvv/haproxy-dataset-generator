# Learning Log - HAProxy Dataset Generator

## 2026-03-02: Améliorations Gradio 6.8.0

### Découvertes
- Le code était déjà compatible avec Gradio 6.x (theme/css dans launch())
- Streaming visuel nécessite `yield` dans la méthode respond()
- Les générateurs doivent utiliser `yield` partout, pas `return`
- `gr.Error()` ne fonctionne pas correctement après un `yield`
- L'infrastructure d'affichage des sources est en place mais get_sources() retourne une liste vide par défaut
- Les sources doivent être affichées avec leur titre et contenu extrait depuis les documents scrapés, pas avec des liens externes

### Implémentations
- Streaming visuel avec yield pour affichage en temps réel
- Panneau latéral pour afficher les sources
- Exemples de questions pour aider les nouveaux utilisateurs
- Gestion d'erreurs avec try/except
- Indicateurs de progression (statut)
- Sauvegarde/chargement des conversations en JSON
- Accessibilité améliorée avec description des fonctionnalités et raccourcis clavier
- Affichage des sources depuis les documents scrapés (chunks_child.json) avec titre et contenu extrait

### Problèmes corrigés
- Incohérence return vs yield dans respond()
- gr.Error() appelé après yield (supprimé)
- get_sources() vide (ajouté source fictive pour démonstration)
- created_at non initialisé (ajouté datetime.now())
- Sources affichées avec lien externe non fonctionnel (modifié pour afficher titre et contenu extrait)

### Notes
- Les fichiers de sauvegarde de conversation sont nommés: chat_history_YYYYMMDD_HHMMSS.json
- La méthode get_sources() charge les sources depuis chunks_child.json pour afficher le titre et le contenu extrait
- Les sources utilisées lors de la requête sont stockées dans la session via sources_used dans l'état du graphe
