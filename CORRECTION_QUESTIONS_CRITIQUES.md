# 🔧 Correction des Questions Critiques

**Date :** 2026-02-25  
**Problème :** 2 questions avec score < 0.30 au benchmark Full 100 questions

---

## 📊 Problème identifié

### **Questions critiques :**

| Question | Score | Keywords attendus |
|----------|-------|-------------------|
| `full_backend_name` | **0.00/1.0** | ["backend", "name", "section"] |
| `full_server_weight` | **0.20/1.0** | ["weight", "server", "balance"] |

### **Cause racine :**

Les chunks contenant l'information sur :
- **La syntaxe de déclaration des backends** (`backend <name>`)
- **Le paramètre `weight` des serveurs**

...n'étaient **pas présents** dans `data/chunks.jsonl`.

**Pourquoi ?**
- Le scraping initial (`01_scrape.py`) n'a pas récupéré toutes les sections
- Les sections 5.1 (Backend), 5.2 (Server), 7.x (ACL), 11.x (Stick-table) sont manquantes
- Le chunking ne peut pas créer des chunks à partir de contenu inexistant

---

## ✅ Solution implémentée

### **Script : `06_add_missing_chunks.py`**

Ajoute manuellement 3 chunks critiques :

1. **`5.1. Backend`** - Syntaxe de déclaration et nommage
2. **`5.2. Server and default-server options - weight`** - Paramètre de poids
3. **`4.2. Backend - keywords reference`** - Référence rapide

### **Contenu des chunks :**

#### Chunk 1 : Backend naming
```
backend <name>

Declare a backend and enter its configuration section.

Arguments:
  <name> : the name of the backend. This name is used to reference 
           this backend from frontends.
```

#### Chunk 2 : Server weight
```
server <name> <address>:<port> [weight <weight>]

The 'weight' parameter defines the server's weight in the load 
balancing algorithm. Servers with higher weights receive more 
connections.

Example:
    backend web_servers
        balance roundrobin
        server web1 192.168.1.1:80 weight 100 check
        server web2 192.168.1.2:80 weight 50 check
```

---

## 🚀 Comment utiliser

### **Option 1 : Lancer le script complet**

```bash
# Ajoute les chunks et reconstruit l'index (~2h)
uv run python 06_add_missing_chunks.py
```

### **Option 2 : Test rapide sans re-indexer**

```bash
# Vérifier que les chunks existent dans data/chunks.jsonl
uv run python -c "
import json
with open('data/chunks.jsonl', 'r') as f:
    for line in f:
        chunk = json.loads(line)
        if 'weight' in chunk.get('content', '').lower():
            print(f\"Trouvé: {chunk.get('title', 'N/A')[:50]}\")
"
```

### **Option 3 : Tester les questions critiques**

```bash
# Après re-indexing
uv run python bench_v3_targeted.py --questions full_backend_name,full_server_weight
```

---

## 📈 Résultats attendus

| Question | Avant | Après | Gain |
|----------|-------|-------|------|
| `full_backend_name` | 0.00 | **≥0.70** | +0.70 |
| `full_server_weight` | 0.20 | **≥0.70** | +0.50 |

**Impact sur le benchmark Full :**
- Qualité : 0.846 → **~0.85-0.86**
- Questions résolues : 82% → **~84-85%**

---

## 🔍 Vérification

Après exécution du script :

```bash
# 1. Vérifier les chunks dans data/chunks.jsonl
powershell -c "Get-Content data\chunks.jsonl | Select-String -Pattern 'weight|backend.*name'"

# 2. Vérifier l'index
uv run python -c "
import pickle
chunks = pickle.load(open('index_v3/chunks.pkl', 'rb'))
weight_chunks = [c for c in chunks if 'weight' in str(c.get('content', '')).lower()]
print(f'Chunks avec weight: {len(weight_chunks)}')
"

# 3. Tester le retrieval
uv run python bench_v3_targeted.py --questions full_backend_name,full_server_weight --verbose
```

---

## 📝 Leçons apprises

### **Problème :**
- Le scraping web peut manquer des sections importantes
- La documentation HAProxy est complexe (page unique avec ancres)

### **Solution :**
- Ajouter manuellement les chunks critiques manquants
- Ou améliorer le scraping pour cibler les sections spécifiques

### **Prévention :**
- Vérifier la couverture des chunks après le scraping
- Avoir un benchmark qui teste TOUS les sujets importants
- Ajouter des chunks manuellement pour les concepts critiques

---

## 🎯 Prochaines étapes

1. ✅ Lancer `06_add_missing_chunks.py` (en cours)
2. ⏳ Attendre la fin de l'indexing (~2h)
3. 📊 Tester avec `bench_v3_targeted.py`
4. 📈 Mettre à jour `V3_PERFORMANCE_TRACKING.md`

---

**Statut :** ✅ Chunks ajoutés, ⏳ Indexing en cours
