# Devpost Submission Draft — VTChain

*Copy each section into the matching Devpost field. Fill in [bracketed] placeholders before submitting.*

---

## Project name
VTChain

## Elevator pitch (one line, ~120 chars)
Verified AI agents that negotiate and settle real supply-chain deals — identity-gated, Gemini-powered, Solana-settled.

## Submission tracks (select exactly these 3 — VTHacks caps entries at 3)
- [ ] GoDaddy — Best Use of ANS
- [ ] Solana — Best Use of Solana
- [ ] Google — Best Use of Gemini API

## Inspiration

Two sponsors at this hackathon independently described the same real-world
gap in their own challenge prompts. GoDaddy asked for agents that
"discover, verify, and communicate with other agents... using ANS for
domain-anchored, verifiable identity" — with examples ranging from
verified ticket resale to agent-to-agent commerce. Solana asked for "a
prototype for supply chain, identity, or payments that can handle massive
real-world volume."

We realized these aren't two separate problems — they're one problem with
two halves. Global supply chains lose billions of dollars a year to
counterfeit sellers, fraudulent buyers, and disputes that come down to "we
can't actually prove who we were dealing with." You can't safely automate
commerce between parties who can't prove their identity, and you can't
prove a deal really happened without a settlement record nobody can fake
after the fact. So we built both halves as one working system.

## What it does

VTChain simulates a fraud-resistant B2B supply chain transaction between
three autonomous AI agents — a Buyer, a Seller, and an independent Auditor
— with no human in the loop:

1. **Identity verification** — before any negotiation can start, Buyer and
   Seller each verify their identity through GoDaddy's Agent Name Service
   (ANS), anchored to a real domain we registered. An unverified or
   spoofed agent is rejected immediately — the pipeline halts before a
   single offer is made.
2. **Negotiation** — the Buyer (with a real budget ceiling) and Seller
   (with a real price floor) negotiate price and quantity using Gemini,
   reasoning independently within their own constraints across a capped
   number of rounds.
3. **Independent audit** — a third agent, who was not part of the
   negotiation, reviews the *agreed deal itself* — not just identities —
   checking whether the final price and terms actually make sense, and
   flagging anything that looks suspicious (a price outside range, a deal
   that closed with no real back-and-forth). This is a genuinely separate
   check from identity verification, and it fails closed on any error.
4. **Settlement** — once approved, funds actually move: a real, signed SOL
   transaction fires on the Solana devnet. Not a database row claiming a
   trade happened — a transaction anyone can independently verify on
   Solana Explorer.

A live dashboard shows all four stages in real time, and includes a toggle
to simulate a spoofed buyer identity — demonstrating the system correctly
halting before any negotiation or money movement occurs.

## How we built it

- **Backend:** Python, FastAPI, MongoDB Atlas (every verification,
  negotiation round, audit decision, and settlement is logged in order for
  a full auditable trail)
- **Identity:** GoDaddy's Agent Name Service — agents are registered and
  verified as subdomains of a real domain we registered through GoDaddy's
  hackathon domain offer
- **Reasoning:** Google Gemini API — powers both the Buyer/Seller
  negotiation logic (structured JSON responses, capped at 4 rounds so it
  always terminates) and the independent Auditor's deal review
- **Settlement:** Solana devnet, via `solders` — a real signed
  wallet-to-wallet transaction, not a simulation
- **Frontend:** a lightweight live dashboard (vanilla JS) polling the
  pipeline as it runs

We built and unit-tested every stage's logic offline first (with the LLM
calls mocked) before wiring in live credentials, which let us catch and
fix two real bugs early: a fully-deprecated Gemini SDK we had to migrate
off of, and a Solana transaction-building API mismatch against
current library versions.

## Challenges we ran into

- **The real ANS protocol is a full production-grade system** — PKI-based
  identity certificates, mTLS, DPoP, and a cryptographic transparency log
  with Merkle inclusion proofs. Implementing that in full was out of scope
  for a weekend. We made a deliberate, documented engineering decision:
  implement real calls against ANS's registration/status REST endpoints
  (confirming an agent is currently registered and active), rather than
  the full zero-trust cryptographic verification chain. It's an honest
  simplification, not a hidden shortcut, and we can speak to exactly where
  the line is if asked.
- **Library version drift** — Solana's Python tooling has changed its
  transaction-building API across versions; code that looked correct
  against older tutorials failed against the currently-installed library.
  Caught by testing against the actual installed versions rather than
  trusting documentation age.
- **Deprecated SDK** — Google's `google-generativeai` package is fully
  sunset; we migrated to the current `google-genai` package mid-build
  after catching the deprecation warning.

## Accomplishments we're proud of

- A working, end-to-end pipeline where identity verification is
  *structurally required*, not decorative — remove it and the whole
  security model collapses, which is exactly the property GoDaddy's
  challenge asked for.
- A settlement step that's actually provable — a real devnet transaction
  with a public, checkable record — instead of a database claim.
- An Auditor that does real independent reasoning about deal legitimacy,
  not just a repeated identity check.
- Catching and fixing real infrastructure bugs (deprecated SDK, library
  API drift) through actual testing rather than shipping untested code.

## What we learned

[Fill in with something genuine from your team — e.g. what surprised you
about building with agent identity systems, working with Gemini's
structured output, or Solana's transaction model for the first time.]

## What's next for VTChain

- Full ANS cryptographic verification chain (mTLS + SCITT transparency log
  proofs), moving from "registered and active" to full zero-trust proof
- More complex, multi-item negotiations with multiple concurrent deals
- A real front-end where human buyers/sellers configure their agents'
  constraints, rather than hardcoded demo values
- Mainnet-readiness review before any real-value deployment

## Built with
Python, FastAPI, MongoDB Atlas, Google Gemini API, GoDaddy Agent Name
Service (ANS), GoDaddy Domain Registry, Solana, solders, HTML/CSS/JS

## Links
- GitHub repo: [your public repo URL — must be public per VTHacks rules]
- Demo video: [record a short screen capture of the live dashboard run,
  including the spoof-halt moment]

---

## Before you submit — checklist
- [ ] Repo is public (VTHacks requires this)
- [ ] `.env` is NOT committed (check `.gitignore` is working:
      `git status` should never show `.env`)
- [ ] Every team member has a Devpost account and is listed as a
      contributor
- [ ] All 3 tracks above are actually selected in the Devpost form
- [ ] Working demo link or video included
- [ ] Libraries/frameworks/open-source code used are credited (this repo's
      README + this file cover that)
