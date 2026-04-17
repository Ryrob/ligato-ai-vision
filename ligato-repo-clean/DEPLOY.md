# Deploy — Ligato AI Vision (test site)

Two pieces to stand up:

1. **Static site** → GitHub Pages (free, public). You'll see the marketing + interactive prototype at `https://ryrob.github.io/ligato-ai-vision/`.
2. **Backend** → Render.com (free tier) or Fly.io. Needed for the Twilio voice + MMS flow to actually work end-to-end. The prototype UI works without it — it's all scripted client-side — so you can ship the static site first and add the backend when you're ready.

Total time: ~10 minutes for the static site, ~20 minutes for backend + Twilio.

---

## Step 1 · Push to GitHub (once)

The folder you have is ready to push. From inside `ligato-ai-vision/`:

```bash
git init
git branch -M main
git add .
git commit -m "Initial Ligato AI Vision prototype"

# Create a new empty repo at https://github.com/new named "ligato-ai-vision"
# (leave it empty — no README, no .gitignore, no license). Then:

git remote add origin https://github.com/Ryrob/ligato-ai-vision.git
git push -u origin main
```

> Shortcut: open https://github.com/new?name=ligato-ai-vision&visibility=public to pre-fill the form.

---

## Step 2 · Turn on GitHub Pages (30 seconds)

1. Open `https://github.com/Ryrob/ligato-ai-vision/settings/pages`
2. Under **Source**, pick **Deploy from a branch**.
3. Branch: `main`, Folder: `/ (root)`. Save.
4. Wait ~60 seconds. Your URLs:
   - Landing page: `https://ryrob.github.io/ligato-ai-vision/`
   - Prototype: `https://ryrob.github.io/ligato-ai-vision/prototype.html`

> The `.nojekyll` file in this repo tells GitHub Pages to serve files as-is (no Jekyll processing). Already included.

That's enough to share the prototype link and walk anyone through the flow.

---

## Step 3 · Deploy the backend on Render (~10 min)

The backend is a FastAPI service that handles Twilio webhooks and talks to Claude.

1. Sign up / log in at **[render.com](https://render.com)** with your GitHub account.
2. **New → Blueprint**. Point it at the `Ryrob/ligato-ai-vision` repo. It'll auto-detect `backend/render.yaml`.
3. When prompted, paste the values for the secrets marked `sync: false` in the blueprint:
   - `ANTHROPIC_API_KEY` — from https://console.anthropic.com
   - `TWILIO_ACCOUNT_SID` + `TWILIO_AUTH_TOKEN` — from https://console.twilio.com
   - `TWILIO_PHONE_NUMBER` — the number you'll use, E.164 format (e.g. `+15550120199`)
   - `PUBLIC_BASE_URL` — leave blank for now; you'll fill it in step 4.
4. Click **Apply**. First build takes ~3 min. You'll get a URL like `https://ligato-ai-vision.onrender.com`.
5. Go back to the service's **Environment** tab and set `PUBLIC_BASE_URL` to that URL. Redeploy.

> **Free tier caveat.** Render's free plan spins services down after 15 min of idle, adding ~30s cold-start on the next Twilio webhook. Fine for testing; upgrade to Starter ($7/mo) for real use. Alternative: Fly.io (`fly launch` in `backend/`, then `fly secrets set ...`).

---

## Step 4 · Wire up Twilio (~5 min)

You need one Twilio phone number that supports **both Voice and MMS**. Most US local numbers do. If yours doesn't, buy a new one under **Phone Numbers → Buy a number** and filter for MMS capable.

1. In Twilio, open your number's **Configure** page.
2. Under **Voice & Fax**:
   - **A CALL COMES IN** → Webhook → `https://<your-render-url>/voice/incoming` · HTTP POST
   - **CALL STATUS CHANGES** → `https://<your-render-url>/voice/status` · HTTP POST
3. Under **Messaging**:
   - **A MESSAGE COMES IN** → Webhook → `https://<your-render-url>/sms/incoming` · HTTP POST
4. Save.

Call the number from your cell phone and say "my kitchen faucet is leaking." Alex should answer, ask you to text a photo, and keep guiding once you do.

---

## Step 5 · Test checklist

- [ ] Static site loads at `https://ryrob.github.io/ligato-ai-vision/`.
- [ ] Prototype animations work (click through the steps).
- [ ] Calling your Twilio number reaches Alex's greeting.
- [ ] Alex requests a photo mid-call and you get an MMS from your Twilio number.
- [ ] Texting a photo back returns `"Got it — reviewing now ✅"` within 2 seconds.
- [ ] Alex picks back up on the call and references what she saw.

If step 4 fails, check Render logs (**Logs** tab) and Twilio's request inspector (**Monitor → Logs → Errors**).

---

## Troubleshooting cheatsheet

| Symptom | Likely cause |
|---|---|
| Twilio says "Application error" when you call | `PUBLIC_BASE_URL` not set or wrong; webhook returned 500 — check Render logs |
| MMS arrives blank / no analysis happens | `ANTHROPIC_API_KEY` wrong or out of credit |
| Alex never asks for a photo | Tool call not firing — check the voice system prompt in `backend/app/prompts.py` |
| Cold start > 30s on first call | You're on Render free; upgrade to Starter or switch to Fly.io |
| MMS sends but customer never receives | Twilio number doesn't support MMS in their carrier region |

---

## Teardown

- GitHub Pages: Settings → Pages → Source → None.
- Render: delete the service from the dashboard.
- Twilio: release the number.
- Anthropic: rotate the API key.

No long-term resources left behind.
