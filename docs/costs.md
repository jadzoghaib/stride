# Stride — Cost Architecture (for the business plan)

Ranged operating-cost model for the platform as designed (docs/architecture.html).
All prices are **provider list prices as of mid-2026, USD, monthly unless noted** —
re-verify each on the provider's pricing page before locking the plan
(pricing pages: supabase.com/pricing, stripe.com/pricing + /connect/pricing,
cloudflare.com/plans, fly.io/pricing, resend.com/pricing, grafana.com/pricing).
Ranges are low = frugal configuration, high = comfortable headroom.

A deliberate property of this architecture: **AI/LLM inference cost is zero.**
The analytics and matching engines are deterministic formulas, not model calls —
marketability scoring costs CPU-milliseconds, not API tokens.

---

## 1. Computing / infrastructure cost by stage

### Stage 0 — Validation (today: demo + first pilot users, ≤ 500 MAU)

| Item | Choice | Monthly |
|---|---|---|
| Database + auth | Supabase Free (500 MB DB, 50k MAU auth) | $0 |
| API + web hosting | Fly.io / Railway / Render hobby instance | $0 – $10 |
| Edge / DNS / TLS | Cloudflare Free | $0 |
| Email | Supabase built-in SMTP (rate-limited) | $0 |
| Observability | Built-in /metrics + logs; Grafana Cloud free tier | $0 |
| Domain | ~$12/year | ~$1 |
| **Total** | | **$1 – $11 / mo** |

Caveats that matter to the plan: Supabase Free pauses after a week of inactivity
(fine for a pilot, not for a launch), and the built-in SMTP (~2 emails/hour) cannot
onboard real users — the first paid line item of a real launch is email.

### Stage 1 — Launch (≤ 10,000 MAU, hundreds of athletes, tens of sponsors)

| Item | Choice | Monthly |
|---|---|---|
| Database + auth + storage | Supabase Pro ($25 base + compute upgrade + usage) | $25 – $100 |
| API hosting | 1–2 small VMs / Fly machines (workers included) | $20 – $80 |
| Web hosting | Static SPA: Cloudflare Pages / Vercel free–Pro | $0 – $20 |
| Edge / WAF | Cloudflare Free → Pro | $0 – $25 |
| Redis (cache + rate limits) | Upstash / small managed instance | $0 – $30 |
| Transactional email | Resend / Postmark, ~10–50k sends | $15 – $50 |
| Error tracking + dashboards | Sentry team + Grafana Cloud starter | $0 – $60 |
| Backups / snapshots | Included in Supabase Pro (7-day PITR add-on if wanted) | $0 – $100 |
| **Total** | | **$60 – $465 / mo** |

Rule of thumb at this stage: **$0.01 – $0.05 per monthly-active user.**

### Stage 2 — Growth (≤ 100,000 MAU, K8s architecture from the blueprint)

| Item | Choice | Monthly |
|---|---|---|
| Postgres | Supabase compute upgrades + read replica (or equivalent RDS) | $300 – $1,000 |
| Kubernetes | Managed control plane + 3–6 nodes (API replicas + workers) | $250 – $900 |
| Redis | Managed, HA | $50 – $200 |
| Edge / WAF / CDN | Cloudflare Pro–Business | $25 – $250 |
| Email | 250k–1M sends | $100 – $400 |
| Observability | Grafana Cloud / Datadog tier, log retention | $100 – $500 |
| Object storage + egress | Media kits, deliverables | $20 – $150 |
| Social API infrastructure | Direct platform APIs are free (rate-limited); a data aggregator (Phyllo/insightIQ class) if used instead | $0 – $1,500 |
| **Total** | | **$845 – $4,900 / mo** |

Still ~**$0.01 – $0.05 per MAU** — the architecture scales roughly linearly because
the expensive work (platform syncs, score computation) is batched in workers, not
per-request.

---

## 2. Third-party / per-transaction costs (variable, revenue-linked)

| Service | Cost | Notes |
|---|---|---|
| Stripe card processing | ~2.9% + $0.30 per charge | paid by the platform out of the deal amount |
| Stripe Connect (Express) | ~0.25% + $0.25 per payout + ~$2 per monthly-active connected account | the athlete/club payout rail |
| Chargebacks | $15 each | budget 0.1–0.5% of transactions |
| Instagram / YouTube / TikTok APIs | $0 | free but rate-limited; the real cost is engineering + app-review lead time (weeks) |
| KYC/identity | $0 extra | included in Stripe Connect onboarding |

**Worked unit economics per deal** (example: $5,000 sponsorship, 10% platform fee):
gross platform revenue $500; Stripe processing ≈ $145 + payout fees ≈ $14
→ **contribution ≈ $341 per deal (~68% margin on fee revenue)** before infra.
At Stage-1 infra midpoint (~$260/mo), **one mid-size deal a month covers the
entire platform's operating cost.** Club packages have identical mechanics.

---

## 3. Maintenance & people cost (the honest line most plans omit)

| Item | Effort / cost | Notes |
|---|---|---|
| Dependency & security updates | 2–4 h/mo (Stage 1) → 0.25 FTE (Stage 2) | `scripts/security_audit.ps1` is the checklist |
| Monitoring & incident response | ~0 until launch → 0.1–0.25 FTE at Stage 2 | runbook exists (docs/runbook.md); no on-call rotation needed before Stage 2 |
| Platform API upkeep | 1–3 days per platform per year | social APIs deprecate versions ~annually |
| Feature development | founder time or contractor $40–$80/h | Stage-2 assumption: 0.5–1 FTE engineer ($4k–$10k/mo) |
| Support & ops (disputes, verification, club onboarding) | 0 → 0.25–0.5 FTE at Stage 2 | first non-engineering hire |

## 4. One-off costs (pre-revenue → launch)

| Item | Range | When |
|---|---|---|
| Legal: ToS, privacy policy, GDPR posture | $1,000 – $5,000 | before public launch |
| Company formation + accounting | $500 – $2,000/yr | before revenue |
| Security review / light pen test | $3,000 – $8,000 | before real money flows |
| Platform app reviews (Meta/TikTok dev approval) | $0 + 2–6 weeks lead time | Phase 2 (live connectors) |
| Design polish / brand | $0 – $5,000 | discretionary |

## 5. Summary for the financial model

| Stage | MAU | Infra (monthly) | People (monthly) | Cost per MAU |
|---|---|---|---|---|
| Validation | ≤ 500 | $1 – $11 | founder time | ~$0 |
| Launch | ≤ 10k | $60 – $465 | $0 – $2k (contract hours) | $0.01 – $0.05 |
| Growth | ≤ 100k | $845 – $4,900 | $5k – $15k | $0.06 – $0.20 incl. people |

Add a **15–20% contingency** on infra lines. The dominant cost driver at every
stage is people, not compute — the architecture was chosen so that compute stays
a rounding error until the marketplace is generating fee revenue (§2), and so
that no line item carries vendor lock-in (portable Postgres/S3/OIDC — see the
exit-options row in docs/architecture.html).
