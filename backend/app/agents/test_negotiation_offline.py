"""Offline test of the negotiation LOOP logic (rounds, accept detection, JSON
parsing incl. ```json fence stripping) with Gemini mocked out.

This exists because live Gemini calls may be blocked by network policy in
some environments (e.g. this sandbox) — this test catches real bugs in the
control flow without needing network access at all.

    python -m app.agents.test_negotiation_offline
"""
import asyncio
import json
from unittest.mock import AsyncMock, patch

from .negotiation import BuyerProfile, SellerProfile, negotiate


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


async def main() -> None:
    buyer = BuyerProfile("buyer-001", "steel bolts", 500, max_unit_price=2.50)
    seller = SellerProfile("seller-001", "steel bolts", 800, min_unit_price=2.00, list_price=2.80)

    # Scripted responses: seller opens high, buyer counters, seller accepts
    # buyer's counter on round 3. Round 2's response is wrapped in a ```json
    # fence to make sure the fence-stripping path is exercised too.
    scripted = [
        json.dumps({"unit_price": 2.75, "quantity": 500, "message": "opening near list price", "accept": False}),
        "```json\n" + json.dumps({"unit_price": 2.30, "quantity": 500, "message": "countering under budget", "accept": False}) + "\n```",
        json.dumps({"unit_price": 2.30, "quantity": 500, "message": "accepting buyer's counter", "accept": True}),
    ]

    call_count = 0

    async def fake_generate_content(model, contents):  # noqa: ARG001 — mock signature
        nonlocal call_count
        resp = FakeResponse(scripted[call_count])
        call_count += 1
        return resp

    with patch("app.agents.negotiation._client") as mock_client:
        mock_client.aio.models.generate_content = AsyncMock(side_effect=fake_generate_content)
        result = await negotiate(buyer, seller)

    print(f"Agreed: {result.agreed}")
    for offer in result.rounds:
        print(f"  Round {offer.round} [{offer.from_role.value}]: ${offer.unit_price}/unit x {offer.quantity} — {offer.message}")

    assert result.agreed, "expected the scripted 3-round negotiation to converge"
    assert result.final_unit_price == 2.30
    assert result.final_quantity == 500
    assert call_count == 3, f"expected exactly 3 model calls, got {call_count}"

    print("\nNegotiation loop logic OK (rounds, fence-stripping, accept detection all verified offline)")


if __name__ == "__main__":
    asyncio.run(main())
