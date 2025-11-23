# HAProxy LLM Dataset Generator & Fine-tuning Pipeline

[![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Ce projet fournit un pipeline complet pour créer un dataset de haute qualité pour le fine-tuning de modèles de langage (LLM), en se basant sur la documentation officielle de HAProxy. L'objectif est de produire un modèle spécialisé dans les questions-réponses liées à la configuration, l'administration et l'utilisation d'HAProxy.

## 🚀 Fonctionnalités

- **Extraction automatisée** de la documentation HAProxy
- **Génération de Q/R** à l'aide de modèles LLM locaux (Ollama)
- **Dataset enrichi** avec titres, contenus et contextes complets
- **Pipeline de fine-tuning** prêt pour Google Colab
- **Support de multiples modèles** pour le fine-tuning (Gemma, Llama, etc.)

## 📁 Structure du projet

```
haproxy-dataset-generator/
├── README.md
├── pyproject.toml
├── TODO.md
├── uv.lock
├── scripts/
│   ├── extract_to_markdown.py      # Extraction de la doc HAProxy
│   └── generate_qa_with_ollama.py  # Génération des paires Q/R
├── training/
│   └── finetune_haproxy_on_colab.ipynb  # Notebook pour fine-tuning
├── data/
│   ├── sections.jsonl              # Sections extraites de la doc
│   └── haproxy_dataset_qa.jsonl    # Dataset final Q/R enrichi
└── .env.example                    # Exemple de fichier de configuration
```

## 🛠 Prérequis

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (gestionnaire de paquets Python)
- [Ollama](https://ollama.com/) (pour exécuter les modèles LLM localement)
- Modèle `qwen3:14b` installé via Ollama (pour la génération de Q/R)

### Installation des outils

#### uv
```bash
# Sur macOS et Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sur Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### Ollama
Suivez les instructions d'installation sur [ollama.com](https://ollama.com/), puis démarrez le service :
```bash
ollama serve
```

#### Téléchargement du modèle
```bash
ollama pull qwen3:14b
```

## 🛠 Installation

1. **Cloner le dépôt**
   ```bash
   git clone <URL_DU_DEPOT>
   cd haproxy-dataset-generator
   ```

2. **Créer l'environnement virtuel avec uv**
   ```bash
   # Crée un environnement virtuel dans un dossier .venv
   uv venv

   # Active l'environnement
   # Sur macOS et Linux :
   source .venv/bin/activate
   # Sur Windows (Command Prompt) :
   .venv\Scripts\activate
   # Sur Windows (PowerShell) :
   .venv\Scripts\Activate.ps1
   ```

3. **Installer les dépendances du projet**
   ```bash
   # Installe le projet en mode développement avec toutes ses dépendances
   uv pip install -e .
   ```

4. **Configurer les variables d'environnement**
   ```bash
   # Copier le fichier exemple
   cp .env.example .env

   # Modifier les variables selon vos besoins (URL de la documentation HAProxy, etc.)
   ```

## 🧱 Utilisation

Le pipeline se compose de deux étapes principales suivies d'une étape de fine-tuning :

### 1. Extraction de la documentation HAProxy

```bash
python scripts/extract_to_markdown.py
```

Ce script :
- Télécharge la documentation HAProxy à partir de l'URL spécifiée dans `.env`
- Découpe le contenu en sections (balises `<h2>`)
- Convertit chaque section en Markdown
- Sauvegarde les sections structurées dans `data/sections.jsonl`

### 2. Génération du dataset Question/Réponse

```bash
python scripts/generate_qa_with_ollama.py
```

Ce script :
- Lit les sections extraites de `data/sections.jsonl`
- Génère des paires Question/Réponse à l'aide du modèle `qwen3:14b`
- Sauvegarde les paires enrichies (avec `title`, `content`) dans `data/haproxy_dataset_qa.jsonl`

### 3. Fine-tuning du modèle

Le dataset généré est prêt à être utilisé pour le fine-tuning d'un modèle plus léger et spécialisé. Le notebook `training/finetune_haproxy_on_colab.ipynb` vous guide à travers le processus de fine-tuning sur Google Colab en utilisant QLoRA (4-bit quantization) et LoRA (Low-Rank Adaptation).

Le notebook inclut :
- Chargement du dataset généré
- Configuration du modèle de base (Gemma-2-9b-it, Llama-3-8B-Instruct, etc.)
- Mise en place de la quantification 4-bit (QLoRA)
- Configuration de LoRA
- Entraînement du modèle
- Sauvegarde du modèle fine-tuné
- Test du modèle fine-tuné

Pour utiliser le notebook :
1. Téléchargez ou clonez le dépôt sur votre Google Drive
2. Ouvrez le fichier dans Google Colab
3. Suivez les instructions pas à pas dans le notebook

## 📊 Format du dataset

Le dataset final `data/haproxy_dataset_qa.jsonl` contient des objets JSON avec les champs suivants :
- `question`: La question générée par le LLM
- `response`: La réponse détaillée générée par le LLM
- `source`: URL de la section d'origine
- `title`: Titre de la section d'origine
- `content`: Contenu de la section d'origine (format Markdown)

Exemple :
```json
{
  "question": "Quelle est la directive 'bind' dans HAProxy et comment l'utiliser ?",
  "response": "La directive 'bind' dans HAProxy est utilisée pour spécifier l'adresse IP et le port sur lesquels le proxy écoutera les connexions entrantes...",
  "source": "https://docs.haproxy.org/3.2/intro.html",
  "title": "3.1. What HAProxy is and isn't",
  "content": "HAProxy is a TCP proxy : it can accept a TCP connection from a listening socket..."
}
```

## 🤝 Contribution

Les contributions sont les bienvenues ! Voici comment vous pouvez contribuer :

1. Fork du projet
2. Créez une branche pour votre fonctionnalité (`git checkout -b feature/NouvelleFonctionnalite`)
3. Committez vos changements (`git commit -m 'Ajouter une nouvelle fonctionnalité'`)
4. Poussez vers la branche (`git push origin feature/NouvelleFonctionnalite`)
5. Ouvrez une Pull Request

## 📄 Licence

Ce projet est distribué sous la licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 🙏 Remerciements

- [HAProxy Technologies](https://www.haproxy.com/) pour la documentation ouverte
- [Ollama](https://ollama.com/) pour les modèles LLM accessibles localement
- [Google Colab](https://colab.research.google.com/) pour l'infrastructure de fine-tuning
- [Hugging Face](https://huggingface.co/) pour les bibliothèques de machine learning
