<!--
This is the full Devpost project description — ready to paste directly
into the Devpost "Project Description" rich-text field as one continuous
document. It's the long-form narrative judges read, separate from the
short elevator pitch and the Built With tags (those are in DEVPOST.md).

Only one placeholder left: "What we learned," near the end — that one
needs to be genuinely yours, not something written for you.
-->

## Inspiration

Two sponsors at this hackathon independently described the same real-world
gap in their own challenge prompts. GoDaddy asked for agents that
"discover, verify, and communicate with other agents... using ANS for
domain-anchored, verifiable identity," with examples ranging from verified
ticket resale to agent-to-agent commerce and negotiation. Solana separately
asked for "a prototype for supply chain, identity, or payments that can
handle massive real-world volume."

We realized these aren't two separate asks — they're one problem in two
halves. Global supply chains lose billions of dollars a year to
counterfeit sellers, fraudulent buyers, and disputes that ultimately come
down to one thing: nobody can actually prove who they were dealing with,
or prove a deal really happened afterward. You can't safely automate
commerce between parties who can't verify their identity, and you can't
trust a settlement that's just a claim in someone's database. So instead
of picking one sponsor's challenge, we built the system that answers both
halves at once, because in a real supply chain they're the same problem.

## What it does

VTChain simulates a fraud-resistant, fully autonomous B2B transaction
between three AI agents — a Buyer, a Seller, and an independent Auditor —
with no human in the loop from negotiation to settlement.

**1. Identity verification.** Before a single offer is made, Buyer and
Seller each verify their identity through GoDaddy's Agent Name Service
(ANS), anchored to a real domain we registered through GoDaddy's hackathon
domain offer. If an agent can't be verified — including a deliberately
spoofed identity, which we can demo live — the pipeline halts immediately.
Nothing downstream ever runs.

**2. Negotiation.** Once both parties are verified, the Buyer (working
within a real budget ceiling) and the Seller (working within a real price
floor) negotiate price and quantity using Google's Gemini API. Each agent
reasons independently, proposing and responding to offers in a capped,
deterministic number of rounds so a deal is always reached or the
negotiation cleanly fails — never stuck in limbo.

**3. Independent audit.** This is the piece we think makes VTChain more
than "a chatbot with a wallet." Once Buyer and Seller agree, a third
agent — one that had no part in the negotiation — steps in. It re-verifies
both parties' identity, then goes further: it reviews the *negotiated deal
itself*, checking whether the final price and terms are actually
consistent with what both sides said they needed, and flagging anything
that looks off, like a price outside anyone's stated range or a deal that
closed suspiciously fast with no real back-and-forth. A verified identity
doesn't guarantee a legitimate deal — a compromised or buggy agent could
still negotiate something wrong — so this check is genuinely separate from
identity, and it fails closed: if the auditor itself errors, no funds move.

**4. Settlement.** Only after every one of those checks passes does
anything real happen: a signed SOL transaction fires on the Solana devnet.
This isn't a row in our database claiming a trade occurred — it's a real,
independently verifiable transaction on a public ledger. We show the
Solana Explorer link live in the demo so anyone, including a judge, can
check it themselves.

A live dashboard walks through all four stages as they happen, ending with
that Explorer link — and includes a toggle to simulate a spoofed buyer
identity, so we can show, live, exactly where and why the system refuses
to proceed.

## How we built it

- **Backend:** Python and FastAPI orchestrate the full pipeline —
  identity check, negotiation, audit, settlement — as one coordinated
  flow, with every step logged to **MongoDB Atlas** in order, giving a
  complete, replayable audit trail of each transaction.
- **Identity:** **GoDaddy's Agent Name Service** anchors each agent's
  identity as a subdomain of a real domain we registered. We implemented
  real REST calls against ANS's documented registration and status-check
  endpoints.
- **Reasoning:** **Google's Gemini API** powers two distinct pieces of
  reasoning — the Buyer/Seller negotiation logic (structured JSON output,
  so responses are parsed reliably rather than freeform chat) and the
  independent Auditor's review of the finished deal.
- **Settlement:** **Solana** devnet, via the `solders` library — a real
  signed wallet-to-wallet transaction between two devnet wallets we
  control, not a simulated or faked transfer.
- **Frontend:** a lightweight live dashboard in vanilla HTML/CSS/JS that
  drives the pipeline and renders each stage as it completes.

Before wiring in any live API keys, we wrote and ran offline tests for
every stage of core logic with the LLM calls mocked out — the negotiation
loop's round-handling and JSON parsing, and the auditor's approve/reject
logic. That testing paid off immediately: it's how we caught that Google's
`google-generativeai` SDK had been fully sunset (we migrated to the
current `google-genai` package), and that our Solana transaction-building
code, written against older examples, didn't match the API surface of the
currently installed library version. Both were real bugs that would have
cost us significant time discovering live, mid-demo-prep, instead of
during a controlled test pass.

## Challenges we ran into

The biggest challenge was scoping GoDaddy's ANS honestly. The real ANS
specification is a production-grade identity system — PKI-based
certificates, mTLS, DPoP, and a cryptographic transparency log with
Merkle-proof verification. Implementing that in full was never realistic
for a hackathon weekend, and we didn't want to fake it. So we made a
deliberate, documented decision: implement real calls against ANS's
registration and status-check REST endpoints — confirming an agent is
genuinely registered and active — rather than the full zero-trust
cryptographic proof chain. It's a real, honest check, just not the deepest
layer the spec supports, and we can speak clearly to exactly where that
line sits if asked.

We also hit two infrastructure surprises that turned into good lessons:
Solana's Python tooling has changed its transaction-building API across
versions, so code that matched older tutorials failed against the library
version we actually had installed — caught only by testing against real
installed versions instead of trusting documentation age. And partway
through, we discovered Google's original Gemini Python SDK had been fully
deprecated in favor of a new unified package, which we migrated to
mid-build.

## Accomplishments that we're proud of

- A pipeline where identity verification is *structurally required*, not
  decorative — remove it, and the system's entire security model
  collapses, which is exactly the property a real agent-to-agent commerce
  system needs.
- A settlement step that's actually provable, not just claimed — a real
  devnet transaction with a public, independently checkable record.
- An Auditor agent that does real, independent reasoning about whether a
  deal is legitimate, rather than just repeating an identity check under a
  different name.
- Catching and fixing real infrastructure bugs — a deprecated SDK, a
  library API mismatch — through disciplined testing before they could
  cost us time during the event itself.

## What we learned

[Write this one yourselves — something genuine about what surprised your
team: working with a real agent-identity protocol for the first time,
getting multiple LLM agents to negotiate reliably, building on Solana,
or anything else that was a real discovery this weekend.]

## What's next for VTChain

- Implementing the full ANS cryptographic verification chain — moving from
  "currently registered and active" to full zero-trust proof via mTLS and
  transparency-log receipts.
- Supporting more complex, multi-item negotiations, and multiple
  concurrent deals running in parallel.
- A real front-end where human buyers and sellers configure their agents'
  constraints directly, instead of the fixed demo values we used tonight.
- A full security and mainnet-readiness review before any real-value
  deployment.
