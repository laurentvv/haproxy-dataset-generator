#!/usr/bin/env python3
"""
bench_questions.py - 100 questions de benchmark HAProxy

Niveaux :
- QUICK     : 7 questions (3 min)
- STANDARD  : 20 questions (8 min)
- FULL      : 100 questions (45 min)

Ce fichier est un module de données (base de questions), pas un script d'exécution.
Il est importé par 07_bench_targeted.py et 08_bench_ollama.py.
"""

QUESTIONS = [
    # ── QUICK (7 questions) ───────────────────────────────────────────────────
    {
        "id": "quick_healthcheck",
        "level": "quick",
        "category": "healthcheck",
        "question": "Comment configurer un health check HTTP dans HAProxy ?",
        "expected_keywords": ["option httpchk", "check", "GET", "http-check", "server"],
        "min_length": 200,
    },
    {
        "id": "quick_bind",
        "level": "quick",
        "category": "bind",
        "question": "Quelle est la syntaxe de la directive bind ?",
        "expected_keywords": ["bind", "port", "ssl", "crt", "frontend"],
        "min_length": 150,
    },
    {
        "id": "quick_stick_table",
        "level": "quick",
        "category": "stick-table",
        "question": "Comment limiter les connexions par IP avec stick-table ?",
        "expected_keywords": ["stick-table", "conn_rate", "track-sc", "deny", "ip"],
        "min_length": 200,
    },
    {
        "id": "quick_acl",
        "level": "quick",
        "category": "acl",
        "question": "Comment utiliser les ACLs pour filtrer le trafic ?",
        "expected_keywords": ["acl", "path_beg", "hdr", "if", "deny"],
        "min_length": 200,
    },
    {
        "id": "quick_timeout",
        "level": "quick",
        "category": "timeout",
        "question": "Quelles sont les options de timeout disponibles ?",
        "expected_keywords": ["timeout", "connect", "client", "server", "http-request"],
        "min_length": 200,
    },
    {
        "id": "quick_ssl",
        "level": "quick",
        "category": "ssl",
        "question": "Comment configurer SSL/TLS sur un frontend ?",
        "expected_keywords": ["bind", "ssl", "crt", "pem", "certificate"],
        "min_length": 200,
    },
    {
        "id": "quick_backend",
        "level": "quick",
        "category": "backend",
        "question": "Comment configurer un backend avec équilibrage de charge ?",
        "expected_keywords": ["backend", "balance", "roundrobin", "server", "check"],
        "min_length": 200,
    },

    # ── STANDARD (13 questions supplémentaires = 20 total) ────────────────────
    {
        "id": "std_tcp_check",
        "level": "standard",
        "category": "healthcheck",
        "question": "Comment configurer un health check TCP dans HAProxy ?",
        "expected_keywords": ["tcp-check", "check", "inter", "fall", "rise"],
        "min_length": 200,
    },
    {
        "id": "std_bind_ssl",
        "level": "standard",
        "category": "ssl",
        "question": "Comment activer SSL sur un bind avec certificat ?",
        "expected_keywords": ["bind", "ssl", "crt", "cert", "pem"],
        "min_length": 200,
    },
    {
        "id": "std_acl_path",
        "level": "standard",
        "category": "acl",
        "question": "Comment créer une ACL basée sur le chemin URL ?",
        "expected_keywords": ["acl", "path_beg", "path_end", "path", "url"],
        "min_length": 200,
    },
    {
        "id": "std_stick_http_req",
        "level": "standard",
        "category": "stick-table",
        "question": "Comment limiter le nombre de requêtes HTTP par IP avec stick-table ?",
        "expected_keywords": ["stick-table", "http_req_rate", "track-sc", "deny", "ip"],
        "min_length": 200,
    },
    {
        "id": "std_balance_leastconn",
        "level": "standard",
        "category": "backend",
        "question": "Comment configurer l'algorithme leastconn pour le load balancing ?",
        "expected_keywords": ["balance", "leastconn", "backend", "server"],
        "min_length": 200,
    },
    {
        "id": "std_timeout_http",
        "level": "standard",
        "category": "timeout",
        "question": "Comment configurer le timeout http-request ?",
        "expected_keywords": ["timeout", "http-request", "http-request-timeout"],
        "min_length": 150,
    },
    {
        "id": "std_frontend_http",
        "level": "standard",
        "category": "frontend",
        "question": "Comment configurer un frontend HTTP sur le port 80 ?",
        "expected_keywords": ["frontend", "bind", "port", "80", "http"],
        "min_length": 200,
    },
    {
        "id": "std_backend_server",
        "level": "standard",
        "category": "backend",
        "question": "Comment ajouter un serveur dans un backend HAProxy ?",
        "expected_keywords": ["server", "backend", "address", "port", "check"],
        "min_length": 200,
    },
    {
        "id": "std_acl_hdr",
        "level": "standard",
        "category": "acl",
        "question": "Comment créer une ACL basée sur un header HTTP ?",
        "expected_keywords": ["acl", "hdr", "header", "http-request"],
        "min_length": 200,
    },
    {
        "id": "std_ssl_verify",
        "level": "standard",
        "category": "ssl",
        "question": "Comment vérifier le certificat SSL d'un serveur backend ?",
        "expected_keywords": ["ssl", "verify", "ca-file", "cafile", "certificate"],
        "min_length": 200,
    },
    {
        "id": "std_stats_enable",
        "level": "standard",
        "category": "stats",
        "question": "Comment activer les statistiques HAProxy ?",
        "expected_keywords": ["stats", "enable", "uri", "listen"],
        "min_length": 200,
    },
    {
        "id": "std_log_global",
        "level": "standard",
        "category": "logs",
        "question": "Comment configurer les logs globaux dans HAProxy ?",
        "expected_keywords": ["log", "global", "syslog", "facility"],
        "min_length": 200,
    },
    {
        "id": "std_tcp_request",
        "level": "standard",
        "category": "tcp",
        "question": "Comment configurer un proxy TCP pur dans HAProxy ?",
        "expected_keywords": ["mode", "tcp", "frontend", "backend"],
        "min_length": 200,
    },

    # ── FULL (80 questions supplémentaires = 100 total) ───────────────────────
    # Health checks (5)
    {
        "id": "full_httpchk_method",
        "level": "full",
        "category": "healthcheck",
        "question": "Comment spécifier la méthode HTTP pour un health check ?",
        "expected_keywords": ["option httpchk", "GET", "POST", "HEAD", "method"],
        "min_length": 200,
    },
    {
        "id": "full_httpchk_uri",
        "level": "full",
        "category": "healthcheck",
        "question": "Comment spécifier l'URI pour un health check HTTP ?",
        "expected_keywords": ["option httpchk", "uri", "path", "GET"],
        "min_length": 200,
    },
    {
        "id": "full_httpchk_version",
        "level": "full",
        "category": "healthcheck",
        "question": "Comment spécifier la version HTTP pour un health check ?",
        "expected_keywords": ["HTTP", "version", "1.0", "1.1", "2"],
        "min_length": 150,
    },
    {
        "id": "full_check_inter",
        "level": "full",
        "category": "healthcheck",
        "question": "Comment configurer l'intervalle entre les health checks ?",
        "expected_keywords": ["inter", "check", "interval", "server"],
        "min_length": 200,
    },
    {
        "id": "full_check_fall_rise",
        "level": "full",
        "category": "healthcheck",
        "question": "Comment configurer les paramètres fall et rise pour un check ?",
        "expected_keywords": ["fall", "rise", "check", "server"],
        "min_length": 200,
    },
    
    # Backend / Server (8)
    {
        "id": "full_backend_name",
        "level": "full",
        "category": "backend",
        "question": "Comment nommer un backend dans HAProxy ?",
        "expected_keywords": ["backend", "name", "section"],
        "min_length": 150,
    },
    {
        "id": "full_balance_roundrobin",
        "level": "full",
        "category": "backend",
        "question": "Comment configurer l'algorithme roundrobin ?",
        "expected_keywords": ["balance", "roundrobin", "algorithm"],
        "min_length": 200,
    },
    {
        "id": "full_balance_source",
        "level": "full",
        "category": "backend",
        "question": "Comment configurer l'algorithme source pour la persistance ?",
        "expected_keywords": ["balance", "source", "ip", "persistence"],
        "min_length": 200,
    },
    {
        "id": "full_balance_uri",
        "level": "full",
        "category": "backend",
        "question": "Comment configurer l'algorithme uri pour le load balancing ?",
        "expected_keywords": ["balance", "uri", "url", "hash"],
        "min_length": 200,
    },
    {
        "id": "full_server_weight",
        "level": "full",
        "category": "backend",
        "question": "Comment configurer le poids d'un serveur ?",
        "expected_keywords": ["weight", "server", "balance"],
        "min_length": 200,
    },
    {
        "id": "full_server_backup",
        "level": "full",
        "category": "backend",
        "question": "Comment configurer un serveur de backup ?",
        "expected_keywords": ["backup", "server", "failover"],
        "min_length": 200,
    },
    {
        "id": "full_server_disabled",
        "level": "full",
        "category": "backend",
        "question": "Comment désactiver temporairement un serveur ?",
        "expected_keywords": ["disabled", "server", "disable"],
        "min_length": 150,
    },
    {
        "id": "full_server_check_port",
        "level": "full",
        "category": "healthcheck",
        "question": "Comment spécifier un port personnalisé pour les health checks ?",
        "expected_keywords": ["port", "check", "server", "health"],
        "min_length": 200,
    },
    
    # ACLs (10)
    {
        "id": "full_acl_host",
        "level": "full",
        "category": "acl",
        "question": "Comment créer une ACL basée sur le host HTTP ?",
        "expected_keywords": ["acl", "hdr", "host", "domain"],
        "min_length": 200,
    },
    {
        "id": "full_acl_method",
        "level": "full",
        "category": "acl",
        "question": "Comment créer une ACL basée sur la méthode HTTP ?",
        "expected_keywords": ["acl", "method", "GET", "POST", "PUT"],
        "min_length": 200,
    },
    {
        "id": "full_acl_status",
        "level": "full",
        "category": "acl",
        "question": "Comment créer une ACL basée sur le status code de réponse ?",
        "expected_keywords": ["acl", "status", "code", "response"],
        "min_length": 200,
    },
    {
        "id": "full_acl_src",
        "level": "full",
        "category": "acl",
        "question": "Comment créer une ACL basée sur l'IP source ?",
        "expected_keywords": ["acl", "src", "source", "ip", "subnet"],
        "min_length": 200,
    },
    {
        "id": "full_acl_dst",
        "level": "full",
        "category": "acl",
        "question": "Comment créer une ACL basée sur l'IP de destination ?",
        "expected_keywords": ["acl", "dst", "destination", "ip"],
        "min_length": 200,
    },
    {
        "id": "full_acl_port",
        "level": "full",
        "category": "acl",
        "question": "Comment créer une ACL basée sur le port de destination ?",
        "expected_keywords": ["acl", "dst_port", "port", "destination"],
        "min_length": 200,
    },
    {
        "id": "full_acl_beg",
        "level": "full",
        "category": "acl",
        "question": "Comment utiliser path_beg pour matcher un début de chemin ?",
        "expected_keywords": ["path_beg", "acl", "path", "begin"],
        "min_length": 200,
    },
    {
        "id": "full_acl_end",
        "level": "full",
        "category": "acl",
        "question": "Comment utiliser path_end pour matcher une fin de chemin ?",
        "expected_keywords": ["path_end", "acl", "path", "end"],
        "min_length": 200,
    },
    {
        "id": "full_acl_regex",
        "level": "full",
        "category": "acl",
        "question": "Comment utiliser une expression régulière dans une ACL ?",
        "expected_keywords": ["acl", "regex", "regexp", "pattern"],
        "min_length": 200,
    },
    {
        "id": "full_acl_negation",
        "level": "full",
        "category": "acl",
        "question": "Comment négativer une condition ACL avec ! ?",
        "expected_keywords": ["!", "not", "acl", "negation", "unless"],
        "min_length": 200,
    },
    
    # Stick-table (8)
    {
        "id": "full_stick_type",
        "level": "full",
        "category": "stick-table",
        "question": "Comment déclarer le type d'une stick-table ?",
        "expected_keywords": ["stick-table", "type", "ip", "string", "integer"],
        "min_length": 200,
    },
    {
        "id": "full_stick_size",
        "level": "full",
        "category": "stick-table",
        "question": "Comment spécifier la taille d'une stick-table ?",
        "expected_keywords": ["stick-table", "size", "entries", "m"],
        "min_length": 200,
    },
    {
        "id": "full_stick_expire",
        "level": "full",
        "category": "stick-table",
        "question": "Comment configurer l'expiration des entrées stick-table ?",
        "expected_keywords": ["stick-table", "expire", "time", "s", "m"],
        "min_length": 200,
    },
    {
        "id": "full_stick_store",
        "level": "full",
        "category": "stick-table",
        "question": "Comment spécifier les compteurs à stocker dans une stick-table ?",
        "expected_keywords": ["stick-table", "store", "conn_rate", "http_req_rate"],
        "min_length": 200,
    },
    {
        "id": "full_track_sc",
        "level": "full",
        "category": "stick-table",
        "question": "Comment utiliser track-sc pour tracker une connexion ?",
        "expected_keywords": ["track-sc", "stick", "counter", "sc"],
        "min_length": 200,
    },
    {
        "id": "full_http_req_rate",
        "level": "full",
        "category": "stick-table",
        "question": "Comment mesurer le taux de requêtes HTTP avec http_req_rate ?",
        "expected_keywords": ["http_req_rate", "stick-table", "store", "period"],
        "min_length": 200,
    },
    {
        "id": "full_conn_rate",
        "level": "full",
        "category": "stick-table",
        "question": "Comment mesurer le taux de connexions avec conn_rate ?",
        "expected_keywords": ["conn_rate", "stick-table", "store", "period"],
        "min_length": 200,
    },
    {
        "id": "full_deny_429",
        "level": "full",
        "category": "stick-table",
        "question": "Comment retourner un 429 Too Many Requests avec deny ?",
        "expected_keywords": ["deny", "deny_status", "429", "http-request"],
        "min_length": 200,
    },
    
    # SSL (8)
    {
        "id": "full_ssl_cert",
        "level": "full",
        "category": "ssl",
        "question": "Comment spécifier un certificat SSL dans un bind ?",
        "expected_keywords": ["ssl", "crt", "certificate", "pem"],
        "min_length": 200,
    },
    {
        "id": "full_ssl_crt_list",
        "level": "full",
        "category": "ssl",
        "question": "Comment utiliser une liste de certificats avec crt-list ?",
        "expected_keywords": ["crt-list", "ssl", "certificates", "list"],
        "min_length": 200,
    },
    {
        "id": "full_ssl_ca_file",
        "level": "full",
        "category": "ssl",
        "question": "Comment spécifier un fichier CA pour la vérification SSL ?",
        "expected_keywords": ["ca-file", "cafile", "verify", "ssl"],
        "min_length": 200,
    },
    {
        "id": "full_ssl_verify_required",
        "level": "full",
        "category": "ssl",
        "question": "Comment rendre la vérification client SSL obligatoire ?",
        "expected_keywords": ["verify", "required", "ssl", "client"],
        "min_length": 200,
    },
    {
        "id": "full_ssl_sni",
        "level": "full",
        "category": "ssl",
        "question": "Comment HAProxy gère-t-il SNI pour les certificats multiples ?",
        "expected_keywords": ["sni", "ssl", "certificate", "bind"],
        "min_length": 200,
    },
    {
        "id": "full_ssl_force_tlsv",
        "level": "full",
        "category": "ssl",
        "question": "Comment forcer une version TLS spécifique ?",
        "expected_keywords": ["force-tlsv", "tls", "version", "ssl"],
        "min_length": 200,
    },
    {
        "id": "full_ssl_default_bind",
        "level": "full",
        "category": "ssl",
        "question": "Comment configurer SSL par défaut pour tous les binds ?",
        "expected_keywords": ["default-bind", "ssl", "global"],
        "min_length": 200,
    },
    {
        "id": "full_ssl_backend_verify",
        "level": "full",
        "category": "ssl",
        "question": "Comment vérifier SSL côté backend dans HAProxy ?",
        "expected_keywords": ["verify", "ssl", "backend", "ca-file"],
        "min_length": 200,
    },
    
    # Timeout (5)
    {
        "id": "full_timeout_connect",
        "level": "full",
        "category": "timeout",
        "question": "Comment configurer le timeout connect ?",
        "expected_keywords": ["timeout", "connect", "connection"],
        "min_length": 150,
    },
    {
        "id": "full_timeout_client",
        "level": "full",
        "category": "timeout",
        "question": "Comment configurer le timeout client ?",
        "expected_keywords": ["timeout", "client", "client-fin"],
        "min_length": 150,
    },
    {
        "id": "full_timeout_server",
        "level": "full",
        "category": "timeout",
        "question": "Comment configurer le timeout server ?",
        "expected_keywords": ["timeout", "server", "server-fin"],
        "min_length": 150,
    },
    {
        "id": "full_timeout_queue",
        "level": "full",
        "category": "timeout",
        "question": "Comment configurer le timeout queue ?",
        "expected_keywords": ["timeout", "queue", "waiting"],
        "min_length": 150,
    },
    {
        "id": "full_timeout_tunnel",
        "level": "full",
        "category": "timeout",
        "question": "Comment configurer le timeout tunnel pour TCP ?",
        "expected_keywords": ["timeout", "tunnel", "tcp", "inactivity"],
        "min_length": 150,
    },
    
    # Logs/Stats (8)
    {
        "id": "full_log_stdout",
        "level": "full",
        "category": "logs",
        "question": "Comment envoyer les logs vers stdout dans HAProxy ?",
        "expected_keywords": ["log", "stdout", "fd@", "global"],
        "min_length": 200,
    },
    {
        "id": "full_log_format",
        "level": "full",
        "category": "logs",
        "question": "Comment configurer un format de log personnalisé ?",
        "expected_keywords": ["log-format", "log", "format", "custom"],
        "min_length": 200,
    },
    {
        "id": "full_stats_uri",
        "level": "full",
        "category": "stats",
        "question": "Comment configurer l'URI pour la page de stats ?",
        "expected_keywords": ["stats", "uri", "enable", "listen"],
        "min_length": 200,
    },
    {
        "id": "full_stats_auth",
        "level": "full",
        "category": "stats",
        "question": "Comment configurer l'authentification pour les stats ?",
        "expected_keywords": ["stats", "auth", "realm", "password"],
        "min_length": 200,
    },
    {
        "id": "full_stats_refresh",
        "level": "full",
        "category": "stats",
        "question": "Comment configurer le rafraîchissement automatique des stats ?",
        "expected_keywords": ["stats", "refresh", "interval", "auto"],
        "min_length": 200,
    },
    {
        "id": "full_stats_hide",
        "level": "full",
        "category": "stats",
        "question": "Comment masquer certains serveurs dans les stats ?",
        "expected_keywords": ["stats", "hide", "server", "disabled"],
        "min_length": 200,
    },
    {
        "id": "full_stats_socket",
        "level": "full",
        "category": "stats",
        "question": "Comment configurer le socket de statistiques HAProxy ?",
        "expected_keywords": ["stats", "socket", "unix", "chmod"],
        "min_length": 200,
    },
    {
        "id": "full_log_backend",
        "level": "full",
        "category": "logs",
        "question": "Comment configurer les logs spécifiques à un backend ?",
        "expected_keywords": ["log", "backend", "global", "disable"],
        "min_length": 200,
    },
    
    # TCP/General (8)
    {
        "id": "full_mode_tcp",
        "level": "full",
        "category": "tcp",
        "question": "Comment configurer HAProxy en mode TCP pur ?",
        "expected_keywords": ["mode", "tcp", "layer4"],
        "min_length": 200,
    },
    {
        "id": "full_mode_http",
        "level": "full",
        "category": "tcp",
        "question": "Comment configurer HAProxy en mode HTTP ?",
        "expected_keywords": ["mode", "http", "layer7"],
        "min_length": 200,
    },
    {
        "id": "full_listen_section",
        "level": "full",
        "category": "tcp",
        "question": "Comment utiliser une section listen au lieu de frontend/backend ?",
        "expected_keywords": ["listen", "frontend", "backend", "combine"],
        "min_length": 200,
    },
    {
        "id": "full_tcp_request",
        "level": "full",
        "category": "tcp",
        "question": "Comment utiliser tcp-request en mode TCP ?",
        "expected_keywords": ["tcp-request", "connection", "content"],
        "min_length": 200,
    },
    {
        "id": "full_tcp_response",
        "level": "full",
        "category": "tcp",
        "question": "Comment utiliser tcp-response en mode TCP ?",
        "expected_keywords": ["tcp-response", "connection", "content"],
        "min_length": 200,
    },
    {
        "id": "full_default_server",
        "level": "full",
        "category": "backend",
        "question": "Comment configurer un default-server pour tous les serveurs d'un backend ?",
        "expected_keywords": ["default-server", "backend", "server"],
        "min_length": 200,
    },
    {
        "id": "full_option_forwardfor",
        "level": "full",
        "category": "tcp",
        "question": "Comment ajouter l'header X-Forwarded-For ?",
        "expected_keywords": ["forwardfor", "X-Forwarded-For", "option"],
        "min_length": 200,
    },
    {
        "id": "full_option_httplog",
        "level": "full",
        "category": "logs",
        "question": "Comment activer le format de log HTTP ?",
        "expected_keywords": ["option", "httplog", "log", "format"],
        "min_length": 200,
    },
    
    # Advanced (12)
    {
        "id": "full_map_file",
        "level": "full",
        "category": "advanced",
        "question": "Comment utiliser un fichier map dans HAProxy ?",
        "expected_keywords": ["map", "file", "path", "acl"],
        "min_length": 200,
    },
    {
        "id": "full_map_str",
        "level": "full",
        "category": "advanced",
        "question": "Comment utiliser map avec une correspondance string ?",
        "expected_keywords": ["map", "str", "string", "exact"],
        "min_length": 200,
    },
    {
        "id": "full_map_beg",
        "level": "full",
        "category": "advanced",
        "question": "Comment utiliser map avec une correspondance par début ?",
        "expected_keywords": ["map", "beg", "begin", "prefix"],
        "min_length": 200,
    },
    {
        "id": "full_var_set",
        "level": "full",
        "category": "advanced",
        "question": "Comment définir une variable avec http-request set-var ?",
        "expected_keywords": ["set-var", "var", "http-request"],
        "min_length": 200,
    },
    {
        "id": "full_var_get",
        "level": "full",
        "category": "advanced",
        "question": "Comment récupérer une variable avec var() ?",
        "expected_keywords": ["var", "variable", "fetch"],
        "min_length": 200,
    },
    {
        "id": "full_var_scope",
        "level": "full",
        "category": "advanced",
        "question": "Comment utiliser les scopes de variables (txn, sess, req, res) ?",
        "expected_keywords": ["var", "txn", "sess", "scope"],
        "min_length": 200,
    },
    {
        "id": "full_converter_lower",
        "level": "full",
        "category": "advanced",
        "question": "Comment convertir une string en minuscules avec lower() ?",
        "expected_keywords": ["lower", "converter", "string"],
        "min_length": 150,
    },
    {
        "id": "full_converter_upper",
        "level": "full",
        "category": "advanced",
        "question": "Comment convertir une string en majuscules avec upper() ?",
        "expected_keywords": ["upper", "converter", "string"],
        "min_length": 150,
    },
    {
        "id": "full_converter_json",
        "level": "full",
        "category": "advanced",
        "question": "Comment extraire des données JSON avec json() ?",
        "expected_keywords": ["json", "converter", "extract", "path"],
        "min_length": 200,
    },
    {
        "id": "full_converter_url",
        "level": "full",
        "category": "advanced",
        "question": "Comment encoder une URL avec url() ?",
        "expected_keywords": ["url", "encode", "converter"],
        "min_length": 150,
    },
    {
        "id": "full_http_request_set_header",
        "level": "full",
        "category": "advanced",
        "question": "Comment ajouter un header HTTP avec http-request set-header ?",
        "expected_keywords": ["http-request", "set-header", "header", "add"],
        "min_length": 200,
    },
    {
        "id": "full_http_request_del_header",
        "level": "full",
        "category": "advanced",
        "question": "Comment supprimer un header HTTP avec http-request del-header ?",
        "expected_keywords": ["http-request", "del-header", "header", "remove"],
        "min_length": 200,
    },
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_questions_by_level(level: str = "quick") -> list[dict]:
    """
    Retourne les questions pour un niveau donné.
    
    Args:
        level: "quick" (7), "standard" (20), ou "full" (100)
    
    Returns:
        list de questions
    """
    if level == "quick":
        return [q for q in QUESTIONS if q["level"] == "quick"]
    elif level == "standard":
        return [q for q in QUESTIONS if q["level"] in ("quick", "standard")]
    elif level == "full":
        return QUESTIONS
    else:
        raise ValueError(f"Niveau inconnu: {level}. Utilisez 'quick', 'standard' ou 'full'.")


def get_questions_by_category(category: str = None) -> list[dict]:
    """
    Retourne les questions pour une catégorie donnée.
    
    Args:
        category: Catégorie (healthcheck, bind, acl, etc.) ou None pour tout
    
    Returns:
        list de questions
    """
    if category is None:
        return QUESTIONS
    return [q for q in QUESTIONS if q["category"] == category]


# ── Test ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Total questions: {len(QUESTIONS)}")
    print(f"Quick: {len(get_questions_by_level('quick'))}")
    print(f"Standard: {len(get_questions_by_level('standard'))}")
    print(f"Full: {len(get_questions_by_level('full'))}")
    
    print("\nCatégories:")
    categories = {}
    for q in QUESTIONS:
        cat = q["category"]
        categories[cat] = categories.get(cat, 0) + 1
    
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")
