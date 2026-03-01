# PLAN — Agentic RAG HAProxy avec ChromaDB + LangGraph
> **Pour agent de codage IA** — Pipeline numéroté, zéro suppression du repo existant, développement en parallèle dans `agentic_rag/`

---

## CONTEXTE & OBJECTIF

### Repos de référence
- **Source existante** : `https://github.com/laurentvv/haproxy-dataset-generator`
  - Pipeline RAG hybride HAProxy 3.2 (retriever_v3, Gradio, Ollama)
  - Stack : `uv`, `qwen3-embedding:8b`, `qwen3:latest`, ChromaDB implicite via retriever_v3
  - Pipeline numéroté `00_rebuild_all.py` → `07_bench_config_correction.py`
- **Architecture cible** : `https://github.com/GiovanniPasq/agentic-rag-for-dummies`
  - LangGraph + conversation memory + human-in-the-loop + parent/child indexing
  - Multi-Agent Map-Reduce pour questions complexes

### Règle absolue
> **Ne jamais modifier, déplacer ou supprimer de fichiers existants** dans le repo racine.
> Tout le nouveau code va dans `agentic_rag/`.

### Stack technique retenue
| Composant | Choix | Raison |
|---|---|---|
| Vector store | **ChromaDB** local | Simple, pas de serveur, suffisant pour ~500 pages HAProxy |
| LLM orchestration | **LangGraph** | Conversation memory + human-in-the-loop natif |
| LLM | **Ollama** (`qwen3:latest`) | Cohérence avec repo existant |
| Embeddings | **Ollama** `qwen3-embedding:8b` | Identique au projet principal — même espace vectoriel, benchmarks comparables |
| Interface | **Gradio 6.6.0** | Copie du chatbot `app/` existant, adapté pour pointer sur ChromaDB agentic |
| Gestion deps | **uv** | Cohérence avec repo existant |

---

## STRUCTURE CIBLE COMPLÈTE

```
agentic_rag/                            ← NOUVEAU répertoire (ne touche à rien d'existant)
│
├── 00_rebuild_agentic.py               ← Orchestrateur : lance tout à la suite
├── 01_scrape_verified.py               ← Scraping + analyse hiérarchie parent/child
├── 02_chunking_parent_child.py         ← Chunking hiérarchique aligné HTML HAProxy
├── 03_indexing_chroma.py               ← Indexation ChromaDB (dense search + MMR)
├── 04_agentic_chatbot.py               ← Chatbot LangGraph complet (Gradio)
├── 05_bench_agentic.py                 ← Benchmark comparatif vs retriever_v3 existant
├── 06_eval_parent_child.py             ← Évaluation qualité stratégie parent/child
├── 07_export_dataset_agentic.py        ← Génération dataset Q&A enrichi (fine-tuning)
│
├── app/                                ← COPIE de app/ existant + adaptations retriever
│   ├── gradio_app.py                   ← Titre modifié uniquement
│   ├── chat_interface.py               ← Import rag_system modifié (1 ligne)
│   ├── document_manager.py             ← Copie sans modification
│   └── rag_system.py                   ← RÉÉCRIT : AgenticRAGSystem wrapping agent_graph
│
│
├── rag_agent/                          ← Module LangGraph
│   ├── __init__.py
│   ├── graph.py                        ← Construction et compilation du graphe
│   ├── graph_state.py                  ← State TypedDict (MessagesState étendu)
│   ├── nodes.py                        ← Nœuds : summarize, analyze_rewrite, agent_node
│   ├── edges.py                        ← Routing conditionnel
│   ├── tools.py                        ← search_child_chunks, retrieve_parent_chunks, validate_config
│   ├── schemas.py                      ← Pydantic v2 : QueryAnalysis, etc.
│   └── prompts.py                      ← System prompts HAProxy-specific
│
├── db/
│   ├── chroma_manager.py               ← Setup/reset ChromaDB
│   └── parent_store_manager.py         ← Lecture/écriture JSON store
│
├── scraper/
│   ├── haproxy_scraper.py              ← Scraper dédié HAProxy docs 3.2 (basé sur 01_scrape.py existant)
│   ├── html_structure_analyzer.py      ← Analyse structure HTML → hiérarchie parent/child
│   └── compare_with_reference.py       ← Diff agentic vs projet principal (validation humaine)
│
├── tests/
│   ├── conftest.py                     ← Fixtures pytest partagées
│   ├── test_scraper_alignment.py       ← Vérifie hiérarchie parent/child dans les données
│   ├── test_chunking.py                ← Vérifie tailles, overlap, parent_id linkage
│   ├── test_retrieval.py               ← Teste search_child + retrieve_parent en isolé
│   ├── test_graph_flow.py              ← Teste transitions LangGraph
│   └── test_end_to_end.py              ← Tests E2E avec vraies questions HAProxy
│
├── data_agentic/                       ← Données générées (dans .gitignore)
│   ├── scraped_pages.json
│   ├── hierarchy_report.json
│   ├── scraping_diff_report.json       ← Diff vs projet principal (validation Phase 1)
│   ├── chunks_child.json               ← Dump de vérification des chunks
│   ├── bench_comparison.json
│   ├── parent_child_eval.json
│   └── pipeline_run.log
│
├── index_agentic/
│   └── chroma_db/                      ← Persistance ChromaDB (dans .gitignore)
│
├── parent_store/                       ← JSON des chunks parents (dans .gitignore)
│
├── pyproject_agentic.toml              ← Dépendances isolées (uv)
└── README_AGENTIC.md                   ← Instructions installation + usage
```

---

## INSTRUCTION PRÉLIMINAIRE POUR L'AGENT — context7

> ⚠️ **AVANT D'ÉCRIRE UNE SEULE LIGNE DE CODE**, l'agent doit interroger **context7** pour obtenir les APIs à jour des bibliothèques suivantes. Les APIs changent fréquemment ; ne jamais coder de mémoire.

```
# Requêtes context7 obligatoires (dans cet ordre) :
1. langgraph          → MessagesState, StateGraph, ToolNode, tools_condition,
                        InMemorySaver, interrupt_before, add_node, add_edge,
                        add_conditional_edges, compile
2. langchain-core     → tool decorator, SystemMessage, HumanMessage, AIMessage,
                        RemoveMessage, BaseModel patterns
3. langchain-chroma   → Chroma class, similarity_search_with_score,
                        max_marginal_relevance_search, PersistentClient
4. chromadb           → PersistentClient API, delete_collection
5. langchain-ollama   → ChatOllama, OllamaEmbeddings, with_structured_output
6. langchain-text-splitters → MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
7. pydantic           → v2 BaseModel, Field patterns
8. gradio             → v6.6.0 — ChatInterface, Blocks, gr.State, gr.JSON,
                        gr.Chatbot, streaming via yield, themes API
```

---

## PHASE 0 — Initialisation du projet

### `pyproject_agentic.toml`

```toml
[project]
name = "haproxy-agentic-rag"
version = "0.1.0"
description = "Agentic RAG sur documentation HAProxy 3.2 avec LangGraph + ChromaDB"
requires-python = ">=3.11"

dependencies = [
    # Vérifier versions exactes via context7 avant de figer
    "langgraph>=0.2",
    "langchain-core>=0.3",
    "langchain-ollama>=0.2",       # LLM + embeddings (qwen3-embedding:8b via Ollama)
    "langchain-chroma>=0.1",
    "langchain-text-splitters>=0.3",
    "chromadb>=0.5",
    "gradio==6.6.0",           # version identique au projet principal
    "pydantic>=2.0",
    "httpx>=0.27",
    "beautifulsoup4>=4.12",
    "requests>=2.31",
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
]
```

### `config_agentic.py`

```python
"""Configuration centralisée — modifier ici uniquement."""
from pathlib import Path

# Chemins
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data_agentic"
INDEX_DIR = BASE_DIR / "index_agentic"
CHROMA_PATH = str(INDEX_DIR / "chroma_db")
PARENT_STORE_PATH = BASE_DIR / "parent_store"

# HAProxy docs
HAPROXY_BASE_URL = "https://docs.haproxy.org/3.2/"
HAPROXY_DOC_SECTIONS = [
    "configuration.html",
    "management.html",
    "intro.html",
    "architecture.html",
]

# ChromaDB
COLLECTION_NAME = "haproxy_child_chunks"

# Chunking
CHILD_CHUNK_SIZE = 500
CHILD_CHUNK_OVERLAP = 80
MIN_PARENT_SIZE = 1500
MAX_PARENT_SIZE = 8000

# ChromaDB score threshold (distance cosine : plus petit = plus proche)
SCORE_THRESHOLD = 1.2   # à calibrer via 06_eval_parent_child.py

# Modèles Ollama
LLM_MODEL = "qwen3:latest"
EMBEDDING_MODEL = "qwen3-embedding:8b"   # identique au projet principal

# Retrieval
DEFAULT_K_CHILD = 5
DEFAULT_K_MMR = 5
MMR_FETCH_K = 20

# Création des dossiers au premier import
for d in [DATA_DIR, INDEX_DIR, PARENT_STORE_PATH]:
    d.mkdir(parents=True, exist_ok=True)
```

---

## PHASE 1 — Scraping + vérification complète

> ⛔ **RÈGLE DE LA PHASE 1 : NE PAS PASSER À LA PHASE 2 AVANT VALIDATION HUMAINE EXPLICITE.**
> L'agent s'arrête après chaque étape de cette phase, affiche un rapport lisible, et attend un `✅ OK` de l'utilisateur. Si l'utilisateur signale un problème, l'agent corrige et relance avant de continuer.

---

### Étape 1.0 — Référence : compter les données du projet principal

Avant de scraper quoi que ce soit, l'agent doit **compter ce que le projet principal a déjà scraé** pour avoir une cible de comparaison.

```python
# À exécuter en premier — script de comptage de référence
# scraper/00_count_existing_data.py

import json
from pathlib import Path

# Chercher les données brutes du projet principal
# Typiquement dans data/ à la racine du repo
candidates = [
    Path("data/scraped_pages.json"),
    Path("data/chunks.json"),
    Path("data/documents.json"),
    Path("data/"),       # lister le contenu si pas de nom connu
]

for path in candidates:
    if path.is_file():
        data = json.loads(path.read_text())
        print(f"📄 {path} → {len(data)} entrées")
        # Afficher un échantillon de 3 entrées pour comprendre la structure
        for entry in data[:3]:
            print(f"   Clés : {list(entry.keys()) if isinstance(entry, dict) else type(entry)}")
    elif path.is_dir():
        files = list(path.glob("**/*"))
        print(f"📁 {path}/ → {len(files)} fichiers")
        for f in files[:10]:
            size = f.stat().st_size if f.is_file() else "-"
            print(f"   {f.name} ({size} bytes)")
```

**→ L'agent affiche le résultat et demande à l'utilisateur :**
```
📊 RÉFÉRENCE PROJET PRINCIPAL :
   - data/scraped_pages.json : X entrées
   - Structure d'une entrée : {clés trouvées}

❓ Ces chiffres vous semblent corrects par rapport à ce que vous connaissez du projet ?
   Répondez OK pour continuer, ou précisez si des données manquent.
```

---

### Étape 1.1 — Scraping initial

#### `scraper/haproxy_scraper.py`

**Objectif** : reproduire exactement le périmètre de scraping du projet principal, en ajoutant la hiérarchie parent/child.

**Avant d'écrire le scraper**, l'agent doit lire `01_scrape.py` du projet principal pour :
- Identifier quelles URLs sont scrapées (liste exacte des pages)
- Comprendre les sélecteurs HTML déjà utilisés et qui fonctionnent
- Repérer les éventuelles exclusions ou transformations de contenu

```python
# À lire avant de coder : ../01_scrape.py (projet principal)
# Objectif : copier la liste des URLs cibles, réutiliser les sélecteurs CSS validés
```

**Structure de sortie attendue pour chaque document** :
```python
{
    "url": "https://docs.haproxy.org/3.2/configuration.html#4",
    "title": "4. Global Parameters",
    "content": "...",           # texte nettoyé — même nettoyage que 01_scrape.py
    "parent_url": "https://docs.haproxy.org/3.2/configuration.html",
    "parent_title": "Configuration Manual",
    "depth": 2,                 # 1=page, 2=section h2, 3=sous-section h3
    "section_path": ["Configuration Manual", "Global Parameters"],
    "anchor": "4",
    "source_file": "configuration"
}
```

**Logique** :
1. Lire `../01_scrape.py` pour récupérer la liste exacte des URLs et les sélecteurs
2. Scraper les mêmes pages + extraire la hiérarchie h1/h2/h3 supplémentaire
3. Nettoyer le contenu de manière identique au projet principal
4. Sauvegarder dans `data_agentic/scraped_pages.json`

#### `01_scrape_verified.py`

```python
"""
Étape 1 : Scraping HAProxy docs avec vérification pas-à-pas.

WORKFLOW :
  1. Lire 01_scrape.py du projet principal pour récupérer URLs + sélecteurs
  2. Scraper les mêmes pages en ajoutant l'extraction de hiérarchie
  3. Sauvegarder scraped_pages.json
  4. Afficher un rapport détaillé et ATTENDRE validation utilisateur
  5. Seulement si OK → générer hierarchy_report.json et terminer
"""
import sys
import json
from scraper.haproxy_scraper import scrape_haproxy_docs
from scraper.html_structure_analyzer import analyze_hierarchy
from config_agentic import DATA_DIR

def print_scraping_report(pages: list, reference_count: int):
    """Affiche un rapport lisible pour validation humaine."""

    # Stats globales
    total = len(pages)
    coverage_pct = (total / reference_count * 100) if reference_count else 0

    # Distribution par profondeur
    by_depth = {}
    for p in pages:
        d = p.get("depth", 1)
        by_depth[d] = by_depth.get(d, 0) + 1

    # Pages avec contenu vide ou trop court
    empty = [p for p in pages if len(p.get("content", "")) < 50]
    short = [p for p in pages if 50 <= len(p.get("content", "")) < 200]

    # Pages sans section_path
    no_path = [p for p in pages if not p.get("section_path")]

    # Top sections scrapées
    sections = {}
    for p in pages:
        sp = p.get("section_path", ["?"])
        top = sp[0] if sp else "?"
        sections[top] = sections.get(top, 0) + 1

    print("\n" + "="*60)
    print("📊 RAPPORT DE SCRAPING — VALIDATION REQUISE")
    print("="*60)
    print(f"\n📈 Volume :")
    print(f"   Pages scrapées     : {total}")
    print(f"   Référence projet   : {reference_count}")
    print(f"   Couverture         : {coverage_pct:.1f}%")

    print(f"\n🌲 Hiérarchie (depth) :")
    for depth, count in sorted(by_depth.items()):
        label = {1: "pages racine", 2: "sections h2", 3: "sous-sections h3"}
        print(f"   depth={depth} ({label.get(depth,'?')}) : {count}")

    print(f"\n📚 Top sections :")
    for section, count in sorted(sections.items(), key=lambda x: -x[1])[:10]:
        print(f"   {section:<40} {count} pages")

    print(f"\n⚠️  Anomalies détectées :")
    print(f"   Contenu vide (<50 chars)   : {len(empty)}")
    print(f"   Contenu court (50-200c)    : {len(short)}")
    print(f"   Sans section_path          : {len(no_path)}")

    if empty:
        print(f"\n   URLs vides :")
        for p in empty[:5]:
            print(f"   ⚠️  {p['url']}")

    print("\n" + "="*60)
    print("❓ VALIDATION REQUISE AVANT DE CONTINUER")
    print("="*60)
    print("""
Vérifiez :
  1. Le nombre de pages correspond-il à ce que vous attendez ?
  2. Les sections listées couvrent-elles bien toute la doc HAProxy ?
  3. Y a-t-il des anomalies à corriger (pages vides, manquantes) ?

→ Répondez O pour continuer vers l'étape 1.2 (analyse hiérarchie)
→ Répondez N pour corriger le scraper et relancer
""")

def wait_for_human_validation(step_name: str) -> bool:
    """Attend une confirmation humaine. Retourne True si OK."""
    while True:
        try:
            answer = input(f"[{step_name}] Continuer ? (O/N) : ").strip().upper()
            if answer == "O":
                return True
            elif answer == "N":
                print("❌ Validation refusée. Corriger le problème puis relancer.")
                return False
            else:
                print("   Répondre O (oui) ou N (non)")
        except EOFError:
            # Mode non-interactif (CI, tests) : on passe automatiquement
            print("   [Mode non-interactif] Passage automatique")
            return True

def main():
    # --- Étape 1.0 : Compter la référence ---
    reference_count = 0
    ref_path = DATA_DIR.parent / "data" / "scraped_pages.json"
    if ref_path.exists():
        ref_data = json.loads(ref_path.read_text())
        reference_count = len(ref_data)
        print(f"📌 Référence projet principal : {reference_count} entrées dans {ref_path}")
    else:
        # Chercher d'autres fichiers de données dans data/
        data_dir = DATA_DIR.parent / "data"
        if data_dir.exists():
            for f in data_dir.glob("*.json"):
                try:
                    d = json.loads(f.read_text())
                    if isinstance(d, list) and len(d) > 0:
                        print(f"📌 Référence candidate : {f.name} → {len(d)} entrées")
                        reference_count = max(reference_count, len(d))
                except Exception:
                    pass
        if reference_count == 0:
            print("⚠️  Aucune référence trouvée dans data/ — la couverture sera estimée sans base de comparaison")

    # --- Étape 1.1 : Scraping ---
    print("\n📡 Démarrage du scraping HAProxy docs 3.2...")
    pages = scrape_haproxy_docs()
    print(f"✓ {len(pages)} pages scrapées")

    # Sauvegarde brute immédiate
    out_path = DATA_DIR / "scraped_pages.json"
    out_path.write_text(json.dumps(pages, ensure_ascii=False, indent=2))
    print(f"💾 Sauvegardé : {out_path}")

    # --- Rapport + validation humaine ---
    print_scraping_report(pages, reference_count)

    if not wait_for_human_validation("Scraping"):
        sys.exit(1)

    # --- Étape 1.2 : Analyse hiérarchie (seulement si scraping validé) ---
    print("\n🔍 Analyse de la hiérarchie parent/child...")
    report = analyze_hierarchy(pages)

    report_path = DATA_DIR / "hierarchy_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))

    print(f"\n📊 Rapport hiérarchie :")
    print(f"   Parent coverage   : {report['parent_coverage']:.1%}")
    print(f"   Orphelins         : {report['orphan_children']}")
    print(f"   Avg children/parent : {report.get('avg_children_per_parent', 'N/A')}")

    # Alerte si couverture insuffisante
    if report["parent_coverage"] < 0.90:
        print(f"\n⚠️  ATTENTION : parent_coverage {report['parent_coverage']:.1%} < 90%")
        print("   La hiérarchie parent/child est insuffisante pour le RAG.")
        print("   Causes possibles : pages scrapées trop plates, TOC non parsée.")
        print("   → Indiquer si vous souhaitez continuer quand même ou corriger.")

    if not wait_for_human_validation("Hiérarchie parent/child"):
        sys.exit(1)

    print("\n✅ PHASE 1 VALIDÉE — prêt pour la Phase 2 (chunking)")
    print(f"   Fichiers produits :")
    print(f"   → {out_path}")
    print(f"   → {report_path}")

if __name__ == "__main__":
    main()
```

---

### Étape 1.2 — Analyse de la hiérarchie

#### `scraper/html_structure_analyzer.py`

```python
def analyze_hierarchy(scraped_pages: list) -> dict:
    """
    Analyse la hiérarchie des pages scrapées.
    Retourne un rapport JSON avec :
    - total_pages          : nombre total de documents
    - depth_distribution   : {"1": N, "2": N, "3": N}
    - orphan_children      : liste des URLs depth>1 sans parent_url valide
    - parent_coverage      : float — % de children dont le parent existe dans le dataset
    - avg_children_per_parent : float
    - sections_root        : liste des sections de profondeur 1 (titres principaux)
    - missing_vs_reference : si référence fournie, liste des sections absentes
    """
```

---

### Étape 1.3 — Comparaison croisée avec le projet principal

Un script dédié compare le contenu scraé par l'agentic_rag avec celui du projet principal, **section par section**.

#### `scraper/compare_with_reference.py`

```python
"""
Compare scraped_pages.json (agentic) avec les données du projet principal.
Produit un rapport de diff lisible pour validation humaine.

Usage : uv run python agentic_rag/scraper/compare_with_reference.py
"""
import json
from pathlib import Path
from config_agentic import DATA_DIR

def load_reference() -> list:
    """Cherche et charge les données du projet principal."""
    candidates = [
        DATA_DIR.parent / "data" / "scraped_pages.json",
        DATA_DIR.parent / "data" / "documents.json",
        DATA_DIR.parent / "data" / "chunks.json",
    ]
    for path in candidates:
        if path.exists():
            data = json.loads(path.read_text())
            if isinstance(data, list):
                print(f"✓ Référence chargée : {path} ({len(data)} entrées)")
                return data
    return []

def extract_urls(data: list) -> set:
    """Extrait toutes les URLs ou identifiants uniques d'un dataset."""
    urls = set()
    for entry in data:
        if isinstance(entry, dict):
            url = entry.get("url") or entry.get("source") or entry.get("id", "")
            if url:
                urls.add(url.split("#")[0])  # normaliser : ignorer les ancres
    return urls

def extract_sections(data: list) -> set:
    """Extrait les titres de sections uniques."""
    sections = set()
    for entry in data:
        if isinstance(entry, dict):
            title = entry.get("title") or entry.get("section") or ""
            if title:
                sections.add(title.strip())
    return sections

def extract_content_volume(data: list) -> dict:
    """Calcule le volume de contenu total et par section."""
    total_chars = sum(len(e.get("content", "") or e.get("text", "")) for e in data if isinstance(e, dict))
    return {"total_chars": total_chars, "entries": len(data)}

def main():
    # Charger les deux datasets
    reference = load_reference()
    agentic_path = DATA_DIR / "scraped_pages.json"

    if not agentic_path.exists():
        print("❌ scraped_pages.json introuvable — lancer 01_scrape_verified.py d'abord")
        return

    agentic = json.loads(agentic_path.read_text())

    # Comparaisons
    ref_urls = extract_urls(reference)
    agt_urls = extract_urls(agentic)
    ref_sections = extract_sections(reference)
    agt_sections = extract_sections(agentic)
    ref_volume = extract_content_volume(reference)
    agt_volume = extract_content_volume(agentic)

    # URLs dans référence mais pas dans agentic (données manquantes)
    missing_urls = ref_urls - agt_urls
    # URLs dans agentic mais pas dans référence (données supplémentaires — normal)
    extra_urls = agt_urls - ref_urls
    # Sections manquantes
    missing_sections = ref_sections - agt_sections

    print("\n" + "="*60)
    print("📊 COMPARAISON AGENTIC vs PROJET PRINCIPAL")
    print("="*60)

    print(f"\n📈 Volume global :")
    print(f"   Projet principal  : {ref_volume['entries']} entrées / {ref_volume['total_chars']:,} chars")
    print(f"   Agentic RAG       : {agt_volume['entries']} entrées / {agt_volume['total_chars']:,} chars")
    coverage = agt_volume['total_chars'] / ref_volume['total_chars'] * 100 if ref_volume['total_chars'] else 0
    print(f"   Couverture contenu: {coverage:.1f}%")

    print(f"\n🔗 URLs :")
    print(f"   Communes          : {len(ref_urls & agt_urls)}")
    print(f"   Manquantes        : {len(missing_urls)}")
    print(f"   Supplémentaires   : {len(extra_urls)} (nouvelles sections hiérarchiques — normal)")

    if missing_urls:
        print(f"\n   ⚠️  URLs manquantes ({len(missing_urls)}) :")
        for url in sorted(missing_urls)[:20]:
            print(f"      - {url}")
        if len(missing_urls) > 20:
            print(f"      ... et {len(missing_urls)-20} autres")

    print(f"\n📚 Sections :")
    print(f"   Projet principal  : {len(ref_sections)} sections uniques")
    print(f"   Agentic RAG       : {len(agt_sections)} sections uniques")

    if missing_sections:
        print(f"\n   ⚠️  Sections manquantes ({len(missing_sections)}) :")
        for s in sorted(missing_sections)[:20]:
            print(f"      - {s}")

    print("\n" + "="*60)
    if len(missing_urls) == 0 and len(missing_sections) == 0:
        print("✅ COUVERTURE COMPLÈTE — aucune donnée manquante détectée")
    elif coverage >= 95:
        print(f"⚠️  COUVERTURE QUASI-COMPLÈTE ({coverage:.1f}%) — vérifier les manques ci-dessus")
    else:
        print(f"❌ COUVERTURE INSUFFISANTE ({coverage:.1f}%) — scraper à corriger avant de continuer")
    print("="*60)

    # Sauvegarder le rapport pour référence
    diff_report = {
        "reference_entries": ref_volume["entries"],
        "agentic_entries": agt_volume["entries"],
        "content_coverage_pct": round(coverage, 2),
        "missing_urls": sorted(missing_urls),
        "missing_sections": sorted(missing_sections),
        "extra_urls_count": len(extra_urls),
    }
    out = DATA_DIR / "scraping_diff_report.json"
    out.write_text(json.dumps(diff_report, ensure_ascii=False, indent=2))
    print(f"\n💾 Rapport sauvegardé : {out}")

if __name__ == "__main__":
    main()
```

**→ L'agent exécute ce script et affiche le résultat. Il attend `✅ OK` de l'utilisateur avant de poursuivre.** Si des URLs ou sections manquent, l'agent corrige `haproxy_scraper.py` et relance.

---

### Étape 1.4 — Tests automatiques

#### `tests/test_scraper_alignment.py`

```python
import json
import pytest
from pathlib import Path
from config_agentic import DATA_DIR

@pytest.fixture
def scraped_pages():
    path = DATA_DIR / "scraped_pages.json"
    if not path.exists():
        pytest.skip("scraped_pages.json non disponible — lancer 01_scrape_verified.py")
    return json.loads(path.read_text())

@pytest.fixture
def hierarchy_report():
    path = DATA_DIR / "hierarchy_report.json"
    if not path.exists():
        pytest.skip("hierarchy_report.json non disponible")
    return json.loads(path.read_text())

@pytest.fixture
def diff_report():
    path = DATA_DIR / "scraping_diff_report.json"
    if not path.exists():
        pytest.skip("scraping_diff_report.json non disponible — lancer compare_with_reference.py")
    return json.loads(path.read_text())

def test_all_children_have_parent(scraped_pages):
    """Toute page depth > 1 doit avoir un parent_url non vide."""
    children = [p for p in scraped_pages if p.get("depth", 1) > 1]
    orphans = [p for p in children if not p.get("parent_url")]
    assert len(orphans) == 0, f"{len(orphans)} orphelins : {[o['url'] for o in orphans[:3]]}"

def test_parent_coverage_above_90(hierarchy_report):
    """Au moins 90% des enfants ont un parent valide."""
    coverage = hierarchy_report["parent_coverage"]
    assert coverage >= 0.90, f"parent_coverage = {coverage:.1%} < 90%"

def test_no_duplicate_urls(scraped_pages):
    """Aucune URL dupliquée dans les pages scrapées."""
    urls = [p["url"] for p in scraped_pages]
    dupes = len(urls) - len(set(urls))
    assert dupes == 0, f"{dupes} URLs dupliquées"

def test_content_not_empty(scraped_pages):
    """Toutes les pages ont du contenu substantiel."""
    empty = [p["url"] for p in scraped_pages if len(p.get("content", "")) < 50]
    assert len(empty) == 0, f"{len(empty)} pages avec contenu insuffisant : {empty[:3]}"

def test_section_path_present(scraped_pages):
    """Chaque page doit avoir un section_path non vide."""
    no_path = [p["url"] for p in scraped_pages if not p.get("section_path")]
    assert len(no_path) == 0, f"{len(no_path)} pages sans section_path : {no_path[:3]}"

def test_coverage_vs_reference(diff_report):
    """La couverture du contenu par rapport au projet principal doit être >= 95%."""
    coverage = diff_report.get("content_coverage_pct", 0)
    assert coverage >= 95.0, (
        f"Couverture {coverage:.1f}% < 95% — "
        f"URLs manquantes : {diff_report.get('missing_urls', [])[:5]}"
    )

def test_no_missing_sections(diff_report):
    """Aucune section du projet principal ne doit être absente."""
    missing = diff_report.get("missing_sections", [])
    assert len(missing) == 0, f"{len(missing)} sections manquantes : {missing[:10]}"
```

---

### Résumé du flux de validation Phase 1

```
Agent : lancer 01_scrape_verified.py
  ↓
Agent affiche : rapport de volume + sections scrapées
  ↓
Utilisateur valide (O) ou demande correction (N)
  ↓ (si O)
Agent : lancer compare_with_reference.py
  ↓
Agent affiche : diff vs projet principal (URLs + sections manquantes)
  ↓
Utilisateur valide (O) ou signale des manques (N)
  ↓ (si N) Agent corrige haproxy_scraper.py → retour au début
  ↓ (si O)
Agent : lancer pytest tests/test_scraper_alignment.py
  ↓
Agent affiche : résultat des 7 tests
  ↓
Utilisateur valide (O) → PHASE 1 TERMINÉE, passage Phase 2 autorisé
```

> **L'agent ne lance JAMAIS `02_chunking_parent_child.py` sans que l'utilisateur ait explicitement validé la Phase 1.**

---

## PHASE 2 — Chunking Parent/Child

### `02_chunking_parent_child.py`

**Stratégie de chunking** :
- **Parents** = sections entières extraites du scraping (groupées par `section_path` jusqu'à profondeur 2)
- **Children** = sous-blocs découpés par `RecursiveCharacterTextSplitter`
- Chaque child porte `parent_id` dans ses métadonnées

```python
"""
Étape 2 : Chunking parent/child aligné sur la hiérarchie HAProxy
- Parent chunks : sections complètes (depth 1-2)
- Child chunks : sous-blocs de 500 chars avec overlap 80
- Sauvegarde parents en JSON dans parent_store/
- Sauvegarde children en JSON dans data_agentic/chunks_child.json (vérification)
"""

import json
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from config_agentic import *

def build_parent_chunks(scraped_pages: list) -> list[tuple[str, Document]]:
    """
    Regroupe les pages scrapées en chunks parents.
    Règles :
    - depth == 1 : parent autonome (page entière)
    - depth == 2 : parent = page h2 complète
    - depth == 3 : rattaché à son parent depth-2
    Merge les chunks trop petits (< MIN_PARENT_SIZE)
    Split les chunks trop grands (> MAX_PARENT_SIZE)
    """

def build_child_chunks(parent_pairs: list) -> list[Document]:
    """
    Découpe chaque parent en children.
    Chaque child.metadata contient :
    - parent_id : str (clé du fichier JSON dans parent_store/)
    - source : str (URL de la page)
    - section_path : list[str]
    - depth : int
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHILD_CHUNK_SIZE,
        chunk_overlap=CHILD_CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    ...

def save_parents(parent_pairs: list):
    """Sauvegarde chaque parent en fichier JSON dans parent_store/."""
    for parent_id, doc in parent_pairs:
        filepath = PARENT_STORE_PATH / f"{parent_id}.json"
        filepath.write_text(json.dumps({
            "page_content": doc.page_content,
            "metadata": doc.metadata
        }, ensure_ascii=False, indent=2))

def main():
    pages = json.loads((DATA_DIR / "scraped_pages.json").read_text())

    print("🔨 Construction des chunks parents...")
    parent_pairs = build_parent_chunks(pages)
    save_parents(parent_pairs)
    print(f"✓ {len(parent_pairs)} parents sauvegardés")

    print("✂️  Construction des chunks enfants...")
    child_chunks = build_child_chunks(parent_pairs)
    print(f"✓ {len(child_chunks)} children générés")

    # Dump de vérification
    dump = [{"content": c.page_content[:200], "metadata": c.metadata}
            for c in child_chunks]
    (DATA_DIR / "chunks_child.json").write_text(json.dumps(dump, ensure_ascii=False, indent=2))

    print(f"📊 Stats :")
    print(f"  - Parents : {len(parent_pairs)}")
    print(f"  - Children : {len(child_chunks)}")
    print(f"  - Ratio moyen : {len(child_chunks)/len(parent_pairs):.1f} children/parent")

if __name__ == "__main__":
    main()
```

### `tests/test_chunking.py`

```python
import json
import pytest
from pathlib import Path
from config_agentic import DATA_DIR, PARENT_STORE_PATH, MIN_PARENT_SIZE, MAX_PARENT_SIZE

@pytest.fixture
def child_chunks():
    path = DATA_DIR / "chunks_child.json"
    if not path.exists():
        pytest.skip("chunks_child.json non disponible — lancer 02_chunking_parent_child.py")
    return json.loads(path.read_text())

def test_every_child_has_valid_parent_id(child_chunks):
    """Chaque child doit avoir un parent_id qui pointe vers un fichier JSON existant."""
    invalid = []
    for chunk in child_chunks:
        pid = chunk["metadata"].get("parent_id", "")
        if not pid:
            invalid.append("MISSING")
            continue
        json_path = PARENT_STORE_PATH / f"{pid}.json"
        if not json_path.exists():
            invalid.append(pid)
    assert len(invalid) == 0, f"{len(invalid)} parent_ids invalides : {invalid[:5]}"

def test_parent_size_in_range():
    """95%+ des parents sont entre MIN et MAX chars."""
    parents = list(PARENT_STORE_PATH.glob("*.json"))
    assert len(parents) > 0, "Aucun parent trouvé"
    sizes = [len(json.loads(p.read_text())["page_content"]) for p in parents]
    in_range = sum(MIN_PARENT_SIZE <= s <= MAX_PARENT_SIZE for s in sizes)
    ratio = in_range / len(sizes)
    assert ratio >= 0.90, f"Seulement {ratio:.1%} des parents sont dans la plage [{MIN_PARENT_SIZE}, {MAX_PARENT_SIZE}]"

def test_child_size_in_range(child_chunks):
    """95%+ des children ont entre 100 et 800 chars."""
    sizes = [len(c["content"]) for c in child_chunks]
    in_range = sum(100 <= s <= 800 for s in sizes)
    ratio = in_range / len(sizes)
    assert ratio >= 0.90, f"Seulement {ratio:.1%} des children sont dans la plage [100, 800]"

def test_children_text_is_subset_of_parent(child_chunks):
    """Échantillon : 20 children doivent apparaître dans leur parent."""
    import random
    sample = random.sample(child_chunks, min(20, len(child_chunks)))
    failures = []
    for chunk in sample:
        pid = chunk["metadata"]["parent_id"]
        parent_path = PARENT_STORE_PATH / f"{pid}.json"
        parent = json.loads(parent_path.read_text())
        snippet = chunk["content"][:80]
        if snippet not in parent["page_content"]:
            failures.append(f"Child snippet non trouvé dans parent {pid}")
    assert len(failures) == 0, f"{len(failures)} incohérences parent/child : {failures[:3]}"

def test_all_children_have_required_metadata(child_chunks):
    """Chaque child doit avoir : parent_id, source, section_path."""
    required_keys = {"parent_id", "source", "section_path"}
    missing = [c for c in child_chunks if not required_keys.issubset(c["metadata"].keys())]
    assert len(missing) == 0, f"{len(missing)} children sans métadonnées complètes"
```

---

## PHASE 3 — Indexation ChromaDB

### `db/chroma_manager.py`

```python
"""Gestion de l'instance ChromaDB partagée."""
import chromadb
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from config_agentic import CHROMA_PATH, COLLECTION_NAME, EMBEDDING_MODEL

def get_embeddings() -> OllamaEmbeddings:
    # Même modèle que le projet principal — assure la cohérence des espaces vectoriels
    return OllamaEmbeddings(model=EMBEDDING_MODEL)

def get_chroma_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=CHROMA_PATH)

def get_vector_store(reset: bool = False) -> Chroma:
    client = get_chroma_client()
    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
            print(f"✓ Collection '{COLLECTION_NAME}' supprimée")
        except Exception:
            pass
    return Chroma(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
    )
```

### `03_indexing_chroma.py`

```python
"""
Étape 3 : Indexation des child chunks dans ChromaDB
- Charge les children depuis data_agentic/chunks_child.json
- Reconstruit les Documents LangChain avec métadonnées complètes
- Indexe dans ChromaDB (dense search)
- Vérifie l'indexation avec une requête test
"""

import json
from langchain_core.documents import Document
from db.chroma_manager import get_vector_store
from config_agentic import DATA_DIR, DEFAULT_K_CHILD

def main():
    print("📂 Chargement des child chunks...")
    raw = json.loads((DATA_DIR / "chunks_child.json").read_text())

    # Reconstruction Documents LangChain complets (pas le dump tronqué)
    # → recharger depuis 02_chunking pour avoir le contenu complet
    # (chunks_child.json est un dump de vérification tronqué)
    from agentic_rag.chunking import rebuild_full_children  # à implémenter dans 02
    child_docs = rebuild_full_children()

    print(f"📊 {len(child_docs)} documents à indexer")

    print("🔨 Initialisation ChromaDB (reset=True)...")
    vector_store = get_vector_store(reset=True)

    print("📥 Indexation en cours (batch de 100)...")
    batch_size = 100
    for i in range(0, len(child_docs), batch_size):
        batch = child_docs[i:i+batch_size]
        vector_store.add_documents(batch)
        print(f"  ✓ Batch {i//batch_size + 1}/{(len(child_docs)//batch_size)+1}")

    # Vérification post-indexation
    print("\n🔍 Vérification post-indexation...")
    test_results = vector_store.similarity_search("haproxy frontend configuration", k=3)
    if len(test_results) == 0:
        print("❌ ERREUR : aucun résultat pour la requête test")
        sys.exit(1)

    print(f"✓ {len(test_results)} résultats pour la requête test")
    for r in test_results:
        print(f"  - [{r.metadata.get('section_path', ['?'])[0]}] {r.page_content[:80]}...")

    print("\n✅ Indexation terminée")

if __name__ == "__main__":
    main()
```

### `tests/test_retrieval.py`

```python
import pytest
from db.chroma_manager import get_vector_store
from config_agentic import PARENT_STORE_PATH, SCORE_THRESHOLD, DEFAULT_K_CHILD, MMR_FETCH_K

@pytest.fixture(scope="module")
def vector_store():
    return get_vector_store(reset=False)

def test_search_returns_results(vector_store):
    """Une requête HAProxy typique doit retourner des résultats."""
    results = vector_store.similarity_search("configure frontend timeout", k=DEFAULT_K_CHILD)
    assert len(results) > 0, "Aucun résultat — index vide ?"
    assert all("parent_id" in r.metadata for r in results)

def test_search_with_score_threshold(vector_store):
    """Les résultats doivent avoir un score de distance < SCORE_THRESHOLD."""
    results = vector_store.similarity_search_with_score(
        "haproxy backend server health check", k=DEFAULT_K_CHILD
    )
    assert len(results) > 0
    scores = [score for _, score in results]
    below = sum(s < SCORE_THRESHOLD for s in scores)
    # Au moins la moitié sous le seuil pour une requête pertinente
    assert below >= len(scores) // 2, f"Scores trop élevés : {scores}"

def test_parent_retrieval_from_child(vector_store):
    """Après search_child, retrieve_parent doit retourner le contexte complet."""
    import json
    results = vector_store.similarity_search("haproxy acl rules", k=3)
    parent_ids = list({r.metadata["parent_id"] for r in results})

    loaded = []
    for pid in parent_ids:
        path = PARENT_STORE_PATH / f"{pid}.json"
        assert path.exists(), f"parent_store/{pid}.json introuvable"
        doc = json.loads(path.read_text())
        loaded.append(doc)

    assert len(loaded) > 0

def test_mmr_search_diversity(vector_store):
    """MMR doit retourner des résultats issus de sections différentes."""
    results = vector_store.max_marginal_relevance_search(
        "haproxy configuration", k=DEFAULT_K_CHILD, fetch_k=MMR_FETCH_K
    )
    assert len(results) >= 3
    parent_ids = {r.metadata["parent_id"] for r in results}
    assert len(parent_ids) >= 3, "MMR ne diversifie pas assez les sections"

def test_unrelated_query_low_score(vector_store):
    """Une requête sans rapport avec HAProxy doit avoir des scores élevés (loin)."""
    results = vector_store.similarity_search_with_score(
        "recette de cuisine pour faire une tarte aux pommes", k=3
    )
    if results:
        scores = [s for _, s in results]
        assert all(s > 0.8 for s in scores), f"Scores trop bas pour requête hors-sujet : {scores}"
```

---

## PHASE 4 — Agent LangGraph

### `rag_agent/graph_state.py`

```python
"""Définition de l'état du graphe LangGraph."""
# Vérifier avec context7 que MessagesState est toujours l'import correct
from langgraph.graph import MessagesState
from pydantic import BaseModel, Field
from typing import Annotated
import operator

class State(MessagesState):
    """État étendu avec mémoire de conversation."""
    questionIsClear: bool = False
    conversation_summary: str = ""
    sources_used: list[str] = []    # parent_ids utilisés dans la réponse
```

### `rag_agent/schemas.py`

```python
"""Schémas Pydantic v2 pour les sorties structurées."""
from pydantic import BaseModel, Field
from typing import List

class QueryAnalysis(BaseModel):
    """Analyse et réécriture de la requête utilisateur."""
    is_clear: bool = Field(
        description="True si la question est claire et peut être recherchée"
    )
    questions: List[str] = Field(
        description="Liste de questions réécrites, autonomes et optimisées pour la recherche"
    )
    clarification_needed: str = Field(
        default="",
        description="Explication de pourquoi la question est floue (si is_clear=False)"
    )
```

### `rag_agent/prompts.py`

```python
"""System prompts spécialisés HAProxy."""

AGENT_SYSTEM_PROMPT = """
Tu es un expert de la documentation HAProxy 3.2. Tu DOIS utiliser les outils
disponibles pour répondre à toute question.

WORKFLOW OBLIGATOIRE (à suivre pour CHAQUE question) :

1. Appeler `search_child_chunks` avec la query (k=5)
2. Examiner les chunks retournés — identifier les parent_ids pertinents
3. Appeler `retrieve_parent_chunks` avec ces parent_ids pour le contexte complet
4. Si le contexte est insuffisant : reformuler la query et rechercher UNE FOIS de plus
5. Répondre en utilisant UNIQUEMENT les informations trouvées dans les chunks

RÈGLES STRICTES :
- Ne jamais inventer de configuration HAProxy
- Toujours citer la section source (section_path des métadonnées)
- Si une réponse contient un bloc de config HAProxy : appeler `validate_haproxy_config`
- Si aucune information trouvée : dire clairement "Cette information n'est pas dans la documentation HAProxy 3.2 disponible"
- Donner des exemples de configuration quand c'est pertinent

FORMAT DE RÉPONSE :
- Répondre en français si la question est en français
- Inclure des blocs de code pour les configurations
- Mentionner la section de la doc en fin de réponse : *Source : [section_path]*
"""

QUERY_REWRITE_SYSTEM_PROMPT = """
Réécris la requête utilisateur pour la rendre optimale pour une recherche
dans la documentation HAProxy 3.2.

INSTRUCTIONS :
1. Résoudre les références pronominales ("it", "ça", "le") grâce au contexte de conversation
2. Éclater les questions multiples en sous-questions distinctes (max 3)
3. Utiliser la terminologie HAProxy exacte (frontend, backend, listen, acl, server, etc.)
4. Supprimer le remplissage conversationnel
5. Marquer comme unclear : gibberish, insultes, questions sans objet clair
"""
```

### `rag_agent/tools.py`

```python
"""Outils de retrieval pour l'agent LangGraph."""
import json
import sys
from typing import List
from pathlib import Path
from langchain_core.tools import tool
from db.chroma_manager import get_vector_store
from config_agentic import PARENT_STORE_PATH, DEFAULT_K_CHILD, SCORE_THRESHOLD

# Instance partagée (lazy init)
_vector_store = None

def _get_vs():
    global _vector_store
    if _vector_store is None:
        _vector_store = get_vector_store(reset=False)
    return _vector_store

@tool
def search_child_chunks(query: str, k: int = DEFAULT_K_CHILD) -> List[dict]:
    """
    Recherche les K chunks enfants les plus pertinents pour une query.

    Args:
        query: La question ou requête de recherche
        k: Nombre de résultats à retourner (défaut: 5)

    Returns:
        Liste de dicts avec content, parent_id, source, section_path, score
    """
    try:
        results = _get_vs().similarity_search_with_score(query, k=k)
        filtered = [
            {
                "content": doc.page_content,
                "parent_id": doc.metadata.get("parent_id", ""),
                "source": doc.metadata.get("source", ""),
                "section_path": doc.metadata.get("section_path", []),
                "score": float(score),
            }
            for doc, score in results
            if score < SCORE_THRESHOLD
        ]
        return filtered if filtered else []
    except Exception as e:
        return [{"error": str(e)}]

@tool
def retrieve_parent_chunks(parent_ids: List[str]) -> List[dict]:
    """
    Récupère le contexte complet des chunks parents par leurs IDs.

    Args:
        parent_ids: Liste des parent_id à récupérer

    Returns:
        Liste de dicts avec content, parent_id, metadata
    """
    unique_ids = list(set(parent_ids))
    results = []
    for pid in unique_ids:
        path = PARENT_STORE_PATH / f"{pid}.json"
        if path.exists():
            try:
                doc = json.loads(path.read_text())
                results.append({
                    "content": doc["page_content"],
                    "parent_id": pid,
                    "metadata": doc["metadata"]
                })
            except Exception as e:
                results.append({"error": f"Erreur lecture {pid}: {e}"})
        else:
            results.append({"error": f"parent_id introuvable: {pid}"})
    return results

@tool
def validate_haproxy_config(config_block: str) -> dict:
    """
    Valide un bloc de configuration HAProxy en utilisant le validateur du repo existant.
    Appeler uniquement si la réponse contient un exemple de configuration HAProxy.

    Args:
        config_block: Le bloc de configuration à valider

    Returns:
        Dict avec is_valid (bool) et errors (list)
    """
    try:
        # Wrapper autour de haproxy_validator.py existant dans le repo racine
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from haproxy_validator import validate_config
        result = validate_config(config_block)
        return {"is_valid": result.get("valid", False), "errors": result.get("errors", [])}
    except ImportError:
        return {"is_valid": None, "errors": ["haproxy_validator non disponible"]}
    except Exception as e:
        return {"is_valid": None, "errors": [str(e)]}
```

### `rag_agent/nodes.py`

```python
"""
Nœuds du graphe LangGraph.
IMPORTANT : vérifier avec context7 les imports exacts de langgraph avant de coder.
"""
from typing import Literal
# Vérifier imports via context7 :
from langgraph.graph import MessagesState
from langchain_core.messages import (
    HumanMessage, AIMessage, SystemMessage, RemoveMessage
)
from langchain_ollama import ChatOllama
from rag_agent.graph_state import State
from rag_agent.schemas import QueryAnalysis
from rag_agent.prompts import AGENT_SYSTEM_PROMPT, QUERY_REWRITE_SYSTEM_PROMPT
from rag_agent.tools import search_child_chunks, retrieve_parent_chunks, validate_haproxy_config
from config_agentic import LLM_MODEL

# LLM instances
llm = ChatOllama(model=LLM_MODEL, temperature=0)
llm_structured = ChatOllama(model=LLM_MODEL, temperature=0.1)

# LLM avec outils bindés
llm_with_tools = llm.bind_tools([
    search_child_chunks,
    retrieve_parent_chunks,
    validate_haproxy_config
])

def summarize_conversation(state: State) -> dict:
    """
    Résume l'historique de conversation pour maintenir le contexte
    sans surcharger le LLM. Actif seulement si > 4 messages.
    """
    if len(state["messages"]) < 4:
        return {"conversation_summary": ""}

    relevant_msgs = [
        msg for msg in state["messages"][:-1]
        if isinstance(msg, (HumanMessage, AIMessage))
        and not getattr(msg, "tool_calls", None)
    ]
    if not relevant_msgs:
        return {"conversation_summary": ""}

    prompt = f"""Résume en 1-2 phrases maximum les sujets clés de cette conversation
sur la configuration HAProxy. Ignore les malentendus.

{chr(10).join(f'{"Utilisateur" if isinstance(m, HumanMessage) else "Assistant"}: {m.content}'
              for m in relevant_msgs[-6:])}

Résumé concis :"""

    response = llm.invoke([SystemMessage(content=prompt)])
    return {"conversation_summary": response.content}

def analyze_and_rewrite_query(state: State) -> dict:
    """
    Analyse la requête utilisateur et la réécrit pour la recherche.
    Détecte les questions floues et demande une clarification (human-in-the-loop).
    """
    last_message = state["messages"][-1]
    summary = state.get("conversation_summary", "")

    context_section = (
        f"Contexte conversation :\n{summary}"
        if summary.strip()
        else "Contexte : première question de la session"
    )

    prompt = f"""{QUERY_REWRITE_SYSTEM_PROMPT}

Question utilisateur : "{last_message.content}"
{context_section}

Analyse et retourne le résultat structuré."""

    llm_with_output = llm_structured.with_structured_output(QueryAnalysis)
    response = llm_with_output.invoke([SystemMessage(content=prompt)])

    if response.is_clear:
        # Supprimer les anciens messages pour repartir sur la question réécrite
        delete_msgs = [
            RemoveMessage(id=m.id)
            for m in state["messages"]
            if not isinstance(m, SystemMessage)
        ]
        rewritten = (
            "\n".join(f"{i+1}. {q}" for i, q in enumerate(response.questions))
            if len(response.questions) > 1
            else response.questions[0]
        )
        return {
            "questionIsClear": True,
            "messages": delete_msgs + [HumanMessage(content=rewritten)]
        }
    else:
        clarification = response.clarification_needed or (
            "Je n'ai pas bien compris votre question sur HAProxy. "
            "Pourriez-vous préciser ce que vous cherchez ? "
            "(ex: configuration d'un frontend, règle ACL, paramètre global...)"
        )
        return {
            "questionIsClear": False,
            "messages": [AIMessage(content=clarification)]
        }

def human_input_node(state: State) -> dict:
    """Nœud placeholder pour l'interruption human-in-the-loop."""
    return {}

def agent_node(state: State) -> dict:
    """Nœud principal de l'agent — utilise les outils pour répondre."""
    messages = [SystemMessage(content=AGENT_SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}
```

### `rag_agent/edges.py`

```python
"""Logique de routing conditionnel du graphe."""
from typing import Literal
from rag_agent.graph_state import State

def route_after_rewrite(state: State) -> Literal["agent", "human_input"]:
    """Route vers l'agent si la question est claire, sinon attend l'humain."""
    return "agent" if state.get("questionIsClear", False) else "human_input"
```

### `rag_agent/graph.py`

```python
"""
Construction et compilation du graphe LangGraph.
IMPORTANT : vérifier avec context7 les APIs StateGraph, ToolNode, tools_condition,
InMemorySaver, interrupt_before avant de coder.
"""
# Vérifier imports via context7 :
from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import InMemorySaver

from rag_agent.graph_state import State
from rag_agent.nodes import (
    summarize_conversation,
    analyze_and_rewrite_query,
    human_input_node,
    agent_node,
)
from rag_agent.edges import route_after_rewrite
from rag_agent.tools import search_child_chunks, retrieve_parent_chunks, validate_haproxy_config

def build_graph():
    """Construit et compile le graphe agentique."""
    checkpointer = InMemorySaver()
    builder = StateGraph(State)

    # Nœuds
    builder.add_node("summarize", summarize_conversation)
    builder.add_node("analyze_rewrite", analyze_and_rewrite_query)
    builder.add_node("human_input", human_input_node)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", ToolNode([
        search_child_chunks,
        retrieve_parent_chunks,
        validate_haproxy_config
    ]))

    # Edges
    builder.add_edge(START, "summarize")
    builder.add_edge("summarize", "analyze_rewrite")
    builder.add_conditional_edges("analyze_rewrite", route_after_rewrite)
    builder.add_edge("human_input", "analyze_rewrite")
    builder.add_conditional_edges("agent", tools_condition)
    builder.add_edge("tools", "agent")

    # Compilation avec interruption avant human_input
    # VÉRIFIER avec context7 : interrupt_before ou autre API
    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_input"]
    )

# Instance partagée
agent_graph = build_graph()
```

### `tests/test_graph_flow.py`

```python
import pytest
from langchain_core.messages import HumanMessage
from rag_agent.graph import agent_graph

@pytest.fixture
def config():
    import uuid
    return {"configurable": {"thread_id": str(uuid.uuid4())}}

def test_graph_builds_without_error():
    """Le graphe doit se compiler sans exception."""
    from rag_agent.graph import build_graph
    g = build_graph()
    assert g is not None

def test_clear_haproxy_query_routes_to_agent(config):
    """Une question HAProxy claire doit atteindre l'agent."""
    result = agent_graph.invoke(
        {"messages": [HumanMessage("What is a frontend in HAProxy?")]},
        config
    )
    assert "messages" in result
    # Si interrupted → questionIsClear est False, sinon il y a une vraie réponse
    last = result["messages"][-1]
    assert last.content != ""

def test_unclear_query_triggers_clarification(config):
    """Une question floue doit déclencher une demande de clarification."""
    # Invoquer puis vérifier si interrupted ou si réponse de clarification
    result = agent_graph.invoke(
        {"messages": [HumanMessage("blargh ???")]},
        config
    )
    assert not result.get("questionIsClear", True), "Query floue mais questionIsClear=True"

def test_conversation_memory_maintained(config):
    """La mémoire de conversation doit permettre la résolution des pronoms."""
    # Tour 1
    agent_graph.invoke(
        {"messages": [HumanMessage("What is a frontend in HAProxy?")]},
        config
    )
    # Tour 2 — "it" doit être résolu en "frontend"
    state = agent_graph.get_state(config)
    agent_graph.invoke(
        {"messages": [HumanMessage("How do I set a timeout for it?")]},
        config
    )
    final_state = agent_graph.get_state(config)
    # Vérifier que la question réécrite contient "frontend" ou "timeout"
    messages = final_state.values.get("messages", [])
    assert len(messages) > 0

def test_graph_completes_haproxy_question(config):
    """Une vraie question HAProxy doit produire une réponse non vide."""
    result = agent_graph.invoke(
        {"messages": [HumanMessage("How to configure a basic HAProxy backend with health checks?")]},
        config
    )
    last = result["messages"][-1]
    assert len(last.content) > 100, "Réponse trop courte"

def test_response_cites_source(config):
    """Les réponses doivent mentionner une source de la documentation."""
    result = agent_graph.invoke(
        {"messages": [HumanMessage("What is the maxconn parameter in HAProxy?")]},
        config
    )
    last = result["messages"][-1]
    # La réponse doit contenir une référence à la section
    assert "source" in last.content.lower() or "section" in last.content.lower() \
        or "configuration" in last.content.lower()
```

---

## PHASE 5 — Chatbot Gradio

### Stratégie : copier et adapter `app/` existant

> **Principe** : ne pas réécrire le chatbot Gradio from scratch. Copier le répertoire `app/` du projet principal dans `agentic_rag/app/` et adapter **uniquement** les points de connexion au retriever. Tout le reste (UI, thème, layout, gestion session) reste identique.

### Fichiers à copier depuis `app/` → `agentic_rag/app/`

```
app/                          →   agentic_rag/app/
├── gradio_app.py             →   agentic_rag/app/gradio_app.py       ← MODIFIER (retriever)
├── chat_interface.py         →   agentic_rag/app/chat_interface.py   ← MODIFIER (agent LangGraph)
├── document_manager.py       →   agentic_rag/app/document_manager.py ← NE PAS MODIFIER
└── rag_system.py             →   agentic_rag/app/rag_system.py       ← REMPLACER par agent
```

### Point d'entrée : `04_agentic_chatbot.py`

```python
"""
Chatbot Agentic RAG — copie de app/ adaptée pour pointer sur ChromaDB agentic.
Port : 7861 (le chatbot principal reste sur 7860).
"""
import sys
from pathlib import Path

# S'assurer que agentic_rag/ est dans le path
sys.path.insert(0, str(Path(__file__).parent))

from app.gradio_app import build_app

if __name__ == "__main__":
    demo = build_app()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7861,   # ← ne pas conflicuer avec 04_chatbot.py existant (7860)
        show_api=False,
    )
```

### Modifications dans `agentic_rag/app/rag_system.py`

C'est le **seul fichier à réécrire complètement**. Il remplace le retriever_v3 par l'agent LangGraph. L'interface que `chat_interface.py` appelle reste identique.

```python
"""
rag_system.py — VERSION AGENTIQUE
Remplace retriever_v3 par l'agent LangGraph + ChromaDB.
L'interface publique (get_response, get_sources) reste identique à l'original
pour ne pas modifier chat_interface.py.
"""
import uuid
from langchain_core.messages import HumanMessage

# Import de l'agent agentique (module parent agentic_rag/)
from rag_agent.graph import agent_graph

class AgenticRAGSystem:
    """
    Wrapper autour de agent_graph qui expose la même interface
    que le RAGSystem original de app/rag_system.py.
    Permet de brancher l'agent sans modifier chat_interface.py.
    """

    def __init__(self):
        self._sessions: dict[str, dict] = {}  # thread_id → config LangGraph

    def create_session(self) -> str:
        """Crée une nouvelle session de conversation. Retourne le thread_id."""
        thread_id = str(uuid.uuid4())
        self._sessions[thread_id] = {
            "configurable": {"thread_id": thread_id}
        }
        return thread_id

    def get_response(self, message: str, thread_id: str) -> str:
        """
        Interface publique identique à l'original.
        Gère automatiquement le human-in-the-loop :
        - Si l'agent est interrompu (question floue) → retourne la demande de clarification
        - Si reprise après clarification → reprend le graph là où il était
        """
        config = self._sessions.get(thread_id)
        if config is None:
            config = {"configurable": {"thread_id": thread_id}}
            self._sessions[thread_id] = config

        current_state = agent_graph.get_state(config)

        if current_state.next:
            # Graph interrompu en attente de clarification humaine
            agent_graph.update_state(
                config,
                {"messages": [HumanMessage(content=message.strip())]}
            )
            result = agent_graph.invoke(None, config)
        else:
            result = agent_graph.invoke(
                {"messages": [HumanMessage(content=message.strip())]},
                config
            )

        return result["messages"][-1].content

    def get_sources(self, thread_id: str) -> list[dict]:
        """
        Retourne les sources utilisées pour la dernière réponse.
        Compatibilité avec l'affichage sources du chatbot original.
        """
        config = self._sessions.get(thread_id)
        if not config:
            return []
        state = agent_graph.get_state(config)
        return state.values.get("sources_used", [])

    def reset_session(self, thread_id: str) -> str:
        """Réinitialise une session et retourne le nouveau thread_id."""
        if thread_id in self._sessions:
            del self._sessions[thread_id]
        return self.create_session()


# Instance partagée utilisée par chat_interface.py
rag_system = AgenticRAGSystem()
```

### Modifications dans `agentic_rag/app/chat_interface.py`

Changer **uniquement** la ligne d'import du rag_system :

```python
# AVANT (version originale)
# from app.rag_system import rag_system   ← pointe sur retriever_v3

# APRÈS (version agentique) — UNE SEULE LIGNE À CHANGER
from app.rag_system import rag_system     # ← pointe sur AgenticRAGSystem
```

> Tout le reste de `chat_interface.py` reste intact. L'interface `get_response(message, thread_id)` est identique.

### Modifications dans `agentic_rag/app/gradio_app.py`

Aucune modification de la logique UI. Changer uniquement le titre et le port dans `demo.launch()` :

```python
# Changer le titre pour distinguer les deux chatbots
gr.Markdown("# 🔧 HAProxy Agentic RAG\n*LangGraph + ChromaDB | Parent/Child retrieval*")

# Changer le port (déjà géré dans 04_agentic_chatbot.py, ne pas le dupliquer ici)
```

### Ce qui NE CHANGE PAS dans `app/`

- La structure des `gr.Blocks()`, `gr.Row()`, `gr.Column()`
- Le composant `gr.Chatbot` et ses paramètres
- `gr.ChatInterface` et ses callbacks
- Le panel sources (`gr.JSON`)
- La gestion des sessions via `gr.State`
- Le thème Gradio
- `document_manager.py` (non utilisé dans la version agentique mais conservé pour compatibilité)

### Checklist Gradio spécifique

```
[ ] Copier app/ → agentic_rag/app/ (cp -r app/ agentic_rag/app/)
[ ] Réécrire agentic_rag/app/rag_system.py avec AgenticRAGSystem
[ ] Modifier la ligne d'import dans agentic_rag/app/chat_interface.py
[ ] Modifier le titre dans agentic_rag/app/gradio_app.py
[ ] 04_agentic_chatbot.py lance sur port 7861
[ ] Tester que le chatbot original (port 7860) fonctionne toujours
[ ] Tester que les deux chatbots peuvent tourner simultanément
```

---

## PHASE 6 — Benchmarks & Évaluation

### `05_bench_agentic.py`

**Métriques comparées vs `retriever_v3` existant** :

```python
METRICS = {
    "answer_quality_score": "Score 0-1 évalué par LLM judge",
    "retrieval_precision": "% chunks retournés pertinents (évalué manuellement sur 10%)",
    "parent_child_utilization_rate": "% réponses ayant utilisé un chunk parent",
    "clarification_rate": "% questions ayant déclenché human-in-the-loop",
    "response_time_p50_sec": "Médiane du temps de réponse",
    "response_time_p95_sec": "95e percentile",
    "source_citation_rate": "% réponses avec citation de section",
}

# Questions test issues de 05_bench_targeted.py existant (réutilisation directe)
# + nouvelles questions complexes multi-sections
```

**Output** : `data_agentic/bench_comparison.json` + rapport Markdown `data_agentic/BENCH_REPORT.md`

### `06_eval_parent_child.py`

```python
"""
Évaluation de la valeur ajoutée de la stratégie parent/child.

Pour 50 questions :
  A) Réponse avec child chunks uniquement (contexte court)
  B) Réponse avec child + parent chunks (contexte étendu)

Métriques :
  - Qualité moyenne A vs B (LLM judge 0-1)
  - Complétude : B contient-il plus d'informations que A ?
  - Cohérence : les réponses B sont-elles plus précises ?

Output : data_agentic/parent_child_eval.json
Calibration du SCORE_THRESHOLD optimal
"""
```

---

## PHASE 7 — Export Dataset

### `07_export_dataset_agentic.py`

```python
"""
Génération d'un dataset Q&A enrichi pour fine-tuning.

- Charge les questions depuis data/ existant
- Génère des réponses via l'agent agentique (contexte parent enrichi)
- Format JSONL compatible Ollama / OpenAI fine-tuning
- Inclut les métadonnées sources (section_path, parent_id)

Structure de chaque entrée :
{
    "messages": [
        {"role": "system", "content": "Tu es un expert HAProxy 3.2..."},
        {"role": "user", "content": "Question..."},
        {"role": "assistant", "content": "Réponse avec contexte parent..."}
    ],
    "metadata": {
        "sources": ["section/path/1", "section/path/2"],
        "parent_ids": ["config_parent_42", "config_parent_17"],
        "quality_score": 0.85
    }
}

Output : data_agentic/dataset_agentic_qa.jsonl
"""
```

---

## PHASE 8 — Orchestrateur

### `00_rebuild_agentic.py`

```python
"""
Pipeline complet Agentic RAG — exécution séquentielle.

Usage :
  uv run python agentic_rag/00_rebuild_agentic.py
  uv run python agentic_rag/00_rebuild_agentic.py --skip-scrape
  uv run python agentic_rag/00_rebuild_agentic.py --skip-index
  uv run python agentic_rag/00_rebuild_agentic.py --test-only

Options :
  --skip-scrape  : utiliser les données scrapées existantes
  --skip-index   : utiliser l'index ChromaDB existant
  --test-only    : lancer uniquement les tests sans reconstruire
"""
import argparse
import subprocess
import sys
import time
import json
from datetime import datetime
from pathlib import Path
from config_agentic import DATA_DIR

STEPS = [
    ("01_scrape_verified.py",       "Scraping + analyse hiérarchie",     "~10-30 min"),
    ("02_chunking_parent_child.py", "Chunking parent/child",             "~2-5 min"),
    ("03_indexing_chroma.py",       "Indexation ChromaDB",               "~5-15 min"),
    ("06_eval_parent_child.py",     "Évaluation couverture parent/child","~10-20 min"),
]

TEST_STEPS = [
    "tests/test_scraper_alignment.py",
    "tests/test_chunking.py",
    "tests/test_retrieval.py",
    "tests/test_graph_flow.py",
]

def run_step(script: str, label: str, eta: str) -> bool:
    print(f"\n{'='*60}")
    print(f"▶ {label} (ETA: {eta})")
    print(f"  Script : agentic_rag/{script}")
    print(f"{'='*60}")

    start = time.time()
    result = subprocess.run(
        [sys.executable, f"agentic_rag/{script}"],
        capture_output=False
    )
    elapsed = time.time() - start

    if result.returncode != 0:
        print(f"\n❌ ÉCHEC : {label} ({elapsed:.1f}s)")
        return False

    print(f"\n✅ OK : {label} ({elapsed:.1f}s)")
    return True

def run_tests() -> bool:
    print(f"\n{'='*60}")
    print("🧪 Lancement des tests pytest")
    print(f"{'='*60}")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "agentic_rag/tests/", "-v", "--tb=short"],
        capture_output=False
    )
    return result.returncode == 0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-scrape", action="store_true")
    parser.add_argument("--skip-index", action="store_true")
    parser.add_argument("--test-only", action="store_true")
    args = parser.parse_args()

    start_total = time.time()
    print(f"\n🚀 Pipeline Agentic RAG HAProxy")
    print(f"   Démarré : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    report = {"steps": [], "tests": None, "total_time": None}

    if not args.test_only:
        for script, label, eta in STEPS:
            # Skip scrape et/ou index si demandé
            if args.skip_scrape and "scrape" in script:
                print(f"⏭ Skip : {label}")
                continue
            if args.skip_index and "indexing" in script:
                print(f"⏭ Skip : {label}")
                continue

            ok = run_step(script, label, eta)
            report["steps"].append({"step": label, "success": ok})

            if not ok:
                print(f"\n💥 Pipeline interrompu à l'étape : {label}")
                sys.exit(1)

    # Tests
    tests_ok = run_tests()
    report["tests"] = {"success": tests_ok}

    total = time.time() - start_total
    report["total_time"] = f"{total:.1f}s"
    report["timestamp"] = datetime.now().isoformat()

    # Sauvegarde rapport
    (DATA_DIR / "pipeline_summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2)
    )

    print(f"\n{'='*60}")
    if tests_ok:
        print(f"✅ PIPELINE COMPLET — {total:.0f}s")
        print(f"   Lancer le chatbot : uv run python agentic_rag/04_agentic_chatbot.py")
    else:
        print(f"⚠️  PIPELINE TERMINÉ AVEC ERREURS DE TEST — {total:.0f}s")
        print(f"   Consulter : agentic_rag/data_agentic/pipeline_summary.json")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
```

---

## CHECKLIST FINALE POUR L'AGENT DE CODAGE

### Avant de commencer
```
[ ] context7 consulté pour : langgraph, langchain-chroma, langchain-core,
    langchain-ollama, langchain-huggingface, chromadb, pydantic v2, gradio 6.6.0
[ ] Versions exactes figées dans pyproject_agentic.toml
[ ] Ollama lancé localement avec qwen3:latest et qwen3-embedding:8b disponibles
    (ollama pull qwen3:latest && ollama pull qwen3-embedding:8b)
```

### Phase 1 — Scraping ⛔ VALIDATION HUMAINE OBLIGATOIRE
```
[ ] Étape 1.0 : lire 01_scrape.py existant → identifier URLs cibles et sélecteurs CSS
[ ] Étape 1.0 : compter les données du projet principal dans data/ → noter le chiffre de référence
[ ] Étape 1.1 : 01_scrape_verified.py lancé → scraped_pages.json produit
[ ] Étape 1.1 : rapport affiché à l'utilisateur (volume, sections, anomalies)
[ ] ✅ VALIDATION HUMAINE 1 : utilisateur confirme le volume et les sections
[ ] Étape 1.2 : compare_with_reference.py lancé → scraping_diff_report.json produit
[ ] Étape 1.2 : diff affiché (URLs et sections manquantes vs projet principal)
[ ] ✅ VALIDATION HUMAINE 2 : utilisateur confirme couverture complète (ou corrections faites)
[ ] Étape 1.3 : test_scraper_alignment.py : 7/7 tests PASS
[ ] ✅ VALIDATION HUMAINE 3 : utilisateur dit explicitement "passer à la Phase 2"
[ ] hierarchy_report.json : parent_coverage >= 90%
[ ] scraping_diff_report.json : content_coverage_pct >= 95%
[ ] AUCUNE URL du projet principal manquante dans missing_urls
```

### Phase 2 — Chunking ⛔ NE PAS DÉMARRER SANS VALIDATION PHASE 1
```
[ ] 02_chunking_parent_child.py : X parents + Y children générés (afficher les stats)
[ ] parent_store/ : N fichiers JSON présents
[ ] chunks_child.json : dump de vérification présent
[ ] test_chunking.py : 5/5 tests PASS
[ ] Ratio children/parent affiché et cohérent (typiquement 8-15)
[ ] ✅ VALIDATION HUMAINE : utilisateur valide les stats avant Phase 3
```

### Phase 3 — Indexation ⛔ NE PAS DÉMARRER SANS VALIDATION PHASE 2
```
[ ] 03_indexing_chroma.py : index construit sans erreur
[ ] Requête test post-indexation : résultats retournés
[ ] test_retrieval.py : 4/4 tests PASS
[ ] SCORE_THRESHOLD calibré (noter la valeur optimale dans config_agentic.py)
[ ] ✅ VALIDATION HUMAINE : utilisateur valide 3 exemples de recherche avant Phase 4
```

### Phase 4 — Agent
```
[ ] rag_agent/__init__.py présent
[ ] graph.py compile sans erreur (agent_graph buildé)
[ ] tools.py : 3 outils fonctionnels (search_child, retrieve_parent, validate_config)
[ ] validate_haproxy_config : wrap haproxy_validator.py existant sans l'importer de manière rigide
[ ] test_graph_flow.py : 5/5 tests PASS
```

### Phase 5 — Chatbot
```
[ ] app/ copié dans agentic_rag/app/ (cp -r)
[ ] agentic_rag/app/rag_system.py réécrit avec AgenticRAGSystem
[ ] Import rag_system modifié dans agentic_rag/app/chat_interface.py (1 ligne)
[ ] Titre modifié dans agentic_rag/app/gradio_app.py
[ ] 04_agentic_chatbot.py démarre sur localhost:7861 sans erreur
[ ] Le chatbot original (port 7860) fonctionne toujours après la copie
[ ] Les deux chatbots tournent simultanément sans conflit
[ ] Human-in-the-loop : question floue → demande de clarification affichée dans Gradio
[ ] Mémoire de conversation : "it" résolu correctement après un premier échange
```

### Phase 6 — Benchmarks
```
[ ] 05_bench_agentic.py : bench_comparison.json généré
[ ] 06_eval_parent_child.py : parent_child_eval.json généré
[ ] SCORE_THRESHOLD mis à jour dans config_agentic.py selon résultats
```

### Phase 7 — Dataset
```
[ ] 07_export_dataset_agentic.py : dataset_agentic_qa.jsonl généré
[ ] Format JSONL valide (chaque ligne parseable par json.loads)
```

### Phase 8 — Pipeline complet
```
[ ] 00_rebuild_agentic.py : pipeline complet tourne sans intervention
[ ] data_agentic/pipeline_summary.json généré avec succès
[ ] --skip-scrape et --skip-index fonctionnels
[ ] README_AGENTIC.md : instructions claires pour installation + usage
```

### Vérification finale — Non-régression
```
[ ] AUCUN fichier du repo racine modifié
[ ] AUCUN fichier du repo racine supprimé
[ ] Les scripts existants 00_rebuild_all.py → 07_bench_config_correction.py fonctionnent toujours
[ ] Le chatbot existant 04_chatbot.py démarre toujours sur port 7860
```

---

## RÉSUMÉ DES COMMANDES

```bash
# Installation
cd haproxy-dataset-generator
uv sync --project agentic_rag/pyproject_agentic.toml

# Pipeline complet (première fois)
uv run python agentic_rag/00_rebuild_agentic.py

# Reconstruire sans re-scraper
uv run python agentic_rag/00_rebuild_agentic.py --skip-scrape

# Tests uniquement
uv run python agentic_rag/00_rebuild_agentic.py --test-only

# Lancer le chatbot agentique
uv run python agentic_rag/04_agentic_chatbot.py
# → http://localhost:7861

# Lancer le chatbot existant (inchangé)
uv run python 04_chatbot.py
# → http://localhost:7860
```

---

*Plan généré pour agent de codage IA — Version ChromaDB + LangGraph + Gradio 6.6.0*
*Repo source : laurentvv/haproxy-dataset-generator*
*Architecture référence : GiovanniPasq/agentic-rag-for-dummies*
