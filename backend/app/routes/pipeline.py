"""The core pipeline endpoint: verify -> negotiate -> re-verify -> settle.

This is the single call the frontend dashboard drives. Every step is logged
to Mongo as it happens (not just at the end) so the dashboard can poll
GET /transactions/{id} and show live progress.
"""
from __future__ import annotations

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

    # --- Step 1: register identities (skip buyer if we're demoing a spoof) ---
    # Each agent is anchored as a subdomain of our one real GoDaddy-registered
    # domain (settings.ans_root_domain) — e.g. buyer.vtchain.xyz — which is
    # what makes "domain-anchored identity" a real claim instead of a fake
    # placeholder like buyer.vtchain.dev.
    root = settings.ans_root_domain
    if not req.simulate_spoof:
        await ans_client.register(req.buyer_id, AgentRole.buyer, f"buyer.{root}")
    await ans_client.register(req.seller_id, AgentRole.seller, f"seller.{root}")
    await ans_client.register(req.auditor_id, AgentRole.auditor, f"auditor.{root}")

    # --- Step 2: verify buyer + seller before any negotiation happens ---
    record.buyer_verification = await ans_client.verify(req.buyer_id, AgentRole.buyer)
    record.seller_verification = await ans_client.verify(req.seller_id, AgentRole.seller)
    await save_transaction(record)

    if not (record.buyer_verification.verified and record.seller_verification.verified):
        record.status = "halted"
        await save_transaction(record)
        return record  # HALT — this is the "spoofed identity stops the trade" demo moment

    # --- Step 3: negotiate ---
    record.status = "negotiating"
    await save_transaction(record)

    buyer = BuyerProfile(req.buyer_id, req.item, req.quantity_needed, req.max_unit_price)
    seller = SellerProfile(req.seller_id, req.item, req.quantity_available, req.min_unit_price, req.list_price)
    record.negotiation = await negotiate(buyer, seller)
    await save_transaction(record)

    if not record.negotiation.agreed:
        record.status = "halted"
        await save_transaction(record)
        return record

    # --- Step 4a: auditor re-verifies both parties' IDENTITY before settlement ---
    record.auditor_verification = await ans_client.verify(req.auditor_id, AgentRole.auditor)
    recheck_buyer = await ans_client.verify(req.buyer_id, AgentRole.buyer)
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
        max_price=req.max_unit_price,
        qty_needed=req.quantity_needed,
        min_price=req.min_unit_price,
        list_price=req.list_price,
        qty_available=req.quantity_available,
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
