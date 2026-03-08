import json
from pathlib import Path

DATA_DIR = Path('scraping_comparison/data')
CRAWL4AI_FILE = DATA_DIR / 'results_crawl4ai.json'
CRAWLEE_FILE = DATA_DIR / 'results_crawlee.json'
REPORT_FILE = Path('scraping_comparison/COMPARISON_REPORT.md')


def main():
    if not CRAWL4AI_FILE.exists() or not CRAWLEE_FILE.exists():
        print('Error: Results files not found. Run the benchmarks first.')
        return

    with open(CRAWL4AI_FILE) as f:
        crawl4ai_data = json.load(f)

    with open(CRAWLEE_FILE) as f:
        crawlee_data = json.load(f)

    report = []
    report.append('# Rapport de Comparaison : Crawl4AI vs Crawlee (Python)')
    report.append('')
    report.append('## Résumé Exécutif')
    report.append('')

    # Global Metrics Table
    report.append('| Métrique | Crawl4AI | Crawlee |')
    report.append('|---|---|---|')
    c4ai_time = crawl4ai_data['total_time_seconds']
    clee_time = crawlee_data['total_time_seconds']
    report.append(f'| Temps d\'exécution total | {c4ai_time:.2f}s | {clee_time:.2f}s |')

    c4ai_results = {r['url']: r for r in crawl4ai_data['results']}
    clee_results = {r['url']: r for r in crawlee_data['results']}

    report.append('')
    report.append('## Comparaison par URL')
    report.append('')
    report.append('| URL | Outil | Temps | Longueur du contenu |')
    report.append('|---|---|---|---|')

    for url in c4ai_results.keys():
        c4ai = c4ai_results[url]
        c4ai_len = len(c4ai['content'])
        report.append(f'| {url} | Crawl4AI | {c4ai["time_seconds"]:.2f}s | {c4ai_len} (MD) |')
        if url in clee_results:
            clee = clee_results[url]
            c_len_h = len(clee['content'])
            c_len_t = len(clee['text'])
            c_time = clee['time_seconds']
            report.append(f'| | Crawlee | {c_time:.2f}s | {c_len_h} (H) / {c_len_t} (T) |')
        report.append('| --- | --- | --- | --- |')

    report.append('')
    report.append('## Observations Qualitatives')
    report.append('')
    report.append('### Crawl4AI')
    report.append('- **Points Forts :**')
    report.append('  - Extraction Markdown native (haute qualité pour le RAG).')
    report.append('  - Filtrage facile des balises (nav, footer).')
    report.append('  - API simple pour du scraping de pages spécifiques.')
    report.append('- **Points Faibles :**')
    report.append('  - Plus lent en raison du post-traitement Markdown.')
    report.append('')
    report.append('### Crawlee')
    report.append('- **Points Forts :**')
    report.append('  - Robustesse exceptionnelle (gestion des files d\'attente).')
    report.append('  - Vitesse brute pour l\'extraction HTML/Texte.')
    report.append('  - Idéal pour le crawling à grande échelle.')
    report.append('- **Points Faibles :**')
    report.append('  - Nécessite des outils tiers pour le Markdown (ex: `html2text`).')
    report.append('  - Configuration plus complexe pour des tâches simples.')
    report.append('')
    report.append('## Recommandation Finale')
    report.append('')
    report.append('Pour le projet actuel (RAG Documentation HAProxy) :')
    report.append('- **Crawl4AI** reste le meilleur choix pour son Markdown natif.')
    report.append('- **Crawlee** est supérieur pour du crawling massif.')

    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))

    print(f'Report generated at {REPORT_FILE}')


if __name__ == '__main__':
    main()
