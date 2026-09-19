"""Auditor agent: an independent reasoning check before settlement fires.

This is deliberately separate from ANS identity re-verification (that's a
different, cheaper check already done in routes/pipeline.py). This module
asks: even if both parties are who they say they are, does this NEGOTIATED
DEAL itself look legitimate? A compromised-but-verified agent, or a buggy
one, could still negotiate a bad deal — identity alone doesn't catch that.

The auditor is given the full negotiation transcript and the parties'
stated constraints, and has to reason about whether anything looks off:
a price outside a sane range, a quantity mismatch, a deal that closed
suspiciously fast without real back-and-forth, etc. It returns a
structured approve/flag decision with reasoning — this is the piece that
makes "Auditor" a real third agent in the system, not just a formality.
"""
from __future__ import annotations

import json

from google import genai

from ..config import settings
from ..models.schemas import AuditResult, NegotiationResult
from ._gemini_retry import call_with_retry

MODEL_NAME = "gemini-3.6-flash"

_client = genai.Client(api_key=settings.gemini_api_key)

_PROMPT_TEMPLATE = """You are an independent auditor agent reviewing a completed \
supply-chain negotiation before funds are allowed to settle. You were NOT part of \
the negotiation — your job is to catch anything that looks wrong even though both \
parties' identities have already been separately verified.

Item: {item}
Buyer's stated constraints: max ${max_price}/unit, needs {qty_needed} units
Seller's stated constraints: min ${min_price}/unit, list price ${list_price}/unit, \
{qty_available} units available

Full negotiation transcript:
{transcript}

Final agreed terms: ${final_price}/unit x {final_qty} units

Review this deal. Consider: does the final price fall within both parties' stated \
constraints? Does the quantity make sense? Did the negotiation involve genuine \
back-and-forth, or does it look suspicious (e.g. immediate acceptance with no \
negotiation, a price outside anyone's stated range)?

Respond with ONLY a JSON object, no other text:
{{"approved": <true/false>, "reasoning": "<one or two sentences>", "flags": ["<short flag string>", ...]}}

"flags" should be an empty list if nothing is wrong. Only set "approved": false if \
there is a genuine, specific problem — not stylistic nitpicks.
"""


def _format_transcript(negotiation: NegotiationResult) -> str:
    lines = [
        f"Round {o.round} [{o.from_role.value}]: ${o.unit_price}/unit x {o.quantity} — \"{o.message}\""
        for o in negotiation.rounds
    ]
    return "\n".join(lines) if lines else "(no rounds recorded)"


async def audit(
    item: str,
    max_price: float,
    qty_needed: int,
    min_price: float,
    list_price: float,
    qty_available: int,
    negotiation: NegotiationResult,
) -> AuditResult:
    if not negotiation.agreed:
        return AuditResult(approved=False, reasoning="negotiation did not reach agreement", flags=["no_agreement"])

    prompt = _PROMPT_TEMPLATE.format(
        item=item,
        max_price=max_price,
        qty_needed=qty_needed,
        min_price=min_price,
        list_price=list_price,
        qty_available=qty_available,
        transcript=_format_transcript(negotiation),
        final_price=negotiation.final_unit_price,
        final_qty=negotiation.final_quantity,
    )

    try:
        response = await call_with_retry(
            _client.aio.models.generate_content, model=MODEL_NAME, contents=prompt
        )
        text = response.text.strip()
        if text.startswith("```"):
            text = text.strip("`").removeprefix("json").strip()
        result = json.loads(text)
        return AuditResult(
            approved=result["approved"],
            reasoning=result.get("reasoning", ""),
            flags=result.get("flags", []),
        )
    except Exception as exc:  # noqa: BLE001
        # Fail closed: if the auditor itself errors, don't let funds move.
        return AuditResult(
            approved=False,
            reasoning=f"auditor error — failing closed: {exc}",
            flags=["auditor_error"],
        )
