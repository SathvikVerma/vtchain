# Parley — Demo Video Script

Target length: **2:30–3:00** (Devpost/MLH videos typically cap around 3
min — check VTHacks' exact submission rules, but this length is safe).
This is scripted tighter than `PITCH.md` (the live judging pitch) because
a video has no room for live Q&A and needs to hold attention with zero
dead air.

## Before you hit record — setup checklist
- [ ] Backend running (`uvicorn app.main:app --reload`), dashboard loaded
      and confirmed working in a full, successful run beforehand — **do a
      full dry run first**, including a devnet airdrop check, so you're
      not debugging live on camera
- [ ] Solana Explorer tab pre-opened in the background (faster cut than
      waiting for a new tab to load)
- [ ] Screen resolution set so dashboard text is readable in the recording
- [ ] Quiet room / decent mic — narration clarity matters more than visual
      polish for a 3-minute technical demo
- [ ] Have the spoof-toggle demo run ready as a SECOND take/segment — if
      something flakes on one run, you can splice, but plan to record both
      the clean run and the spoof-halt run as separate clips up front

## Shot list & script

### [0:00–0:15] Cold open — hook, no dashboard yet
**Visual:** Face cam or a simple title card with "Parley" — whichever
your team is more comfortable with on camera.
**Narration:**
> "Supply chains lose billions of dollars a year to fraud — because most
> B2B deals still trust a name on an invoice, not a verified identity.
> We built a supply chain where AI agents can't even start negotiating
> until they prove who they are — and every deal settles instantly, with
> a receipt anyone can check. This is Parley."

### [0:15–0:35] The problem, fast
**Visual:** Can stay on face cam, or cut to a simple slide with the two
sponsor quotes if you made one — optional, skip if it slows you down.
**Narration:**
> "Two sponsors here separately described the same gap: GoDaddy wants
> agents that can verify each other's identity before doing business.
> Solana wants a real prototype for supply chain and payments at scale.
> Those aren't two problems — they're one. You can't automate trust
> without both halves."

### [0:35–2:20] Live dashboard walkthrough — THE MAIN EVENT
**Visual:** Screen recording, dashboard front and center. Cursor visible,
move deliberately — no fast mouse movements, viewers need to track what
you're clicking.

**[0:35]** Click "Run pipeline."
> "Watch all four stages happen live, no human in the loop after this
> click."

**[0:45] Step 1 lights up — identity verification**
> "Our Buyer and Seller agents are checking in with GoDaddy's Agent Name
> Service — a real identity system anchored to a domain we actually
> registered. This isn't a fake login screen."

**[1:00] Step 2 — negotiation rounds stream in**
> "Now they're negotiating with Gemini. The buyer has a real budget cap,
> the seller has a real price floor — they're reasoning independently
> and closing the gap round by round."
(Let 1-2 rounds actually render on screen before cutting — don't talk
over silence, but don't rush past the actual offers appearing either.)

**[1:35] Step 3 — Auditor review**
> "Here's the part we're most proud of. A third agent, who had zero part
> in the negotiation, independently reviews the deal itself — not just
> 'are you who you say you are,' but 'does this deal actually make
> sense.' If anything looks wrong, it stops right here."
(If the auditor's reasoning text is good, let it sit on screen for a
beat — read a phrase of it aloud if it's punchy.)

**[2:00] Step 4 — settlement, THE PAYOFF SHOT**
> "And now — real money moves. Not a database row. A real, signed
> transaction on Solana."
Click through to the Solana Explorer link.
> "This is public. Anyone — including you — can verify this transaction
> actually happened."
(Hold on the Explorer page for 2-3 full seconds. This is your best visual
proof moment — don't rush the cut.)

### [2:20–2:45] The flex moment — spoof demo
**Visual:** Cut to the second recorded take — toggle "Simulate spoofed
buyer identity," click Run again.
**Narration:**
> "And if we can't verify who you are? Nothing happens. Watch."
(Let it visibly halt at Step 1 on screen — don't narrate over the halt
itself, let the red/failed state speak for a beat.)
> "No negotiation. No settlement. That's the whole point."

### [2:45–3:00] Close
**Visual:** Back to face cam, or hold on the finished dashboard.
**Narration:**
> "Parley: verified identity, real negotiation, provable settlement —
> commerce machines can actually trust. Thanks for watching."

## Editing notes
- Cut dead air aggressively between stages — the negotiation rounds in
  particular can run long in real time; speed up or trim clips where
  nothing new is happening on screen.
- Keep captions/subtitles on if you have time — a lot of judges skim
  videos with sound off first.
- Don't over-produce this. A clean, well-narrated screen recording beats
  flashy editing for a technical demo — judges want to see the thing
  actually work, not a highlight reel that obscures whether it's real.
- If the live Gemini/Solana calls are ever flaky on the recording day,
  it's fine to note in narration "running against Solana's public devnet,
  so timing can vary" rather than trying to hide a slow response — that
  reads as honest, not amateur.
