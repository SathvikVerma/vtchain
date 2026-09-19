"""Pydantic models shared across agents, routes, and Mongo logging.

Person B: this is the contract everyone else builds against. Keep it stable;
add fields rather than renaming once others depend on it.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    buyer = "buyer"
    seller = "seller"
    auditor = "auditor"


class VerificationResult(BaseModel):
    agent_id: str
    role: AgentRole
    verified: bool
    ans_domain: Optional[str] = None
    checked_at: datetime = Field(default_factory=datetime.utcnow)
    reason: Optional[str] = None  # populated when verified=False


class Offer(BaseModel):
    round: int
    from_role: AgentRole
    unit_price: float
    quantity: int
    message: str  # human-readable rationale, from Gemini
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class NegotiationResult(BaseModel):
    agreed: bool
    final_unit_price: Optional[float] = None
    final_quantity: Optional[int] = None
    rounds: list[Offer] = Field(default_factory=list)
    reason: Optional[str] = None  # populated when agreed=False


class AuditResult(BaseModel):
    approved: bool
    reasoning: str
    flags: list[str] = Field(default_factory=list)  # e.g. "price_outside_normal_range"
    audited_at: datetime = Field(default_factory=datetime.utcnow)


class SettlementResult(BaseModel):
    success: bool
    tx_signature: Optional[str] = None
    explorer_url: Optional[str] = None
    lamports_transferred: Optional[int] = None
    error: Optional[str] = None
    settled_at: datetime = Field(default_factory=datetime.utcnow)


class TransactionRecord(BaseModel):
    """One full run of the pipeline — what gets logged to MongoDB and shown
    on the dashboard."""

    transaction_id: str
    buyer_id: str
    seller_id: str
    auditor_id: Optional[str] = None

    buyer_verification: Optional[VerificationResult] = None
    seller_verification: Optional[VerificationResult] = None
    auditor_verification: Optional[VerificationResult] = None

    negotiation: Optional[NegotiationResult] = None
    audit: Optional[AuditResult] = None
    settlement: Optional[SettlementResult] = None

    status: str = "pending"  # pending -> verifying -> negotiating -> settling -> complete | halted
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
