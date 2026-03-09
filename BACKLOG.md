# Funscript Forge — Backlog

Items are loosely ordered by dependency and value. Move to DONE when shipped.

---

## Open

### Upload funscripts · [#5](https://github.com/liquid-releasing/funscript-updater/issues/5)

Allow the user to upload a `.funscript` file directly from the browser instead
of requiring it to live on disk under `test_funscript/`. The uploaded file
should be written to a temp location, assessed on the fly, and treated exactly
like a locally-loaded file for the rest of the session.

Acceptance criteria:

- `st.file_uploader` in the sidebar (accepts `.funscript`)
- Uploaded file saved to `output/uploads/` so the path-based session state still works
- Existing local-file picker remains available alongside upload

---

### Upload and sync media / audio for playback · [#6](https://github.com/liquid-releasing/funscript-updater/issues/6)

Users often want to hear the audio track while reviewing or editing a phrase to
confirm timing and feel.

Scope:

- `st.file_uploader` accepting common audio/video formats (`.mp4`, `.mkv`, `.mp3`, `.m4a`, `.wav`, `.ogg`)
- Uploaded media stored in `output/uploads/` for the session
- Audio/video player embedded in the UI (`st.audio` / `st.video` or custom HTML5 player via `st.components`)
- **Timestamp display** — show the current playback position (M:SS) in real time so the user can note cut points
- **Seek to phrase / segment** — when a phrase or segment is selected in the Pattern Editor or Phrase Selector, a button seeks the player to that phrase's `start_ms`
- **Loop mode** — option to loop the current phrase window so the user can listen while adjusting transform sliders
- Stop / play controls visible alongside the chart (no scrolling required)

---

### Clean up UI tabs — remove stale / low-value tabs · [#7](https://github.com/liquid-releasing/funscript-updater/issues/7)

The current tab bar has grown over time. Audit and remove or merge tabs that
no longer pull their weight, keeping only what a first-time user actually needs.

Candidate tabs to review:

- **Navigator** — mostly superseded by the Phrase Selector chart; consider folding remaining value into Assessment or removing
- **Work Items** and **Edit** — evaluate whether these should merge into a single panel now that the Pattern Editor handles most per-phrase work
- **Assessment** — keep as read-only reference; consider collapsing into an expandable section of the Phrase Selector

Target tab order after cleanup (proposal — confirm before implementing):

1. Phrase Selector (viewer)
2. Pattern Editor
3. Catalog
4. Work Items / Edit (merged)
5. Export

---

## Done

*(nothing yet)*
