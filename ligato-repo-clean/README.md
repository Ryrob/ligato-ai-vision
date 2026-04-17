# Ligato AI Vision — Project Package

Everything you asked for, organized so you can show it, build it, or hand it off.

## Core idea

Customers already on a voice call with Alex (your AI receptionist) can text a photo to the **same number** when Alex asks for one. A vision model reviews the image in under 5 seconds and feeds the result back into the call so Alex can keep guiding. MMS is strictly the visual channel — confirmations only, never prose. Voice does all the reasoning and guidance.

---

## What's in this folder

### Interactive HTML (open in any browser)

- **`prototype.html`** — Interactive customer-facing prototype. Two modes: Voice + MMS (default), and Live Video + Screen Share. Click the steps on the right to drive the demo. Shows a voice-call transcript, a phone with the MMS thread, and a live event log — all staying in sync with the scripted scenario.
- **`marketing.html`** — A new "AI Vision Assistant" product page styled to match the Ligato marketing site. Same hero/footer/cards structure you're using on `ai-chat-widget`, `ai-text-sms`, and `ai-voice-phone`. Drop in when you're ready to launch.

### Documents

- **`Technical_Architecture.docx`** — System diagram, component responsibilities, sequence of the happy path, latency budget, unit economics, security, rollout plan.
- **`Product_Spec.docx`** — PRD: problem, users, design principles, full voice + MMS script, edge cases, KPIs, open questions.
- **`Pitch_Deck.pptx`** — 10-slide deck for your internal team or investors. Cover, problem, insight, product, how-it-works, sample call, architecture, unit economics, risks, rollout/ask. (`Pitch_Deck.pdf` is a rendered preview.)

### Code

- **`backend/`** — Runnable FastAPI scaffold: Twilio voice + messaging webhooks, Claude tool-use voice agent, Claude vision pipeline, WebRTC signaling stub. See `backend/README.md` for setup.

---

## How to read this in 10 minutes

1. Open **`prototype.html`** — click "Run next step" 4–5 times on the default Voice + MMS tab. You'll see the end-to-end emergency-leak flow play out.
2. Skim **`Pitch_Deck.pdf`** (or open the `.pptx` if you want to edit).
3. If you want the depth: the **Product_Spec.docx** is the PRD, and **Technical_Architecture.docx** is the build spec.

---

## Notes on design

- The Ligato logo mark, nav structure, product cards, and "one plan, everything included" tone are matched to `getligato.com` as closely as I could without access to your exact brand tokens. **Swap the hex values in the `:root` block at the top of each HTML file** (`--brand`, `--accent`, `--ink`) to dial in your exact brand. Same for the PPTX — colors live in the `COLOR` object in the build script.
- Fonts are Inter on the web, Calibri/Georgia on the deck, Arial in the Word docs. Safe across Office and PowerPoint on any machine.
- The prototype and marketing page are single-file HTML — no build step, no dependencies.

---

## Next steps (when you're ready)

1. Replace placeholder colors/fonts with Ligato's exact brand tokens.
2. Stand up the backend and point a throwaway Twilio number at it for internal dogfooding.
3. Get 2–3 friendly plumbing customers into beta (see the rollout plan in the architecture doc).
4. Add HVAC and electrical prompt variants in phase 2 — the code is trade-agnostic, only `prompts.py` changes.

If you want edits to any of this — tone, colors, removing the live-video mode for v1, different model choices — just let me know.
