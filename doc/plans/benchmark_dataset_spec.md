# Spécification du Dataset de Test du Benchmark

## Fichier : `bench_config_dataset.py`

Ce fichier contient le dataset de cas de test pour évaluer la correction de fichiers de configuration HAProxy.

## Structure des Cas de Test

### Format d'un Cas de Test

```python
{
    "id": "test_001",
    "name": "Backend avec health check HTTP mal configuré",
    "category": "syntax_error",
    "type": "correction",
    "config_type": "snippet",
    "difficulty": "easy",
    "original_config": "...",
    "expected_errors": [
        {
            "type": "syntax",
            "line": 5,
            "description": "option httpchk mal orthographiée",
            "severity": "error"
        }
    ],
    "expected_fixed_config": "...",
    "metadata": {
        "keywords": ["backend", "healthcheck", "httpchk"],
        "estimated_time": 30,
        "requires_rag": ["option httpchk", "HTTP health check"]
    }
}
```

### Champs Définis

| Champ | Type | Description |
|-------|------|-------------|
| `id` | str | Identifiant unique du test |
| `name` | str | Nom descriptif du test |
| `category` | str | Catégorie : `syntax_error`, `logic_error`, `security_error`, `optimization` |
| `type` | str | Type : `correction`, `detection`, `improvement` |
| `config_type` | str | Type de config : `snippet`, `full_config` |
| `difficulty` | str | Difficulté : `easy`, `medium`, `hard` |
| `original_config` | str | Configuration avec erreurs |
| `expected_errors` | list | Liste des erreurs attendues |
| `expected_fixed_config` | str | Configuration corrigée attendue |
| `metadata` | dict | Métadonnées additionnelles |

## Catégories de Tests

### 1. Erreurs Syntaxiques (6 tests)

#### Test 001 : Mot-clé mal orthographié
```python
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
            "severity": "error"
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
        "requires_rag": ["option httpchk", "HTTP health check"]
    }
}
```

#### Test 002 : Parenthèses manquantes dans ACL
```python
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
            "severity": "error"
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
        "requires_rag": ["acl", "http-request deny"]
    }
}
```

#### Test 003 : Guillemets manquants
```python
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
            "severity": "warning"
        }
    ],
    "expected_fixed_config": """
frontend https_in
    bind *:443 ssl crt "/etc/ssl/cert.pem"
""",
    "metadata": {
        "keywords": ["frontend", "bind", "ssl", "crt"],
        "estimated_time": 20,
        "requires_rag": ["bind", "ssl", "certificate"]
    }
}
```

#### Test 004 : Syntaxe bind incorrecte
```python
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
            "severity": "error"
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
        "requires_rag": ["bind"]
    }
}
```

#### Test 005 : Option sans paramètres requis
```python
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
            "severity": "warning"
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
        "requires_rag": ["option httpchk", "HTTP health check"]
    }
}
```

#### Test 006 : Commentaire mal formé
```python
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
            "severity": "info"
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
        "requires_rag": []
    }
}
```

### 2. Erreurs Logiques (6 tests)

#### Test 007 : Port invalide
```python
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
            "severity": "error"
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
        "requires_rag": ["bind", "port"]
    }
}
```

#### Test 008 : Backend référencé inexistant
```python
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
            "severity": "error"
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
        "requires_rag": ["use_backend", "backend"]
    }
}
```

#### Test 009 : Option incompatible avec le mode
```python
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
            "severity": "error"
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
        "requires_rag": ["mode", "option httplog", "option tcplog"]
    }
}
```

#### Test 010 : Timeout négatif
```python
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
            "severity": "error"
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
        "requires_rag": ["timeout"]
    }
}
```

#### Test 011 : Serveur dupliqué
```python
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
            "severity": "warning"
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
        "requires_rag": ["server"]
    }
}
```

#### Test 012 : Stick-table sans track-sc
```python
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
            "severity": "warning"
        },
        {
            "type": "syntax",
            "line": 4,
            "description": "src_conn_rate nécessite track-sc",
            "severity": "error"
        }
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
        "requires_rag": ["stick-table", "track-sc", "conn_rate"]
    }
}
```

### 3. Erreurs de Sécurité (4 tests)

#### Test 013 : SSL sans vérification
```python
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
            "severity": "warning"
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
        "requires_rag": ["bind", "ssl", "verify", "ca-file"]
    }
}
```

#### Test 014 : Stats sans authentification
```python
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
            "severity": "warning"
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
        "requires_rag": ["stats", "stats auth"]
    }
}
```

#### Test 015 : ACL permissive
```python
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
            "severity": "warning"
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
        "requires_rag": ["acl", "src"]
    }
}
```

#### Test 016 : Forwardfor manquant
```python
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
        "requires_rag": ["option forwardfor"]
    }
}
```

### 4. Améliorations (4 tests)

#### Test 017 : Ajout de health check manquant
```python
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
        "requires_rag": ["server check", "option httpchk"]
    }
}
```

#### Test 018 : Optimisation des timeouts
```python
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
        "requires_rag": ["timeout", "best practices"]
    }
}
```

#### Test 019 : Ajout de logs détaillés
```python
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
        "requires_rag": ["log", "option httplog"]
    }
}
```

#### Test 020 : Configuration SSL améliorée
```python
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
        "requires_rag": ["bind", "ssl", "alpn", "forwardfor"]
    }
}
```

### 5. Fichiers de Configuration Complets (3 tests)

#### Test 021 : Configuration HTTP simple avec erreurs
```python
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
        {"type": "logic", "line": 8, "description": "Timeout négatif", "severity": "error"},
        {"type": "syntax", "line": 13, "description": "optoin → option", "severity": "error"},
        {"type": "syntax", "line": 13, "description": "Port sans wildcard", "severity": "error"},
        {"type": "logic", "line": 19, "description": "Nom de serveur dupliqué", "severity": "warning"}
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
        "requires_rag": ["timeout", "bind", "option", "server"]
    }
}
```

#### Test 022 : Configuration TCP avancée
```python
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
        "requires_rag": ["mode tcp", "option mysql-check"]
    }
}
```

#### Test 023 : Configuration multi-backend complexe
```python
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
        {"type": "security", "line": 14, "description": "SSL sans vérification", "severity": "warning"},
        {"type": "logic", "line": 17, "description": "use_backend sans condition", "severity": "error"},
        {"type": "logic", "line": 18, "description": "use_backend sans condition", "severity": "error"}
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
        "requires_rag": ["acl", "use_backend", "ssl", "verify"]
    }
}
```

## Fonctions d'Accès au Dataset

```python
def get_all_tests() -> list[dict]:
    """Retourne tous les cas de test."""

def get_tests_by_category(category: str) -> list[dict]:
    """Retourne les tests par catégorie (syntax_error, logic_error, security_error, optimization, mixed)."""

def get_tests_by_difficulty(difficulty: str) -> list[dict]:
    """Retourne les tests par difficulté (easy, medium, hard)."""

def get_tests_by_type(test_type: str) -> list[dict]:
    """Retourne les tests par type (correction, detection, improvement)."""

def get_test_by_id(test_id: str) -> dict | None:
    """Retourne un test par son ID."""

def get_quick_tests() -> list[dict]:
    """Retourne les tests rapides (easy, < 30s estimés)."""

def get_full_tests() -> list[dict]:
    """Retourne tous les tests."""
```

## Statistiques du Dataset

| Catégorie | Nombre | Difficulté Moyenne |
|-----------|---------|-------------------|
| Erreurs Syntaxiques | 6 | Easy-Medium |
| Erreurs Logiques | 6 | Medium-Hard |
| Erreurs de Sécurité | 4 | Easy-Medium |
| Améliorations | 4 | Easy-Hard |
| Configurations Complètes | 3 | Medium-Hard |
| **Total** | **23** | **Medium** |

## Estimation du Temps d'Exécution

| Mode | Nombre de Tests | Temps Estimé |
|------|----------------|---------------|
| Quick (tests faciles) | 8 | ~4 min |
| Standard (tous sauf hard) | 18 | ~12 min |
| Full (tous les tests) | 23 | ~20 min |

## Notes d'Implémentation

1. **Validation des réponses** : Le validateur syntaxique sera utilisé pour vérifier les corrections proposées par les LLM
2. **Comparaison avec l'attendu** : Les configurations corrigées seront comparées avec `expected_fixed_config`
3. **Scoring** : Les métriques seront calculées en comparant les erreurs détectées avec les erreurs attendues
4. **Extensibilité** : Le dataset est conçu pour être facilement extensible avec de nouveaux cas de test
