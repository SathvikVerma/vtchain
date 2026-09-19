"""GoDaddy ANS (Agent Name Service) adapter.

REAL PROTOCOL — CONFIRMED AND LIVE (Sept 2026):

All three of our agents (buyer, seller, auditor) are registered for real
against GoDaddy's PRODUCTION Agent Name Service, anchored to our real
registered domain, brownsugar.design:

    ans://v1.0.0.buyer.brownsugar.design
    ans://v1.0.0.seller.brownsugar.design
    ans://v1.0.0.auditor.brownsugar.design

Registration itself is a one-time, CSR-based flow done OUTSIDE this app,
via GoDaddy's official `ans-cli` tool:
  1. `ans-cli generate-csr` — generates an identity cert (EC P-256) + a
     server cert (RSA 2048) locally, never sent anywhere.
  2. `ans-cli register` — submits the CSRs + endpoint info to GoDaddy's RA
     (https://api.godaddy.com), which returns a real agent UUID.
  3. Domain ownership proof: an ACME DNS-01 challenge (`_acme-challenge.<host>`
     TXT record), verified via `ans-cli verify-acme`.
  4. Discovery/trust records: `_ans.<host>` and `_ans-badge.<host>` TXT
     records (+ an HTTPS record and a TLSA cert-binding record), verified
     via `ans-cli verify-dns` — at which point the agent's status flips to
     ACTIVE and GoDaddy issues real identity + server certificates.

That CSR-based flow is genuinely heavy infra and isn't something to redo on
every pipeline run — it's a one-time identity provisioning step, exactly
like registering a TLS cert. So in real mode, THIS APP's register() is a
no-op: the identities already exist. What this app does per-run is the
actual trust-critical operation — VERIFY that an agent claiming to be
buyer-001 is (a) one of our real, pre-provisioned ANS identities at all,
and (b) still ACTIVE (not revoked) according to GoDaddy's RA, right now,
before letting it negotiate or settle.

Our internal agent_id strings (e.g. "buyer-001") are mapped to their real
GoDaddy-assigned UUIDs via settings.ans_{role}_agent_id. An agent_id NOT in
that map (e.g. a spoofed one-off id used to simulate an attacker) fails
verification immediately, before ever calling GoDaddy — that's the
"unregistered/unverified identity halts the trade" demo moment, now backed
by a real identity system instead of a mock dict.

Set ANS_USE_MOCK=true to fall back to the in-memory mock (useful offline /
if GoDaddy's API is unreachable during the demo).
"""
from __future__ import annotations

import time
from typing import Optional

import httpx

from ..config import settings
from ..models.schemas import AgentRole, VerificationResult


class ANSClient:
    def __init__(self) -> None:
        self._registry: dict[str, dict] = {}  # mock in-memory store
        self._http: Optional[httpx.AsyncClient] = None
        if not settings.ans_use_mock:
            self._http = httpx.AsyncClient(
                base_url=settings.ans_api_base_url,
                headers={"Authorization": f"sso-key {settings.ans_api_key}"},
                timeout=10.0,
            )
        # our internal agent_id -> real GoDaddy ANS agent UUID
        self._real_agent_ids: dict[str, str] = {
            k: v
            for k, v in {
                "buyer-001": settings.ans_buyer_agent_id,
                "seller-001": settings.ans_seller_agent_id,
                "auditor-001": settings.ans_auditor_agent_id,
            }.items()
            if v
        }

    async def unregister(self, agent_id: str) -> None:
        """Remove a mock registration — used to force a clean 'spoofed/unverified'
        state for the demo, since agent_id is otherwise reused across runs and
        would still show as verified from an earlier successful run."""
        self._registry.pop(agent_id, None)

    async def register(self, agent_id: str, role: AgentRole, domain: str) -> None:
        """Register an agent identity, anchored to a domain.

        In real mode this is a no-op: real ANS registration is a one-time,
        CSR-based flow done externally via `ans-cli` (see module docstring),
        not something we redo on every pipeline run. The identity already
        exists in GoDaddy's system by the time this app runs.
        """
        if settings.ans_use_mock:
            self._registry[agent_id] = {"role": role, "domain": domain, "registered_at": time.time()}
            return
        # real mode: nothing to do — identity is already provisioned.
        return

    async def verify(self, agent_id: str, role: AgentRole) -> VerificationResult:
        """Verify an agent's identity before it's allowed to negotiate or settle.

        This is the gate: routes/pipeline calls this before every negotiation
        round and again before settlement, and HALT on failure — that
        halt-on-spoof behavior is the strongest demo moment we have.
        """
        if settings.ans_use_mock:
            entry = self._registry.get(agent_id)
            if entry is None:
                return VerificationResult(
                    agent_id=agent_id,
                    role=role,
                    verified=False,
                    reason="unregistered_identity",
                )
            return VerificationResult(
                agent_id=agent_id,
                role=role,
                verified=True,
                ans_domain=entry["domain"],
            )
        return await self._real_verify(agent_id, role)

    # ---- real implementation, against GoDaddy's production ANS RA ----

    async def _real_verify(self, agent_id: str, role: AgentRole) -> VerificationResult:
        assert self._http is not None

        ra_id = self._real_agent_ids.get(agent_id)
        if ra_id is None:
            # Not one of our real, pre-provisioned ANS identities at all —
            # this is what catches a spoofed/unrecognized agent_id.
            return VerificationResult(
                agent_id=agent_id, role=role, verified=False, reason="unregistered_identity"
            )

        try:
            resp = await self._http.get(f"/v1/agents/{ra_id}")
            if resp.status_code == 404:
                return VerificationResult(
                    agent_id=agent_id, role=role, verified=False, reason="not_found_in_ra"
                )
            resp.raise_for_status()
            data = resp.json()
            # Confirmed from a real response (Sept 2026):
            # {"agentId": ..., "agentHost": "seller.brownsugar.design",
            #  "agentStatus": "ACTIVE", ...} — no "status" field at all.
            status = data.get("agentStatus", "unknown")
            verified = status == "ACTIVE"
            domain = data.get("agentHost")
            return VerificationResult(
                agent_id=agent_id,
                role=role,
                verified=verified,
                ans_domain=domain,
                reason=None if verified else f"ra_status={status}",
            )
        except httpx.HTTPError as exc:
            return VerificationResult(
                agent_id=agent_id, role=role, verified=False, reason=f"ra_request_error: {exc}"
            )


# Module-level singleton — import this from routes/pipeline rather than
# instantiating ANSClient directly, so the registry state is shared.
ans_client = ANSClient()
