"""The core pipeline endpoint: verify -> negotiate -> re-verify -> settle.

This is the single call the frontend dashboard drives. Every step is logged
to Mongo as it happens (not just at the end) so the dashboard can poll
GET /transactions/{id} and show live progress.
"""
from __future__ import annotations

import random
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..agents.auditor import audit
from ..agents.negotiation import BuyerProfile, SellerProfile, negotiate
from ..ans.client import ans_client
from ..config import settings
from ..db import get_transaction, list_transactions, save_transaction
from ..models.schemas import AgentRole, TransactionRecord
from ..solana_client.settlement import settle

router = APIRouter()


class RunPipelineRequest(BaseModel):
    buyer_id: str = "buyer-001"
    seller_id: str = "seller-001"
    auditor_id: str = "auditor-001"
    item: str = "pallets of steel bolts"
    quantity_needed: int = 500
    max_unit_price: float = 2.50
    quantity_available: int = 800
    min_unit_price: float = 2.00
    list_price: float = 2.80
    simulate_spoof: bool = False  # if true, buyer_id is NOT pre-registered with ANS
    randomize: bool = True  # vary starting price AND quantities each run for demo variety


@router.post("/pipeline/run")
async def run_pipeline(req: RunPipelineRequest) -> TransactionRecord:
    txn_id = str(uuid.uuid4())
    record = TransactionRecord(
        transaction_id=txn_id,
        buyer_id=req.buyer_id,
        seller_id=req.seller_id,
        auditor_id=req.auditor_id,
        status="verifying",
    )
    await save_transaction(record)

    # Randomize both price AND quantity each run so back-to-back demo runs
    # don't all show the same "$2.80 -> $2.30, 500 units" numbers. Values
    # stay internally consistent — list_price > min_unit_price, with a real
    # gap for max_unit_price to land in, and quantity_needed comfortably
    # under quantity_available — so the negotiation still makes sense and
    # reliably converges within MAX_ROUNDS.
    if req.randomize:
        list_price = round(random.uniform(2.20, 4.00), 2)
        min_unit_price = round(list_price - random.uniform(0.30, 0.90), 2)
        max_unit_price = round(min_unit_price + random.uniform(0.05, 0.45), 2)

        quantity_available = random.randint(300, 1200)
        # buyer needs somewhere between 30% and 80% of what's available
        quantity_needed = max(50, int(quantity_available * random.uniform(0.3, 0.8)))
    else:
        list_price = req.list_price
        min_unit_price = req.min_unit_price
        max_unit_price = req.max_unit_price
        quantity_available = req.quantity_available
        quantity_needed = req.quantity_needed

    # --- Step 1: register identities (skip buyer if we're demoing a spoof) ---
    # Each agent is anchored as a subdomain of our one real GoDaddy-registered
    # domain (settings.ans_root_domain) — e.g. buyer.brownsugar.design —
    # which is what makes "domain-anchored identity" a real claim instead of
    # a fake placeholder.
    #
    # For a spoof demo, we use a FRESH, never-registered id scoped to this
    # one request rather than mutating the shared buyer_id's registry entry.
    # The ANS mock registry is one shared object across all in-flight
    # requests — unregistering the real buyer_id here would also wipe out
    # any OTHER concurrent request (e.g. a teammate clicking Run at the same
    # time) that is mid-negotiation and expects that buyer to still be
    # verified later.
    root = settings.ans_root_domain
    buyer_id = f"spoofed-{uuid.uuid4().hex[:8]}" if req.simulate_spoof else req.buyer_id
    record.buyer_id = buyer_id
    if not req.simulate_spoof:
        await ans_client.register(buyer_id, AgentRole.buyer, f"buyer.{root}")
    await ans_client.register(req.seller_id, AgentRole.seller, f"seller.{root}")
    await ans_client.register(req.auditor_id, AgentRole.auditor, f"auditor.{root}")

    # --- Step 2: verify buyer + seller before any negotiation happens ---
    record.buyer_verification = await ans_client.verify(buyer_id, AgentRole.buyer)
    record.seller_verification = await ans_client.verify(req.seller_id, AgentRole.seller)
    await save_transaction(record)

    if not (record.buyer_verification.verified and record.seller_verification.verified):
        record.status = "halted"
        await save_transaction(record)
        return record  # HALT — this is the "spoofed identity stops the trade" demo moment

    # --- Step 3: negotiate ---
    record.status = "negotiating"
    await save_transaction(record)

    buyer = BuyerProfile(buyer_id, req.item, quantity_needed, max_unit_price)
    seller = SellerProfile(req.seller_id, req.item, quantity_available, min_unit_price, list_price)
    record.negotiation = await negotiate(buyer, seller)
    await save_transaction(record)

    if not record.negotiation.agreed:
        record.status = "halted"
        await save_transaction(record)
        return record

    # --- Step 4a: auditor re-verifies both parties' IDENTITY before settlement ---
    record.auditor_verification = await ans_client.verify(req.auditor_id, AgentRole.auditor)
    recheck_buyer = await ans_client.verify(buyer_id, AgentRole.buyer)
    recheck_seller = await ans_client.verify(req.seller_id, AgentRole.seller)
    await save_transaction(record)

    if not (recheck_buyer.verified and recheck_seller.verified and record.auditor_verification.verified):
        record.status = "halted"
        await save_transaction(record)
        return record

    # --- Step 4b: auditor independently reviews the DEAL ITSELF, not just identity ---
    # A verified-but-compromised (or buggy) agent could still negotiate a bad
    # deal — this is a separate check from identity, and is what makes the
    # auditor a real third agent rather than a formality.
    record.audit = await audit(
        item=req.item,
        max_price=max_unit_price,
        qty_needed=quantity_needed,
        min_price=min_unit_price,
        list_price=list_price,
        qty_available=quantity_available,
        negotiation=record.negotiation,
    )
    await save_transaction(record)

    if not record.audit.approved:
        record.status = "halted"
        await save_transaction(record)
        return record

    # --- Step 5: settle on Solana devnet ---
    record.status = "settling"
    await save_transaction(record)

    record.settlement = await settle(
        unit_price=record.negotiation.final_unit_price,
        quantity=record.negotiation.final_quantity,
    )
    record.status = "complete" if record.settlement.success else "halted"
    await save_transaction(record)

    return record


@router.get("/transactions/{transaction_id}")
async def get_txn(transaction_id: str) -> dict:
    doc = await get_transaction(transaction_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="transaction not found")
    return doc


@router.get("/transactions")
async def get_all_txns(limit: int = 20) -> list[dict]:
    return await list_transactions(limit)
