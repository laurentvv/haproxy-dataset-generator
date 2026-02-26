# TODO: Questions à améliorer

## État actuel (après correctifs retriever_v3)

**Score global :** 0.782/1.0 (12/18 questions résolues ≥0.80)

---

## Questions à faible score (<0.80)

### 1. `full_stats_hide` (0.20) ❌

**Question :** "Comment masquer certains serveurs dans les stats ?"

**Problème :** Cette question demande une fonctionnalité qui **n'existe pas dans HAProxy 3.2**.

**Analyse :**
- La commande `stats hide server` n'existe pas dans le socket de management
- La directive `stats hide` n'existe pas dans la configuration
- Les façons correctes de limiter la visibilité des stats sont :
  - `stats scope` (limiter à certains proxies)
  - `disabled` (désactiver un serveur)
  - `stats http-request deny` (accès conditionnel via ACL)

**Actions recommandées :**
- [ ] **Option 1 :** Supprimer cette question du benchmark (obsolète)
- [ ] **Option 2 :** Mettre à jour la question pour refléter la réalité HAProxy 3.2
  ```python
  "question": "Comment limiter la visibilité des statistiques à certains proxies ?"
  "expected_keywords": ["stats", "scope", "proxy", "backend", "frontend"]
  ```
- [ ] **Option 3 :** Ajouter une question alternative sur `stats http-request deny`

**Priorité :** Haute (question trompeuse)

---

### 2. `std_ssl_verify`, `full_ssl_ca_file` (0.64-0.70) ⚠️

**Questions :**
- `std_ssl_verify` : "Comment vérifier un certificat SSL ?"
- `full_ssl_ca_file` : "Comment configurer cafile pour vérifier les certificats clients ?"

**Problème :** Le retrieval trouve les bons chunks mais le LLM ne synthétise pas correctement.

**Analyse :**
- Les chunks retournés contiennent les informations sur `ca-file`, `verify`, `client certificate`
- Category boost ssl↔frontend fonctionne (chunks 5.1 Bind options bien rankés)
- Le LLM rate la réponse car :
  - Information dispersée dans plusieurs chunks (5.1, 5.2, 7.3.4)
  - Prompt LLM ne guide pas assez vers la synthèse multi-chunks

**Actions recommandées :**
- [ ] Améliorer le prompt LLM pour la synthèse multi-chunks SSL
- [ ] Ajouter des exemples few-shot sur SSL dans `llm.py`
- [ ] Tester avec `verify required`, `ca-file`, `crt` comme keywords prioritaires
- [ ] Enrichir les chunks SSL avec plus de contexte (section 5.1 + 5.2 combinées)

**Priorité :** Moyenne (retrieval OK, problème LLM)

---

### 3. `full_acl_negation` (0.64) ⚠️

**Question :** "Comment utiliser la négation dans une ACL ?"

**Problème :** Le retrieval ne trouve pas assez de contexte sur "!", "unless", "negation".

**Analyse :**
- QUERY_EXPANSIONS ajoute "!", "not", "negation", "negated", "unless"
- Mais les chunks HAProxy utilisent surtout `!` et `unless` dans le code
- Le matching texte ne capture pas bien ces opérateurs courts

**Actions recommandées :**
- [ ] Ajouter un boosting spécial pour les opérateurs ACL (`!`, `unless`)
- [ ] Enrichir QUERY_EXPANSIONS avec des exemples concrets :
  ```python
  "negation": ["acl", "!", "not", "negation", "unless", 
               "!{ path_beg", "unless {", "negated condition"]
  ```
- [ ] Ajouter dans IA_CATEGORY_HINTS : `"unless": "acl"`
- [ ] Tester avec title_boost pour chunks contenant "unless" ou "!" dans le titre

**Priorité :** Moyenne (amélioration retrieval possible)

---

## Autres questions limites (0.76-0.79)

### 4. `quick_stick_table` (0.76) ⚠️

**Proche de l'objectif** (+0.04 pour atteindre 0.80)

**Actions :**
- [ ] Ajuster le poids du category boost pour stick-table (actuellement 0.5)
- [ ] Vérifier si le retrieval trouve bien les sections 11.1 et 11.2

---

### 5. `std_backend_server` (0.64) ⚠️

**Problème :** Similaire à SSL, retrieval OK mais LLM rate la synthèse.

**Actions :**
- [ ] Améliorer prompt LLM pour les questions backend/server
- [ ] Ajouter exemples few-shot sur la déclaration de serveurs

---

## Résumé des actions prioritaires

| Priorité | Action | Impact estimé |
|----------|--------|---------------|
| 🔴 Haute | Supprimer/mettre à jour `full_stats_hide` | +0.05 moyenne |
| 🟡 Moyenne | Améliorer prompt LLM pour SSL | +0.10 sur std_ssl_verify, full_ssl_ca_file |
| 🟡 Moyenne | Enrichir QUERY_EXPANSIONS ACL negation | +0.15 sur full_acl_negation |
| 🟢 Basse | Ajuster boost stick-table | +0.04 sur quick_stick_table |

---

## Notes techniques

### Fichiers à modifier

1. **bench_questions.py** - Mettre à jour/supprimer `full_stats_hide`
2. **llm.py** - Améliorer prompt few-shot pour SSL et ACL
3. **retriever_v3.py** - Enrichir QUERY_EXPANSIONS (negation)

### Commandes de test

```bash
# Tester une question spécifique
uv run python 05_bench_targeted.py --questions full_stats_hide,std_ssl_verify,full_acl_negation

# Tester le retrieval
uv run python retriever_v3.py "Comment utiliser unless dans une ACL ?"
uv run python retriever_v3.py "Comment vérifier un certificat client avec cafile ?"
```

---

**Dernière mise à jour :** 2026-02-26
**Benchmark de référence :** bench_v3_targeted_report.json (18 questions, 0.782/1.0)
