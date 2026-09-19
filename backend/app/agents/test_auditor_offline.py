"""Offline test of the auditor's approve/flag logic, Gemini mocked out.

    python -m app.agents.test_auditor_offline
"""
import asyncio
import json
from unittest.mock import AsyncMock, patch

from .auditor import audit
from ..models.schemas import NegotiationResult, Offer, AgentRole


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


async def main() -> None:
    negotiation = NegotiationResult(
        agreed=True,
        final_unit_price=2.30,
        final_quantity=500,
        rounds=[
            Offer(round=1, from_role=AgentRole.seller, unit_price=2.75, quantity=500, message="opening"),
            Offer(round=2, from_role=AgentRole.buyer, unit_price=2.30, quantity=500, message="counter"),
            Offer(round=3, from_role=AgentRole.seller, unit_price=2.30, quantity=500, message="accept"),
        ],
    )

    scripted = json.dumps({
        "approved": True,
        "reasoning": "Final price is within both parties' stated ranges and reflects genuine back-and-forth.",
        "flags": [],
    })

    async def fake_generate_content(model, contents):  # noqa: ARG001
        return FakeResponse(scripted)

    with patch("app.agents.auditor._client") as mock_client:
        mock_client.aio.models.generate_content = AsyncMock(side_effect=fake_generate_content)
        result = await audit(
            item="steel bolts",
            max_price=2.50,
            qty_needed=500,
            min_price=2.00,
            list_price=2.80,
            qty_available=800,
            negotiation=negotiation,
        )

    print(f"Approved: {result.approved}")
    print(f"Reasoning: {result.reasoning}")
    print(f"Flags: {result.flags}")

    assert result.approved is True
    assert result.flags == []

    # Also verify the fail-closed path: no agreement -> auto-rejected, no model call needed.
    no_deal = NegotiationResult(agreed=False, rounds=[], reason="no agreement reached")
    result2 = await audit(
        item="steel bolts", max_price=2.5, qty_needed=500, min_price=2.0,
        list_price=2.8, qty_available=800, negotiation=no_deal,
    )
    assert result2.approved is False
    assert "no_agreement" in result2.flags

    print("\nAuditor logic OK (approves valid deals, fails closed on no-agreement)")


if __name__ == "__main__":
    asyncio.run(main())
