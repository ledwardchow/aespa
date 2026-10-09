from __future__ import annotations

import asyncio
import json

from sqlmodel import select

from aespa.models import ScanFinding, Site, TargetIntelItem, TestRun, TrafficEntry
from aespa.services import js_libraries
from aespa.services.sast_parsers import extract_parser_facts
from aespa.services.sast_semantic import (
    build_repository_model,
    dependency_match_candidates,
    deterministic_dependency_analysis,
    vendored_library_candidates,
)


def test_detects_versions_from_names_urls_and_content():
    by_name = js_libraries.detect("https://code.jquery.com/jquery-1.12.4.min.js")
    assert [(d.library, d.version, d.method) for d in by_name] == [
        ("jquery", "1.12.4", js_libraries.METHOD_FILENAME)
    ]

    wordpress = js_libraries.detect(
        "https://site.test/wp-includes/js/jquery/jquery.min.js?ver=3.7.1"
    )
    assert [(d.library, d.version) for d in wordpress] == [("jquery", "3.7.1")]

    bundled = js_libraries.detect(
        "https://site.test/static/app.js",
        "/*! jQuery v3.4.1 | (c) JS Foundation */\n//! moment.js\n//! version : 2.24.0\n",
    )
    assert {(d.library, d.version) for d in bundled} == {
        ("jquery", "3.4.1"),
        ("moment", "2.24.0"),
    }


def test_file_content_overrides_url_guess_for_same_library():
    found = js_libraries.detect(
        "https://site.test/assets/1.0/jquery.min.js", "/*! jQuery v3.7.1 | (c) */"
    )
    assert [(d.library, d.version, d.method) for d in found] == [
        ("jquery", "3.7.1", js_libraries.METHOD_CONTENT)
    ]


def test_version_comparison_handles_prereleases_and_extra_parts():
    assert js_libraries.compare_versions("3.0.0-beta1", "3.0.0") < 0
    assert js_libraries.compare_versions("1.6.0.2", "1.6.0") > 0
    assert js_libraries.compare_versions("4.17.21", "4.17.21") == 0
    assert js_libraries.clean_version("^2.29.1") == "2.29.1"


def test_reports_group_issues_and_suggest_fixed_version():
    reports = js_libraries.vulnerable_reports(
        js_libraries.detect("https://code.jquery.com/jquery-1.12.4.min.js")
    )
    assert len(reports) == 1
    report = reports[0]
    assert report.display == "jQuery"
    assert report.fixed_version == "3.5.0"
    assert {"CVE-2019-11358", "CVE-2020-11022", "CVE-2020-11023"} <= set(
        report.identifiers
    )

    current = js_libraries.vulnerable_reports(
        js_libraries.detect("https://code.jquery.com/jquery-3.7.1.min.js")
    )
    assert current == []


def test_end_of_life_library_has_no_fixed_version():
    report = js_libraries.vulnerable_reports(
        js_libraries.detect(
            "https://cdn.test/ajax/libs/angular.js/1.8.3/angular.min.js"
        )
    )[0]
    assert report.fixed_version is None


def test_bootstrap_ranges_are_tracked_per_major_version():
    v3 = js_libraries.vulnerabilities_for("bootstrap", "3.4.1")
    v4 = js_libraries.vulnerabilities_for("bootstrap", "4.3.1")
    v4_old = js_libraries.vulnerabilities_for("bootstrap", "4.1.0")
    assert v3 == [] and v4 == []
    assert v4_old


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
    (vendor / "jquery-ui-1.11.4.min.js").write_text("/* no banner */", encoding="utf-8")
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
