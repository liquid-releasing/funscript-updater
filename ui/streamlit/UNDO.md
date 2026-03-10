# Undo / Redo

Funscript Forge supports 50-level undo and redo for all editing operations.
The **↩ Undo** and **↪ Redo** buttons appear in the sidebar whenever a
funscript is loaded.

---

## What can be undone

| Operation | Trigger | Label shown |
| --- | --- | --- |
| Commit phrase action edits | Phrase Editor "Commit" button | `Edit phrase actions` |
| Add a split point | 📌 pin button in the audio player | `Add split at M:SS` |
| Remove a split point | × button on a split boundary | `Remove split` |
| Apply transform to all instances | Pattern Editor "Apply to all" button | `Apply transform to all '<tag>'` |

> **Note** — moving sliders or selecting a transform in the Pattern Editor
> does **not** push an undo snapshot.  Snapshots are pushed only at discrete
> commit/apply points so the undo history stays meaningful.

---

## How to use

| Action | How |
| --- | --- |
| Undo last operation | Click **↩ Undo** in the sidebar |
| Redo (after undoing) | Click **↪ Redo** in the sidebar |
| See what will be undone/redone | Hover the button — the tooltip names the operation |
| Buttons are greyed out | Nothing left to undo/redo in that direction |

Undo and Redo are always visible in the sidebar when a project is loaded.
They are disabled (greyed) when the stack is empty or already at one end.

---

## Behaviour

- **50-snapshot limit** — the oldest snapshot is silently dropped when the
  limit is reached.  For typical editing sessions this is more than enough.
- **Redo branch is discarded on new edits** — standard behaviour.  If you
  undo two steps and then make a new edit, the two "future" states are gone.
- **Each snapshot captures**:
  - The `Project` object reference (funscript actions + assessment result)
  - All pattern-editor state: split points (`pe_splits_*`), segment
    transforms (`pe_split_transform_*`), and instance transforms
    (`pe_transform_*`)
- **Not captured** (intentionally):
  - View / scroll state (`view_state`)
  - Work item statuses
  - Assessment settings (re-analysis is its own operation)

---

## Architecture

```
ui/common/undo_stack.py          Framework-agnostic UndoStack + Snapshot
ui/streamlit/undo_helpers.py     push_undo() and apply_snapshot() (Streamlit layer)
ui/streamlit/app.py              Stack init, sidebar buttons, _commit_actions hook
ui/streamlit/panels/
    pattern_editor.py            push_undo() before add/remove split, apply-to-all
tests/
    test_undo_stack.py           20 tests — stack logic (push, undo, redo, max_size, labels)
    test_undo_helpers.py         17 tests — helpers with mock session_state
```

### `UndoStack`

Pure Python, no Streamlit dependency.  Lives in `ui/common/` so it can be
reused by any future deployment target (web, desktop).

```python
from ui.common.undo_stack import UndoStack, Snapshot

stack = UndoStack(max_size=50)

# Push before a mutating operation
stack.push(Snapshot(label="Add split at 1:23", project=proj, pe_state={...}))

if stack.can_undo:
    snap = stack.undo()   # returns the Snapshot to restore
    print(stack.undo_label)   # "Add split at 1:23"
```

### `push_undo` / `apply_snapshot`

Streamlit-aware helpers in `ui/streamlit/undo_helpers.py`.

```python
from ui.streamlit.undo_helpers import push_undo, apply_snapshot

# Before any mutating operation:
push_undo("Add split at 1:23")
# ... make changes to session_state ...

# In the undo button handler:
snap = st.session_state.undo_stack.undo()
if snap:
    apply_snapshot(snap)
    st.rerun()
```

`push_undo` is safe to call even before the stack is initialised — it silently
skips if `undo_stack` is not in `session_state`.

---

## Adding undo support to a new operation

1. Import the helper at the call site:
   ```python
   from ui.streamlit.undo_helpers import push_undo
   ```
2. Call it **before** the mutating code with a short, human-readable label:
   ```python
   push_undo("My operation description")
   do_the_mutation()
   ```
3. That's it — the sidebar buttons handle the rest automatically.
