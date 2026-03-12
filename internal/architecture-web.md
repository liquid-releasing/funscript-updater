# FunscriptForge — Web & Deployment Architecture

*Captured 2026-03-11. Internal planning document.*

---

## Guiding principles

- Keep source code for paid/SaaS features **private** — ship them from a separate private repo
- Keep the app source (funscript-forge) and docs **public** — community trust, open-source credibility
- **No container for static sites** — Cloudflare Pages is free, CDN-global, zero ops
- **Container for the SaaS app** — Docker Compose on a single VPS to start; scale later if needed
- Start simple, layer complexity incrementally

---

## Repo map

| Repo | Owner | Visibility | Serves |
| --- | --- | --- | --- |
| `liquid-releasing/funscript-forge` | liquid-releasing | Public (after `internal/` review) | App source, GitHub Releases artifacts |
| `liquid-releasing/funscriptforge-web` | liquid-releasing | Public | funscriptforge.com — marketing + download page |
| `[other-user]/funscriptforge-docs` | separate GitHub account | Public | docs.funscriptforge.com — MkDocs + AI assistant |
| *(future)* `[private]/funscriptforge-app` | private org or account | **Private** | app.funscriptforge.com — multi-user SaaS |

> **Note:** The docs repo needs to be created under a different GitHub username. Parking that for a future session.

---

## Domain map

| Domain | What | Hosting |
| --- | --- | --- |
| `funscriptforge.com` | Marketing site + download page | Cloudflare Pages (free) |
| `docs.funscriptforge.com` | MkDocs documentation + AI research assistant | Cloudflare Pages (free) |
| `app.funscriptforge.com` | Multi-user SaaS (Phase 3+) | Docker Compose on VPS (~$6–20/month) |

Keeping SaaS on `app.funscriptforge.com` means the source repo can stay **private** while
`funscriptforge.com` and the app source remain public. New features and paid-tier code
never touch the public repo.

---

## funscriptforge.com — marketing / download site

**Stack:** single-page static site (plain HTML/CSS or Astro)
**Hosting:** Cloudflare Pages — free tier, git-push deploys, custom domain
**Repo:** `liquid-releasing/funscriptforge-web` (separate public repo)

### What the page needs (MVP)
- Hero: FunscriptForge brand, one-line description
- Download buttons: Windows `.zip` and macOS `.zip` — link directly to GitHub Release URLs
  ```
  https://github.com/liquid-releasing/funscript-forge/releases/download/v0.0.10/FunscriptForge-windows.zip
  https://github.com/liquid-releasing/funscript-forge/releases/download/v0.0.10/FunscriptForge-macos.zip
  ```
- System requirements
- Link to docs
- Branding / logo pulled from GitHub raw URL:
  ```
  https://raw.githubusercontent.com/liquid-releasing/funscript-forge/main/media/funscriptforge.png
  ```

### Updating download links on new release
Two options:
1. **Manual**: update the version string in one place in the site repo on each release
2. **Automatic**: Cloudflare Pages build step hits the GitHub API to fetch the latest release tag
   ```
   https://api.github.com/repos/liquid-releasing/funscript-forge/releases/latest
   ```
   and injects the URL at build time — zero manual updates ever needed

### Next step
Build the single-page site in `funscriptforge-web`, connect to Cloudflare Pages,
point `funscriptforge.com` DNS → done. This unblocks Mac testing: friend downloads
from a real URL, not a raw GitHub link.

---

## docs.funscriptforge.com — documentation + AI assistant

**Stack:** MkDocs (Material theme) → later extended with AI research assistant layer
**Hosting:** Cloudflare Pages (free)
**Repo:** separate GitHub account (TBD — needs setup under different username)

### Content sourcing
The `docs/` folder in `funscript-forge` repo is the source of truth.
The docs repo pulls it via:
- Git submodule pointing at the app repo, OR
- GitHub Action that copies `docs/` from the app repo on each release

### MkDocs engine → AI research assistant evolution
```
Phase 1 (now):   Plain MkDocs + Material theme
Phase 2:         Custom MkDocs plugin that indexes content into vector store
Phase 3:         Chat widget embedded in static pages → Claude API
                 "Ask about this page" → context-aware answers grounded in docs
Phase 4:         Same engine reused for other Liquid Releasing products
                 (swap mkdocs.yml content, keep the AI layer)
```

The engine becomes a reusable chassis. Content differs per product; AI layer is common.

---

## app.funscriptforge.com — multi-user SaaS (Phase 3+)

**Stack:** FastAPI + React/Next.js + PostgreSQL + Redis + Celery (see roadmap-multiuser.md)
**Hosting:** Docker Compose on single VPS (Hetzner/DigitalOcean) to start
**Repo:** private repo (source code never public — paid features stay protected)

### Infrastructure progression
| Stage | Setup | Monthly cost |
| --- | --- | --- |
| Phase 2 MVP | Docker Compose, 1 VPS (2 vCPU / 4 GB) | ~$6–12 |
| Phase 3 | Same VPS + managed DB option | ~$20–40 |
| Phase 4 (paid tiers) | Scale workers, add CDN, managed PostgreSQL | ~$50–100 |
| Growth | Kubernetes only if horizontal scale is needed | Variable |

---

## Immediate next actions

1. **[NEXT]** Build `funscriptforge-web` single-page site → deploy to Cloudflare Pages
   → gives friend a real URL to download the macOS build for testing
2. **[LATER]** Set up docs repo under separate GitHub account → start MkDocs
3. **[LATER]** Review `internal/` folder before making `funscript-forge` repo public

---

*© 2026 Liquid Releasing. Internal document — not for public distribution.*
