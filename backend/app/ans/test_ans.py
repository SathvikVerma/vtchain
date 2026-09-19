"""Standalone smoke test for the ANS gate — run directly, no server needed.

    python -m app.ans.test_ans

Confirms: a registered agent verifies successfully; an unregistered
("spoofed") agent is correctly rejected. This is the exact behavior the
live demo relies on for the "halts on a spoofed identity" moment.
"""
import asyncio

from ..models.schemas import AgentRole
from .client import ANSClient


async def main() -> None:
    client = ANSClient()

    await client.register("buyer-001", AgentRole.buyer, "buyer.vtchain.dev")
    result = await client.verify("buyer-001", AgentRole.buyer)
    print("Registered agent verification:", result)
    assert result.verified, "expected a registered agent to verify successfully"

    spoofed = await client.verify("spoofed-agent-999", AgentRole.seller)
    print("Spoofed agent verification:  ", spoofed)
    assert not spoofed.verified, "expected an unregistered agent to fail verification"
    assert spoofed.reason == "unregistered_identity"

    print("\nANS gate logic OK — ready to swap in the real API in client.py")


if __name__ == "__main__":
    asyncio.run(main())
