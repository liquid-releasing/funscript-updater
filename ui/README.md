# ui

All user interface code for the Funscript Updater.

The `ui/` layer sits on top of the core pipeline modules (`assessment/`,
`suggested_updates/`, `user_customization/`). It is split into
subdirectories by deployment target so that each target can evolve
independently while sharing the same business logic.

## Subdirectories

### `common/`

Framework-agnostic business logic shared by every UI target.

Nothing in here depends on Streamlit, Flask, or any other UI library.
Any new deployment target should import from `common/` rather than
duplicating logic. Contains the `WorkItem` and `Project` models, factory
helpers, and a full unit-test suite.

See [`common/README.md`](common/README.md) for API details.

### `streamlit/`

A locally-runnable interactive app built with
[Streamlit](https://streamlit.io). This is the primary UI for running
the pipeline on your own machine. It can also be deployed to Streamlit
Community Cloud with no code changes.

See [`streamlit/README.md`](streamlit/README.md) for panel layout and
export details.

### `web/`

Planned: a FastAPI backend + frontend intended for hosting as a
web service. Shares all business logic with `common/`. Not yet
implemented.

---

## Running the Streamlit app

```bash
# Install dependencies (once)
pip install -r ui/streamlit/requirements.txt

# Launch
streamlit run ui/streamlit/app.py
```

The app opens at `http://localhost:8501` in your default browser.

---

## Running the tests

Core pipeline tests and UI-layer tests can be run separately or together.

```bash
# Core pipeline tests (76 tests)
python -m unittest discover -s tests -v

# UI common-layer tests (38 tests)
python -m unittest discover -s ui/common/tests -v
```
