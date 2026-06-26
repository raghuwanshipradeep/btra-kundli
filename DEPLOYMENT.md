# Smart Kundli — Production Deployment Architecture

> Deployment scenario: hosting Smart Kundli on a new domain with a dedicated **8 GB RAM** server.
> Audience: ops / deployment. Written as an architecture handoff document.

---

## 1. System Overview

Smart Kundli is a **FastAPI** service that generates Vedic Kundli PDF reports. It is a single deployable app with several external dependencies. The defining architectural trait: **after payment, PDF generation runs as a server-side background job** — decoupled from the user's browser — and the result is archived to Google Drive, with a local recovery fallback if Drive upload fails.

```
                          ┌─────────────────── Your 8GB Server ───────────────────┐
                          │                                                        │
  User browser            │   ┌──────────┐      ┌──────────────────────────────┐  │
  ───────────────────────────▶│ Traefik  │─────▶│  Smart Kundli (FastAPI/      │  │
  HTTPS (kundli.you.com)  │   │ (Coolify │      │  uvicorn) in Docker          │  │
                          │   │  proxy)  │      │   • /verify-and-generate     │  │
  Razorpay webhook ──────────▶│  +SSL    │─────▶│   • /razorpay-webhook        │  │
                          │   └──────────┘      │   • background PDF jobs       │  │
                          │                     │   • WeasyPrint render         │  │
                          │                     └──────┬─────────┬──────┬───────┘  │
                          │                            │         │      │          │
                          │   Persistent volumes:      │         │      │          │
                          │   • /app/recovery  ◀────────┘         │      │          │
                          │   • Drive OAuth token mount           │      │          │
                          └───────────────────────────────────────┼──────┼─────────┘
                                                                   │      │
                       ┌───────────────────────┬───────────────────┘      │
                       ▼                       ▼                          ▼
                 AstrologyAPI            Anthropic (Claude         Google Drive
                 (~100 calls/PDF)         Haiku 4.5 narratives)    (PDF archive)
                                                                   + Pabbly (notify)
```

---

## 2. Server & Infrastructure

### 2.1 Server choice

| Spec | Recommendation | Why |
|---|---|---|
| **Provider** | **Hetzner Cloud (CPX31)** | Best price/performance; EU/US locations |
| **vCPU** | **4 vCPU** | WeasyPrint is CPU/GIL-bound — 4 cores handle bursts |
| **RAM** | **8 GB** | ~6.5 GB usable → comfortably runs 500/day + 10 concurrent |
| **Disk** | **80–160 GB SSD** | OS, Docker images, recovery PDFs, logs |
| **OS** | **Ubuntu 22.04 / 24.04 LTS** | Stable; Coolify-supported |
| **Location** | Closest to your users | Affects form-load latency, not generation |

> **Region note:** Users are India-based. Hetzner is cheapest but EU/US-only (~150–250 ms page-load latency). If local latency matters, use **DigitalOcean Bangalore (BLR1)** or **AWS Lightsail Mumbai** at a higher price. For a form + backend-generated PDF, Hetzner EU is usually fine.

### 2.2 Deployment platform: keep Coolify

Coolify provides Docker orchestration, the Traefik reverse proxy, automatic Let's Encrypt SSL, env var management, persistent volumes, and log viewing — free and self-hosted. No reason to change.

---

## 3. Domain & DNS

1. **Buy the domain** (e.g. `smartkundli.com` or `.in`). Registrars: Namecheap, Cloudflare Registrar, GoDaddy.
2. **Put Cloudflare in front** (free plan) — strongly recommended:
   - Hides the server IP (blocks the `.env` / `.git` scanner bots before they reach you)
   - Free SSL + DDoS protection + basic WAF
   - Caches static assets, exposes real visitor IPs
3. **DNS records:**
   ```
   A     @            → <server-ip>     (proxied via Cloudflare)
   A     www          → <server-ip>     (proxied)
   ```
4. In Coolify, set the app domain to `https://smartkundli.com`; Traefik auto-provisions Let's Encrypt SSL.

> With Cloudflare proxy + Let's Encrypt, set Cloudflare SSL mode to **Full (strict)**.

---

## 4. Application Runtime

The existing `Dockerfile` is production-ready — `python:3.12-slim` + Pango/Cairo libs for WeasyPrint. Coolify builds from it.

- App runs `uvicorn main:app --host 0.0.0.0 --port 3000`.
- `.dockerignore` correctly excludes `.env`, `.git`, `*.db` — **keep it that way**.
- One container is sufficient at 500/day (no replicas needed).

### 4.1 Recommended pre-launch code change: concurrency cap

Add a **global semaphore** so traffic spikes can't OOM the box. For 8 GB / 4 vCPU:

```python
# main.py, module level
_GENERATION_SLOTS = asyncio.Semaphore(5)

async def _generate_and_archive(request, order_id, payment_id):
    async with _GENERATION_SLOTS:
        ...  # existing body
```

Effect: any number of simultaneous payments → max 5 PDFs render at once, the rest queue and complete moments later. Peak RAM ~2.5 GB. **All jobs succeed.**

---

## 5. Configuration & Secrets

Set these in **Coolify → Environment Variables** (never baked into the image):

| Variable | Purpose |
|---|---|
| `ASTRO_API_KEY` | AstrologyAPI (required) |
| `ANTHROPIC_API_KEY` | Claude narratives + Hindi translation |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` | Checkout + verification |
| `RAZORPAY_WEBHOOK_SECRET` | Server-side webhook fulfillment (safety net) |
| `GOOGLE_DRIVE_FOLDER_ID` | Where PDFs archive |
| `DRIVE_ARCHIVE_ENABLED=true` | Enable Drive upload |
| `DRIVE_RECOVERY_DIR=/app/recovery` | **Must match the persistent volume mount (see §6)** |
| `AUTHOR_NAME`, `CTA_*`, `BRAND_FOOTER_*` | Commercial polish sections |
| `ADMIN_KEY` | Protects `/admin/jobs` |
| `KUNDLI_PRICE_PAISE` | Price (e.g. 9900 = ₹99) |

---

## 6. Persistent Storage (critical — prevents losing paid PDFs)

Two volumes must survive redeploys (Coolify → **Persistent Storage**):

| Container path | Purpose |
|---|---|
| `/app/recovery` | Failed-Drive-upload PDFs land here. `DRIVE_RECOVERY_DIR` must equal this exact path. |
| Drive OAuth token mount | `token.json` / credentials so Drive auth survives restarts |

> ⚠️ **Path-match trap:** `DRIVE_RECOVERY_DIR` and the volume mount path must be identical (`/app/recovery`). A mismatch (e.g. env var `/app/data/recovery` while the mount is `/app/recovery`) means failed PDFs write to a non-persistent path and vanish on redeploy.

---

## 7. External Service Wiring (re-do on the new domain)

1. **Razorpay → Webhooks:** point at `https://smartkundli.com/razorpay-webhook` with `RAZORPAY_WEBHOOK_SECRET`. This is the fulfillment safety net — without it, a browser/network drop during checkout can lose a paid order.
2. **Razorpay checkout allowed domains:** add the new domain.
3. **Google Drive OAuth:** re-run the auth flow on the new server; confirm `token.json` lands on the persistent mount.
4. **AstrologyAPI:** confirm the plan's rate limits cover volume (~100 calls per Kundli).
5. **Pabbly notifier:** confirm the webhook URL still fires for CRM/WhatsApp.
6. **Anthropic:** confirm API key tier RPM/TPM covers concurrent narrative bursts.

---

## 8. Security Hardening

- **Cloudflare in front** (§3) — blocks most scanner bots before they reach the server.
- **Server firewall (ufw):** allow only `22` (SSH), `80`, `443`.
- **SSH:** key-only auth, disable password login.
- **`.git` / `.env` never in the image** — handled by `.dockerignore`; never undo.
- **`ADMIN_KEY`** set so `/admin/jobs` isn't public.
- **Coolify `Maximum Memory Limit` ≈ 6 GB** as a backstop, so a pathological spike kills only this container cleanly.

---

## 9. Monitoring, Logging & Backups

- **Logs:** Coolify log viewer. Watch for `DRIVE ARCHIVE MISSING`, `BG TIMEOUT`, `BG PDF FAILED`.
- **Job status:** `/admin/jobs` tracks `archived` / `drive_failed` / `timeout` / `pdf_failed` per order — the operational dashboard.
- **Server backups:** Hetzner automated backups (~20% of server cost) or weekly volume snapshots. Critical for the recovery volume + Drive token mount.
- **Uptime monitoring:** free **UptimeRobot** pinging `/` → alerts on downtime.

---

## 10. Cost Breakdown

### Fixed monthly (infrastructure)

| Item | Cost |
|---|---|
| Hetzner CPX31 (4 vCPU / 8 GB) | ~€15.59 (~$17) / mo |
| Hetzner automated backups (recommended) | ~€3 (~$3) / mo |
| Cloudflare (free) | $0 |
| Coolify (self-hosted) | $0 |
| SSL (Let's Encrypt) | $0 |
| UptimeRobot (free) | $0 |
| Domain (.com, amortized) | ~$1–1.25 / mo (~$12–15/yr) |
| **Fixed subtotal** | **≈ $21–23 / month** |

> India-local alternative: **DigitalOcean Bangalore 8 GB ≈ $48/mo** or **AWS Lightsail Mumbai 8 GB ≈ $44/mo**. Hetzner is ~half the price at EU/US latency.

### Variable monthly (scales with volume)

| Item | Per Kundli | At 100/day | At 500/day |
|---|---|---|---|
| Claude (Haiku 4.5) — verify in console.anthropic.com | ~$0.15–0.25 | ~$450–750/mo | ~$2,250–3,750/mo |
| AstrologyAPI (~100 calls/Kundli) | depends on plan | check plan | likely needs higher tier (50k calls/day) |
| Pabbly / notifications | existing plan | — | — |

> Infrastructure is cheap (~$22/mo); the real cost is **Claude + AstrologyAPI**, both scaling linearly with sales. Lever to cut Claude cost: **prompt caching on the stable narrative system prompts** (cache reads ~10× cheaper).

**Claude pricing reference (Haiku 4.5):** $1.00 / 1M input tokens, $5.00 / 1M output tokens. Cache reads ~$0.10/1M; cache writes ~$1.25/1M (5-min TTL).

### Cost summary

| Volume | Fixed infra | Variable (Claude est.) | + AstrologyAPI | Rough total/mo |
|---|---|---|---|---|
| 100 Kundlis/day | ~$22 | ~$450–750 | + plan cost | **~$500–800+** |
| 500 Kundlis/day | ~$22 | ~$2,250–3,750 | + plan cost | **~$2,300–3,800+** |

> Revenue at ₹99 × 500/day ≈ ₹49,500/day ≈ ~$590/day ≈ **~$17,700/mo** — margins are healthy; API costs are a fraction of revenue.

---

## 11. Deployment Checklist (execution order)

1. ☐ Provision Hetzner CPX31 (Ubuntu 22.04); harden SSH; enable `ufw` (22/80/443).
2. ☐ Install Coolify on the server.
3. ☐ Buy domain → add to Cloudflare → point A records at server (proxied).
4. ☐ In Coolify: create the app from the Git repo (`stage`/`main`), Dockerfile build.
5. ☐ Set the domain → Traefik auto-issues SSL.
6. ☐ Add all env vars (§5); set `DRIVE_RECOVERY_DIR=/app/recovery`.
7. ☐ Add persistent volumes: `/app/recovery` + Drive token mount (§6).
8. ☐ Set Coolify `Maximum Memory Limit` ≈ 6 GB.
9. ☐ Add the `Semaphore(5)` concurrency cap (§4.1), commit, deploy.
10. ☐ Re-run Google Drive OAuth on the new server; confirm token persists.
11. ☐ Point Razorpay webhook at `https://smartkundli.com/razorpay-webhook`; update allowed domains.
12. ☐ Confirm AstrologyAPI + Anthropic rate limits for the volume.
13. ☐ Smoke test: `/demo` PDF, then a real ₹1 test payment → verify Drive archive + recovery fallback.
14. ☐ Set up UptimeRobot + backups.
15. ☐ Go live; watch `/admin/jobs` and logs for the first day.

---

## 12. Capacity Verdict

On an 8 GB / 4 vCPU dedicated box with the concurrency cap:

- **500/day:** comfortable.
- **10 concurrent:** works cleanly (5 render, 5 queue).
- **Extreme bursts (30+):** safe — they queue, all complete, no OOM.
- **Headroom / next step:** when you outgrow it, move to a 16 GB box and raise the semaphore, or split PDF generation into a separate worker process. Both are well beyond 500/day.
