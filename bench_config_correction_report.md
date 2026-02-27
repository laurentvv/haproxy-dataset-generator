# Rapport de Benchmark - Correction de Configuration HAProxy

## Résumé Exécutif

- **Modèle LLM**: gemma3:latest
- **Date du benchmark**: 2026-02-27 10:51:45
- **Nombre total de tests**: 23

## Comparaison Globale

| Métrique | Ollama Seul | Ollama + RAG | Amélioration |
|----------|-------------|-------------|--------------|
| Taux de détection | 🔴 26.1% | 🔴 26.1% | ➡️ 0.0% |
| Conformité syntaxique | 🟢 95.0% | 🟢 96.5% | 📈 +1.5% |
| Précision optimisation | 🔴 0.0% | 🔴 18.3% | ✅ +18.3% |
| Taux d'hallucination | 🔴 3.5% | 🔴 8.7% | ✅ +5.2% |
| Score global | 🟠 50.8% | 🟠 55.0% | 📈 +4.2% |
| Taux de réussite | 🔴 21.7% | 🟠 43.5% | ✅ +21.7% |
| Temps de réponse | 5.839s | 17.150s | ✅ +11310.9%ms |
| Significativité statistique | - | - | ⚠️ Non calculé (scipy non disponible) |

## Analyse par Catégorie

### Catégorie : logic_error

- **Nombre de tests**: 6

| Métrique | Ollama Seul | Ollama + RAG | Amélioration |
|----------|-------------|-------------|--------------|
| Score global | 🟠 41.5% | 🟠 46.2% | 📈 +4.7% |
| Taux de détection | 🔴 0.0% | 🔴 0.0% | ➡️ 0.0% |
| Conformité syntaxique | 🟢 90.0% | 🟢 98.3% | ✅ +8.3% |
| Taux de réussite | 🔴 0.0% | 🔴 16.7% | ✅ +16.7% |

### Catégorie : mixed

- **Nombre de tests**: 2

| Métrique | Ollama Seul | Ollama + RAG | Amélioration |
|----------|-------------|-------------|--------------|
| Score global | 🟠 43.0% | 🟠 43.2% | 📈 +0.2% |
| Taux de détection | 🔴 0.0% | 🔴 0.0% | ➡️ 0.0% |
| Conformité syntaxique | 🟢 95.0% | 🟢 94.0% | 📉 -1.0% |
| Taux de réussite | 🔴 0.0% | 🔴 0.0% | ➡️ 0.0% |

### Catégorie : optimization

- **Nombre de tests**: 5

| Métrique | Ollama Seul | Ollama + RAG | Amélioration |
|----------|-------------|-------------|--------------|
| Score global | 🟡 73.2% | 🟡 74.2% | 📈 +1.0% |
| Taux de détection | 🟢 100.0% | 🟢 100.0% | ➡️ 0.0% |
| Conformité syntaxique | 🟢 96.0% | 🟢 94.0% | 📉 -2.0% |
| Taux de réussite | 🟢 80.0% | 🟢 100.0% | ✅ +20.0% |

### Catégorie : security_error

- **Nombre de tests**: 4

| Métrique | Ollama Seul | Ollama + RAG | Amélioration |
|----------|-------------|-------------|--------------|
| Score global | 🟠 50.7% | 🟡 63.7% | ✅ +13.0% |
| Taux de détection | 🔴 25.0% | 🔴 25.0% | ➡️ 0.0% |
| Conformité syntaxique | 🟢 94.0% | 🟢 95.5% | 📈 +1.5% |
| Taux de réussite | 🔴 25.0% | 🟡 75.0% | ✅ +50.0% |

### Catégorie : syntax_error

- **Nombre de tests**: 6

| Métrique | Ollama Seul | Ollama + RAG | Amélioration |
|----------|-------------|-------------|--------------|
| Score global | 🟠 44.2% | 🟠 46.2% | 📈 +2.0% |
| Taux de détection | 🔴 0.0% | 🔴 0.0% | ➡️ 0.0% |
| Conformité syntaxique | 🟢 100.0% | 🟢 98.3% | 📉 -1.7% |
| Taux de réussite | 🔴 0.0% | 🔴 16.7% | ✅ +16.7% |


## Analyse par Difficulté

### Difficulté : easy

- **Nombre de tests**: 10

| Métrique | Ollama Seul | Ollama + RAG | Amélioration |
|----------|-------------|-------------|--------------|
| Score global | 🟠 51.6% | 🟠 55.1% | 📈 +3.5% |
| Taux de détection | 🔴 30.0% | 🔴 30.0% | ➡️ 0.0% |
| Conformité syntaxique | 🟢 93.6% | 🟢 98.6% | ✅ +5.0% |
| Taux de réussite | 🔴 30.0% | 🟠 40.0% | ✅ +10.0% |

### Difficulté : hard

- **Nombre de tests**: 4

| Métrique | Ollama Seul | Ollama + RAG | Amélioration |
|----------|-------------|-------------|--------------|
| Score global | 🟠 57.8% | 🟠 53.9% | 📉 -3.9% |
| Taux de détection | 🟠 50.0% | 🟠 50.0% | ➡️ 0.0% |
| Conformité syntaxique | 🟢 97.5% | 🟢 92.0% | ❌ -5.5% |
| Taux de réussite | 🔴 25.0% | 🟠 50.0% | ✅ +25.0% |

### Difficulté : medium

- **Nombre de tests**: 9

| Métrique | Ollama Seul | Ollama + RAG | Amélioration |
|----------|-------------|-------------|--------------|
| Score global | 🟠 46.9% | 🟠 55.5% | ✅ +8.7% |
| Taux de détection | 🔴 11.1% | 🔴 11.1% | ➡️ 0.0% |
| Conformité syntaxique | 🟢 95.6% | 🟢 96.2% | 📈 +0.7% |
| Taux de réussite | 🔴 11.1% | 🟠 44.4% | ✅ +33.3% |


## Analyse des Cas d'Échec

⚠️ **31 tests échoués ou problématiques**

### logic_error (11 échecs)

- **Port supérieur à 65535** (Score: 36.0%)
  - ⚠️ Score global insuffisant

- **use_backend avec backend non défini** (Score: 42.0%)
  - ⚠️ Score global insuffisant

- **Option httplog en mode TCP** (Score: 45.0%)
  - ⚠️ Score global insuffisant

- **Timeout avec valeur négative** (Score: 42.0%)
  - ⚠️ Score global insuffisant

- **Deux serveurs avec le même nom** (Score: 42.0%)
  - ⚠️ Score global insuffisant

### mixed (4 échecs)

- **Configuration HTTP complète avec erreurs** (Score: 40.9%)
  - ⚠️ Score global insuffisant

- **Configuration multi-backend avec ACLs** (Score: 45.0%)
  - ⚠️ Score global insuffisant

- **Configuration HTTP complète avec erreurs** (Score: 42.0%)
  - ⚠️ Score global insuffisant

- **Configuration multi-backend avec ACLs** (Score: 44.4%)
  - ⚠️ Score global insuffisant

### optimization (1 échecs)

- **Amélioration de la configuration SSL** (Score: 69.0%)
  - ⚠️ Hallucination élevée: 20.0%

### security_error (4 échecs)

- **SSL activé sans vérification de certificat** (Score: 42.0%)
  - ⚠️ Score global insuffisant

- **Statistiques activées sans authentification** (Score: 43.8%)
  - ⚠️ Score global insuffisant

- **ACL autorisant toutes les adresses IP** (Score: 45.0%)
  - ⚠️ Score global insuffisant

- **Statistiques activées sans authentification** (Score: 43.8%)
  - ⚠️ Score global insuffisant

### syntax_error (11 échecs)

- **Mot-clé 'option' mal orthographié** (Score: 45.0%)
  - ⚠️ Score global insuffisant

- **ACL avec parenthèses manquantes** (Score: 45.0%)
  - ⚠️ Score global insuffisant

- **Chemin de fichier sans guillemets** (Score: 40.0%)
  - ⚠️ Hallucination élevée: 33.3%
  - ⚠️ Score global insuffisant

- **Directive bind avec syntaxe incorrecte** (Score: 45.0%)
  - ⚠️ Score global insuffisant

- **Option httpchk sans paramètres** (Score: 45.0%)
  - ⚠️ Score global insuffisant

### Recommandations

- **Optimisation**: Ajouter plus de cas d'optimisation dans le dataset
- **Cas difficiles**: Considérer l'ajout de prompts spécifiques pour les cas complexes

## Visualisation des Résultats

### Scores Globaux
```
Ollama Seul  │ + 50.81 ███████████████
Ollama + RAG │ + 55.04 ████████████████

              └──────────────────────────────────────
```

### Améliorations par Métrique
```
Détection      │ +  0.00 █
Syntaxe        │ +  1.48 █
Optimisation   │ + 18.26 ██████████████████
Hallucination↓ │ +  5.20 █████
Global         │ +  4.23 ████

                └──────────────────────────────────────
```


## Conclusion et Recommandations

📊 **RAG apporte une légère amélioration**

### Points Forts


### Points d'Attention

- ⚠️ Surcoût temporel important (+11.31s)
- ⚠️ Amélioration globale limitée

### Recommandations

- ⚠️ **Évaluer l'utilité de RAG** (amélioration non significative)
- ❌ Le système nécessite des améliorations majeures
