#!/usr/bin/env python3
"""
Dataset de tests pour le benchmark de correction de configuration HAProxy.

Ce module fournit des cas de test pour évaluer la capacité du système RAG
à détecter et corriger les erreurs de configuration HAProxy.
"""

from typing import Any


# =============================================================================
# Cas de test - Erreurs de syntaxe
# =============================================================================

SYNTAX_ERROR_TESTS: list[dict[str, Any]] = [
    {
        "id": "syntax_invalid_port",
        "name": "Port invalide (> 65535)",
        "category": "syntax",
        "difficulty": "easy",
        "original_config": """global
    maxconn 4096

defaults
    mode http
    timeout connect 5s
    timeout client 50s
    timeout server 50s

frontend http_front
    bind *:99999
    default_backend web_servers

backend web_servers
    balance roundrobin
    server web1 192.168.1.1:80
""",
        "expected_errors": [
            {"type": "syntax", "message": "Port invalide"}
        ],
        "expected_fixed_config": """global
    maxconn 4096

defaults
    mode http
    timeout connect 5s
    timeout client 50s
    timeout server 50s

frontend http_front
    bind *:80
    default_backend web_servers

backend web_servers
    balance roundrobin
    server web1 192.168.1.1:80
""",
        "metadata": {
            "keywords": ["port", "bind", "invalid"]
        }
    },
    {
        "id": "syntax_invalid_mode",
        "name": "Mode invalide",
        "category": "syntax",
        "difficulty": "easy",
        "original_config": """global
    maxconn 4096

defaults
    mode tcp
    timeout connect 5s

frontend http_front
    bind *:80
    mode invalid_mode
    default_backend web_servers

backend web_servers
    server web1 192.168.1.1:80
""",
        "expected_errors": [
            {"type": "syntax", "message": "Mode invalide"}
        ],
        "expected_fixed_config": """global
    maxconn 4096

defaults
    mode tcp
    timeout connect 5s

frontend http_front
    bind *:80
    mode http
    default_backend web_servers

backend web_servers
    server web1 192.168.1.1:80
""",
        "metadata": {
            "keywords": ["mode", "http", "tcp"]
        }
    },
    {
        "id": "syntax_invalid_balance",
        "name": "Algorithme de balance invalide",
        "category": "syntax",
        "difficulty": "easy",
        "original_config": """global
    maxconn 4096

defaults
    mode http

backend web_servers
    balance invalid_algo
    server web1 192.168.1.1:80
    server web2 192.168.1.2:80
""",
        "expected_errors": [
            {"type": "syntax", "message": "Balance invalide"}
        ],
        "expected_fixed_config": """global
    maxconn 4096

defaults
    mode http

backend web_servers
    balance roundrobin
    server web1 192.168.1.1:80
    server web2 192.168.1.2:80
""",
        "metadata": {
            "keywords": ["balance", "roundrobin", "algorithm"]
        }
    },
]


# =============================================================================
# Cas de test - Erreurs logiques
# =============================================================================

LOGIC_ERROR_TESTS: list[dict[str, Any]] = [
    {
        "id": "logic_missing_backend",
        "name": "Backend manquant",
        "category": "logic",
        "difficulty": "medium",
        "original_config": """global
    maxconn 4096

defaults
    mode http

frontend http_front
    bind *:80
    default_backend nonexistent_backend
""",
        "expected_errors": [
            {"type": "logic", "message": "Backend non défini"}
        ],
        "expected_fixed_config": """global
    maxconn 4096

defaults
    mode http

frontend http_front
    bind *:80
    default_backend web_servers

backend web_servers
    server web1 192.168.1.1:80
""",
        "metadata": {
            "keywords": ["backend", "default_backend", "missing"]
        }
    },
    {
        "id": "logic_duplicate_server",
        "name": "Serveurs dupliqués",
        "category": "logic",
        "difficulty": "medium",
        "original_config": """global
    maxconn 4096

defaults
    mode http

backend web_servers
    balance roundrobin
    server web1 192.168.1.1:80
    server web1 192.168.1.2:80
""",
        "expected_errors": [
            {"type": "logic", "message": "Nom de serveur dupliqué"}
        ],
        "expected_fixed_config": """global
    maxconn 4096

defaults
    mode http

backend web_servers
    balance roundrobin
    server web1 192.168.1.1:80
    server web2 192.168.1.2:80
""",
        "metadata": {
            "keywords": ["server", "duplicate", "name"]
        }
    },
    {
        "id": "logic_negative_timeout",
        "name": "Timeout négatif",
        "category": "logic",
        "difficulty": "easy",
        "original_config": """global
    maxconn 4096

defaults
    mode http
    timeout connect -5s
    timeout client 50s
""",
        "expected_errors": [
            {"type": "logic", "message": "Timeout négatif"}
        ],
        "expected_fixed_config": """global
    maxconn 4096

defaults
    mode http
    timeout connect 5s
    timeout client 50s
""",
        "metadata": {
            "keywords": ["timeout", "negative", "connect"]
        }
    },
]


# =============================================================================
# Cas de test - Erreurs de sécurité
# =============================================================================

SECURITY_ERROR_TESTS: list[dict[str, Any]] = [
    {
        "id": "security_stats_no_auth",
        "name": "Stats sans authentification",
        "category": "security",
        "difficulty": "medium",
        "original_config": """global
    maxconn 4096

defaults
    mode http

frontend http_front
    bind *:80
    stats enable
    stats uri /stats
    default_backend web_servers

backend web_servers
    server web1 192.168.1.1:80
""",
        "expected_errors": [
            {"type": "security", "message": "Stats sans authentification"}
        ],
        "expected_fixed_config": """global
    maxconn 4096

defaults
    mode http

frontend http_front
    bind *:80
    stats enable
    stats uri /stats
    stats auth admin:password123
    default_backend web_servers

backend web_servers
    server web1 192.168.1.1:80
""",
        "metadata": {
            "keywords": ["stats", "auth", "security", "password"]
        }
    },
    {
        "id": "security_ssl_no_verify",
        "name": "SSL sans vérification",
        "category": "security",
        "difficulty": "medium",
        "original_config": """global
    maxconn 4096

defaults
    mode http

backend secure_backend
    balance roundrobin
    server secure1 192.168.1.1:443 ssl verify none
""",
        "expected_errors": [
            {"type": "security", "message": "SSL sans vérification"}
        ],
        "expected_fixed_config": """global
    maxconn 4096

defaults
    mode http

backend secure_backend
    balance roundrobin
    server secure1 192.168.1.1:443 ssl verify required ca-file /etc/ssl/certs/ca-certificates.crt
""",
        "metadata": {
            "keywords": ["ssl", "verify", "ca-file", "security"]
        }
    },
    {
        "id": "security_permissive_acl",
        "name": "ACL permissive (0.0.0.0/0)",
        "category": "security",
        "difficulty": "medium",
        "original_config": """global
    maxconn 4096

defaults
    mode http

frontend http_front
    bind *:80
    acl allow_all src 0.0.0.0/0
    http-request allow if allow_all
    default_backend web_servers

backend web_servers
    server web1 192.168.1.1:80
""",
        "expected_errors": [
            {"type": "security", "message": "ACL permissive"}
        ],
        "expected_fixed_config": """global
    maxconn 4096

defaults
    mode http

frontend http_front
    bind *:80
    acl trusted_networks src 192.168.1.0/24
    http-request allow if trusted_networks
    default_backend web_servers

backend web_servers
    server web1 192.168.1.1:80
""",
        "metadata": {
            "keywords": ["acl", "src", "network", "security"]
        }
    },
]


# =============================================================================
# Cas de test - Erreurs de référence
# =============================================================================

REFERENCE_ERROR_TESTS: list[dict[str, Any]] = [
    {
        "id": "reference_undefined_backend",
        "name": "Backend non défini",
        "category": "reference",
        "difficulty": "easy",
        "original_config": """global
    maxconn 4096

defaults
    mode http

frontend http_front
    bind *:80
    use_backend api_backend if { path_beg /api }
    default_backend web_backend
""",
        "expected_errors": [
            {"type": "reference", "message": "Backends non définis"}
        ],
        "expected_fixed_config": """global
    maxconn 4096

defaults
    mode http

frontend http_front
    bind *:80
    use_backend api_backend if { path_beg /api }
    default_backend web_backend

backend web_backend
    server web1 192.168.1.1:80

backend api_backend
    server api1 192.168.1.10:8080
""",
        "metadata": {
            "keywords": ["backend", "undefined", "reference"]
        }
    },
]


# =============================================================================
# Cas de test - Optimisation
# =============================================================================

OPTIMIZATION_TESTS: list[dict[str, Any]] = [
    {
        "id": "optimization_no_keepalive",
        "name": "Keep-alive non configuré",
        "category": "optimization",
        "difficulty": "medium",
        "original_config": """global
    maxconn 4096

defaults
    mode http
    timeout connect 5s
    timeout client 50s
    timeout server 50s

frontend http_front
    bind *:80
    default_backend web_servers

backend web_servers
    balance roundrobin
    server web1 192.168.1.1:80
""",
        "expected_errors": [],
        "expected_fixed_config": """global
    maxconn 4096

defaults
    mode http
    timeout connect 5s
    timeout client 50s
    timeout server 50s
    option http-keep-alive

frontend http_front
    bind *:80
    default_backend web_servers

backend web_servers
    balance roundrobin
    server web1 192.168.1.1:80
""",
        "metadata": {
            "keywords": ["keepalive", "http-keep-alive", "optimization", "performance"]
        }
    },
    {
        "id": "optimization_single_server",
        "name": "Serveur unique sans backup",
        "category": "optimization",
        "difficulty": "easy",
        "original_config": """global
    maxconn 4096

defaults
    mode http

backend web_servers
    balance roundrobin
    server web1 192.168.1.1:80
""",
        "expected_errors": [],
        "expected_fixed_config": """global
    maxconn 4096

defaults
    mode http

backend web_servers
    balance roundrobin
    server web1 192.168.1.1:80 check
    server web2 192.168.1.2:80 check backup
""",
        "metadata": {
            "keywords": ["backup", "redundancy", "check", "ha"]
        }
    },
]


# =============================================================================
# Fonctions utilitaires
# =============================================================================

def get_all_tests() -> list[dict[str, Any]]:
    """Retourne tous les cas de test.

    Returns:
        Liste de tous les cas de test
    """
    return (
        SYNTAX_ERROR_TESTS
        + LOGIC_ERROR_TESTS
        + SECURITY_ERROR_TESTS
        + REFERENCE_ERROR_TESTS
        + OPTIMIZATION_TESTS
    )


def get_quick_tests() -> list[dict[str, Any]]:
    """Retourne les cas de test rapides (difficulté easy).

    Returns:
        Liste des cas de test faciles
    """
    return [test for test in get_all_tests() if test["difficulty"] == "easy"]


def get_standard_tests() -> list[dict[str, Any]]:
    """Retourne les cas de test standards (difficulté easy + medium).

    Returns:
        Liste des cas de test standards
    """
    return [
        test for test in get_all_tests() if test["difficulty"] in ("easy", "medium")
    ]


def get_tests_by_difficulty(difficulty: str) -> list[dict[str, Any]]:
    """Retourne les cas de test par difficulté.

    Args:
        difficulty: Niveau de difficulté (easy, medium, hard)

    Returns:
        Liste des cas de test pour la difficulté spécifiée
    """
    return [test for test in get_all_tests() if test["difficulty"] == difficulty]


def get_tests_by_category(category: str) -> list[dict[str, Any]]:
    """Retourne les cas de test par catégorie.

    Args:
        category: Catégorie de test (syntax, logic, security, reference, optimization)

    Returns:
        Liste des cas de test pour la catégorie spécifiée
    """
    return [test for test in get_all_tests() if test["category"] == category]


# =============================================================================
# Point d'entrée principal (pour test)
# =============================================================================

if __name__ == "__main__":
    print("Dataset de tests pour benchmark HAProxy")
    print("=" * 60)
    print(f"Total tests: {len(get_all_tests())}")
    print(f"Quick tests: {len(get_quick_tests())}")
    print(f"Standard tests: {len(get_standard_tests())}")
    print()
    print("Tests par catégorie:")
    for category in ["syntax", "logic", "security", "reference", "optimization"]:
        count = len(get_tests_by_category(category))
        print(f"  - {category}: {count}")
