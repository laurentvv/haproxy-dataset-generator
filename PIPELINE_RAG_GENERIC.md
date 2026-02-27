# 📘 Pipeline RAG Générique - Guide Complet

**Version :** 1.0  
**Date :** 2026-02-25  
**Statut :** ✅ Prêt pour production

---

## 📋 Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Prérequis](#prérequis)
3. [Architecture du pipeline](#architecture-du-pipeline)
4. [Étape 1 : Préparer les documents](#etape-1-preparer-les-documents)
5. [Étape 2 : Scraper/Parser la source](#etape-2-scraperparser-la-source)
6. [Étape 3 : Chunker les documents](#etape-3-chunker-les-documents)
7. [Étape 4 : Construire les index](#etape-4-construire-les-index)
8. [Étape 5 : Lancer le chatbot](#etape-5-lancer-le-chatbot)
9. [Étape 6 : Benchmarker](#etape-6-benchmarker)
10. [Configuration et optimisation](#configuration-et-optimisation)
11. [Dépannage](#depannage)

---

## 🎯 Vue d'ensemble

Ce guide décrit comment créer un **chatbot RAG (Retrieval-Augmented Generation)** pour **n'importe quelle documentation**.

### **Cas d'usage :**
- Documentation technique (API, frameworks, langages)
- Manuels utilisateur
- Bases de connaissances internes
- Documentation produit
- Procédures et politiques d'entreprise

### **Ce que tu vas construire :**

```
┌─────────────────────────────────────────────────────────────────┐
│                    PIPELINE RAG COMPLET                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SOURCE (docs, PDF, web, etc.)                                  │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────┐  Extraction  →  data/raw.jsonl            │
│  │ 01_scrape.py    │  ou parsing                               │
│  └─────────────────┘                                            │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────┐  Chunking      →  data/chunks.jsonl       │
│  │ 02_chunking.py  │  + metadata                                │
│  └─────────────────┘                                            │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────┐  Indexing      →  index/                  │
│  │ 03_indexing.py  │  - vectoriel (embeddings)                 │
│  └─────────────────┘  - lexical (BM25)                         │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────┐  RAG Chat      →  Interface Web           │
│  │ 04_chatbot.py   │  - Retrieval hybride                      │
│  └─────────────────┘  - LLM (génération)                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Prérequis

### **Système**
- **OS :** Windows 10/11, Linux, macOS
- **Python :** 3.11+
- **RAM :** 16GB minimum (32GB recommandé pour les gros modèles)
- **Stockage :** 10GB libre (plus si gros corpus documentaire)

### **Logiciels à installer**

#### 1. **uv** (package manager Python)
```bash
# Linux/Mac
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Vérifier
uv --version
```

#### 2. **Ollama** (pour les modèles de langage locaux)
```bash
# Télécharger : https://ollama.com

# Installer les modèles (exemples)
ollama pull nomic-embed-text      # Embedding (512 dims, rapide)
ollama pull bge-m3                # Embedding (1024 dims, MTEB SOTA)
ollama pull qwen3-embedding:8b    # Embedding (4096 dims, MTEB #1)
ollama pull llama3.1:8b           # LLM (génération, rapide)
ollama pull qwen3:latest          # LLM (génération, qualité)
ollama pull mistral:latest        # LLM (alternative)

# Vérifier
ollama list
ollama serve
```

---

## 🏗️ Architecture du pipeline

### **Composants principaux**

| Composant | Rôle | Technologies |
|-----------|------|--------------|
| **Extraction** | Récupérer les documents | BeautifulSoup, Scrapy, PyPDF2, etc. |
| **Chunking** | Découper en segments | Tokenization, regex, NLP |
| **Embedding** | Vectoriser les chunks | Ollama, Sentence Transformers |
| **Index Vectoriel** | Recherche sémantique | ChromaDB, FAISS, Qdrant |
| **Index Lexical** | Recherche mots-clés | BM25 (rank-bm25) |
| **Fusion** | Combiner les résultats | RRF (Reciprocal Rank Fusion) |
| **Reranking** | Affiner le classement | FlashRank, Cross-Encoders |
| **LLM** | Générer la réponse | Ollama (local), OpenAI (cloud) |
| **Interface** | Interaction utilisateur | Gradio, Streamlit |

### **Pipeline de retrieval**

```
Question utilisateur
       │
       ▼
┌─────────────────────┐
│  Query Expansion    │  Synonymes, reformulation
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  Vector Search      │  Similarité cosinus (top-K)
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  Lexical Search     │  BM25 (top-K)
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  RRF Fusion         │  Combine les 2 scores
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  Reranking          │  Cross-encoder (top-N)
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  Metadata Filtering │  Filtres optionnels
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  LLM Generation     │  Réponse avec contexte
└─────────────────────┘
       │
       ▼
Réponse finale + sources
```

---

## Étape 1 : Préparer les documents

### **Option A : Documentation web**

Si ta documentation est en ligne (ex: https://docs.example.com) :

**Action :** Créer `01_scrape.py`

```python
#!/usr/bin/env python3
"""
01_scrape.py - Scraper la documentation web
"""
import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path

# Configuration
BASE_URL = "https://docs.example.com"
START_PAGE = "/introduction"
OUTPUT_FILE = Path("data/raw.jsonl")

def scrape_page(url):
    """Scrape une page et retourne le contenu."""
    response = requests.get(url)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extraire le titre
    title = soup.find('h1').text.strip() if soup.find('h1') else "Sans titre"
    
    # Extraire le contenu (ajuster les sélecteurs selon le site)
    content_div = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
    content = content_div.get_text(separator='\n', strip=True) if content_div else ""
    
    # Nettoyer le contenu
    content = ' '.join(content.split())
    
    return {
        "url": url,
        "title": title,
        "content": content,
        "metadata": {
            "source": BASE_URL,
            "scraped_at": "2026-02-25"
        }
    }

def main():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Liste des pages à scraper (à adapter)
    pages_to_scrape = [
        BASE_URL + "/introduction",
        BASE_URL + "/installation",
        BASE_URL + "/configuration",
        # ... ajouter toutes les pages
    ]
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for i, page_url in enumerate(pages_to_scrape, 1):
            print(f"[{i}/{len(pages_to_scrape)}] Scraping: {page_url}")
            
            try:
                data = scrape_page(page_url)
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
            except Exception as e:
                print(f"  ❌ Erreur: {e}")
    
    print(f"\n✅ Terminé ! {len(pages_to_scrape)} pages scrapées")
    print(f"📁 Sortie: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
```

**Execution :**
```bash
uv run python 01_scrape.py
```

---

### **Option B : Documents PDF**

Si tu as des PDFs locaux :

**Action :** Créer `01_parse_pdf.py`

```python
#!/usr/bin/env python3
"""
01_parse_pdf.py - Parser des documents PDF
"""
import PyPDF2
import json
from pathlib import Path

# Configuration
PDF_DIR = Path("data/pdfs")
OUTPUT_FILE = Path("data/raw.jsonl")

def parse_pdf(pdf_path):
    """Parse un PDF et retourne le contenu."""
    with open(pdf_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        
        content = []
        for i, page in enumerate(reader.pages, 1):
            text = page.extract_text()
            content.append(f"--- Page {i} ---\n{text}")
        
        return {
            "filename": pdf_path.name,
            "title": pdf_path.stem,
            "content": '\n\n'.join(content),
            "metadata": {
                "source": str(pdf_path),
                "pages": len(reader.pages),
                "parsed_at": "2026-02-25"
            }
        }

def main():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    pdf_files = list(PDF_DIR.glob("*.pdf"))
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"[{i}/{len(pdf_files)}] Parsing: {pdf_file.name}")
            
            try:
                data = parse_pdf(pdf_file)
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
            except Exception as e:
                print(f"  ❌ Erreur: {e}")
    
    print(f"\n✅ Terminé ! {len(pdf_files)} PDFs parsés")
    print(f"📁 Sortie: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
```

**Execution :**
```bash
# Installer la dépendance
uv add pypdf2

# Lancer le parsing
uv run python 01_parse_pdf.py
```

---

### **Option C : Fichiers Markdown/Texte**

Si tu as des fichiers `.md` ou `.txt` :

**Action :** Créer `01_load_docs.py`

```python
#!/usr/bin/env python3
"""
01_load_docs.py - Charger des documents texte/markdown
"""
import json
from pathlib import Path

# Configuration
DOCS_DIR = Path("data/docs")
OUTPUT_FILE = Path("data/raw.jsonl")

def load_document(file_path):
    """Charge un document texte."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extraire le titre (première ligne ou nom du fichier)
    lines = content.split('\n')
    title = lines[0].lstrip('#').strip() if lines and lines[0].startswith('#') else file_path.stem
    
    return {
        "filename": file_path.name,
        "title": title,
        "content": content,
        "metadata": {
            "source": str(file_path),
            "loaded_at": "2026-02-25"
        }
    }

def main():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Charger tous les .md et .txt
    files = list(DOCS_DIR.glob("*.md")) + list(DOCS_DIR.glob("*.txt"))
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for i, file_path in enumerate(files, 1):
            print(f"[{i}/{len(files)}] Chargement: {file_path.name}")
            
            try:
                data = load_document(file_path)
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
            except Exception as e:
                print(f"  ❌ Erreur: {e}")
    
    print(f"\n✅ Terminé ! {len(files)} documents chargés")
    print(f"📁 Sortie: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
```

**Execution :**
```bash
uv run python 01_load_docs.py
```

---

## Étape 2 : Scraper/Parser la source

*(Voir Étape 1 ci-dessus - c'est la même chose)*

**Sortie attendue :** `data/raw.jsonl`

```json
{"url": "https://docs.example.com/intro", "title": "Introduction", "content": "...", "metadata": {...}}
{"filename": "guide.pdf", "title": "Guide Utilisateur", "content": "...", "metadata": {...}}
{"filename": "README.md", "title": "README", "content": "...", "metadata": {...}}
```

---

## Étape 3 : Chunker les documents

**Objectif :** Découper les documents en chunks de taille gérable.

**Action :** Créer `02_chunking.py`

```python
#!/usr/bin/env python3
"""
02_chunking.py - Découper les documents en chunks intelligents
"""
import json
import re
from pathlib import Path

# Configuration
INPUT_FILE = Path("data/raw.jsonl")
OUTPUT_FILE = Path("data/chunks.jsonl")

# Paramètres de chunking
CHUNK_SIZE = 600  # Caractères par chunk
CHUNK_OVERLAP = 100  # Recouvrement entre chunks

# Mots-clés pour l'extraction de tags (à adapter selon ton domaine)
KEYWORDS = {
    "installation": ["install", "setup", "configure", "prerequisites"],
    "configuration": ["config", "settings", "options", "parameters"],
    "api": ["endpoint", "request", "response", "api", "rest"],
    "troubleshooting": ["error", "debug", "fix", "problem", "issue"],
    # ... ajouter tes propres keywords
}

def extract_tags(content):
    """Extrait des tags du contenu."""
    content_lower = content.lower()
    tags = []
    
    for tag, keywords in KEYWORDS.items():
        if any(kw in content_lower for kw in keywords):
            tags.append(tag)
    
    return tags[:5]  # Limiter à 5 tags

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Découpe un texte en chunks."""
    chunks = []
    
    # Découper aux limites naturelles (paragraphes, sections)
    sections = re.split(r'\n\s*\n|\n(?=#|\*\*|---)', text)
    
    current_chunk = ""
    current_size = 0
    
    for section in sections:
        section = section.strip()
        if not section:
            continue
        
        section_size = len(section)
        
        # Si la section tient dans le chunk actuel
        if current_size + section_size <= chunk_size:
            current_chunk += "\n\n" + section if current_chunk else section
            current_size += section_size + 2
        else:
            # Sauvegarder le chunk actuel
            if current_chunk:
                chunks.append(current_chunk)
            
            # Si la section est trop grande, la découper
            if section_size > chunk_size:
                words = section.split()
                current_chunk = ""
                current_size = 0
                
                for word in words:
                    if current_size + len(word) + 1 <= chunk_size:
                        current_chunk += " " + word if current_chunk else word
                        current_size += len(word) + 1
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = word
                        current_size = len(word)
                
                if current_chunk:
                    chunks.append(current_chunk)
            else:
                current_chunk = section
                current_size = section_size
    
    # Ajouter le dernier chunk
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

def main():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Charger les documents bruts
    documents = []
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            documents.append(json.loads(line))
    
    print(f"📚 {len(documents)} documents à chunker")
    
    all_chunks = []
    chunk_id = 0
    
    for i, doc in enumerate(documents, 1):
        print(f"[{i}/{len(documents)}] Chunking: {doc.get('title', 'Sans titre')}")
        
        # Découper en chunks
        chunks = chunk_text(doc['content'])
        
        for chunk_text_item in chunks:
            chunk = {
                "chunk_id": f"chunk_{chunk_id}",
                "title": doc.get('title', 'Sans titre'),
                "content": chunk_text_item,
                "tags": extract_tags(chunk_text_item),
                "has_code": any(x in chunk_text_item for x in ['```', '    ', '\t', 'function', 'def ']),
                "metadata": {
                    **doc.get('metadata', {}),
                    "chunk_index": len(all_chunks),
                    "total_chunks": len(chunks)
                }
            }
            
            all_chunks.append(chunk)
            chunk_id += 1
    
    # Sauvegarder les chunks
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
    
    print(f"\n✅ Terminé ! {len(all_chunks)} chunks créés")
    print(f"📁 Sortie: {OUTPUT_FILE}")
    
    # Stats
    avg_size = sum(len(c['content']) for c in all_chunks) / len(all_chunks)
    with_code = sum(1 for c in all_chunks if c['has_code'])
    
    print(f"📊 Stats:")
    print(f"   Taille moy: {avg_size:.0f} chars")
    print(f"   Tags moy: {sum(len(c['tags']) for c in all_chunks) / len(all_chunks):.1f}/chunk")
    print(f"   Avec code: {with_code} ({with_code/len(all_chunks)*100:.0f}%)")

if __name__ == "__main__":
    main()
```

**Execution :**
```bash
uv run python 02_chunking.py
```

**Sortie attendue :** `data/chunks.jsonl`

```json
{
  "chunk_id": "chunk_0",
  "title": "Introduction",
  "content": "Ce guide décrit comment utiliser...",
  "tags": ["introduction", "installation"],
  "has_code": false,
  "metadata": {"source": "...", "chunk_index": 0, "total_chunks": 5}
}
```

---

## Étape 4 : Construire les index

**Objectif :** Créer les index vectoriels et lexicaux.

**Action :** Créer `03_indexing.py`

```python
#!/usr/bin/env python3
"""
03_indexing.py - Construire les index vectoriels et lexicaux
"""
import json
import pickle
import subprocess
from pathlib import Path
from typing import List, Dict
import numpy as np

# Configuration
INPUT_FILE = Path("data/chunks.jsonl")
INDEX_DIR = Path("index")
CHROMA_DIR = INDEX_DIR / "chroma"
BM25_PATH = INDEX_DIR / "bm25.pkl"
CHUNKS_PKL = INDEX_DIR / "chunks.pkl"

# Modèles d'embedding (à adapter)
EMBED_MODEL = "nomic-embed-text"  # ou "bge-m3", "qwen3-embedding:8b"

# Configuration du retrieval
TOP_K_RETRIEVAL = 50
TOP_K_RRF = 30
TOP_K_RERANK = 10
RRF_K = 60

def get_embedding(text: str) -> List[float]:
    """Génère un embedding via Ollama."""
    result = subprocess.run(
        ["ollama", "embeddings", EMBED_MODEL],
        input=text,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise Exception(f"Ollama error: {result.stderr}")
    
    return json.loads(result.stdout)["embedding"]

def tokenize(text: str) -> List[str]:
    """Tokenisation pour BM25."""
    text = text.lower()
    tokens = re.findall(r'[a-z0-9][a-z0-9\-\.]*[a-z0-9]|[a-z0-9]', text)
    
    stopwords = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
        'ought', 'used', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
        'from', 'as', 'into', 'through', 'during', 'before', 'after', 'above',
        'below', 'between', 'under', 'again', 'further', 'then', 'once', 'here',
        'there', 'when', 'where', 'why', 'how', 'all', 'each', 'few', 'more',
        'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
        'same', 'so', 'than', 'too', 'very', 'just', 'and', 'but', 'if', 'or',
        'because', 'until', 'while', 'although', 'though', 'after', 'before',
        'le', 'la', 'les', 'de', 'du', 'des', 'un', 'une', 'et', 'ou', 'en'
    }
    
    return [t for t in tokens if t not in stopwords and len(t) > 2]

def main():
    import re
    from rank_bm25 import BM25Okapi
    
    print("="*70)
    print("  BUILD INDEX - RAG Pipeline")
    print("="*70)
    
    # Charger les chunks
    chunks = []
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            chunks.append(json.loads(line))
    
    print(f"\n📦 {len(chunks)} chunks à indexer")
    
    # Vérifier Ollama
    print(f"\n🔍 Vérification d'Ollama...")
    result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    if EMBED_MODEL not in result.stdout:
        print(f"⚠️  Modèle '{EMBED_MODEL}' non trouvé")
        print(f"   Lancez: ollama pull {EMBED_MODEL}")
        return
    
    print(f"✅ Modèle d'embedding: {EMBED_MODEL}")
    
    # Créer les dossiers
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    
    # ── Index Vectoriel (ChromaDB) ─────────────────────────────────────────────
    print(f"\n🔨 Index ChromaDB...")
    
    try:
        import chromadb
        from chromadb.config import Settings
        
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        collection = client.get_or_create_collection(
            name="docs",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Générer les embeddings par batch
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            texts = [c['content'] for c in batch]
            ids = [c['chunk_id'] for c in batch]
            metadatas = [
                {
                    "title": c['title'],
                    "tags": ",".join(c['tags']),
                    "has_code": str(c['has_code'])
                }
                for c in batch
            ]
            
            # Ollama peut être lent, afficher la progression
            print(f"   [{i+len(batch)}/{len(chunks)}] Embedding...")
            
            embeddings = [get_embedding(text) for text in texts]
            
            collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
        
        print(f"   ✅ ChromaDB créé ({len(chunks)} docs)")
        
    except ImportError:
        print("   ❌ chromadb non installé : uv add chromadb")
        return
    
    # ── Index Lexical (BM25) ───────────────────────────────────────────────────
    print(f"\n🔨 Index BM25...")
    
    tokenized_chunks = [tokenize(c['content']) for c in chunks]
    bm25 = BM25Okapi(tokenized_chunks)
    
    with open(BM25_PATH, 'wb') as f:
        pickle.dump(bm25, f)
    
    print(f"   ✅ BM25 créé ({len(chunks)} chunks)")
    
    # ── Metadata ───────────────────────────────────────────────────────────────
    print(f"\n📦 Metadata...")
    
    with open(CHUNKS_PKL, 'wb') as f:
        pickle.dump(chunks, f)
    
    print(f"   ✅ {len(chunks)} chunks sauvegardés")
    
    # ── Résumé ─────────────────────────────────────────────────────────────────
    print(f"\n" + "="*70)
    print(f"   INDEX CONSTRUIT")
    print(f"="*70)
    print(f"   Embedding    : {EMBED_MODEL}")
    print(f"   Chunks       : {len(chunks)}")
    print(f"   ChromaDB     : {CHROMA_DIR}/")
    print(f"   BM25         : {BM25_PATH}")
    print(f"   Metadata     : {CHUNKS_PKL}")
    print(f"="*70)

if __name__ == "__main__":
    main()
```

**Execution :**
```bash
# Installer les dépendances
uv add chromadb rank-bm25

# Construire l'index
uv run python 03_indexing.py
```

**Sortie attendue :**
```
index/
├── chroma/           # Index vectoriel
│   └── chroma.sqlite3
├── bm25.pkl          # Index lexical
└── chunks.pkl        # Metadata
```

---

## Étape 5 : Lancer le chatbot

**Action :** Créer `04_chatbot.py`

*(Voir la structure complète dans le projet HAProxy - c'est la même chose)*

**Execution :**
```bash
uv add gradio flashrank

uv run python 04_chatbot.py
```

---

## Étape 6 : Benchmarker

**Action :** Créer `bench_questions.py` et `bench_only.py`

*(Voir les fichiers du projet HAProxy pour des exemples complets)*

**Execution :**
```bash
# Benchmark rapide
uv run python bench_only.py --level quick

# Benchmark complet
uv run python bench_only.py --level full
```

---

## ⚙️ Configuration et optimisation

### **Ajuster le chunking**

Dans `02_chunking.py` :
```python
CHUNK_SIZE = 600       # 500-800 selon la densité d'info
CHUNK_OVERLAP = 100    # 10-20% de CHUNK_SIZE
```

### **Ajuster le retrieval**

Dans `03_indexing.py` ou `retriever.py` :
```python
TOP_K_RETRIEVAL = 50   # Candidats par méthode
TOP_K_RRF = 30         # Après fusion
TOP_K_RERANK = 10      # Après reranking
RRF_K = 60             # Paramètre RRF (40-100)
```

### **Metadata Filtering**

Ajouter dans `retriever.py` :
```python
SECTION_HINTS = {
    "installation": ["intro", "setup", "install"],
    "api": ["endpoints", "methods", "requests"],
    "config": ["settings", "options", "parameters"],
    # ... adapter selon tes documents
}
```

---

## 🔧 Dépannage

### **Ollama inaccessible**
```bash
ollama serve
ollama list
ollama pull nomic-embed-text
```

### **Index manquants**
```bash
rm -rf index/
uv run python 03_indexing.py
```

### **ChromaDB error**
```bash
rm -rf index/chroma/
uv run python 03_indexing.py
```

### **Qualité faible**
- Augmenter `TOP_K_RETRIEVAL` (50 → 70)
- Ajuster `CHUNK_SIZE` (600 → 800)
- Ajouter des keywords dans `extract_tags()`
- Changer de modèle d'embedding

---

## 📊 Checklist de déploiement

- [ ] Documents extraits/parsés (`data/raw.jsonl`)
- [ ] Chunks créés (`data/chunks.jsonl`)
- [ ] Index construits (`index/`)
- [ ] Chatbot fonctionnel (http://localhost:7860)
- [ ] Benchmark > 80% de questions résolues
- [ ] Temps de réponse < 30s
- [ ] Documentation utilisateur rédigée

---

## 📁 Structure finale

```
mon-projet-rag/
├── 01_scrape.py          # Ou 01_parse_pdf.py, 01_load_docs.py
├── 02_chunking.py        # Découpage en chunks
├── 03_indexing.py        # Construction des index
├── 04_chatbot.py         # Interface Gradio
├── retriever.py          # Retrieval hybride
├── llm.py                # Génération LLM
├── bench_questions.py    # Questions de benchmark
├── bench_only.py         # Script de benchmark
├── data/
│   ├── raw.jsonl         # Documents bruts
│   └── chunks.jsonl      # Chunks
└── index/
    ├── chroma/           # Index vectoriel
    ├── bm25.pkl          # Index lexical
    └── chunks.pkl        # Metadata
```

---

**Dernière mise à jour :** 2026-02-25  
**Version :** 1.0  
**Statut :** ✅ Prêt pour production
