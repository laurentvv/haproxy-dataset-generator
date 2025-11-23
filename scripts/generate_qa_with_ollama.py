import json
import time
import re
from pathlib import Path
import ollama


def generate_qa_from_markdown(section, model_name, verbose=True):
    """
    Génère une paire question-réponse à partir d'une section de documentation HAProxy.

    Args:
        section (dict): Section de documentation avec 'title', 'content', et 'url'
        model_name (str): Nom du modèle Ollama à utiliser
        verbose (bool): Afficher les détails du processus

    Returns:
        dict: Paire Q/R avec 'question', 'response' et 'source', ou None en cas d'erreur
    """
    if verbose:
        title_safe = section.get('title', 'Unknown')[:60].encode('utf-8', errors='replace').decode('utf-8')
        print(f"[INFO] Génération Q/R pour: {title_safe}...")

    # Préparer le prompt pour le modèle
    prompt = f"""
En tant qu'expert HAProxy, génère une question et une réponse détaillée basées sur cette section de documentation.
La question devrait être pertinente et couvrir les points clés de la section.
La réponse devrait être complète, précise et utile.

Titre: {section['title']}
Contenu: {section['content']}

Format de réponse:
{{
  "question": "Question pertinente sur la section",
  "response": "Réponse détaillée et informative",
  "source": "{section['url']}"
}}
"""

    try:
        if verbose:
            print(f"[OLLAMA] Envoi de la requête à {model_name}...")

        # Appel à l'API Ollama
        response = ollama.chat(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            options={
                "temperature": 0.7,
                "max_tokens": 1024,
                "top_p": 0.9
            }
        )

        # Extraire le contenu de la réponse
        content = response['message']['content']

        if verbose:
            print(f"[OLLAMA] Réponse reçue, longueur: {len(content)} caractères")

        # Essayer de parser le JSON de la réponse
        # Le modèle peut retourner le JSON brut ou encapsulé dans un format de texte
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            qa_json_str = json_match.group(0)
            qa_pair = json.loads(qa_json_str)
            # S'assurer que la structure est correcte
            if 'question' in qa_pair and 'response' in qa_pair:
                if verbose:
                    print_safe = "[SUCCESS] Q/R parsée avec succès"
                    try:
                        print(print_safe)
                    except UnicodeEncodeError:
                        print(print_safe.encode('ascii', errors='replace').decode('ascii'))
                qa_pair['source'] = section.get('url', '')
                return qa_pair

        # Si on ne peut pas parser le JSON, retourner une version structurée
        if verbose:
            warn_msg = f"[WARNING] Impossible de parser en JSON, utilisation de la réponse brute"
            try:
                print(warn_msg)
            except UnicodeEncodeError:
                print(warn_msg.encode('ascii', errors='replace').decode('ascii'))
        return {
            "question": f"Quelles sont les informations importantes dans la section '{section['title']}'?",
            "response": content[:500] + "..." if len(content) > 500 else content,
            "source": section.get('url', '')
        }

    except json.JSONDecodeError:
        error_msg = f"[ERROR] Impossible de parser la réponse JSON pour la section: {section['title']}"
        try:
            print(error_msg)
        except UnicodeEncodeError:
            print(error_msg.encode('ascii', errors='replace').decode('ascii'))
        return None
    except Exception as e:
        error_msg = f"[ERROR] Erreur lors de la génération Q/R pour la section '{section['title']}': {e}"
        try:
            print(error_msg)
        except UnicodeEncodeError:
            print(error_msg.encode('ascii', errors='replace').decode('ascii'))
        return None


def main():
    # Utilisation de pathlib pour gérer les chemins
    data_dir = Path("data")
    input_path = data_dir / "sections.jsonl"
    output_path = data_dir / "haproxy_dataset_qa.jsonl"

    model_name = "qwen3:14b"  # Modèle corrigé et mis à jour

    print(f"Début de la génération du dataset avec le modèle Ollama : {model_name}")

    # Lire toutes les sections en mémoire pour avoir le total et permettre un traitement progressif
    print("Chargement des sections depuis le fichier...")
    sections = []
    try:
        with open(input_path, "r", encoding="utf-8") as infile:
            for line in infile:
                sections.append(json.loads(line.strip()))
    except FileNotFoundError:
        print(f"[ERROR] Le fichier d'entrée '{input_path}' n'a pas été trouvé.")
        print(
            "Assurez-vous d'avoir lancé le premier script (extract_to_markdown.py) avant celui-ci."
        )
        return

    total_sections = len(sections)
    print(f"Total des sections à traiter : {total_sections}")

    # Vérifier si le fichier de sortie existe et lire les titres des Q/R déjà générées
    processed_titles = set()
    if output_path.exists():
        print("[INFO] Fichier de sortie existant détecté. Analyse des données existantes...")
        try:
            with open(output_path, "r", encoding="utf-8") as outfile:
                for line in outfile:
                    if line.strip():
                        existing_qa = json.loads(line)
                        # Identifier les sections déjà traitées par titre et URL
                        if 'source' in existing_qa:
                            processed_titles.add((existing_qa.get('question', ''), existing_qa.get('source', '')))
            print(f"[INFO] {len(processed_titles)} paires Q/R déjà existantes détectées, reprise du traitement...")
        except Exception as e:
            print(f"[WARNING] Impossible de lire le fichier existant: {e}. Redémarrage depuis le début.")
            processed_titles = set()

    # Afficher un résumé estimé du temps
    estimated_total_time_minutes = total_sections / 60  # 60 sections par heure avec 1 seconde de pause
    print(f"Temps total estimé (théorique): ~{estimated_total_time_minutes:.1f} minutes")

    # Déterminer les sections déjà traitées en vérifiant les URLs dans le fichier de sortie
    processed_urls = set()
    if output_path.exists():
        print("[INFO] Fichier de sortie existant détecté. Analyse des données existantes...")
        try:
            with open(output_path, "r", encoding="utf-8") as outfile:
                for line in outfile:
                    if line.strip():
                        try:
                            existing_qa = json.loads(line)
                            source_url = existing_qa.get('source', '')
                            if source_url:
                                processed_urls.add(source_url)
                        except json.JSONDecodeError:
                            continue  # Ignorer les lignes mal formées
            print(f"[INFO] {len(processed_urls)} sections déjà traitées détectées, reprise du traitement...")
        except Exception as e:
            print(f"[WARNING] Impossible de lire le fichier existant: {e}. Redémarrage depuis le début.")
            processed_urls = set()

    # Filtrer les sections non traitées
    sections_to_process = []
    for section in sections:
        section_url = section.get('url', '')
        if section_url not in processed_urls:
            sections_to_process.append(section)
        else:
            print(f"[SKIPPED] Section déjà traitée: {section.get('title', 'Unknown')}")

    sections_remaining = len(sections_to_process)
    print(f"Sections restantes à traiter : {sections_remaining}")

    if sections_remaining == 0:
        print("[INFO] Toutes les sections ont déjà été traitées. Aucun traitement nécessaire.")
        return

    estimated_remaining_time_minutes = sections_remaining / 60
    print(f"Temps estimé pour les sections restantes: ~{estimated_remaining_time_minutes:.1f} minutes")

    processed_count = total_sections - sections_remaining
    generated_count = len(processed_urls)  # Approximation: nombre de sections traitées correspond au nombre d'URLs traitées

    # Déterminer le mode d'ouverture du fichier
    mode = "a" if processed_urls else "w"

    try:
        # Open the file with newline='' to avoid newline translation issues
        with open(output_path, mode, encoding="utf-8", newline='') as outfile:
            for i, section in enumerate(sections_to_process, processed_count + 1):
                # Calculer le pourcentage de progression
                progress_percent = (i / total_sections) * 100

                # Afficher une barre de progression ASCII
                bar_length = 40
                filled_length = int(bar_length * i // total_sections)
                bar = '█' * filled_length + '-' * (bar_length - filled_length)

                print(f"\r[PROGRESS] |{bar}| {progress_percent:.1f}% Section {i}/{total_sections}", end='', flush=True)

                # Afficher des détails sur la section en cours - safe encoding
                title_safe = section.get('title', 'Unknown')[:60]
                try:
                    print(f"\n[INFO] Traitement: {title_safe}...")
                except UnicodeEncodeError:
                    # Handle encoding error by replacing problematic characters
                    title_safe_encoded = title_safe.encode('ascii', errors='replace').decode('ascii')
                    print(f"\n[INFO] Traitement: {title_safe_encoded}...")

                # Générer la paire Q/R avec affichage détaillé
                qa_pair = generate_qa_from_markdown(section, model_name, verbose=False)  # verbose géré dans la fonction

                if qa_pair:
                    outfile.write(json.dumps(qa_pair, ensure_ascii=False) + "\n")
                    outfile.flush()  # Ensure data is written immediately
                    generated_count += 1
                    try:
                        print(f"[SUCCESS] Q/R sauvegardée - Total: {generated_count}/{total_sections}")
                    except UnicodeEncodeError:
                        print(f"[SUCCESS] Q/R sauvegardée - Total: {generated_count}/{total_sections}")

                # Petite pause pour ne pas surcharger le CPU/GPU
                time.sleep(1)

                # Afficher un résumé de progression toutes les 5 sections ou à la fin
                if i % 5 == 0 or i == total_sections:
                    remaining_time = (total_sections - i) / 60  # estimation en minutes
                    print(f"\n[SUMMARY] Avancement: {i}/{total_sections} ({progress_percent:.1f}%), {generated_count} Q/R générées, ~{remaining_time:.1f} min restantes")

    except Exception as e:
        print(f"\n[ERROR] Une erreur inattendue est survenue : {e}")
        return

    print(f"\n\n[SUCCESS] Terminé ! Dataset généré avec {generated_count} paires Q/R.")
    print(f"[INFO] Fichier sauvegardé sous : {output_path}")

    # Afficher un résumé final
    success_rate = (generated_count / total_sections) * 100 if total_sections > 0 else 0
    print(f"[SUMMARY] Taux de succès: {success_rate:.1f}% ({generated_count}/{total_sections})")


if __name__ == "__main__":
    main()
