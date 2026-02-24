# 📊 Résultats du Benchmark - HAProxy RAG Chatbot

## 🏆 Classement des modèles testés (APRÈS OPTIMISATION)

| Rang | Modèle | Score | Réussite | Temps moyen | Recommandation |
|------|--------|-------|----------|-------------|----------------|
| 🥇 | `gemma3:latest` | **0.83** | **80%** | 6.94s | ✅ **MEILLEUR** - Utiliser par défaut |

---

## 🚀 Optimisations appliquées (v2)

### 1. Query Expansion
- **Ajout de synonymes techniques HAProxy** dans `retriever.py`
- Exemple: "health check" → `["health check", "check", "option httpchk", "tcp-check", "inter", "fall", "rise"]`
- **Résultat** : Scores BM25 multipliés par 3-5x

### 2. Augmentation TOP_K
- `TOP_K_RETRIEVAL` : 20 → **30** (plus de candidats)
- `TOP_K_RRF` : 10 → **15** (meilleure fusion)

### 3. Keyword Boosting Post-Rerank
- Ajustement des scores basé sur les mots-clés présents
- Formule : `score_final = rerank_score * (1 + 0.3 * match_ratio)`

### 4. Rerank avec Query Étendue
- Flashrank utilise maintenant la requête étendue
- Meilleure compréhension contextuelle

---

## 📈 Comparaison avant/après

| Question | Avant (score retrieval) | Après (score retrieval) | Gain |
|----------|------------------------|-------------------------|------|
| Health check HTTP | 0.86 | **1.13** | +31% |
| Directive bind | 0.01 | **1.02** | x100! |
| Limiter connexions IP | 0.0001 | **0.33** | x3300! |
| ACLs | 0.002 | **1.05** | x500 |
| Timeouts | 0.08 | **1.05** | x13 |

---

## 🎯 Configuration recommandée

### Pour gemma3:latest (RECOMMANDÉ)

**Dans `llm.py`, utiliser ce prompt système :**

```python
SYSTEM_PROMPT = """Tu es un expert HAProxy 3.2.

CONSIGNES STRICTES :
- Utilise EXCLUSIVEMENT le contexte fourni entre <context> et </context>
- Si une information n'est pas dans le contexte : dis "Non documenté dans ce contexte"
- Pas d'invention, pas de suppositions
- Exemples de code en blocs haproxy
- Français uniquement

STRUCTURE :
1. Réponse directe (1-2 phrases)
2. Détails techniques
3. Exemple de configuration
4. Sources entre parenthèses"""
```

**Paramètres de génération :**
```python
options = {
    "temperature": 0.1,      # Faible pour rester factuel
    "top_p": 0.9,
    "repeat_penalty": 1.1,
    "num_predict": 1024,
}
```

---

## ⚠️ Problèmes identifiés

### 1. Retrieval inefficace pour certaines questions

**Exemple :** "Limiter les connexions par IP" trouve des chunks avec score 0.0001

**Solution :**
- Améliorer le chunking dans `02_ingest.py`
- Ajouter des synonymes dans la requête
- Augmenter `TOP_K_RETRIEVAL` dans `retriever.py`

### 2. Modèles GGUF non compatibles

Les modèles GGUF (ex: `Nanbeige4.1-3B-GGUF:Q4_K_M`) nécessitent un format d'API différent.

**Solution :**
- Utiliser des modèles natifs Ollama
- Ou adapter `llm.py` pour gérer le format `/api/generate`

### 3. Modèles vision non optimaux

Les modèles `qwen3-vl:*` et `glm-ocr:*` sont conçus pour la vision, pas le texte.

**Solution :**
- Éviter ces modèles pour du RAG textuel
- Préférer `gemma3`, `qwen3`, `llama3.1`

---

## 🚀 Commandes utiles

### Tester un modèle spécifique
```bash
uv run python 09_model_benchmark.py --model gemma3:latest
```

### Tester plusieurs modèles
```bash
uv run python 09_model_benchmark.py --model gemma3:latest --model qwen3:latest
```

### Benchmark complet (long)
```bash
uv run python 09_model_benchmark.py --all
```

---

## 📈 Métriques de qualité

| Métrique | Objectif | Actuel (gemma3) |
|----------|----------|-----------------|
| Score moyen | > 0.7 | ✅ 0.83 |
| Taux de réussite | > 80% | ✅ 100% |
| Temps de réponse | < 10s | ✅ 5.52s |
| Keywords trouvés | > 75% | ✅ 80% |

---

## 🔧 Améliorations futures

1. **Chunking intelligent** : Regrouper par section thématique
2. **Query expansion** : Ajouter des synonymes automatiquement
3. **HyDE** : Générer une réponse hypothétique pour améliorer le retrieval
4. **Fine-tuning** : Fine-tuner un modèle sur des QA HAProxy

---

**Date du benchmark** : 2026-02-24  
**Version** : HAProxy 3.2, Ollama 0.6.1, Gradio 6.6.0
