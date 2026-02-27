"""Dataset de test pour le benchmark de correction de configuration HAProxy.

Ce module contient 23 cas de test couvrant différents types d'erreurs et
d'améliorations de configuration HAProxy.
"""

from typing import Any

# ============================================================================
# Dataset de cas de test
# ============================================================================

TEST_CASES: list[dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # Erreurs Syntaxiques (6 tests)
    # -------------------------------------------------------------------------
    {
        "id": "syntax_001",
        "name": "Mot-clé 'option' mal orthographié",
        "category": "syntax_error",
        "type": "correction",
        "config_type": "snippet",
        "difficulty": "easy",
        "original_config": """
backend web_servers
    balance roundrobin
    optoin httpchk GET /health
    server web1 192.168.1.1:80 check
""",
        "expected_errors": [
            {
                "type": "syntax",
                "line": 3,
                "description": "optoin → option",
                "severity": "error",
            }
        ],
        "expected_fixed_config": """
backend web_servers
    balance roundrobin
    option httpchk GET /health
    server web1 192.168.1.1:80 check
""",
        "metadata": {
            "keywords": ["backend", "option", "httpchk"],
            "estimated_time": 20,
            "requires_rag": ["option httpchk", "HTTP health check"],
        },
    },
    {
        "id": "syntax_002",
        "name": "ACL avec parenthèses manquantes",
        "category": "syntax_error",
        "type": "correction",
        "config_type": "snippet",
        "difficulty": "medium",
        "original_config": """
frontend http_in
    bind *:80
    acl is_api path_beg /api
    http-request deny if is_api and src 10.0.0.0/8
""",
        "expected_errors": [
            {
                "type": "syntax",
                "line": 4,
                "description": "Parenthèses manquantes autour de la condition",
                "severity": "error",
            }
        ],
        "expected_fixed_config": """
frontend http_in
    bind *:80
    acl is_api path_beg /api
    http-request deny if is_api { src 10.0.0.0/8 }
""",
        "metadata": {
            "keywords": ["frontend", "acl", "http-request", "deny"],
            "estimated_time": 30,
            "requires_rag": ["acl", "http-request deny"],
        },
    },
    {
        "id": "syntax_003",
        "name": "Chemin de fichier sans guillemets",
        "category": "syntax_error",
        "type": "correction",
        "config_type": "snippet",
        "difficulty": "easy",
        "original_config": """
frontend https_in
    bind *:443 ssl crt /etc/ssl/cert.pem
""",
        "expected_errors": [
            {
                "type": "syntax",
                "line": 2,
                "description": "Chemin de certificat sans guillemets",
                "severity": "warning",
            }
        ],
        "expected_fixed_config": """
frontend https_in
    bind *:443 ssl crt "/etc/ssl/cert.pem"
""",
        "metadata": {
            "keywords": ["frontend", "bind", "ssl", "crt"],
            "estimated_time": 20,
            "requires_rag": ["bind", "ssl", "certificate"],
        },
    },
    {
        "id": "syntax_004",
        "name": "Directive bind avec syntaxe incorrecte",
        "category": "syntax_error",
        "type": "correction",
        "config_type": "snippet",
        "difficulty": "easy",
        "original_config": """
frontend http_in
    bind 80
    default_backend web_servers
""",
        "expected_errors": [
            {
                "type": "syntax",
                "line": 2,
                "description": "Port sans adresse ou wildcard",
                "severity": "error",
            }
        ],
        "expected_fixed_config": """
frontend http_in
    bind *:80
    default_backend web_servers
""",
        "metadata": {
            "keywords": ["frontend", "bind"],
            "estimated_time": 20,
            "requires_rag": ["bind"],
        },
    },
    {
        "id": "syntax_005",
        "name": "Option httpchk sans paramètres",
        "category": "syntax_error",
        "type": "correction",
        "config_type": "snippet",
        "difficulty": "medium",
        "original_config": """
backend web_servers
    balance roundrobin
    option httpchk
    server web1 192.168.1.1:80 check
""",
        "expected_errors": [
            {
                "type": "syntax",
                "line": 3,
                "description": "option httpchk requiert au moins une méthode",
                "severity": "warning",
            }
        ],
        "expected_fixed_config": """
backend web_servers
    balance roundrobin
    option httpchk GET /health
    server web1 192.168.1.1:80 check
""",
        "metadata": {
            "keywords": ["backend", "option", "httpchk"],
            "estimated_time": 25,
            "requires_rag": ["option httpchk", "HTTP health check"],
        },
    },
    {
        "id": "syntax_006",
        "name": "Commentaire avec caractère invalide",
        "category": "syntax_error",
        "type": "correction",
        "config_type": "snippet",
        "difficulty": "easy",
        "original_config": """
backend web_servers
    # Backend pour les serveurs web
    balance roundrobin
    server web1 192.168.1.1:80 check
""",
        "expected_errors": [
            {
                "type": "syntax",
                "line": 2,
                "description": "Commentaire valide (pas d'erreur)",
                "severity": "info",
            }
        ],
        "expected_fixed_config": """
backend web_servers
    # Backend pour les serveurs web
    balance roundrobin
    server web1 192.168.1.1:80 check
""",
        "metadata": {
            "keywords": ["backend", "comment"],
            "estimated_time": 15,
            "requires_rag": [],
        },
    },
    # -------------------------------------------------------------------------
    # Erreurs Logiques (6 tests)
    # -------------------------------------------------------------------------
    {
        "id": "logic_001",
        "name": "Port supérieur à 65535",
        "category": "logic_error",
        "type": "correction",
        "config_type": "snippet",
        "difficulty": "easy",
        "original_config": """
frontend http_in
    bind *:70000
    default_backend web_servers
""",
        "expected_errors": [
            {
                "type": "logic",
                "line": 2,
                "description": "Port 70000 > 65535",
                "severity": "error",
            }
        ],
        "expected_fixed_config": """
frontend http_in
    bind *:8080
    default_backend web_servers
""",
        "metadata": {
            "keywords": ["frontend", "bind", "port"],
            "estimated_time": 20,
            "requires_rag": ["bind", "port"],
        },
    },
    {
        "id": "logic_002",
        "name": "use_backend avec backend non défini",
        "category": "logic_error",
        "type": "correction",
        "config_type": "snippet",
        "difficulty": "medium",
        "original_config": """
frontend http_in
    bind *:80
    acl is_api path_beg /api
    use_backend api_servers
""",
        "expected_errors": [
            {
                "type": "reference",
                "line": 4,
                "description": "Backend 'api_servers' non défini",
                "severity": "error",
            }
        ],
        "expected_fixed_config": """
frontend http_in
    bind *:80
    acl is_api path_beg /api
    use_backend api_servers

backend api_servers
    balance roundrobin
    server api1 192.168.1.10:80 check
""",
        "metadata": {
            "keywords": ["frontend", "use_backend", "backend"],
            "estimated_time": 30,
            "requires_rag": ["use_backend", "backend"],
        },
    },
    {
        "id": "logic_003",
        "name": "Option httplog en mode TCP",
        "category": "logic_error",
        "type": "correction",
        "config_type": "snippet",
        "difficulty": "medium",
        "original_config": """
backend tcp_backend
    mode tcp
    option httplog
    server tcp1 192.168.1.1:3306 check
""",
        "expected_errors": [
            {
                "type": "logic",
                "line": 3,
                "description": "option httplog incompatible avec mode tcp",
                "severity": "error",
            }
        ],
        "expected_fixed_config": """
backend tcp_backend
    mode tcp
    option tcplog
    server tcp1 192.168.1.1:3306 check
""",
        "metadata": {
            "keywords": ["backend", "mode", "option", "httplog", "tcplog"],
            "estimated_time": 30,
            "requires_rag": ["mode", "option httplog", "option tcplog"],
        },
    },
    {
        "id": "logic_004",
        "name": "Timeout avec valeur négative",
        "category": "logic_error",
        "type": "correction",
        "config_type": "snippet",
        "difficulty": "easy",
        "original_config": """
defaults
    timeout connect -5s
    timeout client 10s
    timeout server 10s
""",
        "expected_errors": [
            {
                "type": "logic",
                "line": 2,
                "description": "Timeout négatif",
                "severity": "error",
            }
        ],
        "expected_fixed_config": """
defaults
    timeout connect 5s
    timeout client 10s
    timeout server 10s
""",
        "metadata": {
            "keywords": ["defaults", "timeout"],
            "estimated_time": 20,
            "requires_rag": ["timeout"],
        },
    },
    {
        "id": "logic_005",
        "name": "Deux serveurs avec le même nom",
        "category": "logic_error",
        "type": "correction",
        "config_type": "snippet",
        "difficulty": "medium",
        "original_config": """
backend web_servers
    balance roundrobin
    server web1 192.168.1.1:80 check
    server web1 192.168.1.2:80 check
""",
        "expected_errors": [
            {
                "type": "logic",
                "line": 4,
                "description": "Nom de serveur dupliqué 'web1'",
                "severity": "warning",
            }
        ],
        "expected_fixed_config": """
backend web_servers
    balance roundrobin
    server web1 192.168.1.1:80 check
    server web2 192.168.1.2:80 check
""",
        "metadata": {
            "keywords": ["backend", "server"],
            "estimated_time": 25,
            "requires_rag": ["server"],
        },
    },
    {
        "id": "logic_006",
        "name": "Stick-table déclarée mais non utilisée",
        "category": "logic_error",
        "type": "correction",
        "config_type": "snippet",
        "difficulty": "hard",
        "original_config": """
frontend http_in
    bind *:80
    stick-table type ip size 100k expire 30s store conn_rate(10s)
    http-request deny if { src_conn_rate gt 100 }
""",
        "expected_errors": [
            {
                "type": "logic",
                "line": 3,
                "description": "stick-table sans track-sc",
                "severity": "warning",
            },
            {
                "type": "syntax",
                "line": 4,
                "description": "src_conn_rate nécessite track-sc",
                "severity": "error",
            },
        ],
        "expected_fixed_config": """
frontend http_in
    bind *:80
    stick-table type ip size 100k expire 30s store conn_rate(10s)
    http-request track-sc0 src
    http-request deny if { sc0_conn_rate gt 100 }
""",
        "metadata": {
            "keywords": ["frontend", "stick-table", "track-sc", "conn_rate"],
            "estimated_time": 45,
            "requires_rag": ["stick-table", "track-sc", "conn_rate"],
        },
    },
    # -------------------------------------------------------------------------
    # Erreurs de Sécurité (4 tests)
    # -------------------------------------------------------------------------
    {
        "id": "security_001",
        "name": "SSL activé sans vérification de certificat",
        "category": "security_error",
        "type": "correction",
        "config_type": "snippet",
        "difficulty": "medium",
        "original_config": """
frontend https_in
    bind *:443 ssl crt /etc/ssl/cert.pem verify none
    default_backend web_servers
""",
        "expected_errors": [
            {
                "type": "security",
                "line": 2,
                "description": "SSL sans vérification de certificat",
                "severity": "warning",
            }
        ],
        "expected_fixed_config": """
frontend https_in
    bind *:443 ssl crt /etc/ssl/cert.pem verify required ca-file /etc/ssl/ca.pem
    default_backend web_servers
""",
        "metadata": {
            "keywords": ["frontend", "bind", "ssl", "verify"],
            "estimated_time": 30,
            "requires_rag": ["bind", "ssl", "verify", "ca-file"],
        },
    },
    {
        "id": "security_002",
        "name": "Statistiques activées sans authentification",
        "category": "security_error",
        "type": "correction",
        "config_type": "snippet",
        "difficulty": "easy",
        "original_config": """
listen stats
    bind *:8404
    stats enable
    stats uri /stats
""",
        "expected_errors": [
            {
                "type": "security",
                "line": 3,
                "description": "Stats sans authentification",
                "severity": "warning",
            }
        ],
        "expected_fixed_config": """
listen stats
    bind *:8404
    stats enable
    stats uri /stats
    stats auth admin:securepassword
""",
        "metadata": {
            "keywords": ["listen", "stats", "auth"],
            "estimated_time": 20,
            "requires_rag": ["stats", "stats auth"],
        },
    },
    {
        "id": "security_003",
        "name": "ACL autorisant toutes les adresses IP",
        "category": "security_error",
        "type": "correction",
        "config_type": "snippet",
        "difficulty": "medium",
        "original_config": """
frontend admin
    bind *:8080
    acl is_admin src 0.0.0.0/0
    http-request allow if is_admin
""",
        "expected_errors": [
            {
                "type": "security",
                "line": 3,
                "description": "ACL permissive (0.0.0.0/0)",
                "severity": "warning",
            }
        ],
        "expected_fixed_config": """
frontend admin
    bind *:8080
    acl is_admin src 10.0.0.0/8
    http-request allow if is_admin
""",
        "metadata": {
            "keywords": ["frontend", "acl", "src"],
            "estimated_time": 25,
            "requires_rag": ["acl", "src"],
        },
    },
    {
        "id": "security_004",
        "name": "Option forwardfor manquante en mode HTTP",
        "category": "security_error",
        "type": "improvement",
        "config_type": "snippet",
        "difficulty": "easy",
        "original_config": """
frontend http_in
    bind *:80
    mode http
    default_backend web_servers
""",
        "expected_errors": [],
        "expected_fixed_config": """
frontend http_in
    bind *:80
    mode http
    option forwardfor
    default_backend web_servers
""",
        "metadata": {
            "keywords": ["frontend", "mode", "forwardfor"],
            "estimated_time": 20,
            "requires_rag": ["option forwardfor"],
        },
    },
    # -------------------------------------------------------------------------
    # Améliorations (4 tests)
    # -------------------------------------------------------------------------
    {
        "id": "optim_001",
        "name": "Ajout de health check HTTP",
        "category": "optimization",
        "type": "improvement",
        "config_type": "snippet",
        "difficulty": "easy",
        "original_config": """
backend web_servers
    balance roundrobin
    server web1 192.168.1.1:80
    server web2 192.168.1.2:80
""",
        "expected_errors": [],
        "expected_fixed_config": """
backend web_servers
    balance roundrobin
    option httpchk GET /health
    server web1 192.168.1.1:80 check
    server web2 192.168.1.2:80 check
""",
        "metadata": {
            "keywords": ["backend", "server", "check", "httpchk"],
            "estimated_time": 30,
            "requires_rag": ["server check", "option httpchk"],
        },
    },
    {
        "id": "optim_002",
        "name": "Optimisation des timeouts par défaut",
        "category": "optimization",
        "type": "improvement",
        "config_type": "snippet",
        "difficulty": "medium",
        "original_config": """
defaults
    timeout connect 10s
    timeout client 30s
    timeout server 30s
""",
        "expected_errors": [],
        "expected_fixed_config": """
defaults
    timeout connect 5s
    timeout client 10s
    timeout server 10s
    timeout http-keep-alive 1s
""",
        "metadata": {
            "keywords": ["defaults", "timeout"],
            "estimated_time": 25,
            "requires_rag": ["timeout", "best practices"],
        },
    },
    {
        "id": "optim_003",
        "name": "Configuration des logs détaillés",
        "category": "optimization",
        "type": "improvement",
        "config_type": "snippet",
        "difficulty": "easy",
        "original_config": """
global
    maxconn 1000

defaults
    mode http
""",
        "expected_errors": [],
        "expected_fixed_config": """
global
    log stdout local0
    log-tag global
    maxconn 1000

defaults
    mode http
    log global
    option httplog
""",
        "metadata": {
            "keywords": ["global", "defaults", "log", "httplog"],
            "estimated_time": 25,
            "requires_rag": ["log", "option httplog"],
        },
    },
    {
        "id": "optim_004",
        "name": "Amélioration de la configuration SSL",
        "category": "optimization",
        "type": "improvement",
        "config_type": "snippet",
        "difficulty": "hard",
        "original_config": """
frontend https_in
    bind *:443 ssl crt /etc/ssl/cert.pem
    mode http
    default_backend web_servers
""",
        "expected_errors": [],
        "expected_fixed_config": """
frontend https_in
    bind *:443 ssl crt /etc/ssl/cert.pem verify required ca-file /etc/ssl/ca.pem alpn h2,http/1.1
    mode http
    option forwardfor
    default_backend web_servers
""",
        "metadata": {
            "keywords": ["frontend", "bind", "ssl", "alpn"],
            "estimated_time": 40,
            "requires_rag": ["bind", "ssl", "alpn", "forwardfor"],
        },
    },
    # -------------------------------------------------------------------------
    # Configurations Complètes (3 tests)
    # -------------------------------------------------------------------------
    {
        "id": "full_001",
        "name": "Configuration HTTP complète avec erreurs",
        "category": "mixed",
        "type": "correction",
        "config_type": "full_config",
        "difficulty": "medium",
        "original_config": """
global
    log stdout local0
    maxconn 1000

defaults
    mode http
    timeout connect -5s
    timeout client 10s
    timeout server 10s

frontend http_in
    bind 80
    optoin httplog
    default_backend web_servers

backend web_servers
    balance roundrobin
    server web1 192.168.1.1:80
    server web1 192.168.1.2:80
""",
        "expected_errors": [
            {
                "type": "logic",
                "line": 8,
                "description": "Timeout négatif",
                "severity": "error",
            },
            {
                "type": "syntax",
                "line": 13,
                "description": "optoin → option",
                "severity": "error",
            },
            {
                "type": "syntax",
                "line": 13,
                "description": "Port sans wildcard",
                "severity": "error",
            },
            {
                "type": "logic",
                "line": 19,
                "description": "Nom de serveur dupliqué",
                "severity": "warning",
            },
        ],
        "expected_fixed_config": """
global
    log stdout local0
    maxconn 1000

defaults
    mode http
    timeout connect 5s
    timeout client 10s
    timeout server 10s

frontend http_in
    bind *:80
    option httplog
    default_backend web_servers

backend web_servers
    balance roundrobin
    option httpchk GET /health
    server web1 192.168.1.1:80 check
    server web2 192.168.1.2:80 check
""",
        "metadata": {
            "keywords": ["global", "defaults", "frontend", "backend"],
            "estimated_time": 60,
            "requires_rag": ["timeout", "bind", "option", "server"],
        },
    },
    {
        "id": "full_002",
        "name": "Configuration TCP avancée",
        "category": "optimization",
        "type": "improvement",
        "config_type": "full_config",
        "difficulty": "hard",
        "original_config": """
global
    log stdout local0

defaults
    mode tcp
    timeout connect 10s
    timeout client 30s
    timeout server 30s

frontend mysql_in
    bind *:3306
    default_backend mysql_servers

backend mysql_servers
    balance roundrobin
    server mysql1 192.168.1.10:3306
    server mysql2 192.168.1.11:3306
""",
        "expected_errors": [],
        "expected_fixed_config": """
global
    log stdout local0
    maxconn 1000

defaults
    mode tcp
    timeout connect 5s
    timeout client 10s
    timeout server 10s
    option tcplog

frontend mysql_in
    bind *:3306
    mode tcp
    default_backend mysql_servers

backend mysql_servers
    mode tcp
    balance roundrobin
    option mysql-check
    server mysql1 192.168.1.10:3306 check
    server mysql2 192.168.1.11:3306 check
""",
        "metadata": {
            "keywords": ["tcp", "mysql", "mode", "check"],
            "estimated_time": 60,
            "requires_rag": ["mode tcp", "option mysql-check"],
        },
    },
    {
        "id": "full_003",
        "name": "Configuration multi-backend avec ACLs",
        "category": "mixed",
        "type": "correction",
        "config_type": "full_config",
        "difficulty": "hard",
        "original_config": """
global
    log stdout local0
    maxconn 1000

defaults
    mode http
    timeout connect 5s
    timeout client 10s
    timeout server 10s

frontend http_in
    bind *:80
    bind *:443 ssl crt /etc/ssl/cert.pem verify none
    acl is_api path_beg /api
    acl is_static path_beg /static
    use_backend api_servers
    use_backend static_servers

backend api_servers
    balance roundrobin
    server api1 192.168.1.10:80

backend static_servers
    balance roundrobin
    server static1 192.168.1.20:80
""",
        "expected_errors": [
            {
                "type": "security",
                "line": 14,
                "description": "SSL sans vérification",
                "severity": "warning",
            },
            {
                "type": "logic",
                "line": 17,
                "description": "use_backend sans condition",
                "severity": "error",
            },
            {
                "type": "logic",
                "line": 18,
                "description": "use_backend sans condition",
                "severity": "error",
            },
        ],
        "expected_fixed_config": """
global
    log stdout local0
    maxconn 1000

defaults
    mode http
    timeout connect 5s
    timeout client 10s
    timeout server 10s
    option httplog
    option forwardfor

frontend http_in
    bind *:80
    bind *:443 ssl crt /etc/ssl/cert.pem verify required ca-file /etc/ssl/ca.pem
    mode http
    acl is_api path_beg /api
    acl is_static path_beg /static
    use_backend api_servers if is_api
    use_backend static_servers if is_static
    default_backend web_servers

backend api_servers
    balance roundrobin
    option httpchk GET /health
    server api1 192.168.1.10:80 check

backend static_servers
    balance roundrobin
    server static1 192.168.1.20:80 check

backend web_servers
    balance roundrobin
    option httpchk GET /health
    server web1 192.168.1.1:80 check
""",
        "metadata": {
            "keywords": ["frontend", "backend", "acl", "ssl", "use_backend"],
            "estimated_time": 90,
            "requires_rag": ["acl", "use_backend", "ssl", "verify"],
        },
    },
]


# ============================================================================
# Fonctions d'accès au dataset
# ============================================================================


def get_all_tests() -> list[dict[str, Any]]:
    """Retourne tous les cas de test.

    Returns:
        Liste de tous les cas de test disponibles.
    """
    return TEST_CASES.copy()


def get_tests_by_category(category: str) -> list[dict[str, Any]]:
    """Retourne les tests par catégorie.

    Args:
        category: Catégorie de test (syntax_error, logic_error, security_error,
                   optimization, mixed).

    Returns:
        Liste des tests de la catégorie spécifiée.
    """
    return [test for test in TEST_CASES if test["category"] == category]


def get_tests_by_difficulty(difficulty: str) -> list[dict[str, Any]]:
    """Retourne les tests par difficulté.

    Args:
        difficulty: Niveau de difficulté (easy, medium, hard).

    Returns:
        Liste des tests du niveau de difficulté spécifié.
    """
    return [test for test in TEST_CASES if test["difficulty"] == difficulty]


def get_tests_by_type(test_type: str) -> list[dict[str, Any]]:
    """Retourne les tests par type.

    Args:
        test_type: Type de test (correction, detection, improvement).

    Returns:
        Liste des tests du type spécifié.
    """
    return [test for test in TEST_CASES if test["type"] == test_type]


def get_test_by_id(test_id: str) -> dict[str, Any] | None:
    """Retourne un test par son ID.

    Args:
        test_id: Identifiant unique du test.

    Returns:
        Le test correspondant ou None si non trouvé.
    """
    for test in TEST_CASES:
        if test["id"] == test_id:
            return test.copy()
    return None


def get_quick_tests() -> list[dict[str, Any]]:
    """Retourne les tests rapides (easy, < 30s estimés).

    Returns:
        Liste des tests faciles avec un temps estimé inférieur à 30 secondes.
    """
    return [
        test
        for test in TEST_CASES
        if test["difficulty"] == "easy" and test["metadata"]["estimated_time"] < 30
    ]


def get_full_tests() -> list[dict[str, Any]]:
    """Retourne tous les tests.

    Returns:
        Liste complète de tous les cas de test.
    """
    return TEST_CASES.copy()


# ============================================================================
# Fonctions utilitaires
# ============================================================================


def get_dataset_statistics() -> dict[str, Any]:
    """Calcule et retourne les statistiques du dataset.

    Returns:
        Dictionnaire contenant les statistiques du dataset.
    """
    total = len(TEST_CASES)

    # Par catégorie
    categories: dict[str, int] = {}
    for test in TEST_CASES:
        cat = test["category"]
        categories[cat] = categories.get(cat, 0) + 1

    # Par difficulté
    difficulties: dict[str, int] = {}
    for test in TEST_CASES:
        diff = test["difficulty"]
        difficulties[diff] = difficulties.get(diff, 0) + 1

    # Par type
    types: dict[str, int] = {}
    for test in TEST_CASES:
        t = test["type"]
        types[t] = types.get(t, 0) + 1

    # Temps total estimé
    total_time = sum(test["metadata"]["estimated_time"] for test in TEST_CASES)

    return {
        "total": total,
        "by_category": categories,
        "by_difficulty": difficulties,
        "by_type": types,
        "total_estimated_time_seconds": total_time,
        "total_estimated_time_minutes": round(total_time / 60, 1),
    }


def print_statistics() -> None:
    """Affiche les statistiques du dataset de manière lisible."""
    stats = get_dataset_statistics()

    print("=" * 60)
    print("Statistiques du Dataset de Test HAProxy")
    print("=" * 60)
    print(f"\nNombre total de tests : {stats['total']}")
    print(f"Temps estimé total : {stats['total_estimated_time_minutes']} minutes")

    print("\nPar catégorie :")
    for category, count in sorted(stats["by_category"].items()):
        print(f"  - {category}: {count}")

    print("\nPar difficulté :")
    for difficulty, count in sorted(stats["by_difficulty"].items()):
        print(f"  - {difficulty}: {count}")

    print("\nPar type :")
    for test_type, count in sorted(stats["by_type"].items()):
        print(f"  - {test_type}: {count}")

    print("\n" + "=" * 60)


# ============================================================================
# Test du module
# ============================================================================

if __name__ == "__main__":
    # Afficher les statistiques du dataset
    print_statistics()

    # Tester les fonctions d'accès
    print("\nTests des fonctions d'accès :")
    print(f"  get_all_tests() : {len(get_all_tests())} tests")
    print(
        f"  get_tests_by_category('syntax_error') : {len(get_tests_by_category('syntax_error'))} tests"
    )
    print(
        f"  get_tests_by_difficulty('easy') : {len(get_tests_by_difficulty('easy'))} tests"
    )
    print(
        f"  get_tests_by_type('correction') : {len(get_tests_by_type('correction'))} tests"
    )
    print(
        f"  get_test_by_id('syntax_001') : {get_test_by_id('syntax_001')['name'] if get_test_by_id('syntax_001') else 'Not found'}"
    )
    print(f"  get_quick_tests() : {len(get_quick_tests())} tests")
    print(f"  get_full_tests() : {len(get_full_tests())} tests")

    # Afficher un exemple de test
    print("\nExemple de test (syntax_001) :")
    example = get_test_by_id("syntax_001")
    if example:
        print(f"  ID: {example['id']}")
        print(f"  Nom: {example['name']}")
        print(f"  Catégorie: {example['category']}")
        print(f"  Difficulté: {example['difficulty']}")
        print(f"  Temps estimé: {example['metadata']['estimated_time']}s")
