"""One-time setup: create buyer/seller devnet wallets and airdrop test SOL.

    python -m app.solana_client.setup_wallets

Run this FIRST, before anything else in the Solana module — it's the
"prove devnet works at all" step from the build plan (step 2).

Devnet airdrops are commonly rate-limited (especially the public RPC
during a hackathon, when hundreds of teams are hitting it at once) — this
retries with backoff instead of failing on the first 429/error, since a
single silent failure here would otherwise look like "Solana is broken"
when it's just a rate limit.
"""
import asyncio

from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey

from ..config import settings
from .wallets import load_or_create_keypair

MAX_AIRDROP_ATTEMPTS = 5
MIN_USEFUL_BALANCE_LAMPORTS = 100_000_000  # 0.1 SOL — enough for many settle() calls


async def airdrop(client: AsyncClient, pubkey: Pubkey, sol: float = 1.0) -> bool:
    """Returns True if the wallet ends up with a usable balance, even if it
    already had enough SOL from a previous run (idempotent — safe to re-run)."""
    balance = await client.get_balance(pubkey)
    if balance.value >= MIN_USEFUL_BALANCE_LAMPORTS:
        print(f"  already funded: {balance.value / 1_000_000_000} SOL — skipping airdrop")
        return True

    lamports = int(sol * 1_000_000_000)
    for attempt in range(1, MAX_AIRDROP_ATTEMPTS + 1):
        try:
            resp = await client.request_airdrop(pubkey, lamports)
            print(f"  airdrop requested (attempt {attempt}): {resp.value}")
            await asyncio.sleep(2 * attempt)  # backoff: 2s, 4s, 6s, ...
            balance = await client.get_balance(pubkey)
            print(f"  balance now: {balance.value / 1_000_000_000} SOL")
            if balance.value >= MIN_USEFUL_BALANCE_LAMPORTS:
                return True
        except Exception as exc:  # noqa: BLE001 — devnet airdrop errors are common, keep retrying
            print(f"  attempt {attempt} failed: {exc}")
            if attempt < MAX_AIRDROP_ATTEMPTS:
                await asyncio.sleep(2 * attempt)

    print(
        "  Airdrop didn't land after multiple attempts — this is a common devnet rate "
        "limit, not necessarily a bug. Try https://faucet.solana.com manually with the "
        "pubkey below, or retry this script in a few minutes."
    )
    return False


async def main() -> None:
    buyer = load_or_create_keypair(settings.solana_buyer_keypair_path)
    seller = load_or_create_keypair(settings.solana_seller_keypair_path)

    print(f"Buyer pubkey:  {buyer.pubkey()}")
    print(f"Seller pubkey: {seller.pubkey()}")

    async with AsyncClient(settings.solana_rpc_url) as client:
        print("\nFunding buyer...")
        buyer_ok = await airdrop(client, buyer.pubkey())
        print("\nFunding seller...")
        seller_ok = await airdrop(client, seller.pubkey())

    print()
    if buyer_ok and seller_ok:
        print("Both wallets funded and ready — you're good to run the pipeline.")
    else:
        print("One or both wallets are NOT yet funded. Do not assume settlement will")
        print("work until both show ✅ here. Retry this script, or fund manually at")
        print("https://faucet.solana.com using the pubkeys printed above, then re-run")
        print("this script to confirm (it's safe to re-run — already-funded wallets")
        print("are skipped automatically).")


if __name__ == "__main__":
    asyncio.run(main())
