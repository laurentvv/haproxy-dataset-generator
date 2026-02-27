## Qwen Added Memories
- ruff quand tu modifies

---

## 🚨 Benchmark Config Correction - ÉCHEC (2026-02-27)

### Résultats

| Métrique | Ancien (stable) | Nouveau (WIP) | Écart |
|----------|-----------------|---------------|-------|
| **RAG - Taux réussite** | **43.48%** | 30.43% | **-13.05%** ❌ |
| **RAG - Gain vs LLM seul** | **+4.23%** | +2.74% | -1.49% ⚠️ |
| **RAG - Score global** | 55.04% | 53.40% | -1.64% ⚠️ |

### Modifications responsables (NON COMMIT)

| Fichier | Changement | Impact probable |
|---------|------------|-----------------|
| `retriever_v3.py` | Fix slice indices (int vs float), adapt_top_k_by_complexity | ⚠️ Moyen |
| `config.py` | Modifications config | ⚠️ Inconnu |
| `03_indexing.py` | Pipeline indexation | 🔴 **Élevé** |
| `data/sections_enriched.jsonl` | Metadata IA enrichies | 🔴 **Élevé** |
| `index_v3/` | **Nouvel index régénéré** | 🔴 **Principal suspect** |

### Hypothèses de la régression

1. **Nouvel index V3** : Chunks différemment segmentés ou moins pertinents pour la correction de config
2. **Metadata IA** : Keywords/category moins précis dans `sections_enriched.jsonl`
3. **Retrieval modifié** : `adapt_top_k_by_complexity` retourne moins de candidats pertinents

### Leçons apprises

- ❌ **Ne pas régénérer l'index** sans re-valider tous les benchmarks
- ❌ **Modifications `retriever_v3.py`** : Impact majeur sur RAG config correction
- ✅ **Toujours benchmarker** avant/après sur `07_bench_config_correction.py` ET `05_bench_targeted.py`
- ✅ **Garder un backup** de l'index stable (`index_v3_backup/`)

### Prochaines étapes (si on veut fix)

1. Identifier les tests spécifiques qui ont régressé (voir rapport HTML)
2. Comparer les chunks retrievés avant/après pour ces tests
3. Reverter progressivement les changements pour isoler la cause racine

---
