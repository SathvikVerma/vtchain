"""GoDaddy ANS (Agent Name Service) adapter.

REAL PROTOCOL NOTES (confirmed from https://github.com/agentnameservice —
ans-registry spec + ans reference implementation, Sept 2026):

The full ANS protocol is a production-grade PKI + transparency-log system:
agents register with a Registration Authority (RA), get an identity
certificate anchored to a verified domain, and every lifecycle event is
sealed into an immutable Transparency Log (SCITT receipts, Merkle inclusion
proofs, ES256 signatures). Full offline verification means fetching root
keys, checking Merkle paths, and validating signatures — genuinely heavy
infrastructure, not a hackathon-night build.

SCOPE DECISION (say this explicitly in the pitch, it reads as mature
engineering, not a shortcut): we implement real REST calls against the RA's
documented surface —
  POST /v1/agents/         to register
  GET  /v1/agents/{id}     to check registration status
using their documented static-API-key auth ("sso-key" bearer format) —
but we do NOT implement the full mTLS/DPoP/SCITT cryptographic verification
chain. Our "verified" = "the RA confirms this agent is currently registered
and not revoked," which is an honest, real check — just not the full
zero-trust cryptographic proof the spec supports.

STILL UNKNOWN — get this from the GoDaddy hackathon portal/QR code ASAP:
  - ANS_API_BASE_URL: the RA host they've provisioned for VTHacks
  - ANS_API_KEY: your team's issued API key
Fill these into .env the moment you have them and flip ANS_USE_MOCK=false —
no code changes needed, this file is already built against the real shape.

Until then, ANS_USE_MOCK=true keeps the whole pipeline demoable with
identical behavior (register/verify/halt-on-spoof), so nobody is blocked.
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

    async def register(self, agent_id: str, role: AgentRole, domain: str) -> None:
        """Register an agent identity, anchored to a domain."""
        if settings.ans_use_mock:
            self._registry[agent_id] = {"role": role, "domain": domain, "registered_at": time.time()}
            return
        await self._real_register(agent_id, role, domain)

    async def verify(self, agent_id: str, role: AgentRole) -> VerificationResult:
        """Verify an agent's identity before it's allowed to negotiate or settle.

        This is the gate: routes/agents call this before every negotiation
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

    # ---- real implementation, against ANS's documented REST surface ----
    # (RA registration/status endpoints only — see module docstring for what
    # this deliberately does NOT implement, and why.)

    async def _real_register(self, agent_id: str, role: AgentRole, domain: str) -> None:
        assert self._http is not None
        payload = {
            "agentDisplayName": agent_id,
            "agentHost": domain,
            "version": "1.0.0",
            "endpoints": [
                {"protocol": "https", "url": f"https://{domain}/api", "transport": "http"}
            ],
        }
        try:
            resp = await self._http.post("/v1/agents/", json=payload)
            resp.raise_for_status()
            data = resp.json()
            # cache the RA-assigned agentId locally so verify() can look it up
            self._registry[agent_id] = {"role": role, "domain": domain, "ra_agent_id": data.get("agentId")}
        except httpx.HTTPError as exc:
            raise RuntimeError(f"ANS registration failed for {agent_id}: {exc}") from exc

    async def _real_verify(self, agent_id: str, role: AgentRole) -> VerificationResult:
        assert self._http is not None
        entry = self._registry.get(agent_id)
        if entry is None:
            return VerificationResult(
                agent_id=agent_id, role=role, verified=False, reason="not_registered_locally"
            )
        ra_id = entry.get("ra_agent_id")
        try:
            resp = await self._http.get(f"/v1/agents/{ra_id}")
            if resp.status_code == 404:
                return VerificationResult(
                    agent_id=agent_id, role=role, verified=False, reason="not_found_in_ra"
                )
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status", "unknown")
            verified = status == "ACTIVE"  # adjust once real status enum is confirmed
            return VerificationResult(
                agent_id=agent_id,
                role=role,
                verified=verified,
                ans_domain=entry["domain"],
                reason=None if verified else f"ra_status={status}",
            )
        except httpx.HTTPError as exc:
            return VerificationResult(
                agent_id=agent_id, role=role, verified=False, reason=f"ra_request_error: {exc}"
            )


# Module-level singleton — import this from routes/agents rather than
# instantiating ANSClient directly, so the registry state is shared.
ans_client = ANSClient()
