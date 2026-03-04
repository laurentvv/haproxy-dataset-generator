#!/usr/bin/env python3
"""Module de validation syntaxique HAProxy.

Ce module fournit des outils pour valider et analyser les fichiers de
configuration HAProxy sans nécessiter l'installation de HAProxy lui-même.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar


class ErrorSeverity(Enum):
    """Sévérité des erreurs de validation."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ErrorType(Enum):
    """Type d'erreur de validation."""

    SYNTAX = "syntax"
    LOGIC = "logic"
    SECURITY = "security"
    REFERENCE = "reference"


@dataclass
class ValidationError:
    """Représente une erreur de validation HAProxy.

    Attributes:
        line: Numéro de ligne où l'erreur a été détectée
        column: Position du caractère où l'erreur a été détectée
        error_type: Type de l'erreur (syntaxe, logique, sécurité, référence)
        severity: Sévérité de l'erreur
        message: Message descriptif de l'erreur
        suggestion: Suggestion de correction (optionnel)
        context: Contexte de la ligne (optionnel)
    """

    line: int
    column: int
    error_type: ErrorType
    severity: ErrorSeverity
    message: str
    suggestion: str | None = None
    context: str = ""


@dataclass
class ValidationResult:
    """Résultat de la validation d'une configuration HAProxy.

    Attributes:
        is_valid: Indique si la configuration est valide (pas d'erreurs)
        errors: Liste des erreurs détectées
        warnings: Liste des avertissements détectés
        info: Liste d'informations détectées
    """

    is_valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    info: list[ValidationError] = field(default_factory=list)


class HAProxyValidator:
    """Validateur de configuration HAProxy.

    Ce validateur analyse les configurations HAProxy pour détecter :
    - Les erreurs syntaxiques (mot-clés mal orthographiés, ports invalides, etc.)
    - Les erreurs logiques (timeouts négatifs, backends non définis, etc.)
    - Les erreurs de sécurité (SSL sans vérification, stats sans auth, etc.)
    - Les erreurs de référence (backends manquants, ACL non définies, etc.)
    """

    # Grammaire HAProxy simplifiée
    HAProxyGrammar: ClassVar[dict[str, list[str]]] = {
        "global": [
            "chroot",
            "daemon",
            "log",
            "maxconn",
            "pidfile",
            "stats",
            "tune",
            "user",
            "group",
            "nbproc",
            "nbthread",
            "cpu-map",
            "setenv",
        ],
        "defaults": [
            "log",
            "maxconn",
            "mode",
            "option",
            "timeout",
            "retries",
            "balance",
            "default-server",
            "http-check",
        ],
        "frontend": [
            "bind",
            "mode",
            "default_backend",
            "option",
            "timeout",
            "acl",
            "use_backend",
            "http-request",
            "http-response",
            "capture",
            "stats",
        ],
        "backend": [
            "mode",
            "balance",
            "server",
            "option",
            "timeout",
            "acl",
            "cookie",
            "http-check",
            "default-server",
        ],
        "listen": [
            "bind",
            "mode",
            "balance",
            "server",
            "option",
            "timeout",
            "acl",
            "cookie",
            "stats",
        ],
        "userlist": ["user", "group"],
    }

    # Algorithmes de balance valides
    BALANCE_ALGORITHMS: ClassVar[set[str]] = {
        "roundrobin",
        "static-rr",
        "leastconn",
        "first",
        "source",
        "uri",
        "url_param",
        "hdr",
        "random",
        "rdp-cookie",
    }

    # Modes valides
    VALID_MODES: ClassVar[set[str]] = {"http", "tcp", "health"}

    # Types de timeout valides
    TIMEOUT_TYPES: ClassVar[set[str]] = {
        "connect",
        "client",
        "server",
        "http-keep-alive",
        "http-request",
        "queue",
        "tunnel",
        "check",
    }

    # Patterns regex pour la validation
    PATTERNS: ClassVar[dict[str, str]] = {
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

    # Patterns d'erreur
    ERROR_PATTERNS: ClassVar[dict[str, str]] = {
        "invalid_port": r":(\d{5,})\b",  # Port > 65535
        "negative_timeout": r"timeout\s+\S+\s+-\d+",
        "invalid_ip": r"\b(2[5-9][0-9]|3[0-9][0-9]|[4-9][0-9][0-9])\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
    }

    # Patterns de sécurité
    SECURITY_PATTERNS: ClassVar[dict[str, str]] = {
        "stats_no_auth": r"^\s*stats\s+(enable|uri)\b",
        "ssl_no_verify": r"^\s*(bind|server)\s+.*\bssl\b.*\bverify\s+none\b",
        "acl_allow_all": r"^\s*acl\s+\S+\s+src\s+0\.0\.0\.0/0\b",
    }

    def __init__(self, strict_mode: bool = False) -> None:
        """Initialise le validateur.

        Args:
            strict_mode: Si True, le validateur est plus strict dans les validations
        """
        self.strict_mode = strict_mode
        self.current_section: str | None = None
        self.section_name: str | None = None
        self.defined_backends: set[str] = set()
        self.defined_acls: set[str] = set()
        self.used_backends: set[str] = set()
        self.used_acls: set[str] = set()
        self.server_names: set[str] = set()

    def validate(self, config: str) -> ValidationResult:
        """Valide une configuration HAProxy complète.

        Args:
            config: Configuration HAProxy sous forme de chaîne de caractères

        Returns:
            ValidationResult contenant les erreurs, warnings et infos détectés
        """
        errors: list[ValidationError] = []
        warnings: list[ValidationError] = []
        info: list[ValidationError] = []

        # Réinitialiser l'état
        self._reset_state()

        # Analyser chaque ligne
        lines = config.split("\n")
        for line_num, line in enumerate(lines, start=1):
            # Ignorer les lignes vides et les commentaires
            if self._is_empty_or_comment(line):
                continue

            # Détecter les sections
            section_match = re.match(self.PATTERNS["section"], line)
            if section_match:
                self._handle_section(section_match, line_num, line, info)
                continue

            # Valider les directives selon la section
            self._validate_directives(line, line_num, errors, warnings, info)

        # Vérifier les références (backends et ACLs utilisés mais non définis)
        self._check_references(errors, warnings)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            info=info,
        )

    def get_syntax_compliance_score(self, config: str) -> float:
        """Calcule un score de conformité syntaxique (0.0 à 1.0).

        Args:
            config: Configuration HAProxy à analyser

        Returns:
            Score de conformité entre 0.0 et 1.0
        """
        result = self.validate(config)
        return get_syntax_compliance_score_from_result(result)

    def _reset_state(self) -> None:
        """Réinitialise l'état du validateur."""
        self.current_section = None
        self.section_name = None
        self.defined_backends.clear()
        self.defined_acls.clear()
        self.used_backends.clear()
        self.used_acls.clear()
        self.server_names.clear()

    def _is_empty_or_comment(self, line: str) -> bool:
        """Vérifie si une ligne est vide ou un commentaire."""
        return bool(re.match(r"^\s*(#|$)", line))

    def _handle_section(
        self,
        match: re.Match[str],
        line_num: int,
        line: str,
        info: list[ValidationError],
    ) -> None:
        """Gère la détection d'une section."""
        section_type = match.group(1)
        section_name = match.group(2)

        self.current_section = section_type
        self.section_name = section_name

        if section_type == "backend":
            self.defined_backends.add(section_name)

        info.append(
            ValidationError(
                line=line_num,
                column=0,
                error_type=ErrorType.SYNTAX,
                severity=ErrorSeverity.INFO,
                message=f"Section {section_type} '{section_name}'",
                context=line.strip(),
            )
        )

    def _validate_directives(
        self,
        line: str,
        line_num: int,
        errors: list[ValidationError],
        warnings: list[ValidationError],
        info: list[ValidationError],
    ) -> None:
        """Valide les directives d'une ligne."""
        # Validation des directives bind
        self._validate_bind(line, line_num, errors, warnings)

        # Validation des directives server
        self._validate_server(line, line_num, errors, warnings)

        # Validation des directives timeout
        self._validate_timeout(line, line_num, errors, warnings)

        # Validation des directives acl
        self._validate_acl(line, line_num, warnings)

        # Validation des directives use_backend
        self._validate_use_backend(line, line_num)

        # Validation des directives default_backend
        self._validate_default_backend(line, line_num)

        # Validation des directives balance
        self._validate_balance(line, line_num, errors)

        # Validation des directives mode
        self._validate_mode(line, line_num, errors)

        # Validation des directives stats
        self._validate_stats(line, line_num, warnings)

        # Validation des directives option (détection de typos)
        self._validate_option(line, line_num, errors)

        # Vérification des patterns d'erreur généraux
        self._check_error_patterns(line, line_num, errors)

        # Vérification des patterns de sécurité
        self._check_security_patterns(line, line_num, warnings)

    def _validate_bind(
        self,
        line: str,
        line_num: int,
        errors: list[ValidationError],
        warnings: list[ValidationError],
    ) -> None:
        """Valide les directives bind."""
        match = re.match(self.PATTERNS["bind"], line)
        if not match:
            return

        match.group(1)
        port = int(match.group(2))
        options = match.group(3) or ""

        # Vérifier le port
        if port < 1 or port > 65535:
            errors.append(
                ValidationError(
                    line=line_num,
                    column=line.find(str(port)),
                    error_type=ErrorType.SYNTAX,
                    severity=ErrorSeverity.ERROR,
                    message=f"Port invalide: {port} (doit être entre 1 et 65535)",
                    suggestion="Utilisez un port valide, par exemple :80 ou :443",
                    context=line.strip(),
                )
            )

        # Vérifier SSL sans vérification
        if "ssl" in options and "verify none" in options:
            warnings.append(
                ValidationError(
                    line=line_num,
                    column=line.find("ssl") if "ssl" in line else 0,
                    error_type=ErrorType.SECURITY,
                    severity=ErrorSeverity.WARNING,
                    message="SSL configuré sans vérification de certificat",
                    suggestion="Utilisez 'verify required ca-file /path/to/ca.pem'",
                    context=line.strip(),
                )
            )

    def _validate_server(
        self,
        line: str,
        line_num: int,
        errors: list[ValidationError],
        warnings: list[ValidationError],
    ) -> None:
        """Valide les directives server."""
        match = re.match(self.PATTERNS["server"], line)
        if not match:
            return

        server_name = match.group(1)
        match.group(2)
        port = int(match.group(3))
        options = match.group(4) or ""

        # Vérifier le port
        if port < 1 or port > 65535:
            errors.append(
                ValidationError(
                    line=line_num,
                    column=line.find(str(port)),
                    error_type=ErrorType.SYNTAX,
                    severity=ErrorSeverity.ERROR,
                    message=f"Port invalide: {port} (doit être entre 1 et 65535)",
                    suggestion="Utilisez un port valide, par exemple :80",
                    context=line.strip(),
                )
            )

        # Vérifier les noms de serveurs uniques
        if server_name in self.server_names:
            errors.append(
                ValidationError(
                    line=line_num,
                    column=line.find(server_name),
                    error_type=ErrorType.LOGIC,
                    severity=ErrorSeverity.ERROR,
                    message=f"Nom de serveur dupliqué: {server_name}",
                    suggestion="Utilisez un nom unique pour chaque serveur",
                    context=line.strip(),
                )
            )
        else:
            self.server_names.add(server_name)

        # Vérifier SSL sans vérification
        if "ssl" in options and "verify none" in options:
            warnings.append(
                ValidationError(
                    line=line_num,
                    column=line.find("ssl") if "ssl" in line else 0,
                    error_type=ErrorType.SECURITY,
                    severity=ErrorSeverity.WARNING,
                    message="SSL configuré sans vérification de certificat",
                    suggestion="Utilisez 'verify required ca-file /path/to/ca.pem'",
                    context=line.strip(),
                )
            )

    def _validate_timeout(
        self,
        line: str,
        line_num: int,
        errors: list[ValidationError],
        warnings: list[ValidationError],
    ) -> None:
        """Valide les directives timeout."""
        match = re.match(self.PATTERNS["timeout"], line)
        if not match:
            return

        timeout_type = match.group(1)
        value = int(match.group(2))
        unit = match.group(3) or "s"

        # Vérifier le type de timeout
        if timeout_type not in self.TIMEOUT_TYPES:
            errors.append(
                ValidationError(
                    line=line_num,
                    column=line.find(timeout_type),
                    error_type=ErrorType.SYNTAX,
                    severity=ErrorSeverity.ERROR,
                    message=f"Type de timeout invalide: {timeout_type}",
                    suggestion=f"Utilisez un type valide: {', '.join(sorted(self.TIMEOUT_TYPES))}",
                    context=line.strip(),
                )
            )

        # Vérifier les valeurs négatives
        if value < 0:
            errors.append(
                ValidationError(
                    line=line_num,
                    column=line.find(str(value)),
                    error_type=ErrorType.LOGIC,
                    severity=ErrorSeverity.ERROR,
                    message="La valeur de timeout ne peut pas être négative",
                    suggestion="Utilisez une valeur positive",
                    context=line.strip(),
                )
            )

        # Vérifier les valeurs excessives
        value_ms = self._convert_to_ms(value, unit)
        if value_ms > 3600000:  # Plus d'une heure
            warnings.append(
                ValidationError(
                    line=line_num,
                    column=line.find(str(value)),
                    error_type=ErrorType.LOGIC,
                    severity=ErrorSeverity.WARNING,
                    message=f"Valeur de timeout excessive: {value}{unit}",
                    suggestion="Utilisez une valeur plus réaliste (ex: 30s, 5m)",
                    context=line.strip(),
                )
            )

    def _convert_to_ms(self, value: int, unit: str) -> int:
        """Convertit une valeur de timeout en millisecondes."""
        multipliers = {"ms": 1, "s": 1000, "m": 60000, "h": 3600000, "d": 86400000}
        return value * multipliers.get(unit, 1000)

    def _validate_acl(
        self, line: str, line_num: int, warnings: list[ValidationError]
    ) -> None:
        """Valide les directives acl."""
        match = re.match(self.PATTERNS["acl"], line)
        if not match:
            return

        acl_name = match.group(1)
        criterion = match.group(2)
        value = match.group(3)

        self.defined_acls.add(acl_name)

        # Vérifier les ACL permissives
        if criterion == "src" and "0.0.0.0/0" in value:
            warnings.append(
                ValidationError(
                    line=line_num,
                    column=line.find(value),
                    error_type=ErrorType.SECURITY,
                    severity=ErrorSeverity.WARNING,
                    message="ACL permissive détectée: src 0.0.0.0/0",
                    suggestion="Restreignez la plage IP pour améliorer la sécurité",
                    context=line.strip(),
                )
            )

    def _validate_use_backend(self, line: str, line_num: int) -> None:
        """Valide les directives use_backend."""
        match = re.match(self.PATTERNS["use_backend"], line)
        if not match:
            return

        backend_name = match.group(1)
        self.used_backends.add(backend_name)

    def _validate_default_backend(self, line: str, line_num: int) -> None:
        """Valide les directives default_backend."""
        match = re.match(self.PATTERNS["default_backend"], line)
        if not match:
            return

        backend_name = match.group(1)
        self.used_backends.add(backend_name)

    def _validate_balance(
        self, line: str, line_num: int, errors: list[ValidationError]
    ) -> None:
        """Valide les directives balance."""
        match = re.match(self.PATTERNS["balance"], line)
        if not match:
            return

        algorithm = match.group(1)

        if algorithm not in self.BALANCE_ALGORITHMS:
            errors.append(
                ValidationError(
                    line=line_num,
                    column=line.find(algorithm),
                    error_type=ErrorType.SYNTAX,
                    severity=ErrorSeverity.ERROR,
                    message=f"Algorithme de balance invalide: {algorithm}",
                    suggestion=f"Utilisez un algorithme valide: {', '.join(sorted(self.BALANCE_ALGORITHMS))}",
                    context=line.strip(),
                )
            )

    def _validate_mode(
        self, line: str, line_num: int, errors: list[ValidationError]
    ) -> None:
        """Valide les directives mode."""
        match = re.match(self.PATTERNS["mode"], line)
        if not match:
            return

        mode = match.group(1)

        if mode not in self.VALID_MODES:
            errors.append(
                ValidationError(
                    line=line_num,
                    column=line.find(mode),
                    error_type=ErrorType.SYNTAX,
                    severity=ErrorSeverity.ERROR,
                    message=f"Mode invalide: {mode}",
                    suggestion=f"Utilisez un mode valide: {', '.join(sorted(self.VALID_MODES))}",
                    context=line.strip(),
                )
            )

    def _validate_stats(
        self, line: str, line_num: int, warnings: list[ValidationError]
    ) -> None:
        """Valide les directives stats."""
        match = re.match(self.PATTERNS["stats"], line)
        if not match:
            return

        action = match.group(1)

        # Vérifier stats sans authentification
        if action in ("enable", "uri"):
            warnings.append(
                ValidationError(
                    line=line_num,
                    column=line.find("stats"),
                    error_type=ErrorType.SECURITY,
                    severity=ErrorSeverity.WARNING,
                    message="Stats activées sans authentification",
                    suggestion="Ajoutez 'stats auth user:password' pour sécuriser les stats",
                    context=line.strip(),
                )
            )

    def _validate_option(
        self, line: str, line_num: int, errors: list[ValidationError]
    ) -> None:
        """Valide les directives option et détecte les typos."""
        match = re.match(self.PATTERNS["option"], line)
        if not match:
            return

        option_name = match.group(1)

        # Détecter des typos courantes
        common_typos = {
            "optoin": "option",
            "opton": "option",
            "httplog": "httplog",
            "tcplog": "tcplog",
            "forwardfor": "forwardfor",
        }

        for typo, correct in common_typos.items():
            if typo in option_name.lower():
                errors.append(
                    ValidationError(
                        line=line_num,
                        column=line.find(typo),
                        error_type=ErrorType.SYNTAX,
                        severity=ErrorSeverity.ERROR,
                        message=f"Erreur de syntaxe possible: '{typo}'",
                        suggestion=f"Voulez-vous dire '{correct}' ?",
                        context=line.strip(),
                    )
                )
                break

    def _check_error_patterns(
        self, line: str, line_num: int, errors: list[ValidationError]
    ) -> None:
        """Vérifie les patterns d'erreur généraux."""
        # Port invalide
        port_match = re.search(self.ERROR_PATTERNS["invalid_port"], line)
        if port_match:
            port = port_match.group(1)
            errors.append(
                ValidationError(
                    line=line_num,
                    column=line.find(port),
                    error_type=ErrorType.SYNTAX,
                    severity=ErrorSeverity.ERROR,
                    message=f"Port invalide: {port} (doit être entre 1 et 65535)",
                    suggestion="Utilisez un port valide",
                    context=line.strip(),
                )
            )

        # Timeout négatif
        timeout_match = re.search(self.ERROR_PATTERNS["negative_timeout"], line)
        if timeout_match:
            errors.append(
                ValidationError(
                    line=line_num,
                    column=0,
                    error_type=ErrorType.LOGIC,
                    severity=ErrorSeverity.ERROR,
                    message="La valeur de timeout ne peut pas être négative",
                    suggestion="Utilisez une valeur positive",
                    context=line.strip(),
                )
            )

        # IP invalide
        ip_match = re.search(self.ERROR_PATTERNS["invalid_ip"], line)
        if ip_match:
            ip = ip_match.group(1)
            errors.append(
                ValidationError(
                    line=line_num,
                    column=line.find(ip),
                    error_type=ErrorType.SYNTAX,
                    severity=ErrorSeverity.ERROR,
                    message=f"Adresse IP invalide: {ip}",
                    suggestion="Utilisez une adresse IP valide (ex: 192.168.1.1)",
                    context=line.strip(),
                )
            )

    def _check_security_patterns(
        self, line: str, line_num: int, warnings: list[ValidationError]
    ) -> None:
        """Vérifie les patterns de sécurité."""
        # Stats sans auth
        stats_match = re.match(self.SECURITY_PATTERNS["stats_no_auth"], line)
        if stats_match:
            # Déjà géré dans _validate_stats
            pass

        # SSL sans verify
        ssl_match = re.match(self.SECURITY_PATTERNS["ssl_no_verify"], line)
        if ssl_match:
            # Déjà géré dans _validate_bind et _validate_server
            pass

        # ACL permissive
        acl_match = re.match(self.SECURITY_PATTERNS["acl_allow_all"], line)
        if acl_match:
            # Déjà géré dans _validate_acl
            pass

    def _check_references(
        self,
        errors: list[ValidationError],
        warnings: list[ValidationError],
    ) -> None:
        """Vérifie les références (backends et ACLs utilisés mais non définis)."""
        # Vérifier les backends utilisés mais non définis
        for backend in self.used_backends:
            if backend not in self.defined_backends:
                errors.append(
                    ValidationError(
                        line=0,
                        column=0,
                        error_type=ErrorType.REFERENCE,
                        severity=ErrorSeverity.ERROR,
                        message=f"Backend utilisé mais non défini: {backend}",
                        suggestion=f"Définissez une section 'backend {backend}'",
                        context="",
                    )
                )

        # Vérifier les ACLs utilisés mais non définis
        for acl in self.used_acls:
            if acl not in self.defined_acls:
                warnings.append(
                    ValidationError(
                        line=0,
                        column=0,
                        error_type=ErrorType.REFERENCE,
                        severity=ErrorSeverity.WARNING,
                        message=f"ACL utilisée mais non définie: {acl}",
                        suggestion=f"Déclarez l'ACL avec 'acl {acl} ...'",
                        context="",
                    )
                )


def validate_haproxy_config(config: str, strict_mode: bool = False) -> ValidationResult:
    """Fonction utilitaire pour valider une configuration HAProxy.

    Args:
        config: Configuration HAProxy sous forme de chaîne de caractères
        strict_mode: Si True, le validateur est plus strict dans les validations

    Returns:
        ValidationResult contenant les erreurs, warnings et infos détectés
    """
    validator = HAProxyValidator(strict_mode=strict_mode)
    return validator.validate(config)


def get_syntax_score(config: str) -> float:
    """Fonction utilitaire pour obtenir le score de conformité syntaxique.

    Args:
        config: Configuration HAProxy à analyser

    Returns:
        Score de conformité entre 0.0 et 1.0
    """
    validator = HAProxyValidator()
    return validator.get_syntax_compliance_score(config)


def get_syntax_compliance_score_from_result(result: ValidationResult) -> float:
    """Calcule un score de conformité syntaxique à partir d'un ValidationResult.

    Formule :
    score = max(0.0, 1.0 - (errors * 0.1) - (warnings * 0.02))

    Où :
    - Chaque erreur pénalise de 0.1
    - Chaque warning pénalise de 0.02
    - Le score est borné entre 0.0 et 1.0

    Args:
        result: Résultat de validation

    Returns:
        Score de conformité entre 0.0 et 1.0
    """
    error_count = len(result.errors)
    warning_count = len(result.warnings)
    score = 1.0 - (error_count * 0.1) - (warning_count * 0.02)
    return max(0.0, min(1.0, score))


if __name__ == "__main__":
    # Test de validation avec une configuration de test
    test_config = """
    global
        daemon
        maxconn 256
        user haproxy
        group haproxy

    defaults
        log global
        mode http
        timeout connect 5000ms
        timeout client 50000ms
        timeout server 50000ms
        option httplog

    frontend http_in
        bind *:80
        optoin httplog
        default_backend web_servers

    backend web_servers
        balance roundrobin
        server web1 192.168.1.1:80 check
        server web1 192.168.1.2:80 check

    frontend https_in
        bind *:443 ssl verify none
        default_backend web_servers

    backend api_servers
        balance unknown
        server api1 10.0.0.1:8080 check
        server api2 10.0.0.2:8080 check
    """

    print("=" * 60)
    print("Test de validation HAProxy")
    print("=" * 60)

    # Valider la configuration
    result = validate_haproxy_config(test_config)

    print(f"\nConfiguration valide: {result.is_valid}")
    print(f"Erreurs: {len(result.errors)}")
    print(f"Warnings: {len(result.warnings)}")
    print(f"Infos: {len(result.info)}")

    # Afficher les erreurs
    if result.errors:
        print("\n--- Erreurs ---")
        for error in result.errors:
            print(f"Ligne {error.line}: {error.message}")
            if error.suggestion:
                print(f"  -> {error.suggestion}")

    # Afficher les warnings
    if result.warnings:
        print("\n--- Warnings ---")
        for warning in result.warnings:
            print(f"Ligne {warning.line}: {warning.message}")
            if warning.suggestion:
                print(f"  -> {warning.suggestion}")

    # Calculer et afficher le score
    score = get_syntax_score(test_config)
    print(f"\nScore de conformité: {score:.3f}")

    # Interprétation du score
    if score >= 0.9:
        quality = "Excellent"
    elif score >= 0.7:
        quality = "Bon"
    elif score >= 0.5:
        quality = "Moyen"
    else:
        quality = "Mauvais"

    print(f"Qualité: {quality}")
