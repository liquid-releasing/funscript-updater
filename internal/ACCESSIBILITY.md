# Funscript Forge — Accessibility Assessment

**Standard:** WCAG 2.1 Level AA
**Scope:** Streamlit UI (local desktop + web modes)
**Date:** 2026-03-10

---

## Executive Summary

Funscript Forge is currently accessible for sighted, mouse/keyboard users on a standard desktop.
It has significant gaps for users relying on screen readers, users who are colour-blind, and
users with motor impairments who depend entirely on keyboard navigation.  The issues below are
grouped by severity.  Critical and Major items should be resolved before a public release.

---

## Critical — Blocks Use for Affected Users

### C1 · Audio player buttons have no accessible names

**File:** `ui/streamlit/components/audio_player/frontend/index.html`
**WCAG:** 1.3.1 Info and Relationships, 4.1.2 Name, Role, Value

Buttons use emoji glyphs only (`⏮ 5s`, `▶`, `⏹`, `⏭ 5s`, `📌`) with `title` attributes.
Screen readers ignore `title` on interactive elements unless `aria-label` is also set.

**Fix:** Add `aria-label` to each button:

```html
<button id="btn-back"    aria-label="Back 5 seconds">⏮ 5s</button>
<button id="btn-play"    aria-label="Play">▶</button>
<button id="btn-stop"    aria-label="Stop">⏹</button>
<button id="btn-fwd"     aria-label="Forward 5 seconds">⏭ 5s</button>
<button id="btn-pin"     aria-label="Set split here">📌</button>
```

Also add `role="timer"` and `aria-live="polite"` to the time display `<span>`.

---

### C2 · Rejected/accepted items communicated by colour and opacity only

**File:** `ui/streamlit/panels/export_panel.py` lines ~420, ~496
**WCAG:** 1.4.1 Use of Colour, 1.3.1 Info and Relationships

Rejected rows are rendered with `opacity: 0.35` and `<s>` strikethrough via
`unsafe_allow_html`.  There is no semantic marker (ARIA role or attribute) that a screen
reader can convey.

**Fix:** Add `aria-label="rejected"` to the row container, or prepend a visually hidden
`<span class="sr-only">Rejected</span>` alongside the strikethrough.

---

### C3 · BPM colour gradient conveys meaning without text alternative

**File:** `ui/streamlit/panels/assessment.py` lines ~32, ~159, ~203
**WCAG:** 1.4.1 Use of Colour

The phrase timeline and BPM charts use a blue→red gradient as the only indicator of BPM
level.  Users with red-green colour-blindness (8% of males) cannot distinguish the ends of
the gradient reliably.

**Fix (short-term):** Add BPM value labels directly on phrase bars in the timeline chart so
the number conveys the information independently of colour.
**Fix (long-term):** Add a colour-blind-friendly palette option (e.g. viridis or a
blue→orange scale) and a chart pattern/texture toggle.

---

## Major — Significant Barrier

### M1 · `label_visibility="collapsed"` hides labels from screen readers

**File:** `ui/streamlit/panels/viewer.py` line ~193; other panels
**WCAG:** 1.3.1 Info and Relationships, 2.4.6 Headings and Labels

`st.radio("Color mode", ..., label_visibility="collapsed")` visually hides the label but
also removes it from the accessibility tree in Streamlit's HTML output.

**Fix:** Use `label_visibility="visible"` and adjust layout, or if the label truly must be
hidden visually, inject the label via a CSS `sr-only` class so it remains in the DOM for
screen readers.

---

### M2 · Plotly charts have no accessible descriptions

**Files:** All panel files using `st.plotly_chart()`
**WCAG:** 1.1.1 Non-text Content

Interactive Plotly charts (phrase selector, BPM step chart, pattern timeline, etc.) render
as SVG/Canvas with no `alt` text, `aria-label`, or descriptive caption accessible to screen
readers.

**Fix:** Add a `st.caption()` or `aria-label` describing the key information each chart
communicates, e.g.:
*"BPM step chart: 34 phrases ranging from 80 to 145 BPM. Largest transition at 1:26."*

---

### M3 · Keyboard focus trapped in pattern editor fragment

**File:** `ui/streamlit/panels/pattern_editor.py`
**WCAG:** 2.1.2 No Keyboard Trap

The `@st.fragment` decorator scopes reruns to the fragment DOM.  Keyboard navigation
(Tab key) can exit to the parent page unexpectedly, or focus can become lost after
fragment rerenders.  Needs manual keyboard-only testing to confirm severity.

**Fix:** Test with keyboard-only navigation; ensure Tab order flows logically through
the fragment and that focus is restored to a sensible element after fragment reruns.

---

### M4 · Emoji-only status indicators in quality check and export rows

**Files:** `export_panel.py`, `assessment.py`
**WCAG:** 1.3.3 Sensory Characteristics, 4.1.2 Name, Role, Value

`🔴 Error`, `🟡 Warn`, `✅`, `🗑` are used as the sole status indicators in tables.
Screen readers announce emoji names (`red circle`, `yellow circle`) which are verbose
and ambiguous.

**Fix:** Add visually hidden text alongside emoji, e.g.:
`<span aria-hidden="true">🔴</span><span class="sr-only">Error</span>`

---

### M5 · No `lang` attribute on the page

**WCAG:** 3.1.1 Language of Page

Streamlit does not expose a mechanism to set `<html lang="en">`.  Without it, screen
readers may use the wrong speech synthesis engine or pronunciation rules.

**Fix (workaround):** Inject `<script>document.documentElement.lang = 'en';</script>`
via `components.html` at page load.  This is a best-effort fix given Streamlit's
constraints.

---

## Minor — Enhancement

### m1 · Audio player playback progress not announced to screen readers

The time display updates visually on every animation frame but has no `aria-live` region.
Screen reader users receive no feedback about playback position.

**Fix:** Add `aria-live="off"` by default; announce position only on play/pause/stop
events via an `aria-live="polite"` status element.

---

### m2 · Sidebar undo/redo buttons rely on emoji for labelling

`↩ Undo` and `↪ Redo` are announced as "Leftwards arrow with hook Undo" by some screen
readers.  The tooltip `help=` text is not read aloud.

**Fix:** Streamlit button text is already readable; verify the screen reader announcement
is acceptable.  If not, consider plain text labels `Undo` / `Redo` instead of arrow
prefix.

---

### m3 · Work item status selectboxes have `label_visibility="collapsed"`

**File:** `ui/streamlit/panels/work_items.py` line ~99

Status dropdowns in the work items panel suppress their label.  Screen reader users
cannot determine what the dropdown controls without surrounding context.

**Fix:** Use `label_visibility="visible"` or add a visually hidden label via
`st.markdown` with CSS.

---

### m4 · Tab icon images have no alt text

**File:** `ui/streamlit/app.py` (icon row above tabs)

`st.image()` with `use_container_width=True` generates `<img>` tags.  Without an `alt`
parameter, Streamlit emits `alt=""` (decorative intent), which is acceptable for purely
decorative icons — confirm this is the intended behaviour.

**Fix:** Explicitly pass `caption=None` (already the default) to confirm decorative
intent, and add a code comment explaining this is intentional.

---

## Streamlit Platform Limitations

Some issues are outside developer control given Streamlit's architecture:

| Limitation | Impact | Workaround |
| --- | --- | --- |
| No `<html lang>` attribute | Screen reader language detection | JS injection at page load |
| `label_visibility="collapsed"` removes from DOM | Labels lost to AT | Visible label + layout adjustment |
| Plotly charts are SVG/Canvas with no built-in alt text | Charts inaccessible to AT | `st.caption()` descriptions |
| `components.html` iframes require extra keyboard navigation step | Motor impairment | Documented limitation |

---

## Recommended Priority Order for Fixes

| # | Item | Effort | Impact |
| --- | --- | --- | --- |
| 1 | C1 — Audio player `aria-label` on buttons | Low | High |
| 2 | C3 — BPM chart text labels (remove colour-only) | Low | High |
| 3 | M5 — Inject `lang="en"` via JS | Low | Medium |
| 4 | C2 — Rejected rows semantic marker | Low | Medium |
| 5 | M2 — Chart `st.caption()` descriptions | Medium | High |
| 6 | M4 — Emoji status indicators text fallback | Medium | Medium |
| 7 | M1 — `label_visibility` audit and fix | Medium | Medium |
| 8 | M3 — Keyboard focus in fragment (test first) | Medium | Unknown |
| 9 | m1 — Audio `aria-live` for playback | Low | Low |
| 10 | m2–m4 — Minor polish | Low | Low |

---

*Assessment by Claude Sonnet 4.6 · Reviewed against WCAG 2.1 AA criteria.*
