# Funscript Forge — Marketing Plan & Revenue Projections

**INTERNAL ONLY — not for public release or GitHub**

---

## Pricing tiers — feature comparison and rationale

### Recommended model: two tiers + usage limits

Two-tier keeps the decision simple for users ("free or paid?") and reduces
friction at the top of the funnel. Usage limits gate the most expensive operations
(assessment, large file export) without blocking casual exploration.

---

### Tier comparison

| Feature | **Free** | **Creator — $12/month** |
| --- | --- | --- |
| **Funscripts per month** | 5 | Unlimited |
| **Max file duration** | 15 min | 3 hours |
| **Structural analysis** (assess) | ✅ | ✅ |
| **Behavioral classification** (8 tags) | ✅ | ✅ |
| **Phrase Editor** (manual transform) | ✅ | ✅ |
| **Transform Catalog** (view only) | ✅ | ✅ |
| **Export — single transform** | ✅ | ✅ |
| **Pattern Editor** (batch fix by tag) | ❌ | ✅ |
| **Apply to all** (batch apply) | ❌ | ✅ |
| **Export — recommended auto-transforms** | ❌ | ✅ |
| **Blend seams + final smooth** post-processing | ❌ | ✅ |
| **Phrase split** by cycle boundary | ❌ | ✅ |
| **Cross-script pattern catalog** | View only | Full read/write |
| **Custom transforms** (JSON recipes) | ❌ | ✅ |
| **Python plugins** | ❌ | ✅ |
| **CLI access** (all commands) | ❌ | ✅ |
| **Project save/load** (.project.json) | ❌ | ✅ |
| **API access** (when REST API ships) | ❌ | ✅ (100 req/day) |
| **Priority processing queue** | ❌ | ✅ |
| **Support** | Community forum | Email, 48 h SLA |

---

### Rationale for each gate

**Free tier gives enough to evaluate quality:**
The core Phrase Editor + assess pipeline lets a new user see real before/after
results on their own script. This is the "aha moment" — they see their stingy
section become a full-range script. Free is generous enough to convert sceptics.

**Pattern Editor behind paywall — highest leverage feature:**
"Apply to all" is the time-multiplier that distinguishes Forge from manual work.
It's the clearest demonstration of paid value: fix 12 drone sections in one click
instead of 12 separate edits.

**Auto-recommended transforms behind paywall:**
The suggest_transform() system requires the classifier + catalog. It's the
"let the AI decide" feature that casual free users may not need but power users
will pay for.

**Seam blend + final smooth behind paywall:**
These are the polish pass — the difference between "good" and "professional".
They can be mentioned in free-tier output as a teaser: "Your export is ready.
Upgrade to add seam blending."

**CLI behind paywall:**
Technical users who want scripted batch processing are more likely to be
paying customers than casual UI users. Keeping CLI paid also creates an
upgrade incentive for developers.

---

### Usage limits rationale

| Limit | Free | Creator | Why |
| --- | --- | --- | --- |
| Scripts/month | 5 | Unlimited | Covers occasional use; forces upgrade for regular workflow |
| Max duration | 15 min | 3 hours | Prevents abuse of free tier for feature-length content |
| API req/day | — | 100 | Prevents API scraping; Studio tier (future) gets higher limits |

**5 free scripts/month** is the sweet spot:

- Enough to evaluate the tool thoroughly (try it on 5 real scripts)
- Not enough to replace a paid workflow (a regular scripter does 5–30/month)
- Not so low that it feels stingy on first impression

**15 min cap** maps to typical scene length — free users can process a full scene,
just not a full video.

---

### Pricing: why $12/month

| Comparable SaaS | Price | Category |
| --- | --- | --- |
| ElevenLabs Starter | $5/month | AI audio |
| Udio Standard | $10/month | AI music |
| RunwayML Standard | $15/month | AI video |
| Adobe Express | $10/month | Creative tools |
| **Funscript Forge Creator** | **$12/month** | Haptic post-production |

$12 positions Forge as a professional creative tool, not a toy.
It's below the psychological "it's expensive" threshold (~$15–20)
while being above "it's not worth supporting" (~$5).

**Annual plan at $99/year** (save ~$45) — recommended as the default CTA.
Annual subscribers churn at ~half the rate of monthly, and the upfront revenue
improves cash flow.

---

### Upgrade triggers (when to show the paywall)

1. User tries Pattern Editor → "Pattern Editor is a Creator feature — upgrade to fix all [tag] sections at once"
2. User hits 5-script limit → "You've used your 5 free scripts this month. Upgrade to continue."
3. User tries Export with recommended transforms enabled → "Recommended transforms require Creator"
4. User tries to download with seam blend checked → "Seam blend is a Creator feature"
5. User tries to run CLI → mention Creator in help text

These are **contextual paywalls** — shown at the moment of value, not on a
generic pricing page. Contextual paywalls convert at 3–5× the rate of generic ones.

---

## Market sizing

### Who creates funscripts?

The funscript ecosystem is a niche but real market with a passionate, technical community.

**Tier 1 — Active script authors**
Individuals who write or post-process funscripts for personal use or publication.
These are the primary adopters of a tool like Funscript Forge.

- Estimated active script authors globally: **2,000–5,000**
- Distribution: mostly hobbyists; ~200–400 who produce high-volume, high-quality scripts
- Community hubs: EroScripts forum (~15,000 registered, ~2,000 active), Reddit r/funscripts (~8,000 members), GitHub repos
- Tooling they currently use: OpenFunscripter, handy-uf-script, ScriptPlayer, custom Python

**Tier 2 — Studios and platforms**
Companies that sell haptic content or license scripts for commercial use.

- Estimated commercial producers: **30–80** globally
- Typical scale: 10–100 scripts/month per studio
- Willingness to pay: higher — tools save scripting labour ($20–50/hour)

**Tier 3 — Device ecosystem builders**
Firmware developers, device manufacturers, and haptic platform developers who need
pipeline tooling for testing and content validation.

- Estimated organisations: **10–30**
- Mostly startup-scale; some well-funded (Handy, Kiiroo, etc.)

**Total addressable market (TAM):**
~2,000–5,000 individuals + ~100 organizations = small but engaged

**Serviceable obtainable market (SOM) at Year 1:**
~5–10% of active authors + ~20% of studios = ~200–600 users

---

## Community landscape and growth vectors

### Where the audience lives

| Channel | Description | Reach |
| --- | --- | --- |
| EroScripts forum | Primary community; script sharing + tooling discussion | ~2,000 active |
| GitHub | Open-source tooling releases; watched by technical authors | ~500 relevant |
| Discord (various) | Device-specific communities (Handy, OFS, etc.) | ~3,000 combined |
| Reddit r/funscripts | Casual audience; less tool-focused | ~8,000 members |
| Twitter/X niche accounts | Haptic content creators, device reviewers | ~1,000–2,000 |

### Growth vectors

1. **EroScripts forum post** — single thread with before/after demo script is the highest-ROI launch action
2. **OpenFunscripter plugin / companion** — OFS is the dominant editor; being mentioned there is a force multiplier
3. **GitHub stars** — credibility signal for technical adopters
4. **Word of mouth** — quality results drive organic sharing within tight community
5. **PythonDancer integration** — that project's users are exactly the right audience

---

## Capacity planning

### Compute requirements per user tier

| Action | CPU time (est.) | Memory |
| --- | --- | --- |
| Assess 10-min funscript | ~0.5 s | ~50 MB |
| Assess 90-min funscript | ~3–5 s | ~200 MB |
| Full export (transform + export) | ~1–2 s | ~100 MB |
| Concurrent users (Streamlit, local) | N/A | per user |

**For SaaS (API mode):**
Each assessment job is CPU-bound, single-threaded, 0.5–5 seconds.
A single 2-vCPU container handles ~50–100 assessments/minute comfortably.

### Capacity milestones

| Users | Scripts/day | API vCPUs needed | Monthly infra cost |
| --- | --- | --- | --- |
| 100 | ~200 | 0.5 (serverless viable) | ~$10–30 |
| 500 | ~1,000 | 1–2 (small container) | ~$30–60 |
| 2,000 | ~5,000 | 2–4 (auto-scaling group) | ~$100–200 |
| 10,000 | ~25,000 | 8–16 (2–4 instances) | ~$300–600 |

Storage grows at ~1 MB per script (input + output + assessment JSON).
1,000 users × 5 scripts/day × 365 = ~1.8 TB/year — manageable on S3 at ~$40/month.

---

## Revenue projections

### Pricing model (recommended)

| Tier | Monthly | Annual (2 months free) | Limits |
| --- | --- | --- | --- |
| Free | $0 | — | 5 scripts/month, 10 min max |
| Creator | $9 | $90 | 50 scripts/month, 60 min max |
| Studio | $29 | $290 | Unlimited, 3 hr max, API access |
| Enterprise | Custom ($200+) | Custom | On-prem, SLA, priority support |

### Scenario modelling (conservative)

**Year 1 — Community launch (free + early Creator)**

| Metric | Target |
| --- | --- |
| Free users | 300 |
| Creator subscribers | 30 |
| Studio subscribers | 3 |
| MRR | $357 ($270 Creator + $87 Studio) |
| ARR | ~$4,300 |

**Year 2 — Word-of-mouth growth**

| Metric | Target |
| --- | --- |
| Free users | 800 |
| Creator subscribers | 120 |
| Studio subscribers | 15 |
| Enterprise | 1 × $200/month |
| MRR | $1,715 |
| ARR | ~$20,600 |

**Year 3 — Integration partnerships (OFS plugin, PythonDancer)**

| Metric | Target |
| --- | --- |
| Free users | 2,000 |
| Creator subscribers | 400 |
| Studio subscribers | 50 |
| Enterprise | 3 × $300/month |
| MRR | $5,550 |
| ARR | ~$66,600 |

### Upside scenario (agentic pipeline launch)

If the automated video-to-funscript pipeline (PythonDancer + Forge + Restim) is
productised as a one-click service, pricing increases substantially:

| Tier | Price | Basis |
| --- | --- | --- |
| Per-video (casual) | $2–3 | Each video processed |
| Creator pipeline | $25/month | Unlimited automated processing |
| Studio pipeline API | $149/month | Bulk + white-label |

At 500 Creator + 50 Studio pipeline subscribers:
**MRR = $20,050 → ARR ~$240,000**

This is realistic if the automated pipeline achieves 80%+ "good on first pass"
quality (eliminating the manual editing step entirely).

---

## Go-to-market plan

### Phase 1 — Soft launch (Month 1–2)
**Goal: 50 free users, 5 paying**

- [ ] Post on EroScripts: "Show & Tell — Funscript Forge beta, free to try"
  - Include 3 before/after script samples with charts
  - Respond to every reply within 24 hours
- [ ] Open GitHub repo publicly; add demo GIF to README
- [ ] Reach out to top 5 OFS contributors directly (forum DM)
- [ ] Post in PythonDancer GitHub discussions
- [ ] Set up simple landing page (GitHub Pages or Carrd.co, ~$0)

### Phase 2 — Creator growth (Month 3–6)
**Goal: 200 free users, 30 paying**

- [ ] Launch Creator tier with 14-day free trial
- [ ] Write tutorial post: "How I turned a raw AI-generated script into a quality one in 10 minutes"
- [ ] Create 2–3 short demo videos (screen record with narration)
- [ ] Offer first 50 paying users a lifetime 50% discount (scarcity + loyalty)
- [ ] Apply to EroScripts "recommended tools" list

### Phase 3 — Studio outreach (Month 6–12)
**Goal: 400+ free, 150 paying, 10 studio**

- [ ] Cold outreach to 20 known commercial producers (EroScripts "verified authors")
- [ ] Offer Studio tier free trial for one month
- [ ] Create API documentation + postman collection
- [ ] Integrate with one partner tool (OFS plugin or MultiFunPlayer preset)
- [ ] Attend any relevant haptic/VR conferences (AWE, IAAPA) if budget allows

---

## Key risks

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| Market too small to sustain SaaS | Medium | Keep infra lean; break-even at 50 Creator subs |
| Community prefers free/open-source only | Medium | Keep core open; charge for hosted convenience |
| Competitor builds similar tool | Low | Head start + catalog moat + community relationships |
| Platform deplatforming (payment processors) | Medium | Use Stripe (allows adult content); have backup processor |
| Legal / compliance (adult content) | Low | Tool processes scripts, not media; no content hosted |

---

## Success metrics (Year 1)

| Metric | Target |
| --- | --- |
| GitHub stars | 500 |
| EroScripts thread replies | 100 |
| Registered free users | 300 |
| Paying subscribers | 35 |
| MRR at month 12 | $400 |
| Net Promoter Score (survey) | > 50 |
| Scripts processed (total) | 5,000 |
