# Spécification du Module de Validation HAProxy

## Fichier : `haproxy_validator.py`

Ce module fournit des outils pour valider et analyser les fichiers de configuration HAProxy sans nécessiter l'installation de HAProxy lui-même.

## Architecture du Module

### Classes Principales

```python
# Énumérations
class ErrorSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class ErrorType(Enum):
    SYNTAX = "syntax"
    LOGIC = "logic"
    SECURITY = "security"
    REFERENCE = "reference"

# Classes de données
@dataclass
class ValidationError:
    line: int
    column: int
    error_type: ErrorType
    severity: ErrorSeverity
    message: str
    suggestion: str | None = None
    context: str = ""

@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[ValidationError]
    warnings: list[ValidationError]
    info: list[ValidationError]
```

### Classe Principale : HAProxyValidator

```python
class HAProxyValidator:
    """Validateur de configuration HAProxy."""
    
    def __init__(self, strict_mode: bool = False):
        """Initialise le validateur."""
        
    def validate(self, config: str) -> ValidationResult:
        """Valide une configuration HAProxy complète."""
        
    def get_syntax_compliance_score(self, config: str) -> float:
        """Calcule un score de conformité syntaxique (0.0 à 1.0)."""
```

## Grammaire HAProxy Simplifiée

### Sections Supportées

| Section | Directives Validées |
|---------|-------------------|
| `global` | chroot, daemon, log, maxconn, pidfile, stats, tune, user, etc. |
| `defaults` | log, maxconn, mode, option, timeout, retries, balance, etc. |
| `frontend` | bind, mode, default_backend, option, timeout, acl, etc. |
| `backend` | mode, balance, server, option, timeout, acl, cookie, etc. |
| `listen` | bind, mode, balance, server, option, timeout, acl, etc. |
| `userlist` | user, group |

### Directives Validées

#### `bind`
```haproxy
bind [address]:port [ssl crt /path/to/cert.pem] [verify required]
```
- Validation des ports (1-65535)
- Détection SSL sans vérification

#### `server`
```haproxy
server <name> <address>:port [check] [inter <time>] [fall <count>]
```
- Validation des ports
- Détection SSL sans vérification

#### `timeout`
```haproxy
timeout <type> <value> [unit]
```
- Types : connect, client, server, http-keep-alive, http-request, queue, tunnel, check
- Détection des valeurs négatives
- Avertissement pour les valeurs excessives

#### `acl`
```haproxy
acl <name> <criterion> <value>
```
- Détection des ACL permissives (src 0.0.0.0/0)
- Critères supportés : hdr, path, url, method, src, dst, etc.

#### `balance`
```haproxy
balance <algorithm>
```
- Algorithmes valides : roundrobin, static-rr, leastconn, first, source, uri, url_param, hdr, random, rdp-cookie

#### `mode`
```haproxy
mode <http|tcp|health>
```

#### `stats`
```haproxy
stats enable|uri|auth|refresh|hide|show|scope|admin
```
- Détection de stats sans authentification

## Types d'Erreurs Détectées

### 1. Erreurs Syntaxiques

| Erreur | Exemple | Correction |
|--------|---------|------------|
| Mot-clé mal orthographié | `optoin httplog` | `option httplog` |
| Port invalide | `bind *:70000` | `bind *:80` |
| Algorithme invalide | `balance unknown` | `balance roundrobin` |
| Mode invalide | `mode ftp` | `mode http` |

### 2. Erreurs Logiques

| Erreur | Exemple | Correction |
|--------|---------|------------|
| Timeout négatif | `timeout connect -5s` | `timeout connect 5s` |
| Backend non défini | `use_backend missing` | Définir `backend missing` |
| Serveur dupliqué | Deux serveurs avec même nom | Noms uniques |
| Timeout excessif | `timeout server 1000000s` | Valeur réaliste |

### 3. Erreurs de Sécurité

| Erreur | Exemple | Correction |
|--------|---------|------------|
| SSL sans vérification | `bind *:443 ssl verify none` | `bind *:443 ssl verify required ca-file /path/to/ca.pem` |
| Stats sans auth | `stats enable` | `stats auth user:password` |
| ACL permissive | `acl all src 0.0.0.0/0` | Restreindre la plage IP |
| Forwardfor manquant | Absence dans frontend HTTP | Ajouter `option forwardfor` |

### 4. Erreurs de Référence

| Erreur | Exemple | Correction |
|--------|---------|------------|
| Backend manquant | `use_backend web_servers` sans définition | Définir `backend web_servers` |
| ACL non définie | Utilisation d'une ACL non déclarée | Déclarer l'ACL |

## Patterns de Validation

### Patterns Regex

```python
PATTERNS = {
    "comment": r"^\s*#.*$",
    "section": r"^\s*(global|defaults|frontend|backend|listen|userlist)\s+(\S+)",
    "bind": r"^\s*bind\s+([^\s:]+):(\d+)(?:\s+(.*))?$",
    "server": r"^\s*server\s+(\S+)\s+([^\s:]+):(\d+)(?:\s+(.*))?$",
    "option": r"^\s*option\s+(\S+)(?:\s+(.*))?$",
    "timeout": r"^\s*timeout\s+(\S+)\s+(\d+)(?:\s*(ms|s|m|h|d))?$",
    "acl": r"^\s*acl\s+(\S+)\s+(\S+)\s+(.+)$",
    "use_backend": r"^\s*use_backend\s+(\S+)(?:\s+(.*))?$",
    "default_backend": r"^\s*default_backend\s+(\S+)$",
    "balance": r"^\s*balance\s+(\S+)(?:\s+(.*))?$",
    "mode": r"^\s*mode\s+(http|tcp|health)$",
    "stats": r"^\s*stats\s+(enable|uri|auth|refresh|hide|show|scope|admin)(?:\s+(.*))?$",
}
```

### Patterns d'Erreur

```python
ERROR_PATTERNS = {
    "invalid_port": r":(\d{5,})\b",  # Port > 65535
    "negative_timeout": r"timeout\s+\S+\s+-\d+",
    "invalid_ip": r"\b(\d{3,}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b",
}

SECURITY_PATTERNS = {
    "stats_no_auth": r"^\s*stats\s+(enable|uri)\b",
    "ssl_no_verify": r"^\s*(bind|server)\s+.*\bssl\b.*\bverify\s+none\b",
    "acl_allow_all": r"^\s*acl\s+\S+\s+src\s+0\.0\.0\.0/0\b",
}
```

## Calcul du Score de Conformité

```python
def get_syntax_compliance_score(config: str) -> float:
    """
    Calcule un score de conformité syntaxique (0.0 à 1.0).
    
    Formule :
    score = max(0.0, 1.0 - (errors * 0.1) - (warnings * 0.02))
    
    Où :
    - Chaque erreur pénalise de 0.1
    - Chaque warning pénalise de 0.02
    - Le score est borné entre 0.0 et 1.0
    """
```

### Interprétation des Scores

| Score | Qualité |
|-------|---------|
| 1.0 | Parfait (pas d'erreurs ni warnings) |
| 0.9 - 0.99 | Excellent (quelques warnings mineurs) |
| 0.7 - 0.89 | Bon (erreurs mineures ou warnings modérés) |
| 0.5 - 0.69 | Moyen (erreurs modérées) |
| 0.0 - 0.49 | Mauvais (erreurs multiples) |

## Fonctions Utilitaires

```python
def validate_haproxy_config(config: str, strict_mode: bool = False) -> ValidationResult:
    """Fonction utilitaire pour valider une configuration HAProxy."""

def get_syntax_score(config: str) -> float:
    """Fonction utilitaire pour obtenir le score de conformité syntaxique."""
```

## Exemple d'Utilisation

```python
from haproxy_validator import validate_haproxy_config, get_syntax_score

config = """
frontend http_in
    bind *:80
    optoin httplog
    default_backend web_servers

backend web_servers
    balance roundrobin
    server web1 192.168.1.1:80 check
"""

# Validation
result = validate_haproxy_config(config)
print(f"Valide: {result.is_valid}")
print(f"Erreurs: {len(result.errors)}")
print(f"Warnings: {len(result.warnings)}")

# Affichage des erreurs
for error in result.errors:
    print(f"Ligne {error.line}: {error.message}")
    if error.suggestion:
        print(f"  → {error.suggestion}")

# Score de conformité
score = get_syntax_score(config)
print(f"Score: {score:.3f}")
```

## Limitations

Ce validateur est une implémentation simplifiée et ne couvre pas :

1. **Toutes les directives HAProxy** : Seules les directives les plus courantes sont validées
2. **La validation sémantique complète** : Certaines erreurs logiques complexes ne sont pas détectées
3. **Les dépendances entre options** : Les interactions complexes entre options ne sont pas analysées
4. **La validation des expressions ACL** : Seule la syntaxe de base est vérifiée

Pour une validation complète, utilisez l'outil officiel `haproxy -c`.

## Intégration avec le Benchmark

Le validateur sera utilisé dans le benchmark pour :

1. **Évaluer la conformité syntaxique** des configurations corrigées par les LLM
2. **Détecter les erreurs** dans les configurations d'origine
3. **Calculer les métriques de performance** :
   - Taux de détection d'erreurs
   - Conformité syntaxique
   - Réduction des hallucinations
