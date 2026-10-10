from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest
from sqlmodel import select

from aespa.models import (
    ScanFinding,
    Site,
    TargetIntelItem,
    TestRun,
    TrafficEntry,
    UpstreamProxyConfig,
)
from aespa.services import js_libraries, retire_repository
from aespa.services.retire_repository import ensure_fresh as real_ensure_fresh
from aespa.services.sast_parsers import extract_parser_facts
from aespa.services.sast_semantic import (
    build_repository_model,
    dependency_match_candidates,
    deterministic_dependency_analysis,
    vendored_library_candidates,
)

SMALL = str(Path(__file__).parents[1] / "fixtures" / "retire_small.json")
SHIPPED = retire_repository.BUNDLED_DIR / retire_repository.FILE_NAME


# ── Detector, against a small Retire.js-format fixture ──────────────────────


def test_detects_versions_from_names_urls_and_content():
    by_name = js_libraries.detect("https://cdn.test/jquery-1.12.4.min.js", path=SMALL)
    assert [(d.library, d.version, d.method) for d in by_name] == [
        ("jquery", "1.12.4", js_libraries.METHOD_FILENAME)
    ]
    by_url = js_libraries.detect("https://cdn.test/3.4.1/jquery.min.js", path=SMALL)
    assert [(d.version, d.method) for d in by_url] == [
        ("3.4.1", js_libraries.METHOD_URI)
    ]
    by_content = js_libraries.detect(
        "https://site.test/app.js", "/*! jQuery v3.4.1 | (c) */", path=SMALL
    )
    assert [(d.version, d.method) for d in by_content] == [
        ("3.4.1", js_libraries.METHOD_CONTENT)
    ]


def test_file_content_overrides_url_guess_for_same_library():
    found = js_libraries.detect(
        "https://site.test/assets/1.0/jquery.min.js",
        "/*! jQuery v3.7.1 | (c) */",
        path=SMALL,
    )
    assert [(d.version, d.method) for d in found] == [
        ("3.7.1", js_libraries.METHOD_CONTENT)
    ]


def test_filecontentreplace_and_hashes():
    replaced = js_libraries.detect_in_content(
        'var a="2.2.4",b=function(){};jqmark', "app.js", SMALL
    )
    assert [(d.library, d.version) for d in replaced] == [("jquery", "2.2.4")]

    hashed = js_libraries.detect_in_content("hello", "dojo.js", SMALL, raw=b"hello")
    assert [(d.library, d.version, d.method) for d in hashed] == [
        ("dojo", "1.4.1", js_libraries.METHOD_HASH)
    ]
    # Without the complete file there is no hash match.
    assert js_libraries.detect_in_content("hello", "dojo.js", SMALL) == []


def test_repository_loading_skips_examples_and_unusable_patterns():
    repo = js_libraries.get_repository(SMALL)
    assert "retire-example" not in repo.libraries
    assert "dont check" not in repo.libraries
    assert repo.skipped_patterns == 1
    assert js_libraries.detect("https://ignored.test/jquery-1.0.0.js", path=SMALL) == []
    assert js_libraries.runtime_probes(SMALL) == [("jquery", "window.jQuery.fn.jquery")]


def test_version_comparison_handles_prereleases_and_extra_parts():
    assert js_libraries.compare_versions("3.0.0-beta1", "3.0.0") < 0
    assert js_libraries.compare_versions("1.6.0.2", "1.6.0") > 0
    assert js_libraries.compare_versions("4.17.21", "4.17.21") == 0
    assert js_libraries.clean_version("^2.29.1") == "2.29.1"


def test_reports_group_issues_and_suggest_fixed_version():
    report = js_libraries.vulnerable_reports(
        js_libraries.detect("https://cdn.test/jquery-1.12.4.min.js", path=SMALL),
        SMALL,
    )[0]
    assert report.display == "jQuery"
    assert report.fixed_version == "3.5.0"
    assert report.identifiers == [
        "CVE-2020-11022",
        "GHSA-gxr4-xjj5-5px2",
        "CVE-2019-11358",
    ]
    assert js_libraries.vulnerabilities_for("jquery", "3.7.1", SMALL) == []


def test_excluded_builds_are_not_flagged():
    vulns = js_libraries.vulnerabilities_for("jquery", "1.12.4-aem", SMALL)
    assert [v["identifiers"]["CVE"] for v in vulns] == [["CVE-2019-11358"]]


def test_no_fixed_release_ranges():
    report = js_libraries.vulnerable_reports(
        js_libraries.detect("https://cdn.test/angular.js/1.8.3/angular.js", path=SMALL),
        SMALL,
    )[0]
    assert report.fixed_version is None
    assert "no fixed release" in js_libraries.describe_vulnerabilities(report)[0]


def test_package_families_are_reported_once():
    assert js_libraries.libraries_for_package("jquery-ui", SMALL) == [
        "jquery-ui",
        "jquery-ui-dialog",
    ]
    assert js_libraries.libraries_for_package("jQuery", SMALL) == ["jquery"]
    detections = [
        js_libraries.Detection(
            lib, "1.11.4", js_libraries.METHOD_MANIFEST, "bower.json"
        )
        for lib in ("jquery-ui", "jquery-ui-dialog")
    ]
    reports = js_libraries.vulnerable_reports(detections, SMALL)
    assert len(reports) == 1
    assert reports[0].identifiers == ["CVE-2021-41182", "CVE-2016-7103"]


def test_shipped_retire_list_flags_old_jquery():
    repo = js_libraries.get_repository(SHIPPED)
    assert len(repo.libraries) >= 50
    assert repo.skipped_patterns <= 0.05 * repo.total_patterns
    old = js_libraries.vulnerable_reports(
        js_libraries.detect("https://code.jquery.com/jquery-1.12.4.min.js")
    )
    assert [r.display for r in old] == ["jQuery"]
    assert "CVE-2020-11022" in old[0].identifiers
    current = js_libraries.vulnerable_reports(
        js_libraries.detect("https://code.jquery.com/jquery-3.7.1.min.js")
    )
    assert current == []


# ── Downloading the latest list ─────────────────────────────────────────────


def _transport(responses: list[httpx.Response], seen: list[httpx.Request]):
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return responses.pop(0)

    return httpx.MockTransport(handler)


def _refresh(client, **kwargs):
    async def run():
        async with client:
            return await real_ensure_fresh(client=client, **kwargs)

    return asyncio.run(run())


def test_list_download_uses_testing_ca_bundle(db_session, monkeypatch):
    db_session.add(
        UpstreamProxyConfig(id=1, scanner_ca_bundle_path="/tmp/testing-ca.pem")
    )
    db_session.commit()
    captured = {}

    class FakeClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def stream(self, *_args, **_kwargs):
            raise RuntimeError("offline test")

        async def aclose(self):
            pass

    monkeypatch.setattr(retire_repository.httpx, "AsyncClient", FakeClient)
    result = asyncio.run(real_ensure_fresh())
    assert result["status"] == "failed"
    assert captured["verify"] == "/tmp/testing-ca.pem"


def test_download_replaces_cached_copy_and_uses_etag(offline_retire_list):
    shipped = SHIPPED.read_bytes()
    seen: list[httpx.Request] = []
    client = httpx.AsyncClient(
        transport=_transport(
            [
                httpx.Response(200, content=shipped, headers={"etag": '"v1"'}),
                httpx.Response(304),
            ],
            seen,
        )
    )
    result = _refresh(client)
    assert result["status"] == "updated"
    assert result["copy"] == "downloaded"
    assert (
        retire_repository.active_path() == offline_retire_list / "jsrepository-v6.json"
    )

    client = httpx.AsyncClient(transport=_transport([httpx.Response(304)], seen))
    result = _refresh(client, max_age=retire_repository.timedelta(0))
    assert result["status"] == "unchanged"
    assert seen[-1].headers["if-none-match"] == '"v1"'

    # A fresh copy is not downloaded again.
    client = httpx.AsyncClient(transport=_transport([], seen))
    assert _refresh(client)["status"] == "fresh"


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, content=b"not json"),
        httpx.Response(200, content=json.dumps({"jquery": {}}).encode()),
        httpx.Response(500),
    ],
)
def test_bad_downloads_keep_the_current_copy(offline_retire_list, response):
    client = httpx.AsyncClient(transport=_transport([response], []))
    result = _refresh(client)
    assert result["status"] == "failed"
    assert result["copy"] == "shipped"
    assert not (offline_retire_list / "jsrepository-v6.json").exists()


def test_disabled_download_makes_no_request():
    client = httpx.AsyncClient(transport=_transport([], []))
    assert _refresh(client, enabled=False)["status"] == "disabled"


# ── Scanner and SAST, against the shipped list ──────────────────────────────


def _web_run(db_session) -> TestRun:
    site = Site(name="Target", base_url="https://target.test")
    db_session.add(site)
    db_session.commit()
    db_session.refresh(site)
    run = TestRun(site_id=site.id, name="Run")
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    return run


def test_scanner_module_reports_outdated_libraries_from_captured_traffic(db_session):
    from aespa.services import scanner

    run = _web_run(db_session)
    body = "/*! jQuery v1.12.4 | (c) jQuery Foundation | jquery.org/license */"
    db_session.add_all(
        [
            TrafficEntry(
                test_run_id=run.id,
                source="playwright",
                method="GET",
                url="https://target.test/static/vendor.js",
                status=200,
                response_headers=json.dumps({"content-type": "application/javascript"}),
                response_body=body,
                response_body_size=len(body),
            ),
            TrafficEntry(
                test_run_id=run.id,
                source="playwright",
                method="GET",
                url="https://code.jquery.com/jquery-3.7.1.min.js",
                status=200,
                response_body="/*! jQuery v3.7.1 | (c) */",
            ),
            TargetIntelItem(
                test_run_id=run.id,
                kind="script",
                key="/static/vendor.js",
                value="https://target.test/static/vendor.js",
                url="https://target.test/login",
            ),
        ]
    )
    db_session.commit()

    findings = asyncio.run(
        scanner._run_outdated_js_module(
            run_id=run.id, base_url="https://target.test", site_id=run.site_id
        )
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding.owasp_category == "A06"
    assert finding.title == "Outdated jQuery 1.12.4 with known vulnerabilities"
    assert finding.affected_url == "https://target.test/static/vendor.js"
    assert "CVE-2020-11022" in finding.description
    assert "https://target.test/login" in finding.description
    assert "3.5.0" in finding.recommendation

    assert scanner._save_deterministic_findings(run.id, findings) == 1
    rerun = asyncio.run(
        scanner._run_outdated_js_module(
            run_id=run.id, base_url="https://target.test", site_id=run.site_id
        )
    )
    assert scanner._save_deterministic_findings(run.id, rerun) == 0
    saved = db_session.exec(
        select(ScanFinding).where(ScanFinding.test_run_id == run.id)
    ).all()
    assert len(saved) == 1


def test_lockfile_version_wins_over_declared_range(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"jquery": "^3.4.1", "lodash": "^4.17.15"}}),
        encoding="utf-8",
    )
    (tmp_path / "package-lock.json").write_text(
        json.dumps(
            {
                "lockfileVersion": 3,
                "packages": {
                    "": {"name": "app"},
                    "node_modules/jquery": {"version": "3.7.1"},
                    "node_modules/left-pad": {"version": "1.0.0"},
                },
            }
        ),
        encoding="utf-8",
    )
    lock_facts = extract_parser_facts(tmp_path).facts
    assert not any(f.get("name") == "left-pad" for f in lock_facts)

    analysis = deterministic_dependency_analysis(
        build_repository_model(tmp_path), {"updated_at": None, "advisories": []}
    )
    matched = {m["library"]: m for m in analysis["matches"] if m.get("library")}
    # jQuery resolves to a fixed version in the lockfile; Lodash only has a range.
    assert "jQuery" not in matched
    assert matched["Lodash"]["declared_range"] is True

    candidates = dependency_match_candidates(analysis)
    assert any(c["title"].startswith("Outdated Lodash 4.17.15") for c in candidates)


def test_yarn_lock_and_vendored_files_are_checked(tmp_path):
    (tmp_path / "yarn.lock").write_text(
        '"handlebars@^4.0.0":\n  version "4.1.2"\n  resolved "x"\n\n'
        '"react@^18.0.0":\n  version "18.2.0"\n',
        encoding="utf-8",
    )
    vendor = tmp_path / "public" / "js"
    vendor.mkdir(parents=True)
    (vendor / "jquery-ui.min.js").write_text(
        "/*! jQuery UI - v1.11.4 - 2015-03-11 */", encoding="utf-8"
    )
    (vendor / "bundle.js").write_text(
        "/*! @license DOMPurify 2.3.1 */", encoding="utf-8"
    )
    ignored = tmp_path / "node_modules" / "jquery" / "dist"
    ignored.mkdir(parents=True)
    (ignored / "jquery.js").write_text("/*! jQuery v1.8.3 */", encoding="utf-8")

    analysis = deterministic_dependency_analysis(
        build_repository_model(tmp_path), {"updated_at": None, "advisories": []}
    )
    assert [m["library"] for m in analysis["matches"]] == ["Handlebars"]

    titles = {c["title"] for c in vendored_library_candidates(tmp_path)}
    assert titles == {
        "Outdated jQuery UI 1.11.4 with known vulnerabilities",
        "Outdated DOMPurify 2.3.1 with known vulnerabilities",
    }


def test_light_sast_records_library_leads_once(isolated_db_engine, tmp_path):
    from sqlmodel import Session

    from aespa.models import SastRun, ScanLead
    from aespa.services import sast_scanner_light

    (tmp_path / "bower.json").write_text(
        json.dumps({"dependencies": {"jquery": "1.11.1"}}), encoding="utf-8"
    )
    (tmp_path / "static").mkdir()
    (tmp_path / "static" / "handlebars-4.0.5.js").write_text("", encoding="utf-8")
    with Session(isolated_db_engine) as session:
        run = SastRun(name="light", analysis_mode="light")
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    sast_scanner_light._candidates.pop(run_id, None)
    try:
        added = sast_scanner_light._add_library_candidates(run_id, None, tmp_path)
        again = sast_scanner_light._add_library_candidates(run_id, None, tmp_path)
        candidates = sast_scanner_light._candidates[run_id]
    finally:
        sast_scanner_light._candidates.pop(run_id, None)

    assert (added, again) == (2, 0)
    assert {c["title"] for c in candidates} == {
        "Outdated jQuery 1.11.1 with known vulnerabilities",
        "Outdated Handlebars 4.0.5 with known vulnerabilities",
    }
    assert all(c["validation_status"] == "pending" for c in candidates)
    with Session(isolated_db_engine) as session:
        leads = session.exec(
            select(ScanLead).where(ScanLead.producer_run_id == run_id)
        ).all()
    assert len(leads) == 2


def test_settings_api_reports_and_refreshes_the_list(client, monkeypatch):
    status = client.get("/api/settings/retire-list").json()
    assert status["copy"] == "shipped"
    assert status["libraries"] >= 50

    calls = []

    async def fake_refresh(**kwargs):
        calls.append(kwargs)
        return {**retire_repository.info(), "status": "unchanged"}

    monkeypatch.setattr(retire_repository, "ensure_fresh", fake_refresh)
    refreshed = client.post("/api/settings/retire-list/refresh").json()
    assert refreshed["status"] == "unchanged"
    # A manual refresh always checks, even when automatic updates are off.
    assert calls[0]["enabled"] is True
    assert calls[0]["max_age"].total_seconds() == 0

    policy = client.get("/api/settings/scanner-policy").json()
    assert policy["retire_auto_update"] is True
    policy["retire_auto_update"] = False
    saved = client.put("/api/settings/scanner-policy", json=policy).json()
    assert saved["retire_auto_update"] is False
