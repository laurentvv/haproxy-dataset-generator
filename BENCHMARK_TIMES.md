# ⏱️ Temps d'exécution réels - Pipeline RAG V3

## Reconstruction complète (2026-02-26)

### Commande
```bash
uv run python 00_rebuild_all.py --no-benchmark
```

### Temps réels mesurés

| Étape | Description | Temps réel |
|-------|-------------|------------|
| **1/4** | Scrapping (docs.haproxy.org) | **00:00:01** |
| **2/4** | Chunking (3651 chunks) | **00:00:00** |
| **3/4** | Indexing (qwen3-embedding:8b) | **02:16:39** |
| **4/4** | Benchmark Full | *Skip* |
| **TOTAL** | **Reconstruction sans benchmark** | **02:16:41** |

### Détails par étape

#### Étape 1 - Scrapping
- **URLs scrapées**: 3 (intro.html, configuration.html, management.html)
- **Sections extraites**: 144
  - intro.html: 12 sections
  - configuration.html: 112 sections
  - management.html: 20 sections
- **Temps**: ~1 minute

#### Étape 2 - Chunking
- **Chunks générés**: 3651
- **Avec code**: 2142 (58%)
- **Taille moyenne**: 668 chars
- **Tags par chunk**: 3.0
- **Temps**: ~1 minute

#### Étape 3 - Indexing
- **Embedding**: qwen3-embedding:8b (4096 dims, MTEB 70.58 #1)
- **Chunks indexés**: 3651
- **Batches**: 37 (100 chunks/batch)
- **Temps par batch**: ~3.7 min
- **Temps total**: 02:16:39

### Performances

| Métrique | Valeur |
|----------|--------|
| **Débit embedding** | ~26.8 chunks/min |
| **Temps par chunk** | ~2.24 secondes |
| **Taille index ChromaDB** | ~46 MB |
| **Taille BM25** | ~5 MB |
| **Taille metadata** | ~1 MB |

---

## Benchmark (à titre indicatif)

### Niveaux de benchmark

| Niveau | Questions | Temps estimé |
|--------|-----------|--------------|
| **quick** | 7 | ~3 min |
| **standard** | 20 | ~8 min |
| **full** | 92 | ~45 min |

### Temps total avec benchmark Full
- **Reconstruction**: 02:16:41
- **Benchmark Full**: ~45 min
- **TOTAL**: **~3h05**

---

## Configuration matérielle (pour référence)

> ⚠️ Les temps peuvent varier selon :
> - Vitesse CPU
> - RAM disponible
> - Vitesse disque (SSD vs HDD)
> - Connexion internet (pour Ollama)
> - Modèle d'embedding utilisé

---

## Commandes utiles

```bash
# Reconstruction complète sans benchmark
uv run python 00_rebuild_all.py --no-benchmark

# Reconstruction avec benchmark automatique
uv run python 00_rebuild_all.py --benchmark

# Lancer le chatbot
uv run python 04_chatbot.py

# Benchmark rapide
uv run python 06_bench_v3.py --level quick

# Benchmark complet
uv run python 06_bench_v3.py --level full
```

---

**Dernière mise à jour**: 2026-02-26  
**Version**: V3 Finale (qwen3-embedding:8b)
