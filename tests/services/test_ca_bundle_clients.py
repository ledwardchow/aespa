from __future__ import annotations

from aespa.services import llm, scanner, traffic


def test_llm_ca_bundle_is_used_even_with_proxy(monkeypatch):
    seen = []
    monkeypatch.setattr(llm.httpx2, "AsyncClient", lambda **kwargs: seen.append(kwargs))
    proxy_token = llm._llm_proxy_var.set("http://proxy.local:8080")
    ca_token = llm._llm_ca_bundle_var.set("/certs/company.pem")
    try:
        llm._llm_client_kwargs()
    finally:
        llm._llm_ca_bundle_var.reset(ca_token)
        llm._llm_proxy_var.reset(proxy_token)
    assert seen[0]["verify"] == "/certs/company.pem"
    assert seen[0]["proxy"] == "http://proxy.local:8080"


def test_scanner_ca_bundle_changes_http_verification(monkeypatch):
    seen = []
    monkeypatch.setattr(
        traffic, "LoggingAsyncClient", lambda **kwargs: seen.append(kwargs)
    )
    token = scanner._scanner_ca_bundle_var.set("/certs/company.pem")
    try:
        scanner._make_scanner_client()
    finally:
        scanner._scanner_ca_bundle_var.reset(token)
    scanner._make_scanner_client()
    assert seen[0]["verify"] == "/certs/company.pem"
    assert seen[1]["verify"] is False
