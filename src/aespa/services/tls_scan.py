"""sslscan-like TLS/SSL posture probe — pure stdlib + ``cryptography`` (already a dep).

Given a ``host:port``, this connects and reports what an operator would want from
``sslscan``/``testssl.sh``:

- which TLS protocol versions the server accepts (TLS 1.0 → 1.3),
- whether legacy/weak or non-forward-secret cipher suites are accepted,
- the negotiated protocol + cipher, and
- the leaf certificate (validity, key size, signature algorithm, SANs, self-signed,
  hostname match).

It also derives an ``issues`` list (deprecated protocol enabled, weak cipher, expired /
expiring cert, small key, SHA-1 signature, hostname mismatch) so the calling agent can
turn confirmed weaknesses straight into an OWASP **A02 Cryptographic Failures** finding.

**Deliberate limitation:** SSLv2/SSLv3 are compiled out of the OpenSSL that Python's
``ssl`` links against, so they cannot be handshake-tested here — they are reported as
``"not-testable"`` rather than falsely "not supported". Testing them would require a
bundled OpenSSL (``nassl``/``sslyze``), which is AGPL and intentionally not a dep.

All socket work is blocking; the public entry point ``scan_tls`` runs it in a thread.
"""

from __future__ import annotations

import asyncio
import logging
import socket
import ssl
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import dsa, rsa

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT_S = 10.0

# OpenSSL cipher strings for the targeted "does the server accept weak suites?" checks.
# @SECLEVEL=0 re-enables suites modern OpenSSL disables by default so we can actually
# test whether the *server* still offers them.
_WEAK_CIPHERS = "RC4:3DES:DES:IDEA:EXPORT:LOW:aNULL:eNULL:NULL:MD5:@SECLEVEL=0"
# Static-RSA key exchange = no forward secrecy.
_NO_PFS_CIPHERS = "kRSA:@SECLEVEL=0"
# Permissive suite used for protocol-version enumeration.
_ALL_CIPHERS = "ALL:COMPLEMENTOFALL:@SECLEVEL=0"

# (label, ssl.TLSVersion, name reported by SSLSocket.version()). Oldest → newest.
# Note the reported name for TLS 1.0 is "TLSv1", not "TLSv1.0".
_PROTOCOLS: list[tuple[str, ssl.TLSVersion, str]] = [
    ("TLSv1.0", ssl.TLSVersion.TLSv1, "TLSv1"),
    ("TLSv1.1", ssl.TLSVersion.TLSv1_1, "TLSv1.1"),
    ("TLSv1.2", ssl.TLSVersion.TLSv1_2, "TLSv1.2"),
    ("TLSv1.3", ssl.TLSVersion.TLSv1_3, "TLSv1.3"),
]
# Deprecated protocol versions that should raise a finding when accepted.
_DEPRECATED_PROTOCOLS = {"TLSv1.0", "TLSv1.1", "SSLv3", "SSLv2"}


def _permissive_context() -> ssl.SSLContext:
    """A client context that trusts anything — we inspect the cert ourselves."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _parse_target(host: str, port: int | None) -> tuple[str, int]:
    """Accept a bare host, ``host:port``, or a full URL and return ``(host, port)``."""
    raw = (host or "").strip()
    if "://" in raw:
        parts = urlsplit(raw)
        return parts.hostname or raw, port or parts.port or 443
    if raw.count(":") == 1 and not raw.replace(":", "").isalpha():
        # host:port form (skip bare IPv6 without brackets — rare for this tool)
        h, _, p = raw.partition(":")
        try:
            return h, port or int(p)
        except ValueError:
            pass
    return raw, port or 443


def _hostname_matches(host: str, names: list[str]) -> bool:
    """RFC 6125-ish match: exact or single left-most wildcard label.

    ``ssl.match_hostname`` was removed in Python 3.12, so match here.
    """
    host = host.lower().rstrip(".")
    for name in names:
        name = name.lower().rstrip(".")
        if name == host:
            return True
        if name.startswith("*."):
            suffix = name[1:]  # ".example.com"
            head, _, tail = host.partition(".")
            if head and ("." + tail) == suffix:
                return True
    return False


def _describe_cert(der: bytes, host: str) -> dict[str, Any]:
    """Parse the leaf certificate and flag common weaknesses."""
    cert = x509.load_der_x509_certificate(der)
    now = datetime.now(timezone.utc)

    # cryptography ≥42 exposes tz-aware *_utc accessors; fall back for older builds.
    not_before = getattr(cert, "not_valid_before_utc", None) or (
        cert.not_valid_before.replace(tzinfo=timezone.utc)
    )
    not_after = getattr(cert, "not_valid_after_utc", None) or (
        cert.not_valid_after.replace(tzinfo=timezone.utc)
    )
    days_left = int((not_after - now).total_seconds() // 86400)

    try:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        dns_names = san.get_values_for_type(x509.DNSName)
    except x509.ExtensionNotFound:
        dns_names = []

    key = cert.public_key()
    key_size = getattr(key, "key_size", None)
    if isinstance(key, rsa.RSAPublicKey):
        key_type = "RSA"
    elif isinstance(key, dsa.DSAPublicKey):
        key_type = "DSA"
    else:
        key_type = type(key).__name__.replace("PublicKey", "")

    try:
        _sig = cert.signature_hash_algorithm
        sig_algo = _sig.name if _sig else None
    except Exception:
        sig_algo = None

    self_signed = cert.subject == cert.issuer
    hostname_ok = _hostname_matches(host, dns_names) if dns_names else None

    issues: list[str] = []
    if days_left < 0:
        issues.append(f"Certificate expired {abs(days_left)} day(s) ago.")
    elif days_left < 30:
        issues.append(f"Certificate expires in {days_left} day(s).")
    if key_type in ("RSA", "DSA") and key_size is not None and key_size < 2048:
        issues.append(f"Weak {key_type} public key: {key_size} bits (< 2048).")
    if sig_algo in ("md5", "sha1"):
        issues.append(f"Weak certificate signature algorithm: {sig_algo.upper()}.")
    if self_signed:
        issues.append("Certificate is self-signed (not issued by a trusted CA).")
    if hostname_ok is False:
        issues.append(f"Certificate is not valid for hostname '{host}' (SAN mismatch).")

    return {
        "subject": cert.subject.rfc4514_string(),
        "issuer": cert.issuer.rfc4514_string(),
        "not_before": not_before.isoformat(),
        "not_after": not_after.isoformat(),
        "days_until_expiry": days_left,
        "expired": days_left < 0,
        "self_signed": self_signed,
        "key_type": key_type,
        "key_bits": key_size,
        "signature_algorithm": sig_algo,
        "subject_alt_names": dns_names[:50],
        "hostname_match": hostname_ok,
        "issues": issues,
    }


def _probe_protocol(
    host: str,
    port: int,
    label: str,
    version: ssl.TLSVersion,
    reported_name: str,
    timeout: float,
):
    """Attempt a handshake pinned to one protocol version.

    Returns ``(accepted: bool | None, cipher_name: str | None)``. ``accepted`` is
    ``None`` when the local OpenSSL cannot offer the version at all (not testable).
    Only counts as accepted when the *negotiated* version actually matches, so a
    server that silently upgrades cannot produce a false positive.
    """
    ctx = _permissive_context()
    try:
        ctx.minimum_version = version
        ctx.maximum_version = version
    except (ValueError, OSError):
        return None, None
    try:
        ctx.set_ciphers(_ALL_CIPHERS)
    except ssl.SSLError:
        pass
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ss:
                if ss.version() != reported_name:
                    return False, None
                cipher = ss.cipher()
                return True, (cipher[0] if cipher else None)
    except (ssl.SSLError, socket.timeout, TimeoutError):
        return False, None
    except OSError as exc:
        log.debug("TLS probe %s %s:%s protocol error: %s", label, host, port, exc)
        return False, None


def _probe_cipher_set(host: str, port: int, ciphers: str, timeout: float) -> str | None:
    """Return the negotiated cipher name if the server accepts any suite in the set.

    Capped at TLS 1.2 on purpose: ``set_ciphers`` does not govern TLS 1.3 suites, so
    without this cap a 1.3-only server would negotiate a strong 1.3 suite and falsely
    look like it accepted a weak/non-PFS one.
    """
    ctx = _permissive_context()
    try:
        ctx.minimum_version = ssl.TLSVersion.TLSv1
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2
    except (ValueError, OSError):
        pass
    try:
        ctx.set_ciphers(ciphers)
    except ssl.SSLError:
        return None
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ss:
                cipher = ss.cipher()
                return cipher[0] if cipher else None
    except (ssl.SSLError, socket.timeout, TimeoutError, OSError):
        return None


def _probe(host: str, port: int, timeout: float) -> dict[str, Any]:
    """Blocking end-to-end TLS probe. Runs several short handshakes."""
    # 1. Baseline connect: negotiated protocol/cipher + leaf certificate.
    ctx = _permissive_context()
    try:
        der: bytes | None = None
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ss:
                negotiated_version = ss.version()
                negotiated_cipher = ss.cipher()
                der = ss.getpeercert(binary_form=True)
    except (OSError, ssl.SSLError) as exc:
        return {
            "ok": False,
            "host": host,
            "port": port,
            "error": f"{type(exc).__name__}: {exc}",
        }

    result: dict[str, Any] = {
        "ok": True,
        "host": host,
        "port": port,
        "negotiated_protocol": negotiated_version,
        "negotiated_cipher": negotiated_cipher[0] if negotiated_cipher else None,
        "negotiated_cipher_bits": negotiated_cipher[2] if negotiated_cipher else None,
    }

    # 2. Certificate details.
    if der:
        try:
            result["certificate"] = _describe_cert(der, host)
        except Exception as exc:  # never let a parse quirk abort the whole probe
            log.warning("TLS cert parse failed for %s:%s: %s", host, port, exc)
            result["certificate"] = {"error": str(exc), "issues": []}
    else:
        result["certificate"] = {"error": "no certificate presented", "issues": []}

    # 3. Protocol version enumeration.
    protocols: dict[str, str] = {}
    for label, version, reported_name in _PROTOCOLS:
        accepted, _cipher = _probe_protocol(
            host, port, label, version, reported_name, timeout
        )
        if accepted is None:
            protocols[label] = "not-testable"
        else:
            protocols[label] = "accepted" if accepted else "rejected"
    # SSLv2/SSLv3 cannot be tested by the linked OpenSSL — be honest about it.
    protocols["SSLv3"] = "not-testable"
    protocols["SSLv2"] = "not-testable"
    result["protocols"] = protocols

    # 4. Weak / non-PFS cipher acceptance.
    weak_cipher = _probe_cipher_set(host, port, _WEAK_CIPHERS, timeout)
    no_pfs_cipher = _probe_cipher_set(host, port, _NO_PFS_CIPHERS, timeout)
    result["weak_cipher_accepted"] = weak_cipher
    result["non_pfs_cipher_accepted"] = no_pfs_cipher

    # 5. Aggregate issues for the agent.
    issues: list[str] = list(result["certificate"].get("issues", []))
    for label in _DEPRECATED_PROTOCOLS:
        if protocols.get(label) == "accepted":
            issues.append(f"Deprecated protocol {label} is enabled.")
    if weak_cipher:
        issues.append(f"Server accepts a weak cipher suite: {weak_cipher}.")
    if no_pfs_cipher:
        issues.append(f"Server accepts a non-forward-secret cipher: {no_pfs_cipher}")
    result["issues"] = issues

    return result


async def scan_tls(
    host: str,
    port: int | None = None,
    *,
    timeout: float = DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Run an sslscan-like TLS/SSL probe against ``host[:port]`` (default 443).

    ``host`` may be a bare hostname, ``host:port``, or a full URL. Returns a JSON-
    serialisable dict; on connect failure returns ``{"ok": False, "error": ...}``.
    """
    resolved_host, resolved_port = _parse_target(host, port)
    if not resolved_host:
        return {"ok": False, "error": "no host provided"}
    return await asyncio.to_thread(_probe, resolved_host, resolved_port, timeout)
