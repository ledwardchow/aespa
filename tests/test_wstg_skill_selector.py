"""Tests for the WSTG skill selector (issue #98 prompt-coverage improvements)."""

from aespa.services.llm import select_wstg_skills, build_wstg_skill_context
from aespa.services.prompts.test_lead import WSTG_SKILLS, _SKILL_ORDER


def test_auth_robustness_skill_is_defined_and_ordered():
    # The skill block exists and is wired into the render order.
    assert "auth_robustness" in WSTG_SKILLS
    assert "auth_robustness" in _SKILL_ORDER
    block = WSTG_SKILLS["auth_robustness"]
    # Covers all three reported gaps: weak password policy + rate limiting + enumeration.
    assert "password policy" in block.lower()
    assert "rate-limiting" in block.lower() or "rate limiting" in block.lower()
    assert "6" in block  # the explicit bounded login-attempt count


def test_auth_pages_select_auth_robustness():
    selected = select_wstg_skills(
        pages=[{"url": "https://t/login", "req_auth": False}],
        intel_items=[],
    )
    assert "auth_robustness" in selected
    # And it renders into the assembled context.
    ctx = build_wstg_skill_context(selected)
    assert "AUTHENTICATION ROBUSTNESS" in ctx


def test_requires_auth_flag_selects_auth_robustness():
    selected = select_wstg_skills(pages=[], intel_items=[], requires_auth=True)
    assert "auth_robustness" in selected


def test_no_auth_surface_omits_auth_robustness():
    selected = select_wstg_skills(
        pages=[{"url": "https://t/static/style.css"}],
        intel_items=[],
    )
    assert "auth_robustness" not in selected


def test_ssrf_selected_on_expanded_param_name():
    # avatarurl is one of the newly-added SSRF-prone parameter names.
    selected = select_wstg_skills(
        pages=[],
        intel_items=[{"kind": "input", "key": "avatarurl", "value": "", "url": ""}],
    )
    assert "ssrf" in selected


def test_ssrf_selected_on_feature_url_without_url_param():
    # A PDF-export feature is an SSRF lead even with no url= parameter.
    selected = select_wstg_skills(
        pages=[{"url": "https://t/account/export/pdf"}],
        intel_items=[],
    )
    assert "ssrf" in selected


def test_ssrf_selected_on_import_feature_key():
    selected = select_wstg_skills(
        pages=[],
        intel_items=[{"kind": "input", "key": "import_source", "value": "", "url": ""}],
    )
    assert "ssrf" in selected


def test_ssrf_not_selected_on_unrelated_surface():
    selected = select_wstg_skills(
        pages=[{"url": "https://t/about"}],
        intel_items=[{"kind": "input", "key": "comment", "value": "hi", "url": ""}],
    )
    assert "ssrf" not in selected
