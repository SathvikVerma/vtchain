"""Standalone smoke test — run directly once GEMINI_API_KEY is set in .env.

    python -m app.agents.test_negotiation
"""
import asyncio

from .negotiation import BuyerProfile, SellerProfile, negotiate


async def main() -> None:
    buyer = BuyerProfile(
        agent_id="buyer-001",
        item="pallets of steel bolts",
        quantity_needed=500,
        max_unit_price=2.50,
    )
    seller = SellerProfile(
        agent_id="seller-001",
        item="pallets of steel bolts",
        quantity_available=800,
        min_unit_price=2.00,
        list_price=2.80,
    )

    result = await negotiate(buyer, seller)
    print(f"Agreed: {result.agreed}")
    for offer in result.rounds:
        print(f"  Round {offer.round} [{offer.from_role.value}]: ${offer.unit_price}/unit x {offer.quantity} — {offer.message}")
    if result.agreed:
        print(f"\nFinal: ${result.final_unit_price}/unit x {result.final_quantity} units")
    else:
        print(f"\nNo deal: {result.reason}")


if __name__ == "__main__":
    asyncio.run(main())
