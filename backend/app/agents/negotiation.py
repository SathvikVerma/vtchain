"""Buyer/Seller agent negotiation, powered by Gemini.

Deliberately deterministic-leaning: each agent has a hard budget/floor and
Gemini is asked to reason within it and return STRUCTURED output (JSON), not
freeform chat. Capped at MAX_ROUNDS so it always terminates in a demo-safe
number of steps.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from google import genai

from ..config import settings
from ..models.schemas import AgentRole, NegotiationResult, Offer
from ._gemini_retry import call_with_retry

MAX_ROUNDS = 5
MODEL_NAME = "gemini-3.6-flash"

_client = genai.Client(api_key=settings.gemini_api_key)


@dataclass
class BuyerProfile:
    agent_id: str
    item: str
    quantity_needed: int
    max_unit_price: float


@dataclass
class SellerProfile:
    agent_id: str
    item: str
    quantity_available: int
    min_unit_price: float
    list_price: float


_PROMPT_TEMPLATE = """You are the {role} agent in a supply-chain negotiation for "{item}".

Your constraints:
{constraints}

Negotiation so far:
{history}

Respond with ONLY a JSON object, no other text, in this exact shape:
{{"unit_price": <number>, "quantity": <integer>, "message": "<one short sentence, your rationale>", "accept": <true/false — true if you accept the other side's last offer as-is>}}

Rules:
- Never propose a price that violates your constraints above.
- If the other side's last offer already satisfies your constraints, set "accept": true and echo their terms.
- Move toward agreement each round — narrow the gap, don't restate your opening position.
"""


def _format_history(rounds: list[Offer]) -> str:
    if not rounds:
        return "(no offers yet — you may open)"
    lines = []
    for o in rounds:
        lines.append(f"Round {o.round} — {o.from_role.value}: ${o.unit_price}/unit x {o.quantity} units. \"{o.message}\"")
    return "\n".join(lines)


async def _ask_agent(role: AgentRole, item: str, constraints: str, history: list[Offer]) -> dict:
    prompt = _PROMPT_TEMPLATE.format(
        role=role.value,
        item=item,
        constraints=constraints,
        history=_format_history(history),
    )
    response = await call_with_retry(
        _client.aio.models.generate_content, model=MODEL_NAME, contents=prompt
    )
    text = response.text.strip()
    # Gemini sometimes wraps JSON in ```json fences despite instructions — strip them.
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    return json.loads(text)


async def negotiate(buyer: BuyerProfile, seller: SellerProfile) -> NegotiationResult:
    rounds: list[Offer] = []

    buyer_constraints = f"- Need {buyer.quantity_needed} units\n- Max price: ${buyer.max_unit_price}/unit"
    seller_constraints = (
        f"- Have {seller.quantity_available} units available\n"
        f"- Minimum acceptable price: ${seller.min_unit_price}/unit\n"
        f"- List price: ${seller.list_price}/unit"
    )

    for round_num in range(1, MAX_ROUNDS + 1):
        # Seller moves on odd rounds (opens), buyer responds on even rounds — alternate.
        acting_role = AgentRole.seller if round_num % 2 == 1 else AgentRole.buyer
        constraints = seller_constraints if acting_role == AgentRole.seller else buyer_constraints
        item = buyer.item

        try:
            result = await _ask_agent(acting_role, item, constraints, rounds)
        except (json.JSONDecodeError, Exception) as exc:  # noqa: BLE001
            return NegotiationResult(agreed=False, rounds=rounds, reason=f"agent response error: {exc}")

        offer = Offer(
            round=round_num,
            from_role=acting_role,
            unit_price=result["unit_price"],
            quantity=result["quantity"],
            message=result.get("message", ""),
        )
        rounds.append(offer)

        if result.get("accept") and round_num > 1:
            return NegotiationResult(
                agreed=True,
                final_unit_price=offer.unit_price,
                final_quantity=offer.quantity,
                rounds=rounds,
            )

    return NegotiationResult(
        agreed=False,
        rounds=rounds,
        reason=f"no agreement reached within {MAX_ROUNDS} rounds",
    )
