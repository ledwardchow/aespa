from __future__ import annotations

import ssl

import certifi

from aespa.services.tls import httpx_verify


def test_without_a_bundle_the_default_decides_verification():
    assert httpx_verify(None, True) is True
    assert httpx_verify("", False) is False


def test_bundle_file_is_loaded_into_a_verifying_context():
    context = httpx_verify(certifi.where(), False)
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.cert_store_stats()["x509_ca"] > 0


def test_bundle_directory_is_loaded_as_capath(tmp_path):
    context = httpx_verify(str(tmp_path), False)
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
