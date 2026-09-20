# Parley — Verified Agentic Supply Chain

VTHacks 14 project. Three autonomous agents (Buyer, Seller, Auditor) verify each
other's identity via GoDaddy ANS, negotiate terms via Gemini, and settle on
Solana devnet — a fraud-resistant, auditable trade with no human in the loop.

## Sponsor tracks targeted (3, per submission cap)
1. GoDaddy — Best Use of ANS
2. Solana — Best Use of Solana
3. Google — Best Use of Gemini API

## Architecture

```
backend/
  app/
    agents/         Buyer, Seller, Auditor agent logic (Gemini-powered negotiation)
    ans/             GoDaddy ANS identity registration + verification adapter
    solana_client/   Devnet wallet setup + settlement transfer
    models/          Pydantic models + Mongo schema
    routes/          FastAPI endpoints tying it all together
    main.py          FastAPI app entrypoint
frontend/
  index.html         Live dashboard: verify -> negotiate -> settle
```

## Team split (suggested)
- **Person A — Solana**: `app/solana_client/` — devnet wallets, settlement transfer.
  Start here first; it's the biggest unknown.
- **Person B — ANS + backend**: `app/ans/`, `app/routes/`, `app/models/`, Mongo logging.
- **Person C — Agents + frontend**: `app/agents/`, `frontend/`.

## Setup

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your keys
python check_setup.py  # tells you exactly what's still missing, self-serve
uvicorn app.main:app --reload
```

Run `python check_setup.py` anytime — it checks every credential and wallet
against `.env` and prints exactly what's ready and what's blocking a full
live run, so nobody has to guess or ask around.

## Demo flow
1. Buyer and Seller agents register + verify identity via ANS.
2. They negotiate price/terms over Gemini (capped at 4 rounds).
3. On agreement, Auditor re-verifies both parties' identity, THEN
   independently reviews the negotiated deal itself (price in range, real
   back-and-forth vs. suspicious instant acceptance) — a genuinely separate
   check from identity, not a formality. Fails closed on any error.
4. Settlement fires: a real SOL transfer on devnet.
5. Dashboard shows the whole flow live, ending with a Solana Explorer link
   to the actual transaction.
6. Bonus demo moment: feed in a spoofed/unverified agent — negotiation halts
   at the ANS gate. This is the strongest technical flex for judges.

See `PITCH.md` for the full timed pitch script and anticipated Q&A.

## Testing without live credentials

Three offline test suites verify core logic with Gemini/ANS mocked out —
run these first, before touching real API keys, to confirm the control
flow itself is sound:

```bash
cd backend
python -m app.ans.test_ans                    # identity gate: register/verify/reject
python -m app.agents.test_negotiation_offline  # negotiation rounds + JSON parsing
python -m app.agents.test_auditor_offline      # auditor approve/reject logic
```

Once real credentials are in `.env`, the live-network versions are:

```bash
python -m app.agents.test_negotiation   # real Gemini call
python -m app.solana_client.setup_wallets  # real devnet wallets + airdrop
```

## Confirmed sponsor resources (real codes/keys, not placeholders)

- **GoDaddy Registry domain code: `MLH0918VTH`** — use this at checkout when
  registering your domain. This gets you the domain itself (e.g.
  `vtchain.xyz`) at no cost. This is DIFFERENT from ANS credentials below —
  registering the domain doesn't automatically register an agent identity
  against it; you still need ANS API access separately to do that.
- **Vultr credit code: `MAJORLEAUGEHACKING`** — apply at signup for free
  cloud credits. Not currently required for Parley's core build (no
  external hosting needed for the demo — it runs locally against devnet),
  but useful if you want the deployed app reachable by a public URL for
  the judges to poke at, or if Solana devnet RPC calls need to run
  somewhere more stable than a laptop during judging.
- **Google AI Studio (Gemini) API key** — send it over and I'll drop it
  into `.env` (or set `GEMINI_API_KEY` yourself, never share it in a place
  that gets committed to a public repo — see note below).

## Known unknowns — resolve ASAP
- **GoDaddy ANS credentials.** `app/ans/client.py` now has a REAL implementation
  built against ANS's actual documented REST surface (confirmed from
  github.com/agentnameservice — RA registration/status endpoints, static
  API-key auth). It's wired and ready — it just needs your team's
  `ANS_API_BASE_URL` and `ANS_API_KEY` from the GoDaddy hackathon portal/QR
  code slide, dropped into `.env`, then flip `ANS_USE_MOCK=false`. No other
  code changes needed. Until you have those, `ANS_USE_MOCK=true` (the
  default) keeps the whole pipeline fully demoable with identical behavior.

  One scope decision worth knowing and repeating to judges if asked: the
  full ANS spec includes a heavy PKI + transparency-log verification chain
  (mTLS, DPoP, SCITT receipts, Merkle proofs) — genuinely too much to
  implement from scratch overnight. We check "is this agent currently
  registered and active with the RA," which is real and honest, just not
  the full zero-trust cryptographic proof. Framed correctly in the pitch,
  this reads as mature scoping, not a shortcut.

  webmesh.ai is public ANS-registered agents you can point at for a live,
  external interoperability demo moment if time allows — it's not a
  registry you register against, but it's proof the ecosystem is real.

- **GoDaddy free domain — register this ASAP, it's on the critical path.**
  ANS identity is domain-anchored, so a real registered domain (not the
  fake `vtchain.dev` placeholder) is what makes "verified agent identity"
  a true claim instead of a demo fiction. It also separately qualifies for
  the GoDaddy Domain Registry prize — one domain, two prize tables.
  1. Register one domain (e.g. `vtchain.xyz` or similar — short, on-theme).
  2. Set `ANS_ROOT_DOMAIN=<your domain>` in `.env`.
  3. Each agent is anchored as a subdomain automatically:
     `buyer.<domain>`, `seller.<domain>`, `auditor.<domain>` — no code
     changes needed, `app/routes/pipeline.py` already derives these from
     `ANS_ROOT_DOMAIN`.
  4. You don't need working DNS/hosting on the subdomains for the demo to
     run — ANS registration just needs the domain to exist and (per the
     real spec) be verifiable as under your control. If GoDaddy's RA
     requires actual DNS verification (a TXT record, etc.), that's worth
     confirming early — it's a 5-minute DNS change if so, but better to
     know tonight than at 8am.
