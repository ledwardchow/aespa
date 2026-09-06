"""Integration checks for the framework-independent frontend fact adapter."""

from __future__ import annotations

from aespa.services.component_facts import extract_component_facts


def _facts(root, fact_type: str) -> list[dict]:
    return [
        fact for fact in extract_component_facts(root) if fact["fact_type"] == fact_type
    ]


def test_nested_request_wrappers_keep_template_path_and_source_evidence(tmp_path):
    source = tmp_path / "src" / "checkout.js"
    source.parent.mkdir()
    source.write_text(
        "const send = (method, path, body) => { return fetch(path, { method, body }); };\n"
        "const api = (method, path, body) => { return send(method, path, body); };\n"
        "export function submitOrder(order) {\n"
        "  return api('POST', `/api/orders/${order.id}`, order);\n"
        "}\n"
        "document.querySelector('#checkout').addEventListener('click', submitOrder);\n"
    )

    calls = _facts(tmp_path, "http_call")

    call = next(fact for fact in calls if fact["path"] == "/api/orders/{order.id}")
    assert call["method"] == "POST"
    assert call["detail"]["request_role"] == "browser_request"
    assert call["detail"]["frontend"] is True
    assert call["evidence_location"].startswith("src/checkout.js:")


def test_vanilla_react_vue_and_angular_bindings_are_browser_requests(tmp_path):
    (tmp_path / "vanilla.js").write_text(
        "document.querySelector('#profile').addEventListener('click', () => {\n"
        "  fetch('/api/profile');\n"
        "});\n"
    )
    (tmp_path / "Checkout.jsx").write_text(
        "function submitCheckout() { return fetch('/api/checkout', { method: 'POST' }); }\n"
        "export default () => <button onClick={submitCheckout}>Checkout</button>;\n"
    )
    (tmp_path / "Profile.vue").write_text(
        '<button @click="saveProfile">Save profile</button>\n'
        "<script>export default { methods: { saveProfile() { return fetch('/api/profile/save'); } } }</script>\n"
    )
    (tmp_path / "billing.ts").write_text(
        "@Component({ selector: 'billing-form' })\n"
        "saveInvoice() { return this.http.post('/api/invoices', this.invoice); }\n"
    )

    calls = _facts(tmp_path, "http_call")
    paths = {fact["path"] for fact in calls}
    assert {
        "/api/profile",
        "/api/checkout",
        "/api/profile/save",
        "/api/invoices",
    } <= paths
    assert all(fact["detail"]["request_role"] == "browser_request" for fact in calls)
    assert all(fact["evidence_location"] for fact in calls)


def test_unrelated_actions_remain_separate_frontend_facts(tmp_path):
    (tmp_path / "orders.jsx").write_text(
        "function loadOrder() { return fetch('/api/orders/42'); }\n"
        "function archiveOrder() { return fetch('/api/orders/42/archive', { method: 'POST' }); }\n"
        "export default () => <>\n"
        "  <button onClick={loadOrder}>Continue</button>\n"
        "  <button onClick={archiveOrder}>Continue</button>\n"
        "</>;\n"
    )

    actions = _facts(tmp_path, "ui_action")
    calls = _facts(tmp_path, "http_call")
    handlers = {fact["detail"].get("handler") for fact in actions}
    paths = {fact["path"] for fact in calls}

    assert {"loadOrder", "archiveOrder"} <= handlers
    assert {"/api/orders/42", "/api/orders/42/archive"} <= paths
    assert len([fact for fact in calls if fact["path"] == "/api/orders/42"]) == 1
    assert (
        len([fact for fact in calls if fact["path"] == "/api/orders/42/archive"]) == 1
    )


def test_repository_semantics_resolve_imported_request_wrapper_alias(tmp_path):
    (tmp_path / "api" / "request.js").parent.mkdir()
    (tmp_path / "api" / "request.js").write_text(
        "export function request(method, path, body) {\n"
        "  return fetch(path, { method, body });\n"
        "}\n"
    )
    (tmp_path / "Order.jsx").write_text(
        "import { request as sendRequest } from './api/request.js';\n"
        "function placeOrder(order) {\n"
        "  return sendRequest('POST', `/api/orders/${order.id}`, order);\n"
        "}\n"
        "export default () => <button onClick={placeOrder}>Place order</button>;\n"
    )

    calls = _facts(tmp_path, "http_call")
    call = next(fact for fact in calls if fact["path"] == "/api/orders/{order.id}")
    assert call["method"] == "POST"
    assert call["detail"]["request_role"] == "browser_request"
    assert "Order.jsx:2" in call["detail"]["handler_locations"]
    assert call["evidence_location"] == "api/request.js:2"


def test_repository_semantics_do_not_attach_an_unrelated_import_to_action(tmp_path):
    (tmp_path / "request.js").write_text(
        "export function request(method, path) {\n"
        "  return fetch(path, { method });\n"
        "}\n"
    )
    (tmp_path / "unrelated.js").write_text(
        "export function request(method, path) {\n"
        "  return fetch(path, { method });\n"
        "}\n"
    )
    (tmp_path / "Profile.jsx").write_text(
        "import { request as sendRequest } from './request.js';\n"
        "import { request as unusedRequest } from './unrelated.js';\n"
        "function loadProfile() {\n"
        "  return sendRequest('GET', '/api/profile');\n"
        "}\n"
        "export default () => <button onClick={loadProfile}>Load</button>;\n"
    )

    calls = _facts(tmp_path, "http_call")
    profile = next(fact for fact in calls if fact["path"] == "/api/profile")
    assert "Profile.jsx:3" in profile["detail"]["handler_locations"]
    assert all(
        not any(
            location.startswith("unrelated.js:")
            for location in fact["detail"]["handler_locations"]
        )
        for fact in calls
    )


def test_express_server_fetch_is_server_egress_and_has_no_ui_root(tmp_path):
    (tmp_path / "server.js").write_text(
        "const express = require('express');\n"
        "const app = express();\n"
        "app.post('/proxy', (req, res) => {\n"
        "  fetch('/internal/orders', { method: 'POST' });\n"
        "  res.sendStatus(204);\n"
        "});\n"
    )

    calls = _facts(tmp_path, "http_call")
    call = next(fact for fact in calls if fact["path"] == "/internal/orders")
    assert call["detail"]["request_role"] == "server_egress"
    assert not _facts(tmp_path, "ui_action")


def test_ambiguous_standalone_typescript_request_stays_conservative(tmp_path):
    (tmp_path / "request.ts").write_text(
        "export function load() {\n  return fetch('/api/health');\n}\n"
    )

    calls = _facts(tmp_path, "http_call")
    call = next(fact for fact in calls if fact["path"] == "/api/health")
    assert call["detail"]["request_role"] is None
    assert call["detail"]["frontend"] is False


def test_semantic_listener_does_not_keep_an_unlinked_button_duplicate(tmp_path):
    (tmp_path / "payment.js").write_text(
        "function pay() { return fetch('/api/payment', { method: 'POST' }); }\n"
        "view.innerHTML = '<button id=\"pay\">Pay now</button>';\n"
        "document.getElementById('pay').addEventListener('click', pay);\n"
    )

    actions = _facts(tmp_path, "ui_action")

    assert len(actions) == 1
    assert actions[0]["detail"]["handler"] == "pay"
    assert actions[0]["detail"]["label"] == "Pay now"
