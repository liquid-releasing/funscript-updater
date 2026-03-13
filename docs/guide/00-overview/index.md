# How FunscriptForge Fits Into Your Workflow

> **TODO — This page is a placeholder.** The content outline is complete; the final copy,
> screenshots, and Mermaid diagram need to be written before this page goes live.
> See the writing brief below.

---

## Writing Brief

### Purpose of this page

This is the first page a new user reads. It answers three questions before they install anything:

1. **What is a funscript?** (30-second primer for someone who just found this tool)
2. **Where does FunscriptForge fit?** (It is not a funscript creator — it is a post-processor)
3. **Why does it matter?** (What a raw script feels like vs. what a processed one feels like)

The page sets expectations for the entire guide. It does not teach the user to do anything yet.
It gives them the mental model they need so that every subsequent step makes sense.

### Tone

Welcoming, direct, slightly enthusiastic. This community knows what they're doing —
don't over-explain the basics, but don't assume they've seen a tool like this before.

### What to include

#### 1. The 30-second funscript primer
Two or three sentences: what a `.funscript` file is, what device uses it, why quality matters.
Target reader: someone who has a device but has only used scripts they downloaded.

#### 2. The workflow diagram (Mermaid)
Show the full pipeline — from raw video to device. FunscriptForge's role is highlighted.
See diagram scaffold below.

#### 3. "Why a raw script isn't enough"
Explain what a freshly generated or hand-scripted funscript typically looks like:
- Uniform tempo throughout (no dynamics)
- No quiet moments — everything at the same intensity
- Jarring transitions between sections
- No "shape" that follows the mood of the content

One or two sentences each. Keep it concrete — this is the pain the tool solves.

#### 4. "What FunscriptForge adds"
The same list, flipped:
- Structure-aware analysis that finds natural phrases in the motion
- Transform tools that add dynamics, smooth transitions, and expressive variation
- Preview against your video before committing any change
- Export that is clean, clamped, and ready to use

#### 5. What you will build in this guide
One paragraph. Mention the example funscript that every tutorial page uses (TBD — pick one of
the three test funscripts from the repo or create a tutorial-specific one). Tell the reader
exactly what state they will be in at the end of Part 1.

#### 6. A note on Part 2
One sentence: "Once you're comfortable, Part 2 explains every option in detail."

### Mermaid diagram scaffold

```
TODO: Replace this scaffold with the final diagram once copy is approved.

The diagram should show a left-to-right flow:

  [Video file]
       |
       v
  [Initial funscript]  <-- created by FapTap / JoyFunscripter / manual / AI
       |
       v
  ╔══════════════════════════════════╗
  ║        FunscriptForge            ║
  ║  1. Assess (find structure)      ║
  ║  2. Review phrases               ║
  ║  3. Apply transforms             ║
  ║  4. Preview with video           ║
  ║  5. Export                       ║
  ╚══════════════════════════════════╝
       |
       v
  [Improved funscript]
       |
       v
  [Haptic device — The Handy, OSR2, etc.]

Side note: FunscriptForge does NOT generate a funscript from video.
It takes an existing funscript and makes it better.
```

### Screenshots needed

- [ ] Side-by-side chart: raw funscript (flat, uniform) vs. processed (dynamic, varied)
- [ ] The app open with a funscript loaded — just the main view, no UI deep-dive yet
- [ ] Optional: a device photo for context (check licensing before using)

### Cross-links

- Next → [Install FunscriptForge](../01-getting-started/install.md)
- Reference → [Concepts and Glossary](../../reference/concepts.md) *(not yet written)*

---

*This placeholder was created 2026-03-13. Assign to: TBD.*
*Remove this TODO block and the writing brief when the page is complete.*
