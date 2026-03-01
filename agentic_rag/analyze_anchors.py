#!/usr/bin/env python3
"""Script pour compter les ancres sur chaque page."""

import requests
from bs4 import BeautifulSoup

# Pages à analyser
pages = [
    'https://docs.haproxy.org/3.2/intro.html',
    'https://docs.haproxy.org/3.2/configuration.html',
    'https://docs.haproxy.org/3.2/management.html',
]

for url in pages:
    print(f'\n=== Analyse de {url} ===')

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        # Compter tous les éléments avec un attribut id
        elements_with_id = soup.find_all(attrs={'id': True})

        # Filtrer les ancres spéciales (tab-summary, tab-keywords, etc.)
        anchors = []
        for elem in elements_with_id:
            elem_id = elem['id']
            # Ignorer les ancres spéciales
            if elem_id.startswith('tab-'):
                continue
            anchors.append(elem_id)

        print(f"Nombre total d'éléments avec id: {len(elements_with_id)}")
        print(f"Nombre d'ancres (après filtrage): {len(anchors)}")

        # Afficher les 20 premières ancres
        print('\n=== 20 premières ancres ===')
        for i, anchor in enumerate(anchors[:20]):
            print(f'{i + 1}. {anchor}')

    except Exception as e:
        print(f'Erreur: {e}')
