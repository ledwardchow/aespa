"""Burp Suite web scanner extension entrypoint."""

from .scanner import BurpSuiteExtension


def create_extension() -> BurpSuiteExtension:
    return BurpSuiteExtension()
