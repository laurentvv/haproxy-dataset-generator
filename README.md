# HAProxy LLM Dataset Generator & Fine-tuning Pipeline

Ce projet fournit un pipeline complet pour créer un dataset de haute qualité pour le fine-tuning de modèles de langage (LLM), en se basant sur la documentation officielle de HAProxy.

Le processus se déroule en trois grandes étapes :
1.  **Extraction** : Le contenu des pages de documentation HAProxy est extrait et structuré en sections Markdown.
2.  **Génération de Q/R** : Un modèle LLM local puissant (`qwen3:14b` via Ollama) est utilisé pour générer des paires Question/Réponse pertinentes à partir de chaque section Markdown.
3.  **Fine-tuning** : Le dataset généré est utilisé pour fine-tuner un modèle plus petit et plus efficace (ex: Gemma-2-9b, Llama-3-8B) directement sur Google Colab.

## Structure du projet

```
.
├── README.md
├── pyproject.toml
├── scripts/
│   ├── extract_to_markdown.py
│   └── generate_qa_with_ollama.py
├── data/
│   ├── sections.jsonl         (généré par l'étape 1)
│   └── haproxy_dataset_qa.jsonl (généré par l'étape 2)
├── Notebook.md                (instructions pour fine-tuning sur Colab)
└── requirements.txt
```

---

## Prérequis

Avant de commencer, assurez-vous d'avoir les outils suivants installés sur votre machine locale :

1.  **Python 3.13+**
2.  **uv** : Un gestionnaire de paquets et d'environnements Python très rapide.
    ```bash
    # Sur macOS et Linux
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Sur Windows (PowerShell)
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```
3.  **Ollama** : Pour exécuter des modèles LLM localement.
    *   Suivez les instructions d'installation sur [ollama.com](https://ollama.com/).
    *   Une fois installé, démarrez le serveur Ollama.
    *   Téléchargez le modèle `qwen3:14b`
        ```bash
        ollama pull qwen3:14b
        ```

---

## Étape 1 : Installation et Configuration de l'Environnement

Ce projet utilise `uv` pour gérer un environnement virtuel et installer les dépendances de manière reproductible.

1.  **Cloner ce dépôt** (si vous l'avez sur un Git) ou créez les fichiers localement.

2.  **Créer et activer l'environnement virtuel avec uv** :
    ```bash
    # Crée un environnement virtuel dans un dossier .venv et l'active immédiatement
    uv venv
    
    # Active l'environnement
    # Sur macOS et Linux :
    source .venv/bin/activate
    # Sur Windows (Command Prompt) :
    .venv\Scripts\activate
    # Sur Windows (PowerShell) :
    .venv\Scripts\Activate.ps1
    ```

3.  **Installer les dépendances du projet** :
    Le fichier `pyproject.toml` liste toutes les dépendances nécessaires. La commande suivante les installera en suivant les spécifications du fichier pyproject.toml.
    ```bash
    # Installe le projet en mode développement avec toutes ses dépendances
    uv pip install -e .
    
    # Optionnel : pour installer aussi les dépendances de développement
    uv pip install -e ".[dev]"
    ```
    *(Le flag `-e .` installe le projet en mode "editable", ce qui est une bonne pratique.)*

4.  **Vérifier que les dépendances sont installées** :
    ```bash
    # Vérifie les paquets installés
    uv pip list
    ```

---

## Étape 2 : Génération du Dataset

Cette étape est divisée en deux scripts Python à exécuter séquentiellement.

### 2.1. Extraction du contenu vers Markdown

Ce script récupère la documentation HAProxy, la découpe en sections (basées sur les balises `<h2>`) et convertit chaque section en format Markdown.

```bash
python scripts/extract_to_markdown.py
```

Le script va :
1. Télécharger la documentation HAProxy à partir de l'URL spécifiée dans le fichier `.env` (variable `HAPROXY_DOCS_URL`)
2. Extraire le contenu de chaque section (balises `<h2>`)
3. Convertir le HTML en Markdown
4. Sauvegarder les sections dans `data/sections.jsonl`

### 2.2. Génération des paires Question/Réponse

Ce script prend les sections extraites et utilise un LLM local pour générer des questions et réponses.

```bash
python scripts/generate_qa_with_ollama.py
```

Le script va :
1. Lire les sections de `data/sections.jsonl`
2. Pour chaque section, générer une question pertinente et une réponse détaillée à l'aide du modèle `qwen3:14b`
3. Sauvegarder les paires Q/R dans `data/haproxy_dataset_qa.jsonl`

---

## Étape 3 : Fine-tuning sur Google Colab

Le fichier `Notebook.md` contient les instructions étape par étape pour fine-tuner un modèle sur le dataset généré. 

Vous pouvez copier-coller le contenu du fichier dans un notebook Google Colab pour effectuer le fine-tuning.
