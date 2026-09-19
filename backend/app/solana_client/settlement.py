"""Settlement: fires a real SOL transfer on devnet once negotiation agrees.

Deliberately scoped small per the build plan — a wallet-to-wallet SOL
transfer, not a custom program/smart contract. That's enough to prove
"the deal settled for real, not just in a database" without needing
Anchor/Rust, which would eat the whole build.

NOTE ON LIBRARY VERSIONS: solana-py's API around transaction building has
changed across versions — older examples online use `solana.transaction
.Transaction` directly, which no longer exists in current releases
(confirmed against solana-py 0.40.3 / solders 0.29.0, installed here).
Current versions build transactions through solders (MessageV0 +
VersionedTransaction) and send them via AsyncClient.send_transaction,
which is what this file does. If your teammate's machine has a very
different pinned version and this breaks, check `pip show solana solders`
and compare method signatures with `python -c "import inspect; ..."`
before assuming the logic is wrong — it's very likely just an API shape
mismatch, same as we hit building this.
"""
from __future__ import annotations

from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solders.message import MessageV0
from solders.system_program import TransferParams, transfer
from solders.transaction import VersionedTransaction

from ..config import settings
from ..models.schemas import SettlementResult
from .wallets import load_or_create_keypair

LAMPORTS_PER_SOL = 1_000_000_000
# Negotiated price is in fictional "supply chain" currency; convert to a
# small, demo-safe lamport amount rather than moving real-scale sums.
DEMO_LAMPORTS_PER_UNIT_PRICE = 1000  # tune for a visible-but-tiny transfer


def _explorer_url(signature: str) -> str:
    return f"https://explorer.solana.com/tx/{signature}?cluster=devnet"


async def settle(unit_price: float, quantity: int) -> SettlementResult:
    """Transfer lamports from buyer to seller representing the agreed trade."""
    try:
        buyer = load_or_create_keypair(settings.solana_buyer_keypair_path)
        seller = load_or_create_keypair(settings.solana_seller_keypair_path)

        lamports = int(unit_price * quantity * DEMO_LAMPORTS_PER_UNIT_PRICE)
        lamports = max(lamports, 5000)  # floor above network fee dust

        async with AsyncClient(settings.solana_rpc_url) as client:
            balance = await client.get_balance(buyer.pubkey())
            if balance.value < lamports:
                return SettlementResult(
                    success=False,
                    error=f"buyer balance too low ({balance.value} lamports, need {lamports}) — "
                    f"run setup_wallets.py to airdrop more devnet SOL",
                )

            blockhash_resp = await client.get_latest_blockhash()
            recent_blockhash = blockhash_resp.value.blockhash

            transfer_ix = transfer(
                TransferParams(
                    from_pubkey=buyer.pubkey(),
                    to_pubkey=seller.pubkey(),
                    lamports=lamports,
                )
            )
            message = MessageV0.try_compile(
                payer=buyer.pubkey(),
                instructions=[transfer_ix],
                address_lookup_table_accounts=[],
                recent_blockhash=recent_blockhash,
            )
            txn = VersionedTransaction(message, [buyer])

            resp = await client.send_transaction(txn)
            signature = str(resp.value)
            await client.confirm_transaction(resp.value, commitment=Confirmed)

        return SettlementResult(
            success=True,
            tx_signature=signature,
            explorer_url=_explorer_url(signature),
            lamports_transferred=lamports,
        )
    except Exception as exc:  # noqa: BLE001 — surface any failure to the caller/demo
        return SettlementResult(success=False, error=str(exc))
