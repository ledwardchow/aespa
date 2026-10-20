from __future__ import annotations

import json

import pytest
from sqlmodel import Session, select

from aespa.models import SastCodeCall, SastCodeSymbol, SastRun, SastSurfaceItem
from aespa.services import sast_codegraph, sast_workprogram


def _graph(tmp_path, files: dict[str, str]) -> sast_codegraph.CodeGraph:
    pairs = []
    for name, contents in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)
        pairs.append((name, path))
    return sast_codegraph.build_code_graph(pairs)


def _edges(graph: sast_codegraph.CodeGraph) -> set[tuple[str, str]]:
    return {
        (graph.defs[call.caller_key].qualname, graph.defs[target].qualname)
        for call in graph.calls
        for target in call.targets
    }


def test_php_methods_resolve_this_static_and_new(tmp_path):
    graph = _graph(
        tmp_path,
        {
            "src/Db.php": "<?php class Db {\n"
            "  public static function getInstance() { return new Db(); }\n"
            "  public function __construct() {}\n"
            "  public function run($sql) { return $this->pdo->query($sql); }\n"
            "}\n",
            "src/Controllers/UserController.php": "<?php class UserController {\n"
            "  public function show() { $id = $_GET['id']; $this->load($id); }\n"
            "  private function load($id) { Db::getInstance()->run($id); }\n"
            "}\n",
        },
    )
    assert graph.parsed_files == {
        "src/Db.php": "php",
        "src/Controllers/UserController.php": "php",
    }
    edges = _edges(graph)
    assert ("UserController.show", "UserController.load") in edges
    assert ("UserController.load", "Db.getInstance") in edges
    assert ("UserController.load", "Db.run") in edges
    assert ("Db.getInstance", "Db.__construct") in edges
    query = next(call for call in graph.calls if call.callee_name == "query")
    assert query.receiver == "$this->pdo"
    assert query.targets == []


@pytest.mark.parametrize(
    ("name", "source", "caller", "callee"),
    [
        (
            "app.py",
            "class A:\n  @app.route('/x')\n  def m(self, x):\n    self.h(x)\n"
            "  def h(self, y):\n    pass\n",
            "A.m",
            "A.h",
        ),
        (
            "A.java",
            "class A { void m(String x){ h(x); } void h(String y){} }\n",
            "A.m",
            "A.h",
        ),
        ("m.go", "package m\nfunc f(){ g() }\nfunc g(){}\n", "f", "g"),
        (
            "a.cs",
            "class A { void M(){ this.H(); } void H(){} }\n",
            "A.M",
            "A.H",
        ),
        (
            "a.rb",
            "class A\n  def m\n    h(1)\n  end\n  def h(x)\n  end\nend\n",
            "A.m",
            "A.h",
        ),
        (
            "a.ts",
            "export const h = (y: number) => y;\nfunction f(): void { h(1); }\n",
            "f",
            "h",
        ),
    ],
)
def test_calls_resolve_in_each_supported_language(
    tmp_path, name, source, caller, callee
):
    graph = _graph(tmp_path, {name: source})
    assert name in graph.parsed_files
    assert (caller, callee) in _edges(graph)


def test_calls_do_not_resolve_across_languages(tmp_path):
    graph = _graph(
        tmp_path,
        {
            "A.java": "class A { void m(){ helper(); } }\n",
            "b.rb": "def helper\nend\n",
            "c.go": "package c\nfunc helper(){}\n",
        },
    )
    call = next(call for call in graph.calls if call.callee_name == "helper")
    assert call.targets == []


def test_function_references_count_as_edges(tmp_path):
    graph = _graph(
        tmp_path,
        {
            "router.js": "function render() { eval(location.hash); }\n"
            "router.add('/home', render);\n",
            "view.jsx": "function go() {}\n"
            "const App = () => <button onClick={go}>x</button>;\n",
        },
    )
    graph.compute_reachability({graph.module_key("router.js")})
    render = next(item for item in graph.defs.values() if item.name == "render")
    assert graph.reachability[render.key] == sast_codegraph.REACHABLE
    assert ("App", "go") in _edges(graph)


def test_reachability_labels_and_chain(tmp_path):
    graph = _graph(
        tmp_path,
        {
            "app.py": "def handler():\n  step()\n"
            "def step():\n  sink()\n"
            "def sink():\n  pass\n"
            "def orphan():\n  lonely()\n"
            "def lonely():\n  pass\n",
        },
    )
    keys = {item.name: item.key for item in graph.defs.values()}
    graph.compute_reachability({keys["handler"]})
    assert graph.reachability[keys["sink"]] == sast_codegraph.REACHABLE
    assert graph.reachability[keys["orphan"]] == sast_codegraph.NO_CALLERS
    assert graph.reachability[keys["lonely"]] == sast_codegraph.NOT_REACHED
    assert [graph.defs[key].name for key in graph.path_to(keys["sink"])] == [
        "handler",
        "step",
        "sink",
    ]
    status, enclosing = graph.status_for("app.py", 6)
    assert enclosing is not None and enclosing.name == "sink"
    assert status == sast_codegraph.REACHABLE


def test_missing_grammar_leaves_file_unparsed(tmp_path, monkeypatch):
    def broken():
        raise ImportError("grammar not installed")

    spec = sast_codegraph._SPECS["python"]
    monkeypatch.setitem(
        sast_codegraph._SPECS,
        "python",
        sast_codegraph._LangSpec(
            spec.name, broken, spec.defs, spec.classes, spec.calls, spec.refs
        ),
    )
    graph = _graph(tmp_path, {"a.py": "def f():\n  pass\n", "b.go": "package b\n"})
    assert "a.py" not in graph.parsed_files
    assert "b.go" in graph.parsed_files
    assert graph.warnings and graph.warnings[0]["language"] == "python"
    assert graph.status_for("a.py", 1) == (sast_codegraph.UNKNOWN, None)


def _atlas(tmp_path, engine, files):
    root = tmp_path / "source"
    for name, contents in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)
    with Session(engine) as session:
        run = SastRun(name="code graph", status="scanning")
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id
    summary = sast_workprogram.build_source_atlas(run_id, root)
    with Session(engine) as session:
        surfaces = session.exec(
            select(SastSurfaceItem).where(SastSurfaceItem.sast_run_id == run_id)
        ).all()
    return run_id, summary, surfaces


def test_atlas_ignores_call_sinks_in_comments_and_strings(tmp_path, isolated_db_engine):
    _run_id, summary, surfaces = _atlas(
        tmp_path,
        isolated_db_engine,
        {
            "src/Controllers/PageController.php": "<?php class PageController {\n"
            "  public function show() {\n"
            "    // never call exec($cmd) here\n"
            "    $help = 'use shell_exec($x) carefully';\n"
            "    return shell_exec($_GET['cmd']);\n"
            "  }\n"
            "}\n",
            "templates/help.html": "<p>Never call system(cmd) directly</p>\n",
        },
    )
    command_lines = {
        (item.path, item.line)
        for item in surfaces
        if item.kind == "sink" and item.name == "Command execution"
    }
    assert command_lines == {
        ("src/Controllers/PageController.php", 5),
        ("templates/help.html", 1),
    }
    # Line 3 matches command and code evaluation; line 4 matches command.
    assert summary["code_graph"]["sink_matches_outside_calls"] == 3


def test_atlas_records_function_and_reachability(tmp_path, isolated_db_engine):
    run_id, summary, surfaces = _atlas(
        tmp_path,
        isolated_db_engine,
        {
            "app/routes.py": "from flask import request\n"
            "@app.route('/run')\n"
            "def run_view():\n"
            "  return helper(request.args['c'])\n",
            "app/util.py": "import os\n"
            "def helper(value):\n"
            "  return os.system(value)\n"
            "def unused(value):\n"
            "  return os.system(value)\n",
        },
    )
    sinks = {
        item.line: json.loads(item.details_json)
        for item in surfaces
        if item.kind == "sink" and item.path == "app/util.py"
    }
    assert sinks[3]["reachability"] == sast_codegraph.REACHABLE
    assert sinks[3]["function"] == "helper (app/util.py:2)"
    assert sinks[3]["reached_from"][0].startswith("run_view")
    assert sinks[5]["reachability"] == sast_codegraph.NO_CALLERS

    graph = summary["code_graph"]
    assert graph["files_parsed"] == 2
    assert graph["resolved_calls"] >= 1
    assert graph["sink_reachability"][sast_codegraph.REACHABLE] >= 1

    with Session(isolated_db_engine) as session:
        symbols = session.exec(
            select(SastCodeSymbol).where(SastCodeSymbol.sast_run_id == run_id)
        ).all()
        calls = session.exec(
            select(SastCodeCall).where(SastCodeCall.sast_run_id == run_id)
        ).all()
    by_name = {symbol.name: symbol for symbol in symbols}
    assert by_name["helper"].reachability == sast_codegraph.REACHABLE
    assert by_name["run_view"].is_root
    helper_call = next(call for call in calls if call.callee_name == "helper")
    assert json.loads(helper_call.targets_json) == [by_name["helper"].symbol_key]

    worker = next(
        worker
        for worker in sast_workprogram.worker_rows(run_id)
        if any(
            item["surface"].get("function")
            for item in sast_workprogram.worker_payload(worker.id)["work_items"]
        )
    )
    item = next(
        item
        for item in sast_workprogram.worker_payload(worker.id)["work_items"]
        if item["surface"].get("function")
    )
    assert item["surface"]["reachability"] in {
        sast_codegraph.REACHABLE,
        sast_codegraph.NO_CALLERS,
        sast_codegraph.NOT_REACHED,
    }


def test_rebuilding_atlas_replaces_code_graph(tmp_path, isolated_db_engine):
    run_id, _summary, _surfaces = _atlas(
        tmp_path, isolated_db_engine, {"a.py": "def f():\n  g()\ndef g():\n  pass\n"}
    )
    sast_workprogram.build_source_atlas(run_id, tmp_path / "source")
    with Session(isolated_db_engine) as session:
        symbols = session.exec(
            select(SastCodeSymbol).where(SastCodeSymbol.sast_run_id == run_id)
        ).all()
    assert sorted(symbol.name for symbol in symbols) == ["<module>", "f", "g"]
