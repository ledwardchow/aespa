from __future__ import annotations

import asyncio

import pytest
from sqlmodel import Session, select

from aespa.models import (
    SastEvidenceReceipt,
    SastRun,
    SastSurfaceItem,
    SastWorker,
    SastWorkItem,
)
from aespa.services import sast_scanner, sast_scanner_light, sast_workprogram


def _atlas(tmp_path, engine, files):
    root = tmp_path / "source"
    for name, contents in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)
    with Session(engine) as session:
        run = SastRun(name="route review", status="scanning")
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id
    sast_workprogram.build_source_atlas(run_id, root)
    with Session(engine) as session:
        surfaces = session.exec(
            select(SastSurfaceItem).where(SastSurfaceItem.sast_run_id == run_id)
        ).all()
        work_items = session.exec(
            select(SastWorkItem).where(SastWorkItem.sast_run_id == run_id)
        ).all()
    assigned_ids = {item.surface_item_id for item in work_items}
    return run_id, surfaces, assigned_ids


def test_php_routes_handlers_and_serializers_get_discovery_work(
    tmp_path, isolated_db_engine
):
    run_id, surfaces, assigned_ids = _atlas(
        tmp_path,
        isolated_db_engine,
        {
            "src/Router.php": (
                "<?php\n"
                "$config = getenv('ENV');\n"
                "$r->addRoute('POST', '/api/auth/login', "
                "['handler' => [AuthController::class, 'login']]);\n"
            ),
            "src/Controllers/AuthController.php": (
                "<?php\nclass AuthController {\n"
                "public static function login() {\n"
                "$data = json_decode(file_get_contents('php://input'), true);\n"
                "Response::error('MISSING', 'Unknown user', 401);\n}}\n"
            ),
            "public/index.php": "<?php\nRouter::dispatch();\n",
            "src/Models/User.php": (
                "<?php\nclass User {\n"
                "public static function toPublic($user) { return $user; }\n}\n"
            ),
        },
    )
    assert any(
        item.path == "src/Router.php"
        and item.kind == "entrypoint"
        and item.category == "http"
        for item in surfaces
    )
    assert any(
        item.path == "src/Controllers/AuthController.php"
        and item.kind == "input"
        and item.category == "request"
        for item in surfaces
    )
    for path in (
        "src/Router.php",
        "src/Controllers/AuthController.php",
        "public/index.php",
    ):
        assert any(
            item.path == path
            and item.category == "handler_review"
            and item.id in assigned_ids
            for item in surfaces
        )
    assert any(
        item.path == "src/Models/User.php"
        and item.name == "Response serialization"
        and item.id in assigned_ids
        for item in surfaces
    )
    assert "No production entry point" not in " ".join(
        sast_workprogram.completion_decision(run_id)[1]
    )


def test_route_and_handler_reviews_are_not_php_specific(tmp_path, isolated_db_engine):
    _, surfaces, assigned_ids = _atlas(
        tmp_path,
        isolated_db_engine,
        {
            "src/server.js": "app.post('/login', login);\n",
            "src/controllers/login.js": "export function login(req, res) { res.json(req.body); }\n",
            "api/views.py": "@app.get('/profile')\ndef profile(request): return jsonify({})\n",
            "api/urls.py": "urlpatterns = [\n    path('profile', profile),\n]\n",
            "routes/web.php": "<?php\nRoute::post('/login', [AuthController::class, 'login']);\n",
        },
    )
    for path in (
        "src/server.js",
        "src/controllers/login.js",
        "api/views.py",
        "api/urls.py",
        "routes/web.php",
    ):
        assert any(
            item.path == path
            and item.category == "handler_review"
            and item.id in assigned_ids
            for item in surfaces
        )
    for path in ("api/urls.py", "routes/web.php"):
        assert any(
            item.path == path and item.kind == "entrypoint" and item.category == "http"
            for item in surfaces
        )


def test_unknown_route_syntax_still_assigns_handler_review_and_reports_gap(
    tmp_path, isolated_db_engine
):
    run_id, surfaces, assigned_ids = _atlas(
        tmp_path,
        isolated_db_engine,
        {"src/handlers/account.go": "package handlers\nfunc Account(w, r) {}\n"},
    )
    assert any(
        item.category == "handler_review" and item.id in assigned_ids
        for item in surfaces
    )
    assert any(item.category == "inferred_handler" for item in surfaces)
    assert "No production entry point" in " ".join(
        sast_workprogram.completion_decision(run_id)[1]
    )


def test_route_worker_owns_local_sinks_and_helper_sinks_keep_later_review(
    tmp_path, isolated_db_engine
):
    run_id, _, _ = _atlas(
        tmp_path,
        isolated_db_engine,
        {
            "routes.py": (
                "@app.get('/items')\n"
                "def items(request):\n"
                "    return db.execute(request.args['q'])\n"
            ),
            "helpers/query.py": "def query(value):\n    return db.execute(value)\n",
        },
    )
    with Session(isolated_db_engine) as session:
        workers = {
            worker.id: worker
            for worker in session.exec(
                select(SastWorker).where(SastWorker.sast_run_id == run_id)
            ).all()
        }
        surfaces = {
            surface.id: surface
            for surface in session.exec(
                select(SastSurfaceItem).where(SastSurfaceItem.sast_run_id == run_id)
            ).all()
        }
        sink_items = session.exec(
            select(SastWorkItem)
            .where(SastWorkItem.sast_run_id == run_id)
            .where(SastWorkItem.work_type == "sink")
        ).all()
    assert any(
        surfaces[item.surface_item_id].path == "routes.py"
        and workers[item.worker_id].class_group == "review"
        for item in sink_items
    )
    assert any(
        surfaces[item.surface_item_id].path == "helpers/query.py"
        and workers[item.worker_id].class_group == "sink"
        for item in sink_items
    )
    assert all(item.status == "pending" for item in sink_items)


def test_route_worker_can_claim_only_a_helper_sink_it_opened(
    tmp_path, isolated_db_engine
):
    run_id, _, _ = _atlas(
        tmp_path,
        isolated_db_engine,
        {
            "routes.py": "@app.get('/items')\ndef items(request):\n    return run_sql(request.args['q'])\n",
            "helpers/query.py": "def run_sql(value):\n    return db.execute(value)\n",
        },
    )
    workers = sast_workprogram.worker_rows(run_id)
    route = next(
        worker
        for worker in workers
        if worker.class_group == "review"
        and "routes.py" in sast_workprogram.worker_payload(worker.id)["files"]
    )
    sink = next(worker for worker in workers if worker.class_group == "sink")
    claimed, message = sast_workprogram.claim_traced_sinks(
        route.id, "helpers/query.py", 2
    )
    assert claimed == []
    assert "read_file" in message
    with Session(isolated_db_engine) as session:
        session.add(
            SastEvidenceReceipt(
                sast_run_id=run_id,
                worker_id=route.id,
                phase="discovery",
                tool_name="read_file",
                path="helpers/query.py",
                start_line=1,
                end_line=2,
            )
        )
        session.commit()
    claimed, message = sast_workprogram.claim_traced_sinks(
        route.id, "helpers/query.py", 2
    )
    assert claimed == []
    assert "route or handler" in message
    with Session(isolated_db_engine) as session:
        session.add(
            SastEvidenceReceipt(
                sast_run_id=run_id,
                worker_id=route.id,
                phase="discovery",
                tool_name="read_file",
                path="routes.py",
                start_line=1,
                end_line=3,
            )
        )
        session.commit()
    claimed, _ = sast_workprogram.claim_traced_sinks(route.id, "helpers/query.py", 2)
    assert len(claimed) == 1
    assert (
        sast_workprogram.work_program_summary(run_id)["work_items"][
            "claimed_helper_sinks"
        ]
        == 1
    )
    assert claimed[0] in sast_workprogram.unresolved_for_worker(route.id)
    assert sast_workprogram.unresolved_for_worker(sink.id) == []
    ok, _ = sast_workprogram.record_disposition(
        claimed[0], status="safe", reasoning="The query uses a fixed SQL statement."
    )
    assert ok
    assert claimed[0] not in sast_workprogram.unresolved_for_worker(route.id)


@pytest.mark.parametrize("scanner", [sast_scanner, sast_scanner_light])
def test_both_scan_modes_can_close_claimed_sink_work(
    scanner, tmp_path, isolated_db_engine
):
    root = tmp_path / "source"
    (root / "helpers").mkdir(parents=True)
    (root / "routes.py").write_text(
        "@app.get('/items')\ndef items(request):\n    return query(request.args['q'])\n"
    )
    (root / "helpers/query.py").write_text(
        "def query(value):\n    return db.execute(value)\n"
    )
    with Session(isolated_db_engine) as session:
        run = SastRun(name="claimed sink", status="scanning")
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id
    sast_workprogram.build_source_atlas(run_id, root)
    route = next(
        worker
        for worker in sast_workprogram.worker_rows(run_id)
        if worker.class_group == "review"
        and "routes.py" in sast_workprogram.worker_payload(worker.id)["files"]
    )
    execute = scanner._make_tool_executor(
        run_id,
        root,
        None,
        initial_candidates=[],
        assigned_worker_id=route.id,
    )

    async def review():
        await execute("read_file", {"path": "routes.py"}, 1)
        await execute("read_file", {"path": "helpers/query.py"}, 2)
        result = await execute(
            "claim_traced_sink", {"path": "helpers/query.py", "line": 2}, 3
        )
        assert "Claimed sink" in result
        helper_items = [
            item
            for item in sast_workprogram.worker_payload(route.id)["work_items"]
            if item["work_type"] == "sink"
            and item["surface"]["path"] == "helpers/query.py"
        ]
        assert len(helper_items) == 1
        return await execute(
            "record_disposition",
            {
                "work_item_id": helper_items[0]["work_item_id"],
                "status": "safe",
                "reasoning": "The query uses a fixed statement.",
            },
            4,
        )

    assert "recorded as safe" in asyncio.run(review())
