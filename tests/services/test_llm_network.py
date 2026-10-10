from __future__ import annotations

from aespa.models import UpstreamProxyConfig
from aespa.services.llm import _bedrock_session
from aespa.services.llm_network import child_network_env, httpx_options


def test_saved_llm_proxy_and_ca_reach_http_and_cli_clients(db_session):
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
        "verify": "/tmp/company-ca.pem",
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


def test_bedrock_credential_session_uses_saved_ca_and_proxy():
    session = _bedrock_session(None, "http://proxy.example:8080", "/tmp/company-ca.pem")
    assert session._session.get_config_variable("ca_bundle") == "/tmp/company-ca.pem"
    assert session._session.get_default_client_config().proxies == {
        "http": "http://proxy.example:8080",
        "https": "http://proxy.example:8080",
    }
