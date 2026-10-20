"""OpenAPI ``webhooks`` describing the callbacks AESPA sends.

These handlers are never served. They exist so the OpenAPI definition
documents each callback's body and headers.
"""

from __future__ import annotations

from fastapi import APIRouter, Header

from .schemas import CALLBACK_EVENTS, CallbackPayload

SIGNATURE_HELP = (
    "t=<unix seconds>,v1=<hex HMAC-SHA256>. Compute the HMAC over "
    "'<t>.' followed by the raw request body, using the callback secret as the "
    "key. Reject the request if the values differ or t is more than 5 minutes old."
)

DESCRIPTIONS = {
    "scan.started": "The scan began preparing source, crawling, or scanning.",
    "scan.phase_changed": "The scan moved to another phase, or resumed after a pause.",
    "scan.progress": "The percentage changed. Sent at most once a minute; opt in.",
    "scan.needs_action": "A person must act in AESPA, for example to sign in.",
    "scan.paused": "The scan paused, for example when the LLM provider was unavailable.",
    "scan.completed": "The scan finished. Fetch results with the scan's links.",
    "scan.failed": "The scan ended with an error. See scan.error.",
    "scan.stopped": "The scan was stopped before it finished.",
}


def build_webhooks() -> APIRouter:
    webhooks = APIRouter(tags=["Callbacks"])

    for event in CALLBACK_EVENTS:

        def handler(
            body: CallbackPayload,
            x_aespa_event: str = Header(description="The event name."),
            x_aespa_delivery: str = Header(
                description="Unique delivery ID. The same ID is reused when a delivery is retried."
            ),
            x_aespa_signature: str = Header(description=SIGNATURE_HELP),
        ) -> None:
            return None

        webhooks.add_api_route(
            event,
            handler,
            methods=["POST"],
            operation_id=f"callback_{event.replace('.', '_')}",
            summary=event,
            description=(
                f"{DESCRIPTIONS[event]} Respond with any 2xx status within 10 "
                "seconds. Other responses are retried after 30 seconds, 2, 5, 15, "
                "and 30 minutes, then the delivery is marked failed. Redirects are "
                "not followed."
            ),
            status_code=204,
            responses={204: {"description": "Received"}},
        )
    return webhooks
