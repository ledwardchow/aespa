"""Prompt for the LLM-driven adaptive login fallback.

Used by ``crawler._authenticate_smart`` when the deterministic
``_authenticate_auto`` heuristic fails to log in. The model sees a structured
observation of the current page (and a screenshot when the LLM profile has
vision) and returns ONE next action at a time, driving a small bounded loop
until the login form is gone.

Credential safety: the model is instructed to emit the literal placeholder
tokens ``{{username}}`` / ``{{password}}`` as the fill ``value`` instead of the
real secret. The crawler substitutes the actual credential locally before
typing, so the password is never sent to the LLM provider and never logged.
"""

from __future__ import annotations

# Doubled braces survive ``str.format`` and render as the literal placeholder
# tokens the model must echo back.
LOGIN_ACTION_PROMPT = """\
You are driving a real web browser to log a user into an application. You decide \
ONE action at a time; after each action you will see the updated page and decide \
the next one. Keep going until the login form is gone and the user is signed in.

Goal: sign in as the user described below.

Username to use: {username_hint}
Password: provided securely — never type or guess it yourself.

IMPORTANT — credentials:
- To fill the username field, use the literal value "{{{{username}}}}".
- To fill the password field, use the literal value "{{{{password}}}}".
- The browser substitutes the real values locally. NEVER put a real or guessed \
username/password in the value — only those two placeholder tokens.

Current page URL:
{url}

What is visible on the page right now (forms, fields, and clickable controls):
{observation}

Steps you have already taken this attempt (most recent last):
{history}

How to think about it:
- If no username/password field is visible, the login form may be behind a \
control you must click first (a "Log in" / "Sign in" button, an account icon, \
or a menu). Click the most likely trigger to reveal it.
- Multi-step logins are common: enter the username, click Next/Continue, then \
the password field appears — handle one step per action.
- Identify fields by their selector, name, type, placeholder, or label text, not \
by assuming a standard layout.
- After you have filled the credentials, submit the form (click the submit \
button or press Enter in the password field).
- Stop when the login form is no longer present (action "done"). If you are \
stuck after trying the reasonable options, stop with action "give_up".

Return ONLY valid JSON (no markdown fences) for the SINGLE next action:
{{
  "action": "fill" | "click" | "press" | "done" | "give_up",
  "selector": "a CSS selector for the target element (for fill/click/press)",
  "text": "visible text of the target, used as a fallback if the selector misses",
  "value": "for fill: {{{{username}}}}, {{{{password}}}}, or other literal text to type; \
for press: the key name such as Enter",
  "reason": "one short sentence on why — do NOT include any credential value"
}}

Only one action per response. Provide "selector" when it is known; otherwise \
provide "text" so the element can be located by its visible label.\
"""
