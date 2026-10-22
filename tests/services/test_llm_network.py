from __future__ import annotations

from aespa.models import UpstreamProxyConfig
from aespa.services import llm
from aespa.services.llm import _bedrock_session, _bedrock_verify
from aespa.services.llm_network import child_network_env, httpx_options


def test_saved_llm_proxy_and_ca_reach_http_and_cli_clients(
    db_session, fake_ssl_context
):
    db_session.add(
        UpstreamProxyConfig(
            id=1,
            proxy_llm=True,
            llm_proxy_url="http://proxy.example:8080",
            llm_ca_bundle_path="/tmp/company-ca.pem",
        )
    )
    db_session.commit()

    assert httpx_options() == {
        "proxy": "http://proxy.example:8080",
        "verify": fake_ssl_context("/tmp/company-ca.pem"),
    }
    assert httpx_options("http://override.example:9000")["proxy"] == (
        "http://override.example:9000"
    )
    child = child_network_env({"PATH": "/usr/bin"})
    assert child["HTTPS_PROXY"] == "http://proxy.example:8080"
    assert child["SSL_CERT_FILE"] == "/tmp/company-ca.pem"
    assert child["NODE_EXTRA_CA_CERTS"] == "/tmp/company-ca.pem"
    assert child["AWS_CA_BUNDLE"] == "/tmp/company-ca.pem"


def test_default_llm_http_keeps_certificate_checks():
    assert httpx_options() == {"verify": True}


def test_saved_llm_transport_scope_uses_saved_ca_and_restores_context(db_session):
    db_session.add(
        UpstreamProxyConfig(
            id=1,
            llm_ca_bundle_path="/tmp/company-ca.pem",
            llm_proxy_url="http://proxy.example:8080",
            proxy_llm=True,
        )
    )
    db_session.commit()
    with llm.saved_llm_transport_scope():
        assert llm._llm_proxy_var.get() == "http://proxy.example:8080"
        assert llm._llm_ca_bundle_var.get() == "/tmp/company-ca.pem"
    assert llm._llm_proxy_var.get() is None
    assert llm._llm_ca_bundle_var.get() is None


def test_bedrock_credential_session_uses_saved_ca_and_proxy():
    session = _bedrock_session(None, "http://proxy.example:8080", "/tmp/company-ca.pem")
    assert session._session.get_config_variable("ca_bundle") == "/tmp/company-ca.pem"
    assert session._session.get_default_client_config().proxies == {
        "http": "http://proxy.example:8080",
        "https": "http://proxy.example:8080",
    }


def test_bedrock_keeps_aws_ca_bundle_without_saved_override(monkeypatch):
    monkeypatch.setenv("AWS_CA_BUNDLE", "/tmp/aws-ca.pem")
    session = _bedrock_session(None, None, None)

    assert _bedrock_verify(None, None) is None
    assert session._session.get_config_variable("ca_bundle") == "/tmp/aws-ca.pem"
    assert _bedrock_verify(None, "/tmp/aespa-ca.pem") == "/tmp/aespa-ca.pem"
    assert _bedrock_verify("http://proxy.example:8080", None) is False


def test_price_and_access_requests_use_saved_application_ca(
    db_session, monkeypatch, fake_ssl_context
):
    from aespa import cloudflare_access
    from aespa.services import statistics

    db_session.add(
        UpstreamProxyConfig(
            id=1,
            proxy_llm=True,
            llm_proxy_url="http://proxy.example:8080",
            llm_ca_bundle_path="/tmp/company-ca.pem",
        )
    )
    db_session.commit()
    seen = []

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {}

    def fake_get(url, **kwargs):
        seen.append((url, kwargs))
        return FakeResponse()

    monkeypatch.setattr(statistics.httpx, "get", fake_get)
    statistics.refresh_prices(db_session)
    cloudflare_access._get_jwks("https://company.cloudflareaccess.com")

    assert len(seen) == 2
    for _, options in seen:
        assert options["proxy"] == "http://proxy.example:8080"
        assert options["verify"] == fake_ssl_context("/tmp/company-ca.pem")
