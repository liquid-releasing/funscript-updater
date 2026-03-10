# Funscript Forge — Roadmap to Multi-User SaaS with Paid Tier

Items marked 🔒 are for internal tracking only (not public backlog).

---

## Phase 1 — Production-ready single user (1–2 months)

Goal: make the current Streamlit app solid enough to hand to anyone.

| Item | Priority | Notes |
| --- | --- | --- |
| Fix `use_container_width` deprecation warnings | High | Streamlit 1.35+ |
| Replace shared `output/` with per-session temp dirs | High | Prevents collisions |
| Input validation on all file uploads | High | Security prerequisite |
| Max file size enforcement | High | OOM protection |
| Graceful error messages (no raw tracebacks) | High | User experience |
| Undo / redo for phrase transforms | Medium | Session-level history stack |
| Browser file upload (no disk drop required) | Medium | GitHub #5 |
| Improve uniform-tempo segmentation | Medium | GitHub #2, VictoriaOaks |
| Smoke-test against all three test funscripts | Medium | GitHub #1 |
| Packaging as standalone executable | Low | PyInstaller / Briefcase |

---

## Phase 2 — REST API + containerisation (1–2 months)

Goal: decouple the pipeline from the UI; enable programmatic access.

| Item | Priority | Notes |
| --- | --- | --- |
| FastAPI app with `/assess`, `/transform`, `/export` routes | High | GitHub #8 |
| Pydantic schemas for all request/response payloads | High | — |
| API-key auth middleware | High | For SaaS gating |
| Docker + Docker Compose | High | GitHub #3 prerequisite |
| Async job queue (Celery + Redis) | Medium | Long files non-blocking |
| OpenAPI docs at `/docs` | Medium | Auto from FastAPI |
| Health check + readiness endpoints | Medium | Container orchestration |
| GitHub Actions CI (test + build + push) | Medium | — |

---

## Phase 3 — Multi-user web UI (2–3 months)

Goal: browser-based UI usable by multiple users simultaneously.

| Item | Priority | Notes |
| --- | --- | --- |
| User auth (Auth0 / Clerk) | High | OAuth2 + JWT |
| Per-user S3 file namespacing | High | Tenant isolation |
| PostgreSQL user + project store | High | Replace local JSON |
| React + Next.js frontend scaffold | High | — |
| Port Assessment tab to React | High | — |
| Port Phrase Editor to React | High | Largest effort |
| Port Pattern Editor to React | High | — |
| Port Export tab to React | High | — |
| Session state migration from Streamlit | High | — |
| Per-user pattern catalog | Medium | Or opt-in shared |
| Project sharing (view-only link) | Medium | — |
| Admin panel (usage, users) | Medium | — |

---

## Phase 4 — Paid tiers (1 month, after Phase 3)

Goal: sustainable revenue.

### Tier model

| Tier | Price | Limits | Features |
| --- | --- | --- | --- |
| **Free** | $0 | 5 scripts/month, 10 min max | Core pipeline, download |
| **Creator** | $9/month | 50 scripts/month, 60 min max | + catalog, custom transforms |
| **Studio** | $29/month | Unlimited, 3h max | + batch API, priority queue |
| **Enterprise** | Custom | Unlimited | + SSO, SLA, private deploy |

### Items

| Item | Priority | Notes |
| --- | --- | --- |
| Stripe integration (checkout + webhooks) | High | — |
| Entitlement enforcement middleware | High | Quota checks per user |
| Usage metering (scripts processed, minutes) | High | — |
| Billing portal (manage subscription) | High | Stripe portal |
| Free trial (14 days Creator) | Medium | Acquisition |
| Referral program | Low | Growth |
| 🔒 Stripe price IDs | — | See 1Password |

---

## Phase 5 — Growth features (ongoing)

| Item | Priority |
| --- | --- |
| Audio/video sync playback in UI (GitHub #6) | High |
| Batch processing (upload multiple scripts) | Medium |
| Script versioning + diff view | Medium |
| Collaborative editing (real-time cursors) | Low |
| Mobile-responsive UI | Low |
| Webhooks (notify on job complete) | Low |
| Public script library / marketplace | Low |

---

## Key dependencies

```
Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4
                 │                       │
                 └──► Phase 5 (ongoing) ─┘
```

Phases 1 and 2 are prerequisite for Phase 3. Paid tiers require Phase 3.
Phase 5 features can be shipped incrementally in any phase.

---

## 🔒 Internal notes (not for public roadmap)

- Payment processor: Stripe (Checkout + Customer Portal)
- Target launch: Creator tier public beta after Phase 3 MVP
- Pricing validated against: Udio ($10/mo), ElevenLabs ($5–22/mo), similar creative tools
- Revenue target: 500 Creator + 50 Studio = $5,950 MRR at steady state
- Infrastructure cost at that scale: ~$400–500/month → healthy margin

---

*© 2026 [Liquid Releasing](https://github.com/liquid-releasing). Licensed under the [MIT License](../LICENSE).  Written by human and Claude AI (Claude Sonnet).*
