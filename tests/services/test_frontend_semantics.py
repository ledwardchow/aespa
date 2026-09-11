from aespa.services.frontend_semantics import (
    extract_frontend_facts,
    extract_frontend_repository_facts,
)


def _facts(source: str, path: str = "src/checkout.tsx"):
    return extract_frontend_facts(source, path)


def test_infers_nested_request_wrapper_and_jsx_action_from_behavior():
    source = """
    function request(method, path, body) {
        const options = { method, body };
        return fetch(path, options);
    }
    function sendOrder() { return request("POST", `/api/orders/${orderId}`, formData); }
    <button onClick={sendOrder}>Place order</button>
    """

    facts = _facts(source)
    call = next(f for f in facts if f["fact_type"] == "http_call")
    action = next(f for f in facts if f["fact_type"] == "ui_action")

    assert (call["method"], call["path"]) == ("POST", "/api/orders/{orderId}")
    assert call["detail"]["request_role"] == "browser_request"
    assert action["detail"]["handler"] == "sendOrder"
    assert action["detail"]["handler_locations"] == ["src/checkout.tsx:6"]
    assert "src/checkout.tsx:2" in call["detail"]["supporting_locations"]


def test_resolves_vanilla_inline_listener_and_button_label():
    source = """
    <button id="buttonId">Human label</button>
    function handler(itemId) { return api.post(`/api/items/${itemId}`, payload); }
    document.getElementById("buttonId").addEventListener("click", () => handler(itemId));
    """

    facts = _facts(source, "src/items.js")
    action = next(f for f in facts if f["fact_type"] == "ui_action")
    call = next(f for f in facts if f["fact_type"] == "http_call")
    assert action["name"] == "Human label"
    assert action["detail"]["handler"] == "handler"
    assert (call["method"], call["path"]) == ("POST", "/api/items/{itemId}")


def test_resolves_submit_listener_callback():
    source = """
    function submitFunction() { return fetch("/api/submit", { method: "POST" }); }
    form.addEventListener("submit", event => {
        event.preventDefault();
        submitFunction();
    });
    """

    facts = _facts(source, "src/form.js")
    actions = [f for f in facts if f["fact_type"] == "ui_action"]
    calls = [f for f in facts if f["fact_type"] == "http_call"]
    assert len(actions) == 1
    assert actions[0]["detail"]["handler"] == "submitFunction"
    assert len(calls) == 1
    assert calls[0]["method"] == "POST"


def test_does_not_link_unrelated_action_and_call_in_same_file():
    source = """
    function deleteUser() { return fetch("/api/users/delete", { method: "DELETE" }); }
    function loadNews() { return fetch("/api/news", { method: "GET" }); }
    <button onClick={deleteUser}>Delete</button>
    <button onClick={loadNews}>News</button>
    """

    facts = _facts(source, "src/page.jsx")
    calls = [f for f in facts if f["fact_type"] == "http_call"]
    by_path = {f["path"]: f for f in calls}
    assert by_path["/api/users/delete"]["detail"]["handler_locations"] == [
        "src/page.jsx:2"
    ]
    assert by_path["/api/news"]["detail"]["handler_locations"] == ["src/page.jsx:3"]
    assert (
        "src/page.jsx:3"
        not in by_path["/api/users/delete"]["detail"]["handler_locations"]
    )


def test_expression_arrow_and_axios_request_are_supported():
    source = """
    const request = (method, path, body) => axios.request({ method, url: path, data: body });
    const save = () => request("PUT", "/api/profile", profile);
    <form onSubmit={save}>Save</form>
    """

    facts = _facts(source, "src/profile.tsx")
    call = next(f for f in facts if f["fact_type"] == "http_call")
    assert (call["method"], call["path"]) == ("PUT", "/api/profile")


def test_multiline_request_options_preserve_method_through_nested_wrapper():
    source = """
    function request(method, path, body) {
        const options = {
            method,
            body,
            credentials: "include",
        };
        return fetch(path, options);
    }
    function pay() { return request("POST", "/api/payment", payment); }
    button.addEventListener("click", pay);
    """

    facts = _facts(source, "src/payment.js")
    call = next(f for f in facts if f["fact_type"] == "http_call")
    assert (call["method"], call["path"]) == ("POST", "/api/payment")
    assert call["detail"]["handler_locations"] == ["src/payment.js:10"]


def test_event_callback_does_not_make_render_calls_synchronous():
    source = """
    function render() {
        navigateTo("/checkout");
        form.addEventListener("submit", event => {
            event.preventDefault();
            pay();
        });
    }
    function pay() { return fetch("/api/payment", { method: "POST" }); }
    function navigateTo(path) { return fetch(path, { method: "GET" }); }
    """

    facts = _facts(source, "src/app.js")
    calls = {f["path"]: f for f in facts if f["fact_type"] == "http_call"}
    assert calls["/api/payment"]["detail"]["handler_locations"] == ["src/app.js:9"]
    assert calls["/checkout"]["detail"]["handler_locations"] == ["src/app.js:2"]


def test_repository_import_resolves_renamed_es_module_helper():
    sources = {
        "src/request.js": """
        export function send(method, path, body) {
            return fetch(path, { method, body });
        }
        export function unrelated() { return fetch(dynamicUrl); }
        """,
        "src/checkout.tsx": """
        import { send as callApi } from "./request";
        function pay() { return callApi("POST", `/api/payment/${paymentId}`, form); }
        <button onClick={pay}>Pay</button>
        """,
    }

    facts = extract_frontend_repository_facts(sources)
    calls = [f for f in facts if f["fact_type"] == "http_call"]
    assert [(call["method"], call["path"]) for call in calls] == [
        ("POST", "/api/payment/{paymentId}")
    ]
    assert calls[0]["evidence_location"] == "src/request.js:3"
    assert calls[0]["detail"]["handler_locations"] == ["src/checkout.tsx:3"]
    assert "src/request.js:2" in calls[0]["detail"]["supporting_locations"]


def test_repository_import_resolves_commonjs_alias_without_unrelated_helper():
    sources = {
        "src/client.js": """
        function submit(method, path) { return fetch(path, { method }); }
        function unrelated() { return fetch("/api/unrelated", { method: "GET" }); }
        module.exports = { submit };
        """,
        "src/form.js": """
        const { submit: sendRequest } = require("./client");
        function save() { return sendRequest("POST", "/api/save"); }
        form.addEventListener("submit", save);
        """,
    }

    facts = extract_frontend_repository_facts(sources)
    calls = [f for f in facts if f["fact_type"] == "http_call"]
    save_call = next(call for call in calls if call["path"] == "/api/save")
    assert save_call["method"] == "POST"
    assert save_call["detail"]["handler_locations"] == ["src/form.js:3"]
    unrelated = next(call for call in calls if call["path"] == "/api/unrelated")
    assert "src/form.js:2" not in unrelated["detail"]["handler_locations"]


def test_inline_callback_gets_synthetic_handler_and_direct_request_evidence():
    facts = _facts(
        '<button onClick={() => fetch("/api/charge", { method: "POST" })}>Charge</button>',
        "src/charge.jsx",
    )
    action = next(f for f in facts if f["fact_type"] == "ui_action")
    call = next(f for f in facts if f["fact_type"] == "http_call")
    assert action["detail"]["handler"].startswith("__event_callback_")
    assert call["method"] == "POST"
    assert call["path"] == "/api/charge"
    assert call["detail"]["handler_locations"] == ["src/charge.jsx:1"]


def test_native_form_action_method_is_a_linked_submit_request():
    facts = _facts(
        '<form action="/api/checkout" method="post"><button>Pay</button></form>',
        "src/checkout.html",
    )
    action = next(f for f in facts if f["fact_type"] == "ui_action")
    call = next(f for f in facts if f["fact_type"] == "http_call")
    assert action["detail"]["trigger"] == "submit"
    assert call["method"] == "POST"
    assert call["path"] == "/api/checkout"
    assert call["detail"]["handler_locations"] == ["src/checkout.html:1"]


def test_vue_inline_named_handler_call_is_resolved():
    facts = _facts(
        '<button @click="save()">Save</button>\n'
        'function save() { return fetch("/api/save", { method: "POST" }); }',
        "src/Save.vue",
    )
    action = next(f for f in facts if f["fact_type"] == "ui_action")
    call = next(f for f in facts if f["fact_type"] == "http_call")
    assert action["detail"]["handler"] == "save"
    assert call["path"] == "/api/save"


def test_axios_create_base_url_is_applied_to_client_alias():
    facts = _facts(
        'const client = axios.create({ baseURL: "/api" });\n'
        'function load() { return client.get("/profile"); }\n'
        "<button onClick={load}>Load</button>",
        "src/profile.jsx",
    )
    call = next(f for f in facts if f["fact_type"] == "http_call")
    assert (call["method"], call["path"]) == ("GET", "/api/profile")


def test_imported_alias_does_not_overwrite_local_symbol():
    sources = {
        "src/helper.js": 'export function request() { return fetch("/api/helper"); }',
        "src/app.js": """
        import { request } from "./helper";
        function request() { return fetch("/api/local", { method: "POST" }); }
        function save() { return request(); }
        <button onClick={save}>Save</button>
        """,
    }
    calls = [
        f
        for f in extract_frontend_repository_facts(sources)
        if f["fact_type"] == "http_call"
    ]
    assert any(call["path"] == "/api/local" for call in calls)
    local = next(call for call in calls if call["path"] == "/api/local")
    assert local["detail"]["handler_locations"] == ["src/app.js:4"]


def test_multiple_routes_do_not_all_attach_to_one_action():
    facts = _facts(
        '<Route path="/home" element={<Home />} />\n'
        '<Route path="/checkout" element={<Checkout />} />\n'
        'function pay() { return fetch("/api/payment", { method: "POST" }); }\n'
        "<button onClick={pay}>Pay</button>",
        "src/routes.jsx",
    )
    action = next(f for f in facts if f["fact_type"] == "ui_action")
    assert "route_locations" not in action["detail"]


def test_parameterized_request_resolves_each_concrete_call_site_and_owner():
    source = """
    function request(method, path) { return fetch(path, { method }); }
    function submitQuote(product) {
        const path = `/api/quotes/${product}`;
        return request("POST", path);
    }
    function submitMotor() { return submitQuote("motor"); }
    function submitHome() { return submitQuote("home"); }
    function submitContents() { return submitQuote("contents"); }
    <button onClick={submitMotor}>Motor</button>
    <button onClick={submitHome}>Home</button>
    <button onClick={submitContents}>Contents</button>
    """

    calls = {
        fact["path"]: fact
        for fact in _facts(source, "src/quotes.jsx")
        if fact["fact_type"] == "http_call"
    }

    assert set(calls) == {
        "/api/quotes/motor",
        "/api/quotes/home",
        "/api/quotes/contents",
    }
    assert calls["/api/quotes/motor"]["detail"]["handler_locations"] == [
        "src/quotes.jsx:7"
    ]
    assert calls["/api/quotes/home"]["detail"]["handler_locations"] == [
        "src/quotes.jsx:8"
    ]
    assert calls["/api/quotes/contents"]["detail"]["handler_locations"] == [
        "src/quotes.jsx:9"
    ]


def test_async_event_callback_resolves_request_owner_past_validation_helper():
    source = """
    async function apiFull(method, path, body) {
        return fetch(path, { method, body });
    }
    function saveStep(form) { return form.checkValidity(); }
    async function submitMotorQuote() {
        return apiFull("POST", "/api/quotes/motor", motorQuotePayload());
    }
    function setup() {
        const form = document.getElementById("motorStepForm");
        form.addEventListener("submit", async event => {
            event.preventDefault();
            if (!saveStep(form)) return;
            submitMotorQuote();
        });
    }
    """

    facts = _facts(source, "static/js/app.js")
    actions = [fact for fact in facts if fact["fact_type"] == "ui_action"]
    handlers = [fact for fact in facts if fact["fact_type"] == "handler"]
    calls = [fact for fact in facts if fact["fact_type"] == "http_call"]

    assert [action["detail"]["handler"] for action in actions] == ["submitMotorQuote"]
    assert any(
        handler["name"] == "submitMotorQuote"
        and handler["evidence_location"] == "static/js/app.js:6"
        for handler in handlers
    )
    call = next(call for call in calls if call["path"] == "/api/quotes/motor")
    assert call["detail"]["handler_locations"] == ["static/js/app.js:6"]


def test_async_listener_does_not_emit_language_keywords_as_actions():
    facts = _facts(
        """
        form.addEventListener("submit", async event => {
            event.preventDefault();
            await saveForm();
        });
        function saveForm() { return fetch("/api/forms", { method: "POST" }); }
        """,
        "src/forms.js",
    )

    actions = [fact for fact in facts if fact["fact_type"] == "ui_action"]
    assert [action["detail"]["handler"] for action in actions] == ["saveForm"]


def test_state_property_request_resolves_dataset_variants():
    source = """
    <button data-product="motor">Motor</button>
    <button data-product="home">Home</button>
    <button data-product="contents">Contents</button>
    const quoteState = { product: null };
    buttons.forEach(button => button.addEventListener("click", () => {
        quoteState.product = button.dataset.product;
    }));
    async function submitQuote() {
        return fetch(`/api/quotes/${quoteState.product}`, { method: "POST" });
    }
    form.addEventListener("submit", submitQuote);
    """

    calls = [
        fact
        for fact in _facts(source, "src/quotes.js")
        if fact["fact_type"] == "http_call"
    ]

    assert {call["path"] for call in calls} == {
        "/api/quotes/motor",
        "/api/quotes/home",
        "/api/quotes/contents",
    }
    assert all(
        call["detail"]["handler_locations"] == ["src/quotes.js:9"] for call in calls
    )


def test_thymeleaf_form_action_is_normalized_to_route_template():
    facts = _facts(
        '<form th:action="@{/claims/{id}/disburse(id=${claim.id})}" method="post">'
        "<button>Disburse</button></form>",
        "templates/claims.html",
    )

    call = next(fact for fact in facts if fact["fact_type"] == "http_call")
    assert call["method"] == "POST"
    assert call["path"] == "/claims/{id}/disburse"


def test_dom_and_builtin_calls_are_not_reported_as_ui_handlers():
    source = """
    document.querySelectorAll("button").forEach(button => {
        button.addEventListener("click", () => {
            Number(button.dataset.id);
            button.closest("form").querySelectorAll("input");
        });
    });
    form.addEventListener("submit", event => {
        event.preventDefault();
        saveForm();
    });
    function saveForm() { return fetch("/api/forms", { method: "POST" }); }
    """

    actions = [
        fact
        for fact in _facts(source, "src/forms.js")
        if fact["fact_type"] == "ui_action"
    ]
    assert [action["detail"]["handler"] for action in actions] == ["saveForm"]


def test_partly_evaluated_javascript_expression_is_not_emitted_as_a_path():
    facts = _facts(
        """
        const product = policyType === 'MOTOR';
        function submit() {
            return fetch(`/api/quotes/${product}`, { method: "POST" });
        }
        <button onClick={submit}>Quote</button>
        """,
        "src/quotes.jsx",
    )

    paths = [
        fact["path"]
        for fact in facts
        if fact["fact_type"] == "http_call" and fact["path"]
    ]
    assert all("===" not in path and "'" not in path for path in paths)
