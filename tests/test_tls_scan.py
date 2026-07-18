"""Tests for the sslscan-like TLS probe service (no network — cert crafted locally)."""

import asyncio
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from aespa.services import tls_scan

# ── _parse_target ─────────────────────────────────────────────────────────────


def test_parse_target_bare_host_defaults_443():
    assert tls_scan._parse_target("example.com", None) == ("example.com", 443)


def test_parse_target_host_port():
    assert tls_scan._parse_target("example.com:8443", None) == ("example.com", 8443)


def test_parse_target_full_url():
    assert tls_scan._parse_target("https://example.com:9443/path", None) == (
        "example.com",
        9443,
    )


def test_parse_target_explicit_port_wins_over_default():
    assert tls_scan._parse_target("example.com", 1234) == ("example.com", 1234)


# ── _hostname_matches ─────────────────────────────────────────────────────────


def test_hostname_exact_match():
    assert tls_scan._hostname_matches("api.example.com", ["api.example.com"]) is True


def test_hostname_wildcard_match():
    assert tls_scan._hostname_matches("api.example.com", ["*.example.com"]) is True


def test_hostname_wildcard_does_not_span_labels():
    assert tls_scan._hostname_matches("a.b.example.com", ["*.example.com"]) is False


def test_hostname_mismatch():
    assert tls_scan._hostname_matches("evil.com", ["example.com"]) is False


# ── _describe_cert ────────────────────────────────────────────────────────────


def _make_cert(*, host, key_bits=2048, hash_algo=None, days_valid=365, san=None):
    hash_algo = hash_algo or hashes.SHA256()
    key = rsa.generate_private_key(public_exponent=65537, key_size=key_bits)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, host)])
    now = datetime.now(timezone.utc)
    not_after = now + timedelta(days=days_valid)
    not_before = min(now - timedelta(days=1), not_after - timedelta(days=1))
    builder = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)  # self-signed
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_after)
    )
    san_names = san if san is not None else [host]
    builder = builder.add_extension(
        x509.SubjectAlternativeName([x509.DNSName(n) for n in san_names]),
        critical=False,
    )
    cert = builder.sign(key, hash_algo)
    return cert.public_bytes(serialization.Encoding.DER)


def test_describe_cert_healthy_has_no_issues():
    der = _make_cert(host="good.example.com")
    info = tls_scan._describe_cert(der, "good.example.com")
    assert info["self_signed"] is True  # our test CA is self-signed
    assert info["key_bits"] == 2048
    assert info["hostname_match"] is True
    # self-signed is the only expected issue here
    assert any("self-signed" in i for i in info["issues"])


def test_describe_cert_flags_weak_key():
    der = _make_cert(host="weak.example.com", key_bits=1024)
    info = tls_scan._describe_cert(der, "weak.example.com")
    assert info["key_bits"] == 1024
    assert any("1024 bits" in i for i in info["issues"])


def test_describe_cert_flags_expired():
    der = _make_cert(host="old.example.com", days_valid=-5)
    info = tls_scan._describe_cert(der, "old.example.com")
    assert info["expired"] is True
    assert any("expired" in i.lower() for i in info["issues"])


def test_describe_cert_flags_hostname_mismatch():
    der = _make_cert(host="real.example.com", san=["real.example.com"])
    info = tls_scan._describe_cert(der, "attacker.example.com")
    assert info["hostname_match"] is False
    assert any("not valid for hostname" in i for i in info["issues"])


# ── scan_tls (probe mocked) ───────────────────────────────────────────────────


def test_scan_tls_runs_probe_with_resolved_target(monkeypatch):
    captured = {}

    def _fake_probe(host, port, timeout):
        captured["host"] = host
        captured["port"] = port
        return {"ok": True, "host": host, "port": port, "issues": []}

    monkeypatch.setattr(tls_scan, "_probe", _fake_probe)
    result = asyncio.run(tls_scan.scan_tls("https://svc.example.com:8443/x"))
    assert captured == {"host": "svc.example.com", "port": 8443}
    assert result["ok"] is True


def test_scan_tls_rejects_empty_host():
    result = asyncio.run(tls_scan.scan_tls(""))
    assert result["ok"] is False


# ── deterministic posture finding (scanner._tls_posture_finding) ──────────────

from aespa.services import scanner  # noqa: E402


def _result(*, issues, certificate=None, protocols=None, **extra):
    return {
        "ok": True,
        "host": "h.example.com",
        "port": 443,
        "issues": issues,
        "certificate": certificate or {},
        "protocols": protocols or {},
        "negotiated_protocol": "TLSv1.2",
        "negotiated_cipher": "ECDHE-RSA-AES128-GCM-SHA256",
        **extra,
    }


def test_posture_finding_none_when_clean():
    r = _result(issues=[], protocols={"TLSv1.2": "accepted", "TLSv1.3": "accepted"})
    assert scanner._tls_posture_finding(1, "https://h.example.com/", r) is None


def test_posture_finding_is_single_a02_finding():
    r = _result(
        issues=[
            "Certificate expired 5 day(s) ago.",
            "Deprecated protocol TLSv1.0 is enabled.",
        ],
        certificate={"expired": True, "key_bits": 2048},
        protocols={"TLSv1.0": "accepted", "TLSv1.2": "accepted"},
    )
    f = scanner._tls_posture_finding(1, "https://h.example.com/", r)
    assert f is not None
    assert f.owasp_category == "A02"
    assert f.title == "TLS/SSL configuration weaknesses"
    assert f.affected_url == "https://h.example.com/"
    # both issues summarised in the one finding
    assert "expired" in f.description.lower()
    assert "TLSv1.0" in f.description


def test_posture_severity_high_for_expired_cert():
    r = _result(issues=["Certificate expired."], certificate={"expired": True})
    f = scanner._tls_posture_finding(1, "https://h.example.com/", r)
    assert f.severity == "high"


def test_posture_severity_medium_for_deprecated_protocol_only():
    r = _result(
        issues=["Deprecated protocol TLSv1.1 is enabled."],
        protocols={"TLSv1.1": "accepted", "TLSv1.2": "accepted"},
    )
    f = scanner._tls_posture_finding(1, "https://h.example.com/", r)
    assert f.severity == "medium"


def test_posture_severity_high_beats_medium():
    r = _result(
        issues=["Server accepts a weak cipher suite: RC4.", "Self-signed cert."],
        certificate={"self_signed": True},
        weak_cipher_accepted="RC4-SHA",
    )
    assert scanner._tls_worst_cvss(r) == scanner._TLS_HIGH_CVSS


def test_run_module_skips_non_https():
    findings = asyncio.run(
        scanner._run_tls_posture_module(run_id=1, base_url="http://h.example.com/")
    )
    assert findings == []


def test_posture_finding_api_mode_keys_api_column():
    r = _result(issues=["Certificate expired."], certificate={"expired": True})
    f = scanner._tls_posture_finding(7, "https://h.example.com/", r, is_api_run=True)
    assert f.api_test_run_id == 7
    assert f.test_run_id is None


def test_run_module_api_mode_builds_single_api_finding(monkeypatch):
    def _fake_probe(host, port, timeout):
        return {
            "ok": True,
            "host": host,
            "port": port,
            "issues": ["Certificate expired.", "TLSv1.0 enabled."],
            "certificate": {"expired": True},
            "protocols": {"TLSv1.0": "accepted"},
            "negotiated_protocol": "TLSv1.2",
            "negotiated_cipher": "X",
        }

    monkeypatch.setattr(tls_scan, "_probe", _fake_probe)
    findings = asyncio.run(
        scanner._run_tls_posture_module(
            run_id=7, base_url="https://api.example.com/", is_api_run=True
        )
    )
    assert len(findings) == 1
    assert findings[0].api_test_run_id == 7
    assert findings[0].test_run_id is None
    assert findings[0].severity == "high"
