from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Callable
from urllib.parse import urlparse

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from sqlmodel import Session, select

from aespa.browser import (
    launch_playwright_browser,
    playwright_user_agent,
    protect_playwright_context,
)
from aespa.db import get_engine
from aespa.models import (
    AuthMode,
    CrawledPage,
    Credential,
    PageCredentialView,
    ScanLog,
    Site,
    TestRun,
)
from aespa.schemas import SiteWorkflowInput
from aespa.services import llm as llm_svc
from aespa.services import traffic as traffic_svc

log = logging.getLogger("aespa.crawl_workflows")

_MAX_WORKFLOWS = 4
_MAX_ACTIONS = 7
_MAX_RETRY_ACTIONS = 18
_MAX_DECISION_CORRECTIONS = 2
_MAX_SAME_FORM_ERROR = 2
_FIELD_SELECTOR = 'input:not([type="hidden"]),textarea,select'
_CONTROL_SELECTOR = 'a[href],button,input[type="submit"],[role="button"]'
_DELETE_ACTION = re.compile(r"\b(?:delete|remove|destroy|erase|purge)\b", re.I)
_PAYMENT_WORKFLOW = re.compile(
    r"\b(?:pay|payment|paying|checkout|purchase|charge|"
    r"(?:place|submit)\W+(?:an?\W+)?order|"
    r"(?:transfer\W+(?:money|funds)|(?:money|funds|account)\W+transfer)|"
    r"(?:credit|debit|payment)\W*card|card\W*(?:details|number|payment|method)|"
    r"bank[-_ ](?:transfer|details))\b",
    re.I,
)
_PAYMENT_ACTION = re.compile(
    r"\b(?:pay|payment|paying|charge|purchase|"
    r"(?:place|submit)\W+(?:an?\W+)?order|(?:credit|debit)\W*card|"
    r"card\W*(?:number|details)|bank\W*transfer)\b",
    re.I,
)
_PAYMENT_CONTEXT = re.compile(
    r"(?:^|[/_-])(?:payment|card|bank[-_]transfer)(?:[/_-]|$)",
    re.I,
)
_MISSING_DATA = re.compile(
    r"\b(?:no|none|without|missing|lack)\b.{0,150}"
    r"\b(?:provided|supplied|available|sample|details|data|invent|content)\b",
    re.IGNORECASE,
)
_SENSITIVE_SAMPLE_FIELD = re.compile(
    r"payment|card|cvc|cvv|security.?code|bank.?transfer|"
    r"bank.?details|"
    r"iban|routing|sort.?code|swift|bic\b|account.?number|"
    r"password|passcode|one.?time|otp|pin\b|api.?key|secret",
    re.IGNORECASE,
)
_PASSWORD_FIELD = re.compile(r"password", re.I)
_EXISTING_PASSWORD = re.compile(r"\b(?:current|old|existing)\W*password\b", re.I)
_NEW_PASSWORD = re.compile(
    r"\b(?:new|create|confirm|repeat)\W*password\b|\bpassword\W*confirm",
    re.I,
)
_REGISTRATION_PAGE = re.compile(
    r"\b(?:register|registration|sign.?up|create.?account|new.?account)\b",
    re.I,
)
_MAX_PARALLEL_WORKFLOWS = 3
# Workflow retries are keyed by (run_id, note_id) so several can run at once.
_retry_tasks: dict[tuple[int, int], asyncio.Task] = {}
_retry_results: dict[tuple[int, int], dict] = {}


def _is_payment_workflow(workflow: dict) -> bool:
    return bool(
        _PAYMENT_WORKFLOW.search(
            f"{workflow.get('name') or ''} {workflow.get('goal') or ''}"
        )
    )


def _can_generate_sample_data(workflow: dict) -> bool:
    return not workflow.get("destructive") and not _is_payment_workflow(workflow)


def _is_new_password_field(field: dict, observation: dict) -> bool:
    field_text = " ".join(
        str(field.get(key) or "") for key in ("name", "fieldName", "fieldId", "label")
    )
    field_text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", field_text).replace("_", "-")
    if not _PASSWORD_FIELD.search(field_text) or _EXISTING_PASSWORD.search(field_text):
        return False
    if _NEW_PASSWORD.search(field_text):
        return True
    page_text = " ".join(str(observation.get(key) or "") for key in ("url", "title"))
    return bool(_REGISTRATION_PAGE.search(page_text))


def _field_needs_supplied_secret(field: dict, observation: dict) -> bool:
    field_text = " ".join(
        str(field.get(key) or "") for key in ("name", "fieldName", "fieldId", "label")
    )
    return bool(_SENSITIVE_SAMPLE_FIELD.search(field_text)) and not (
        _is_new_password_field(field, observation)
    )


def _needs_user_input(note: dict) -> bool:
    if note.get("status") == "crawled":
        return False
    if "needs_input" in note:
        return note["needs_input"] is True
    return note.get("status") == "not_attempted" and bool(
        _MISSING_DATA.search(str(note.get("detail") or ""))
    )


def can_retry_workflow(note: dict) -> bool:
    return (
        isinstance(note.get("id"), int)
        and note.get("status") != "crawled"
        and not note.get("destructive")
        and not note.get("superseded")
        and not _DELETE_ACTION.search(
            f"{note.get('name') or ''} {note.get('goal') or ''}"
        )
        and "appears destructive" not in str(note.get("detail") or "").lower()
    )


def list_workflow_notes(session: Session, run_id: int) -> list[dict]:
    notes: list[dict] = []
    resolved_ids: set[int] = set()
    superseded_ids: set[int] = set()
    for row in session.exec(
        select(ScanLog)
        .where(ScanLog.test_run_id == run_id)
        .where(ScanLog.run_kind == "web")
        .where(ScanLog.phase == "crawl_note")
        .order_by(ScanLog.id)
    ):
        try:
            note = json.loads(row.data_json or "{}").get("note")
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(note, dict):
            continue
        note = {**note, "id": row.id, "needs_input": _needs_user_input(note)}
        notes.append(note)
        if note.get("status") == "crawled" and isinstance(note.get("retry_of"), int):
            resolved_ids.add(note["retry_of"])
        if isinstance(note.get("retry_of"), int):
            superseded_ids.add(note["retry_of"])
    for note in notes:
        if note["id"] in resolved_ids or note["id"] in superseded_ids:
            note["needs_input"] = False
            note["resolved"] = note["id"] in resolved_ids
            note["superseded"] = True
        note["retryable"] = can_retry_workflow(note)
    return notes


def _parse_json_object(raw: str) -> dict:
    try:
        parsed = llm_svc._extract_json(raw, expect=dict)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _crawl_inventory(run_id: int) -> tuple[list[dict], dict[str, CrawledPage]]:
    from aespa.services.crawler import _norm

    with Session(get_engine()) as session:
        pages = list(
            session.exec(
                select(CrawledPage)
                .where(CrawledPage.test_run_id == run_id)
                .where(CrawledPage.in_scope.is_(True))
                .where(CrawledPage.status == "crawled")
            )
        )
        for page in pages:
            session.expunge(page)
    pages.sort(
        key=lambda page: (
            not bool(page.has_business_logic or page.takes_input),
            page.depth,
            page.url,
        )
    )
    inventory: list[dict] = []
    seen_functions: set[tuple[str, str]] = set()
    for page in pages:
        parsed = urlparse(page.url)
        function = (page.state_label or page.title or "").strip().lower()
        key = (parsed.path.rsplit("/", 1)[0], function)
        if key in seen_functions and len(inventory) >= 20:
            continue
        seen_functions.add(key)
        page_text = " ".join((page.page_text or "").split())
        if len(page_text) > 1150:
            page_text = page_text[:180] + " ... " + page_text[-950:]
        try:
            replay = json.loads(page.replay_steps_json or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            replay = {}
        inventory.append(
            {
                "page_id": page.id,
                "url": page.url,
                "state_label": page.state_label,
                "state_kind": page.state_kind,
                "has_business_logic": bool(page.has_business_logic),
                "title": (page.title or "")[:100],
                "purpose": (page.llm_context or "")[:230],
                "text": page_text,
                "takes_input": bool(page.takes_input),
                "reached_from": (
                    replay.get("root_url") if isinstance(replay, dict) else None
                ),
                "actions_to_reach": (
                    [
                        step.get("name") or step.get("selector")
                        for step in replay.get("steps", [])[:_MAX_ACTIONS]
                        if isinstance(step, dict)
                    ]
                    if isinstance(replay, dict)
                    else []
                ),
            }
        )
        if len(inventory) >= 80:
            break
    known_pages: dict[str, CrawledPage] = {}
    for page in pages:
        key = _norm(page.url)
        if key not in known_pages or known_pages[key].state_kind == "interactive":
            known_pages[key] = page
    return inventory, known_pages


def _historical_credential_usernames(run_id: int) -> dict[int, set[str]]:
    usernames: dict[int, set[str]] = {}
    with Session(get_engine()) as session:
        views = session.exec(
            select(PageCredentialView.credential_id, PageCredentialView.username).where(
                PageCredentialView.test_run_id == run_id
            )
        )
        for credential_id, username in views:
            if credential_id is not None and username:
                usernames.setdefault(credential_id, set()).add(username)
    return usernames


def _workflow_credential(
    start_page: CrawledPage | None,
    creds: list[Credential],
    historical_usernames: dict[int, set[str]],
) -> tuple[Credential | None, bool]:
    if start_page is None:
        return (creds[0] if creds else None), bool(creds)
    candidate_ids = []
    if start_page.replay_credential_id is not None:
        candidate_ids.append(start_page.replay_credential_id)
    try:
        candidate_ids.extend(json.loads(start_page.accessible_by or "[]"))
    except (TypeError, ValueError, json.JSONDecodeError):
        pass
    candidate_ids = list(
        dict.fromkeys(cid for cid in candidate_ids if isinstance(cid, int))
    )
    current_by_id = {cred.id: cred for cred in creds}
    current_by_username: dict[str, list[Credential]] = {}
    for cred in creds:
        current_by_username.setdefault(cred.username, []).append(cred)
    for old_id in candidate_ids:
        if old_id in current_by_id:
            return current_by_id[old_id], True
        old_names = historical_usernames.get(old_id, set())
        if len(old_names) == 1:
            matches = current_by_username.get(next(iter(old_names)), [])
            if len(matches) == 1:
                return matches[0], True
    return None, bool(candidate_ids or start_page.req_auth)


def _workflow_identity(workflow: dict) -> tuple[str, str, str]:
    from aespa.services.crawler import _norm

    return (
        str(workflow.get("name") or "").strip().casefold(),
        _norm(str(workflow.get("start_url") or "")),
        str(workflow.get("goal") or "").strip().casefold(),
    )


def _prior_workflow_identities(run_id: int) -> set[tuple[str, str, str]]:
    with Session(get_engine()) as session:
        rows = session.exec(
            select(ScanLog.data_json)
            .where(ScanLog.test_run_id == run_id)
            .where(ScanLog.run_kind == "web")
            .where(ScanLog.phase == "crawl_note")
        )
        identities = set()
        for data_json in rows:
            try:
                note = json.loads(data_json or "{}").get("note", {})
            except (TypeError, ValueError, json.JSONDecodeError, AttributeError):
                continue
            if isinstance(note, dict) and isinstance(note.get("name"), str):
                identities.add(_workflow_identity(note))
        return identities


def _saved_workflow_proposals(site: Site) -> list[dict]:
    from aespa.services.crawler import _same_domain
    from aespa.services.sites import workflow_data_for_site

    base_netloc = urlparse(site.base_url).netloc
    proposals = []
    for raw in workflow_data_for_site(site):
        try:
            saved = SiteWorkflowInput.model_validate(raw)
        except ValueError:
            continue
        start_url = str(saved.start_url)
        if not _same_domain(start_url, base_netloc):
            continue
        workflow = {
            "name": saved.name,
            "goal": saved.goal,
            "start_url": start_url,
            "reason": "Saved workflow data for this site.",
            "destructive": bool(_DELETE_ACTION.search(f"{saved.name} {saved.goal}")),
            "user_instructions": saved.instructions,
            "saved_site_data": True,
        }
        workflow["generate_sample_data"] = _can_generate_sample_data(workflow)
        proposals.append(workflow)
    return proposals


async def _infer_workflows(
    llm_cfg,
    inventory: list[dict],
    known_urls: set[str],
    prior_identities: set[tuple[str, str, str]] | None = None,
) -> list[dict]:
    from aespa.services.crawler import _norm

    prompt = (
        "You are reviewing a completed web crawl. Identify user actions with a "
        "specific goal, such as submitting a review or changing an address. "
        "Do not list ordinary pages, page titles, reading content, or navigation "
        "as workflows. Include a reached action only when its goal was observed, "
        "even when several actions share a URL. For a reached action, set "
        "reached_page_id to its page_id only "
        "when the goal is already visible in that page's observations. If further "
        "actions are needed to reach the goal, it has not been reached. "
        "For an unreached workflow, set reached_page_id to null. Use only the page observations "
        "below. Look past setup actions to a specific user goal they may unlock. "
        "For example, adding an item can be a step toward placing an order. "
        "A workflow can require state changes such as adding "
        "an item, saving a draft, or submitting a review. "
        "An interactive page with reached_from requires its recorded actions; "
        "choose reached_from as start_url if you need to reproduce that state. "
        "Do not repeat these already noted workflows: "
        f"{json.dumps(sorted(prior_identities or set()))}. Each entry contains its name, "
        "starting URL, and goal. Do not invent a URL or claim "
        "that an unseen page definitely exists. Pick an observed start_url. Mark a "
        "workflow destructive only if reaching it requires deleting or removing "
        "something. Other state changes, including submitting reviews and placing "
        "orders, are allowed. "
        'Return only JSON: {"workflows":[{"name":"...","start_url":"...",'
        '"goal":"...","reason":"visible evidence","reached_page_id":null,'
        '"destructive":false}]}. Return an empty array if there is no evidence.\n'
        + json.dumps(inventory, ensure_ascii=False)
    )
    result = _parse_json_object(await llm_svc.plain_completion(llm_cfg, prompt))
    workflows = result.get("workflows")
    if not isinstance(workflows, list):
        raise ValueError("The workflow model did not return a workflow list")
    proposals: list[dict] = []
    seen: set[str] = set()
    page_ids = {
        page["page_id"] for page in inventory if isinstance(page.get("page_id"), int)
    }
    for raw in workflows:
        if not isinstance(raw, dict):
            continue
        start_url = str(raw.get("start_url") or "")
        name = " ".join(str(raw.get("name") or "").split())[:100]
        goal = " ".join(str(raw.get("goal") or "").split())[:220]
        reason = " ".join(str(raw.get("reason") or "").split())[:360]
        if not name or not goal or not reason or _norm(start_url) not in known_urls:
            continue
        page_id = raw.get("reached_page_id")
        if page_id is not None and (
            type(page_id) is not int or page_id not in page_ids
        ):
            continue
        key = (
            f"page:{page_id}:{name.casefold()}:{goal.casefold()}"
            if page_id is not None
            else f"unreached:{name.casefold()}:{_norm(start_url)}:{goal.casefold()}"
        )
        if key in seen or (
            page_id is None
            and _workflow_identity({"name": name, "start_url": start_url, "goal": goal})
            in (prior_identities or set())
        ):
            continue
        seen.add(key)
        workflow = {
            "name": name,
            "start_url": start_url,
            "goal": goal,
            "reason": reason,
            "reached_page_id": page_id,
            "inferred": True,
            "destructive": bool(
                _DELETE_ACTION.search(f"{name} {goal}")
                or (raw.get("destructive") and _DELETE_ACTION.search(reason))
            ),
        }
        workflow["generate_sample_data"] = _can_generate_sample_data(workflow)
        proposals.append(workflow)
    return proposals


async def _observe(page) -> dict:
    return await page.evaluate(
        """() => {
          const visible = el => {
            const rect = el.getBoundingClientRect();
            const style = getComputedStyle(el);
            return rect.width > 0 && rect.height > 0 && !el.disabled
              && style.display !== 'none' && style.visibility !== 'hidden';
          };
          const label = el => (el.getAttribute('aria-label') || el.innerText
            || el.textContent || el.getAttribute('name') || el.value || '')
            .replace(/\\s+/g, ' ').trim().slice(0, 100);
          const formContext = el => {
            const form = el.form || el.closest('form');
            if (!form) return '';
            const copy = form.cloneNode(true);
            copy.querySelectorAll('button,input[type="submit"],input[type="button"],a[href],[role="button"]')
              .forEach(control => control.remove());
            return (copy.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 180);
          };
          return {
            url: location.href,
            title: document.title,
            text: (document.body?.innerText || '').slice(0, 3200),
            controls: Array.from(document.querySelectorAll(
              'a[href],button,input[type="submit"],[role="button"]'))
              .map((el, domIndex) => ({el, domIndex})).filter(({el}) => visible(el))
              .slice(0, 60).map(({el, domIndex}, index) => ({
                index, domIndex, name: label(el),
                kind: el.tagName.toLowerCase() === 'a' ? 'link' : 'button',
                submits: el.tagName.toLowerCase() !== 'a' &&
                  (el.type === 'submit' ||
                   (el.tagName.toLowerCase() === 'button' && !el.type)),
                href: el.tagName.toLowerCase() === 'a' ? el.href : '',
                rawHref: el.tagName.toLowerCase() === 'a' ? el.getAttribute('href') : '',
                form: formContext(el),
                formAction: el.getAttribute('formaction') ||
                  (el.form || el.closest('form'))?.getAttribute('action') || ''
              })),
            fields: Array.from(document.querySelectorAll(
              'input:not([type="hidden"]),textarea,select'))
              .map((el, domIndex) => ({el, domIndex})).filter(({el}) => visible(el))
              .slice(0, 30).map(({el, domIndex}, index) => ({
                index, domIndex, name: el.name || el.id || label(el),
                fieldName: el.name || '', fieldId: el.id || '',
                type: (el.type || el.tagName).toLowerCase(),
                label: (el.labels?.[0]?.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 100),
                has_value: el.type === 'radio' || el.type === 'checkbox'
                  ? el.checked : Boolean(el.value?.trim()),
                checked: Boolean(el.checked),
                choice_value: el.type === 'radio' ? el.value : '',
                selected_value: el.tagName === 'SELECT' ? el.value : '',
                invalid: !el.validity?.valid || el.getAttribute('aria-invalid') === 'true',
                value_limit: el.tagName === 'TEXTAREA'
                  ? Math.min(el.maxLength > 0 ? el.maxLength : 2000, 2000)
                  : Math.min(el.maxLength > 0 ? el.maxLength : 100, 100),
                options: el.tagName === 'SELECT'
                  ? Array.from(el.options).filter(o => !o.disabled).slice(0, 12)
                    .map(o => ({value:o.value, label:o.textContent?.trim()})) : []
              })),
            validation_errors: Array.from(document.querySelectorAll(
              'input:invalid,textarea:invalid,select:invalid,' +
              'input[aria-invalid="true"],textarea[aria-invalid="true"],' +
              'select[aria-invalid="true"]'))
              .filter((el, index, all) => all.indexOf(el) === index && visible(el))
              .slice(0, 8).map(el => ({
                field: (el.getAttribute('aria-label') || el.labels?.[0]?.textContent ||
                  el.name || el.id || 'field').replace(/\\s+/g, ' ').trim().slice(0, 80),
                message: (el.validationMessage ||
                  document.getElementById(el.getAttribute('aria-describedby'))?.textContent ||
                  el.closest('form')?.querySelector('[role="alert"]')?.textContent || '')
                  .replace(/\\s+/g, ' ').trim().slice(0, 160),
                has_value: Boolean(el.value?.trim())
              })),
            form_errors: Array.from(document.querySelectorAll(
              'form [role="alert"],form [aria-live="assertive"],form .field-error,' +
              'form .form-error,form [data-error]'))
              .filter(visible).map(el => (el.innerText || el.textContent || '')
                .replace(/\\s+/g, ' ').trim().slice(0, 160))
              .filter(Boolean).slice(0, 5)
          };
        }"""
    )


async def _decide_action(
    llm_cfg, workflow: dict, observation: dict, history: list[str]
) -> dict:
    sample_data_rule = (
        "Generate missing ordinary sample values for this workflow. Use clearly "
        "fictitious test names, addresses, emails, and phone "
        "numbers where needed. Keep provided values unchanged. Do not generate "
        "payment card or bank details, existing passwords, one-time codes, "
        "API keys, or other secrets. A new password for a test account may be "
        "generated. Reuse that value for its confirmation field. "
        if workflow.get("generate_sample_data")
        else "Use only sample data or instructions supplied for this workflow; "
        "do not invent names, addresses, card details, or review text. "
    )
    prompt = (
        "You are a web crawler trying to reach a workflow suggested by the earlier "
        "crawl. Choose one action from the current visible controls or fields. "
        "You may click a control, fill a text field, select a dropdown option, "
        "check a radio choice, declare reached, or stop. Click indexes refer "
        "to controls. Fill, select, and check indexes refer to fields. For a "
        "radio group, choose the field index with the desired choice_value and "
        "use action=check. Use only supplied indexes, options, and URLs. "
        "Do not delete or remove anything. "
        "Other state changes, including submitting reviews and placing orders, "
        "are allowed. Stop if the next action would delete something. "
        + sample_data_rule
        + "If required data is missing and cannot be generated under the rule "
        "above, stop with needs_input=true and state what to ask for in "
        "request. If the site rejects a value explicitly supplied by the user, "
        "stop with needs_input=true and explain which value to correct. "
        "Keep each proposed value within its field's value_limit. Fields expose has_value "
        "and checked but omit text values for privacy. Do not refill a field "
        "that already has a valid value or repeat a completed action. "
        "Use visible validation messages when available. After a form rejects "
        "generated data, correct the affected field even if it still has a value. "
        "Keep values supplied by the user unchanged. Do not repeat "
        "supplied values in reason or evidence. Adding an "
        "item to a cart is a setup action. "
        "Return only JSON with action, index, value, reason, evidence, "
        "needs_input, and request. "
        "Use action=reached only when the "
        "current page visibly shows the goal; evidence must be an exact short "
        "substring of the current URL, title, or page text.\n"
        f"Workflow: {json.dumps(workflow, ensure_ascii=False)}\n"
        f"Actions so far: {json.dumps(history[-_MAX_ACTIONS:])}\n"
        f"Current page: {json.dumps(observation, ensure_ascii=False)}"
    )
    return _parse_json_object(await llm_svc.plain_completion(llm_cfg, prompt))


async def _decide_with_corrections(
    llm_cfg,
    workflow: dict,
    observation: dict,
    history: list[str],
    prior_actions: set[tuple[str, str, str, str]] | None = None,
) -> dict:
    decision = await _decide_action(llm_cfg, workflow, observation, history)
    for _ in range(_MAX_DECISION_CORRECTIONS):
        if decision.get("action") == "stop":
            request_text = " ".join(
                str(decision.get(key) or "") for key in ("request", "reason")
            )
            if not (
                workflow.get("generate_sample_data")
                and decision.get("needs_input") is True
                and re.search(
                    r"\b(?:missing|provide|supply|need|required)\b",
                    request_text,
                    re.I,
                )
                and (
                    not _SENSITIVE_SAMPLE_FIELD.search(request_text)
                    or (
                        _PASSWORD_FIELD.search(request_text)
                        and any(
                            _is_new_password_field(field, observation)
                            for field in observation.get("fields", [])
                        )
                        and not _SENSITIVE_SAMPLE_FIELD.search(
                            _PASSWORD_FIELD.sub("", request_text)
                        )
                    )
                )
                and (
                    not _invalid_supplied_input(observation)
                    or observation.get("form_errors")
                )
            ):
                break
            feedback = (
                "Generate ordinary test values for missing fields. Choose the "
                "next form action instead of asking "
                "for those values."
            )
        else:
            allowed, why = _action_allowed(
                decision,
                observation,
                workflow.get("user_instructions") or "",
                generate_sample_data=bool(workflow.get("generate_sample_data")),
                prior_actions=prior_actions,
            )
            if allowed or why not in {
                "The proposed field value is too long.",
                "Use check to choose a radio option.",
                "The chosen option was not visible.",
                "This field already has that value.",
            }:
                break
            feedback = {
                "The proposed field value is too long.": (
                    "That field value exceeded its value_limit. "
                    "Choose a shorter value for the same field."
                ),
                "Use check to choose a radio option.": (
                    "Radio choices use action=check and a field index, not select."
                ),
                "The chosen option was not visible.": (
                    "Choose an option value from the selected field's visible options."
                ),
                "This field already has that value.": (
                    "That field already has the value you set. Choose an unfinished "
                    "field or submit the form."
                ),
            }[why]
        decision = await _decide_action(
            llm_cfg, workflow, observation, [*history, feedback]
        )
    return decision


def _invalid_supplied_input(observation: dict) -> str:
    errors = [
        error
        for error in observation.get("validation_errors", [])
        if error.get("has_value")
    ]
    if errors:
        first = errors[0]
        field = str(first.get("field") or "field")[:80]
        message = str(first.get("message") or "The value was rejected.")[:160]
        return f"Check the {field} value: {message}"
    form_errors = observation.get("form_errors") or []
    if form_errors:
        return f"Check the form data: {str(form_errors[0])[:160]}"
    return ""


def _submission_validation_action(
    observation: dict, *, generate_sample_data: bool, seen_errors: dict[str, int]
) -> tuple[str, str]:
    request = _invalid_supplied_input(observation)
    if not request:
        return "ok", ""
    if not generate_sample_data:
        return "needs_input", request
    seen_errors[request] = seen_errors.get(request, 0) + 1
    if seen_errors[request] >= _MAX_SAME_FORM_ERROR:
        return "needs_input", request
    return "retry", request


def _plain_words(text: str) -> str:
    return " ".join(re.sub(r"[\W_]+", " ", text.casefold()).split())


def _radio_choice_supplied(item: dict, instructions: str) -> bool:
    """Whether the instructions name this radio option by its value or label."""
    value = str(item.get("choice_value") or "")
    if value and value.casefold() in " ".join(instructions.split()).casefold():
        return True
    supplied = f" {_plain_words(instructions)} "
    label = str(item.get("label") or "")
    # A label such as "Bank transfer - pay after placing the order" can be
    # mentioned by its leading phrase, e.g. "Pay by bank transfer".
    phrases = {
        _plain_words(value),
        _plain_words(label),
        _plain_words(re.split(r"\s[-\u2013\u2014:|(]|[(:|,]", label, maxsplit=1)[0]),
    }
    return any(len(phrase) >= 3 and f" {phrase} " in supplied for phrase in phrases)


def _field_display_name(item: dict) -> str:
    return str(
        item.get("label") or item.get("fieldName") or item.get("fieldId") or "field"
    )[:80]


def _input_request(why: str, decision: dict, observation: dict) -> str:
    """Name the exact field or option that needs a value from the user."""
    try:
        item = observation["fields"][int(decision.get("index"))]
    except (IndexError, KeyError, TypeError, ValueError):
        return "Provide the sample values needed for this form."
    if decision.get("action") == "check":
        option = _field_display_name(item)
        others = [
            _field_display_name(field)
            for field in observation["fields"]
            if field is not item
            and field.get("type") == "radio"
            and field.get("fieldName")
            and field.get("fieldName") == item.get("fieldName")
        ]
        request = f'Name the option to choose, such as "{option}".'
        if others:
            request += " Other options: " + ", ".join(f'"{o}"' for o in others) + "."
        return request
    field = _field_display_name(item)
    if why.startswith("Payment or secret"):
        return f'Provide a test value for the "{field}" payment or secret field.'
    return f'Provide a sample value for the "{field}" field.'


def _field_action_key(decision: dict, observation: dict) -> tuple[str, str, str, str]:
    item = observation["fields"][int(decision["index"])]
    value = (
        item.get("choice_value")
        if decision["action"] == "check"
        else decision.get("value")
    )
    return (
        str(observation.get("url") or ""),
        str(item.get("fieldId") or item.get("fieldName") or ""),
        str(decision["action"]),
        str(value or ""),
    )


def _action_allowed(
    decision: dict,
    observation: dict,
    user_instructions: str = "",
    *,
    generate_sample_data: bool = False,
    prior_actions: set[tuple[str, str, str, str]] | None = None,
) -> tuple[bool, str]:
    action = decision.get("action")
    if action not in {"click", "fill", "select", "check"}:
        return False, "The model did not choose a browser action."
    group = "controls" if action == "click" else "fields"
    try:
        item = observation[group][int(decision.get("index"))]
    except (IndexError, TypeError, ValueError):
        return False, "The chosen control was not visible."
    if action == "click":
        if not item.get("name"):
            return False, "The chosen control could not be identified uniquely."
        if sum(
            control.get("kind") == item.get("kind")
            and control.get("name") == item.get("name")
            for control in observation["controls"]
        ) != 1 and not isinstance(item.get("domIndex"), int):
            return False, "The chosen control could not be identified uniquely."
        direct_action = " ".join(
            str(item.get(key) or "") for key in ("name", "href", "formAction", "form")
        )
        direct_action = re.sub(r"[-_/]+", " ", direct_action)
        if _DELETE_ACTION.search(direct_action):
            return False, "The next action would delete something."
        if _PAYMENT_ACTION.search(direct_action):
            supplied_payment = bool(user_instructions.strip()) and (
                not generate_sample_data
                or bool(_PAYMENT_ACTION.search(user_instructions))
            )
            if not supplied_payment:
                return False, "Payment steps need user-supplied test data."
        href = item.get("href") or ""
        if href and urlparse(href).netloc != urlparse(observation["url"]).netloc:
            return False, "The next action leaves the target site."
    else:
        field_type = str(item.get("type") or "")
        payment_context = bool(
            _PAYMENT_CONTEXT.search(urlparse(observation.get("url") or "").path)
        )
        if action in {"fill", "select"} and field_type == "radio":
            return False, "Use check to choose a radio option."
        if action == "check":
            if field_type != "radio" or not item.get("choice_value"):
                return False, "The chosen field is not a radio option."
            if decision.get("value") not in (None, "") and str(
                decision["value"]
            ) != str(item["choice_value"]):
                return False, "The chosen radio value did not match the field."
            radio_supplied = _radio_choice_supplied(item, user_instructions)
            if not radio_supplied and not generate_sample_data:
                return False, "The field needs a value supplied by the user."
        if action == "fill":
            value = " ".join(str(decision.get("value") or "").split())
            supplied = " ".join(user_instructions.split())
            if not value:
                return False, "The field needs a value."
            if value.casefold() not in supplied.casefold() and not generate_sample_data:
                return False, "The field needs a value supplied by the user."
            if value.casefold() not in supplied.casefold() and (
                payment_context or _field_needs_supplied_secret(item, observation)
            ):
                return False, "Payment or secret fields need user-supplied test data."
        if (
            action == "check"
            and not radio_supplied
            and (payment_context or _field_needs_supplied_secret(item, observation))
        ):
            return False, "Payment or secret fields need user-supplied test data."
        if (
            action == "select"
            and (payment_context or _field_needs_supplied_secret(item, observation))
            and str(decision.get("value") or "").casefold()
            not in user_instructions.casefold()
        ):
            return False, "Payment or secret fields need user-supplied test data."
        if not item.get("fieldName") and not item.get("fieldId"):
            return False, "The chosen field has no stable identifier."
        if item.get("type") == "file":
            return False, "The field needs a file upload."
        value_limit = item.get("value_limit") or (
            2000 if field_type == "textarea" else 100
        )
        if (
            action in {"fill", "select"}
            and len(str(decision.get("value") or "")) > value_limit
        ):
            return False, "The proposed field value is too long."
        if action == "select" and field_type not in {"select-one", "select-multiple"}:
            return False, "The chosen field is not a dropdown."
        if action == "select" and str(decision.get("value")) not in {
            str(option.get("value")) for option in item.get("options") or []
        }:
            return False, "The chosen option was not visible."
        if prior_actions and _field_action_key(decision, observation) in prior_actions:
            if action == "check" and item.get("checked"):
                return False, "This field already has that value."
            if action == "select" and str(item.get("selected_value")) == str(
                decision.get("value")
            ):
                return False, "This field already has that value."
            if action == "fill" and item.get("has_value") and not item.get("invalid"):
                return False, "This field already has that value."
    return True, ""


async def _block_delete_request(route) -> None:
    request = route.request
    path = urlparse(request.url).path.replace("-", "_")
    if request.method.upper() == "DELETE" or _DELETE_ACTION.search(
        path.replace("_", " ")
    ):
        await route.abort()
    else:
        await route.continue_()


def _instructions_with_generated_values(workflow: dict) -> str:
    instructions = str(workflow.get("user_instructions") or "").strip()
    generated = workflow.get("generated_values") or []
    if not generated:
        return instructions
    lines = [f"{item['field']}: {item['value']}" for item in generated]
    return "\n".join(filter(None, [instructions, "Generated test values:", *lines]))[
        :4000
    ]


def _remember_generated_value(
    workflow: dict, decision: dict, observation: dict
) -> None:
    if not workflow.get("generate_sample_data") or decision.get("action") not in {
        "fill",
        "select",
        "check",
    }:
        return
    field = observation["fields"][int(decision["index"])]
    value = str(
        field.get("choice_value")
        if decision["action"] == "check"
        else decision.get("value") or ""
    ).strip()
    supplied = str(workflow.get("user_instructions") or "")
    if not value or value.casefold() in supplied.casefold():
        return
    field_name = str(
        field.get("name") or field.get("fieldName") or field.get("fieldId") or "field"
    )[:100]
    generated = workflow.setdefault("generated_values", [])
    generated[:] = [item for item in generated if item["field"] != field_name]
    generated.append({"field": field_name, "value": value})


async def _apply_action(page, decision: dict, observation: dict) -> dict:
    action = decision["action"]
    group = "controls" if action == "click" else "fields"
    item = observation[group][int(decision["index"])]
    if action == "click":
        if isinstance(item.get("domIndex"), int):
            locator = page.locator(_CONTROL_SELECTOR).nth(item["domIndex"])
            matches = await locator.evaluate(
                """(el, expected) => {
                  const name = (el.getAttribute('aria-label') || el.innerText
                    || el.textContent || el.getAttribute('name') || el.value || '')
                    .replace(/\\s+/g, ' ').trim().slice(0, 100);
                  const kind = el.tagName.toLowerCase() === 'a' ? 'link' : 'button';
                  return name === expected.name && kind === expected.kind
                    && (kind !== 'link' || el.href === expected.href);
                }""",
                {"name": item["name"], "kind": item["kind"], "href": item.get("href")},
            )
            if not matches:
                raise ValueError(
                    "The chosen page control changed before it could be clicked."
                )
            await locator.click(timeout=8000)
        elif item.get("kind") == "link" and item.get("rawHref"):
            await page.locator(
                f"a[href={json.dumps(item['rawHref'])}]:visible"
            ).first.click(timeout=8000)
        else:
            await page.get_by_role(
                item["kind"], name=item["name"], exact=True
            ).first.click(timeout=8000)
        return {"kind": "click", "role": item["kind"], "name": item["name"]}
    if item.get("fieldName"):
        selector = f"[name={json.dumps(item['fieldName'])}]"
        if action == "check":
            selector += f"[value={json.dumps(item['choice_value'])}]"
        locator = page.locator(f"{selector}:visible").first
    elif item.get("fieldId"):
        selector = f"[id={json.dumps(item['fieldId'])}]"
        locator = page.locator(f"{selector}:visible").first
    else:
        selector = ""
        locator = page.locator(_FIELD_SELECTOR).nth(item["domIndex"])
    if action == "check":
        await locator.check(force=True, timeout=8000)
    elif action == "fill":
        value = str(decision.get("value") or "")
        try:
            await locator.fill(value, timeout=8000)
        except PlaywrightTimeoutError:
            filled = await page.evaluate(
                """({selector, value}) => {
                  const matches = Array.from(document.querySelectorAll(selector))
                    .filter(el => {
                      const rect = el.getBoundingClientRect();
                      const style = getComputedStyle(el);
                      return rect.width > 0 && rect.height > 0 && !el.disabled
                        && !el.readOnly && style.display !== 'none'
                        && style.visibility !== 'hidden'
                        && (el instanceof HTMLInputElement
                          || el instanceof HTMLTextAreaElement);
                    });
                  if (matches.length !== 1) return false;
                  const field = matches[0];
                  const prototype = field instanceof HTMLTextAreaElement
                    ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
                  Object.getOwnPropertyDescriptor(prototype, 'value').set.call(field, value);
                  field.dispatchEvent(new Event('input', {bubbles: true}));
                  field.dispatchEvent(new Event('change', {bubbles: true}));
                  return field.value === value;
                }""",
                {"selector": selector, "value": value},
            )
            if not filled:
                raise
    else:
        await locator.select_option(str(decision["value"]), timeout=8000)
    return {
        "kind": "select_option" if action == "select" else action,
        "selector": selector,
        "value": str(
            item.get("choice_value")
            if action == "check"
            else decision.get("value") or ""
        ),
    }


async def _save_discovered_page(
    *,
    run_id: int,
    page,
    root_url: str,
    steps: list[dict],
    parent_id: int | None,
    credential_id: int | None,
    username: str,
    shared,
    max_pages: int,
    llm_cfg,
) -> int | None:
    from aespa.services.crawler import (
        _interactive_state_snapshot,
        _norm,
        _page_function_label,
        _record_page_intelligence,
        _save_credential_view,
        _save_link,
        _save_page_placeholder,
        _update_accessible_by,
        _update_page,
        _update_run,
    )

    url = page.url
    state = None
    if steps:
        state = await _interactive_state_snapshot(page, capture_screenshot=False)
    async with shared.lock:
        existing_id = shared.crawled_norms.get(_norm(url))
        state_key = state.get("key") if state else None
        if state_key and state_key in shared.state_keys:
            return shared.state_keys[state_key]
        if existing_id is not None and not state_key:
            return existing_id
        if shared.pages_done >= max_pages:
            return None
        page_id = _save_page_placeholder(run_id, url, len(steps))
        if existing_id is None:
            shared.crawled_norms[_norm(url)] = page_id
        if state_key:
            shared.state_keys[state_key] = page_id
        shared.pages_done += 1
    title = await page.title()
    try:
        body = await page.evaluate("() => document.body?.innerText || ''")
    except Exception:
        body = ""
    try:
        context, _suggested, categories = await llm_svc.analyse_page(
            llm_cfg, url, title, body[:8000]
        )
    except Exception as exc:
        log.warning("Could not analyze workflow page %s: %s", url, exc)
        context, categories = "Workflow page reached; analysis unavailable.", {}
    try:
        raw_links = await page.evaluate(
            """() => Array.from(document.querySelectorAll('a[href]')).map(a => ({
              href: a.href, text: (a.textContent || '').trim().slice(0, 80)
            }))"""
        )
        await _record_page_intelligence(
            run_id=run_id,
            page=page,
            page_url=url,
            text=body,
            raw_links=raw_links,
            base_netloc=urlparse(root_url).netloc,
            username=username,
            js_endpoint_discovery_enabled=False,
            extra_scripts=[],
            shared=shared,
        )
    except Exception as exc:
        log.debug("Could not collect workflow page inputs for %s: %s", url, exc)
    _update_page(
        page_id,
        title=title,
        page_text=body[:10_000],
        llm_context=context,
        state_label=_page_function_label(categories.get("page_label")),
        state_key=state_key,
        status="crawled",
        state_kind="interactive",
        replay_steps_json=json.dumps({"root_url": root_url, "steps": steps}),
        replay_credential_id=credential_id,
        req_auth=categories.get("req_auth"),
        takes_input=categories.get("takes_input"),
        has_object_ref=categories.get("has_object_ref"),
        has_business_logic=categories.get("has_business_logic"),
        owasp_applicable_json=json.dumps(categories.get("owasp_applicable") or {}),
    )
    _save_credential_view(
        page_id,
        run_id,
        credential_id,
        username,
        None,
        context,
        body[:10_000],
        categories,
    )
    _update_accessible_by(page_id, credential_id)
    _save_link(
        run_id,
        parent_id,
        page_id,
        url,
        link_text=steps[-1].get("name") if steps else "Workflow",
        action_kind="click",
        action_data={"replay_steps": steps},
    )
    _update_run(run_id, pages_discovered=shared.pages_done)
    return page_id


def _record_note(
    run_id: int,
    workflow: dict,
    status: str,
    steps: list[str],
    detail: str,
    url: str = "",
    *,
    page_id: int | None = None,
    needs_input: bool = False,
    request: str = "",
    instructions: str = "",
) -> None:
    from aespa.services.crawler import _crawl_log

    note = {
        "name": workflow["name"],
        "goal": workflow["goal"],
        "reason": workflow["reason"],
        "start_url": workflow["start_url"],
        "retry_of": workflow.get("retry_of"),
        "destructive": bool(workflow.get("destructive")),
        "status": status,
        "needs_input": needs_input,
        "request": request[:300],
        "instructions": instructions[:4000],
        "generate_sample_data": bool(workflow.get("generate_sample_data")),
        "save_to_site_requested": bool(workflow.get("save_to_site_requested")),
        "steps": steps,
        "detail": detail[:500],
        "url": url[:1000],
        "page_id": page_id,
    }
    _crawl_log(
        run_id,
        "crawl_note",
        "complete" if status == "crawled" else "info",
        f"{workflow['name']}: {detail}",
        page_url=url or workflow["start_url"],
        data={"stage": "workflow_note", "note": note},
    )


async def explore_after_crawl(
    run_id: int,
    *,
    llm_cfg,
    site,
    creds: list[Credential],
    shared,
    max_pages: int,
    browser_engine: str,
    browser_visible: bool,
    pw_proxy: dict,
    global_http_header: dict[str, str],
    selected_workflows: list[dict] | None = None,
    progress: Callable[[dict], None] | None = None,
) -> None:
    """Use the crawler model to try unseen workflows after URL discovery."""
    from playwright.async_api import async_playwright

    from aespa.services.crawler import (
        _authenticate,
        _login_url_for_credential,
        _norm,
        _same_domain,
        _stop_requested,
        _wait_for_content_settle,
    )

    inventory, known_pages = _crawl_inventory(run_id)
    if not inventory:
        if selected_workflows is not None:
            raise ValueError("This run has no crawled pages to continue from")
        return
    if run_id in _stop_requested:
        if selected_workflows is not None:
            raise ValueError("The crawl was stopped")
        return

    def report(message: str, **changes) -> None:
        if progress is not None:
            progress({"message": message, **changes})

    base_netloc = urlparse(site.base_url).netloc
    if selected_workflows is not None:
        proposals = selected_workflows
    else:
        saved_workflows = _saved_workflow_proposals(site)
        try:
            inferred = await _infer_workflows(
                llm_cfg,
                inventory,
                set(known_pages),
                _prior_workflow_identities(run_id)
                | {_workflow_identity(item) for item in saved_workflows},
            )
        except Exception as exc:
            log.warning("Post-crawl workflow inference failed: %s", exc)
            if not saved_workflows:
                raise
            inferred = []
        proposals = saved_workflows + inferred
        with Session(get_engine()) as session:
            reached = {
                (
                    note.get("page_id"),
                    str(note.get("name") or "").casefold(),
                    str(note.get("goal") or "").casefold(),
                )
                for note in list_workflow_notes(session, run_id)
                if note.get("status") == "crawled"
            }
        pending = []
        inferred_to_explore = 0
        for workflow in proposals:
            page_id = workflow.get("reached_page_id")
            if page_id is None:
                if workflow.get("inferred") and inferred_to_explore >= _MAX_WORKFLOWS:
                    _record_note(
                        run_id,
                        workflow,
                        "not_attempted",
                        [],
                        "Not tried because the workflow exploration limit was reached.",
                    )
                else:
                    pending.append(workflow)
                    if workflow.get("inferred"):
                        inferred_to_explore += 1
            elif (
                page_id,
                workflow["name"].casefold(),
                workflow["goal"].casefold(),
            ) not in reached:
                _record_note(
                    run_id,
                    workflow,
                    "crawled",
                    [],
                    "Reached during the page crawl.",
                    url=next(
                        page["url"] for page in inventory if page["page_id"] == page_id
                    ),
                    page_id=page_id,
                )
                reached.add(
                    (page_id, workflow["name"].casefold(), workflow["goal"].casefold())
                )
        proposals = pending
    if not proposals:
        return

    for workflow in proposals:
        workflow["generate_sample_data"] = _can_generate_sample_data(workflow)

    for workflow in proposals:
        if known_pages.get(_norm(workflow["start_url"])) is None and not (
            workflow.get("saved_site_data")
            and _same_domain(workflow["start_url"], base_netloc)
        ):
            raise ValueError("Workflow start page is not in the saved crawl")

    historical_usernames = _historical_credential_usernames(run_id)
    # Each workflow gets its own browser context and signs in separately, so
    # several can run at once without sharing cookies or application state.
    limit = asyncio.Semaphore(_MAX_PARALLEL_WORKFLOWS)

    async def explore_workflow(browser, workflow: dict) -> None:
        if run_id in _stop_requested:
            return
        start_page = known_pages.get(_norm(workflow["start_url"]))
        if workflow["destructive"]:
            _record_note(
                run_id,
                workflow,
                "not_attempted",
                [],
                "Not tried because this workflow appears to delete something.",
            )
            return
        if (
            _is_payment_workflow(workflow)
            and not str(workflow.get("user_instructions") or "").strip()
        ):
            _record_note(
                run_id,
                workflow,
                "needs_input",
                [],
                "Payment details are needed before trying this workflow.",
                needs_input=True,
                request="Provide test payment details or instructions for this workflow.",
            )
            return
        credential, requires_credential = _workflow_credential(
            start_page, creds, historical_usernames
        )
        if credential is None and requires_credential:
            _record_note(
                run_id,
                workflow,
                "not_attempted",
                [],
                "The saved account for this page is no longer available. "
                "Update the site credentials and retry this workflow.",
            )
            return
        credential_id = credential.id if credential else None
        if credential and credential.auth_mode in {
            AuthMode.guided,
            AuthMode.entra_id,
        }:
            _record_note(
                run_id,
                workflow,
                "not_attempted",
                [],
                "Not tried because this workflow needs a guided sign-in.",
            )
            return
        context = await browser.new_context(
            user_agent=playwright_user_agent(browser),
            ignore_https_errors=True,
            **pw_proxy,
        )
        protect_playwright_context(browser, context)
        await context.route("**/*", _block_delete_request)
        if global_http_header:
            await context.set_extra_http_headers(global_http_header)
        username = credential.username if credential else "unauthenticated"
        traffic_svc.setup_playwright_logging(
            context, run_id, username=username, purpose="Post-crawl workflow"
        )
        page = await context.new_page()
        steps: list[dict] = []
        descriptions: list[str] = []
        decision_feedback: list[str] = []
        prior_actions: set[tuple[str, str, str, str]] = set()
        submission_errors: dict[str, int] = {}
        detail = "Stopped before the workflow was reached."
        status = "not_reached"
        saved_id = None
        needs_input = False
        request = ""
        attempted_action = "opening the starting page"
        try:
            if credential:
                report("Signing in", stage="sign_in")
                try:
                    await _authenticate(
                        page,
                        _login_url_for_credential(site.login_url or "", credential),
                        credential,
                        run_id,
                        llm_cfg=llm_cfg,
                    )
                except Exception:
                    log.warning(
                        "Could not sign in for workflow %s",
                        workflow["name"],
                        exc_info=True,
                    )
                    detail = (
                        "Could not sign in with the saved site credential. "
                        "Update it and retry this workflow."
                    )
                    status = "not_attempted"
                    return
            report(
                "Opening the starting page",
                stage="opening_page",
                current_path=urlparse(workflow["start_url"]).path or "/",
            )
            await page.goto(
                workflow["start_url"],
                wait_until="domcontentloaded",
                timeout=20_000,
            )
            await _wait_for_content_settle(page, max_wait_ms=1200)
            if not _same_domain(page.url, base_netloc):
                detail = "The starting page redirected outside the target site."
                return
            parent_id = start_page.id if start_page else None
            action_limit = (
                _MAX_RETRY_ACTIONS if selected_workflows is not None else _MAX_ACTIONS
            )
            report(
                "Checking the page",
                stage="checking_page",
                current_path=urlparse(page.url).path or "/",
                actions_done=0,
                action_limit=action_limit,
                actions=[],
            )
            for _ in range(action_limit):
                attempted_action = "checking the page"
                if run_id in _stop_requested:
                    detail = "Stopped by the user."
                    break
                observation = await _observe(page)
                report(
                    "Choosing the next step",
                    stage="deciding",
                    current_path=urlparse(page.url).path or "/",
                )
                decision = await _decide_with_corrections(
                    llm_cfg,
                    workflow,
                    observation,
                    [*descriptions, *decision_feedback],
                    prior_actions,
                )
                action = decision.get("action")
                if action == "reached":
                    evidence = str(decision.get("evidence") or "").strip()
                    visible = " ".join(
                        str(observation.get(key) or "")
                        for key in ("url", "title", "text")
                    )
                    if evidence and evidence.casefold() in visible.casefold():
                        status = "crawled"
                        report("Saving the reached page", stage="saving_page")
                        detail = (
                            "Reached the workflow with test data."
                            if workflow.get("user_instructions")
                            or workflow.get("generate_sample_data")
                            else f"Reached the workflow. Visible evidence: {evidence[:140]}"
                        )
                        saved_id = await _save_discovered_page(
                            run_id=run_id,
                            page=page,
                            root_url=workflow["start_url"],
                            steps=steps,
                            parent_id=parent_id,
                            credential_id=credential_id,
                            username=username,
                            shared=shared,
                            max_pages=max_pages,
                            llm_cfg=llm_cfg,
                        )
                        if saved_id is None:
                            status = "not_reached"
                            detail = "The crawl page limit was reached."
                    else:
                        detail = "The model could not point to visible evidence that the workflow was reached."
                    break
                if action == "stop":
                    needs_input = decision.get("needs_input") is True
                    request = str(decision.get("request") or "")[:300]
                    detail = str(decision.get("reason") or detail)[:500]
                    if (
                        workflow.get("user_instructions")
                        and not workflow.get("generate_sample_data")
                        and _invalid_supplied_input(observation)
                    ):
                        needs_input = True
                        request = _invalid_supplied_input(observation)
                    if needs_input:
                        status = "needs_input"
                    elif _DELETE_ACTION.search(detail):
                        status = "not_attempted"
                    break
                allowed, why = _action_allowed(
                    decision,
                    observation,
                    workflow.get("user_instructions") or "",
                    generate_sample_data=bool(workflow.get("generate_sample_data")),
                    prior_actions=prior_actions,
                )
                if not allowed:
                    needs_input = why in {
                        "The field needs a value supplied by the user.",
                        "Payment or secret fields need user-supplied test data.",
                        "Payment steps need user-supplied test data.",
                    }
                    status = "needs_input" if needs_input else "not_attempted"
                    if needs_input:
                        request = _input_request(why, decision, observation)
                    detail = why
                    break
                before_url = page.url
                action_label = {
                    "click": "Clicking a page control",
                    "fill": "Filling a field",
                    "select": "Choosing an option",
                    "check": "Choosing a radio option",
                }.get(action, "Using a page control")
                report(action_label, stage="acting")
                if action == "click":
                    attempted_action = "clicking a page control"
                else:
                    field = observation["fields"][int(decision["index"])]
                    field_name = str(field.get("name") or "field")[:80]
                    attempted_action = (
                        f"filling {field_name}"
                        if action == "fill"
                        else f"selecting {field_name}"
                        if action == "select"
                        else f"checking {field_name}"
                    )
                step = await _apply_action(page, decision, observation)
                steps.append(step)
                if action in {"fill", "select", "check"}:
                    prior_actions.add(_field_action_key(decision, observation))
                _remember_generated_value(workflow, decision, observation)
                descriptions.append(
                    f"{decision['action']} {step.get('name') or step.get('selector')}"
                )
                report(
                    "Checking the result",
                    stage="checking_page",
                    current_path=urlparse(page.url).path or "/",
                    actions_done=len(descriptions),
                    actions=descriptions.copy(),
                )
                await _wait_for_content_settle(page, max_wait_ms=1200)
                if action == "click" and (
                    observation["controls"][int(decision["index"])].get("submits")
                    or re.search(
                        r"\b(?:save|submit|continue|confirm|apply|next)\b",
                        observation["controls"][int(decision["index"])].get("name", ""),
                        re.I,
                    )
                ):
                    submitted_observation = await _observe(page)
                    validation_action, validation_request = (
                        _submission_validation_action(
                            submitted_observation,
                            generate_sample_data=bool(
                                workflow.get("generate_sample_data")
                            ),
                            seen_errors=submission_errors,
                        )
                    )
                    if validation_action == "needs_input":
                        needs_input = True
                        status = "needs_input"
                        request = validation_request
                        detail = (
                            "The site kept rejecting the generated form data."
                            if workflow.get("generate_sample_data")
                            else "The site rejected a supplied form value."
                        )
                        break
                    if validation_action == "retry":
                        decision_feedback.append(
                            f"Form error after submit: {validation_request}"
                        )
                if not _same_domain(page.url, base_netloc):
                    detail = "The action left the target site."
                    break
                if _norm(page.url) != _norm(before_url):
                    parent_id = await _save_discovered_page(
                        run_id=run_id,
                        page=page,
                        root_url=workflow["start_url"],
                        steps=steps,
                        parent_id=parent_id,
                        credential_id=credential_id,
                        username=username,
                        shared=shared,
                        max_pages=max_pages,
                        llm_cfg=llm_cfg,
                    )
                    if parent_id is None:
                        detail = "The crawl page limit was reached."
                        break
            else:
                detail = "Stopped after the workflow exploration limit."
        except PlaywrightTimeoutError as exc:
            log.warning(
                "Timed out while %s in workflow %s: %s",
                attempted_action,
                workflow["name"],
                exc,
            )
            detail = f"Timed out while {attempted_action}."
        except Exception as exc:
            log.warning("Could not explore workflow %s: %s", workflow["name"], exc)
            detail = f"Could not finish exploring: {type(exc).__name__}."
        finally:
            _record_note(
                run_id,
                workflow,
                status,
                descriptions,
                detail,
                page.url if page.url.startswith("http") else "",
                page_id=saved_id if status == "crawled" else None,
                needs_input=needs_input,
                request=request,
                instructions=_instructions_with_generated_values(workflow),
            )
            report(
                detail,
                stage="finished",
                current_path=urlparse(page.url).path or "/",
                actions_done=len(descriptions),
                actions=descriptions.copy(),
                result_status=status,
            )
            await context.close()

    async def explore_when_free(browser, workflow: dict) -> None:
        async with limit:
            await explore_workflow(browser, workflow)

    report("Opening browser", stage="browser")
    async with async_playwright() as playwright:
        browser = await launch_playwright_browser(
            playwright,
            browser_engine=browser_engine,
            headless=not browser_visible,
            args=["--proxy-bypass-list=<-loopback>"] if pw_proxy else [],
        )
        try:
            results = await asyncio.gather(
                *(explore_when_free(browser, workflow) for workflow in proposals),
                return_exceptions=True,
            )
        finally:
            await browser.close()
    for result in results:
        if isinstance(result, BaseException):
            raise result


def _active_retry_notes(run_id: int) -> set[int]:
    return {
        note_id
        for (task_run_id, note_id), task in _retry_tasks.items()
        if task_run_id == run_id and not task.done()
    }


def workflow_retry_status(run_id: int) -> dict:
    retries = [
        dict(state)
        for (state_run_id, _note_id), state in sorted(_retry_results.items())
        if state_run_id == run_id
    ]
    running = any(state.get("status") == "running" for state in retries)
    return {"status": "running" if running else "idle", "retries": retries}


def start_workflow_retry(
    run_id: int,
    note: dict,
    instructions: str,
    *,
    save_to_site: bool = False,
    generate_sample_data: bool = False,
) -> dict:
    from aespa.services import crawler

    if crawler.is_running(run_id):
        raise ValueError("Wait for the crawl to finish before continuing a workflow.")
    active_notes = _active_retry_notes(run_id)
    if note["id"] in active_notes:
        raise ValueError("This workflow is already running.")
    if len(active_notes) >= _MAX_PARALLEL_WORKFLOWS:
        raise ValueError(
            f"Up to {_MAX_PARALLEL_WORKFLOWS} workflows can run at once. "
            "Wait for one to finish."
        )
    if not can_retry_workflow(note):
        raise ValueError("This workflow cannot be retried.")
    instructions = instructions.strip() or str(note.get("instructions") or "").strip()
    if len(instructions) > 4000:
        raise ValueError("Enter up to 4000 characters of sample data or instructions.")
    workflow = {
        "name": str(note.get("name") or "Workflow")[:100],
        "goal": str(note.get("goal") or note.get("name") or "Workflow")[:220],
        "reason": str(note.get("reason") or "User-requested workflow retry")[:360],
        "start_url": str(note.get("start_url") or note.get("url") or ""),
        "destructive": False,
        "retry_of": note["id"],
        "user_instructions": instructions,
        "generate_sample_data": False,
        "save_to_site_requested": save_to_site,
    }
    generate_sample_data = _can_generate_sample_data(workflow)
    workflow["generate_sample_data"] = generate_sample_data
    key = (run_id, note["id"])
    _retry_results[key] = {
        "status": "running",
        "note_id": note["id"],
        "workflow_name": workflow["name"],
        "generate_sample_data": generate_sample_data,
        "save_to_site_requested": save_to_site,
        "saved_to_site": False,
        "stage": "preparing",
        "message": "Preparing the browser",
        "actions_done": 0,
        "action_limit": _MAX_RETRY_ACTIONS,
        "actions": [],
    }
    task = asyncio.create_task(
        _run_workflow_retry(run_id, workflow, save_to_site=save_to_site)
    )
    _retry_tasks[key] = task
    task.add_done_callback(
        lambda done: (
            _retry_tasks.pop(key, None) if _retry_tasks.get(key) is done else None
        )
    )
    return dict(_retry_results[key])


async def _run_workflow_retry(
    run_id: int, workflow: dict, *, save_to_site: bool = False
) -> None:
    from aespa.services import crawler
    from aespa.services.settings import (
        get_browser_debug_config,
        get_global_http_header_config,
        get_llm_config_for_role,
        get_upstream_proxy_config,
    )

    note_id = workflow["retry_of"]
    key = (run_id, note_id)

    def report(changes: dict) -> None:
        state = _retry_results.get(key, {})
        _retry_results[key] = {**state, **changes, "status": "running"}

    crawler._crawl_log(
        run_id,
        "crawl_workflow_retry",
        "start",
        f"Continuing {workflow['name']} with "
        + (
            "generated sample data"
            if workflow.get("generate_sample_data")
            else "supplied instructions"
            if workflow.get("user_instructions")
            else "no new instructions"
        ),
        data={
            "note_id": note_id,
            "generate_sample_data": bool(workflow.get("generate_sample_data")),
        },
    )
    try:
        with Session(get_engine()) as session:
            run = session.get(TestRun, run_id)
            if run is None or run.status == "running":
                raise ValueError("The test run is not available for workflow retry")
            site = session.get(Site, run.site_id)
            llm_cfg = get_llm_config_for_role(session, run, "crawler")
            if llm_cfg is None:
                raise ValueError("No crawler model is configured for this run")
            creds = list(site.credentials)
            proxy_cfg = get_upstream_proxy_config(session)
            browser_cfg = get_browser_debug_config(session)
            header_cfg = get_global_http_header_config(session)
            pages = list(
                session.exec(
                    select(CrawledPage).where(CrawledPage.test_run_id == run_id)
                )
            )
            for obj in [*creds, site, run, *pages]:
                session.expunge(obj)
        shared = crawler._CrawlShared(
            crawled_norms={crawler._norm(page.url): page.id for page in pages},
            state_keys={page.state_key: page.id for page in pages if page.state_key},
            pages_done=len(pages),
            run_id=run_id,
        )
        proxy_url = proxy_cfg.scanner_proxy_url if proxy_cfg.proxy_scanner else None
        await explore_after_crawl(
            run_id,
            llm_cfg=llm_cfg,
            site=site,
            creds=creds,
            shared=shared,
            max_pages=max(run.max_pages, len(pages) + _MAX_RETRY_ACTIONS),
            browser_engine=browser_cfg.browser_engine,
            browser_visible=bool(browser_cfg.browser_visible),
            pw_proxy={"proxy": {"server": proxy_url}} if proxy_url else {},
            global_http_header={
                header.header_name: header.header_value for header in header_cfg.headers
            },
            selected_workflows=[workflow],
            progress=report,
        )
        if "result_status" not in _retry_results.get(key, {}):
            raise ValueError("The workflow did not produce a result")
        from aespa.services.workflow_workprogram import seed_workflow_tests

        seed_workflow_tests(run_id)
        effective_instructions = _instructions_with_generated_values(workflow)
        if (
            save_to_site
            and effective_instructions
            and _retry_results[key]["result_status"] == "crawled"
        ):
            from aespa.services.sites import save_site_workflow_data

            with Session(get_engine()) as session:
                save_site_workflow_data(
                    session, run.site_id, workflow, effective_instructions
                )
            report({"saved_to_site": True})
    except Exception as exc:
        log.warning(
            "Workflow retry failed for run %s note %s", run_id, note_id, exc_info=True
        )
        _retry_results[key] = {
            **_retry_results.get(key, {}),
            "status": "error",
            "note_id": note_id,
            "error": f"Could not continue the workflow: {type(exc).__name__}.",
        }
        if "result_status" not in _retry_results[key]:
            _record_note(
                run_id,
                workflow,
                "not_reached",
                _retry_results[key].get("actions") or [],
                f"Could not continue the workflow: {type(exc).__name__}.",
                needs_input=True,
                request="Check the instructions and try again.",
                instructions=_instructions_with_generated_values(workflow),
            )
        crawler._crawl_log(
            run_id,
            "crawl_workflow_retry",
            "error",
            f"Could not continue {workflow['name']}",
            data={"note_id": note_id},
        )
    else:
        _retry_results[key] = {
            **_retry_results[key],
            "status": "complete",
            "note_id": note_id,
        }
        crawler._crawl_log(
            run_id,
            "crawl_workflow_retry",
            "complete",
            f"Finished continuing {workflow['name']}",
            data={"note_id": note_id},
        )
