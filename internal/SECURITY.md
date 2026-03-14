# Security Model — FunscriptForge

*Internal document — not shipped to end users.*

---

## Scope

FunscriptForge is a local single-user desktop tool.  It reads and writes
files on the local file system; it does not have a server component, does not
expose network ports, and does not authenticate users.  The threat model
focuses on **malicious content delivered to the local machine** rather than
remote network attacks.

---

## Threat Analysis

### T1 — Malicious JSON recipe file

**Vector:** A user is socially engineered into placing a crafted `.json` file
in `user_transforms/`, or downloads a "transform pack" from an untrusted
source that contains a malicious recipe.

**Risk without mitigation (High):**
If recipe entries were loaded without validation, an attacker could craft:
- Steps referencing unknown keys that crash the application or trigger
  unexpected code paths.
- Param values that are nested objects (e.g., `{"__reduce__": ...}`), which
  could exploit insecure deserialisation if params were ever passed to `eval`,
  `pickle`, or similar.
- Extremely long strings or deeply nested structures that cause denial-of-
  service via resource exhaustion.

**Risk after mitigation (Low):**
JSON is pure data — it cannot directly execute code.  The schema validator
(see Mitigations) closes all known indirect execution paths.  A malformed
entry is skipped with a stderr warning; it cannot crash the app or escalate
privileges.

**Residual risk:** A crafted recipe could still produce nonsensical output
(e.g., stacking many transforms to degrade audio-script quality), but this
is a data-quality issue, not a security issue.

---

### T2 — Malicious Python plugin file

**Vector:** A user is socially engineered into placing a `.py` file in
`plugins/`, or downloads a tool/script that secretly drops a plugin file
there.  The file is executed at app startup.

**Risk without mitigation (Critical):**
Python files loaded with `importlib.util.exec_module` run with full OS-level
permissions of the current user.  A malicious plugin can:
- Read, write, or delete any file the user can access (funscripts, credentials,
  config files, documents).
- Exfiltrate data over the network (HTTP, DNS, sockets).
- Spawn subprocesses (`subprocess`, `os.system`) to install malware or
  execute arbitrary shell commands.
- Persist itself by modifying shell profiles, startup scripts, or scheduled
  tasks.
- Access environment variables (API keys, tokens stored in the shell
  environment).

This is functionally equivalent to running an untrusted executable.

**Risk after mitigation (Medium when opt-in, Low when disabled):**
Python plugins are **disabled by default**.  They only execute when
`FUNSCRIPT_PLUGINS_ENABLED=1` is set explicitly in the environment.  When the
flag is absent and `.py` files are present, a warning is printed to stderr and
no code is executed.

When the user does enable the flag, the risk is equivalent to running any
user-supplied script — they have explicitly accepted that responsibility.

---

### T3 — Funscript file with crafted content

**Vector:** A user opens a `.funscript` file received from an untrusted source.

**Risk (Low):**
Funscript files are JSON.  The analyzer reads `actions` (list of
`{"at": int, "pos": int}` objects) and `metadata`.  No `eval`, `exec`, or
shell interpolation is performed on any field value.  Malformed files are
rejected by the JSON parser; unexpected field values (strings where ints are
expected) are caught by the analyzer's input validation layer.

**Residual risk:** A very large file could cause high memory use.  The
current implementation does not impose a size limit.  This is noted as a
future hardening opportunity.

---

### T4 — Assessment / work-item JSON files

**Vector:** A crafted `.assessment.json` or work-item file is placed in
`output/` or opened via the UI.

**Risk (Low):**
These files are read as JSON and their structure is validated.  No field
value is executed.  An attacker who can write to `output/` already has
local file-system access, making this an unlikely attack path.

---

### T5 — Dependency supply chain

**Vector:** A dependency (Streamlit, Plotly, etc.) is compromised and ships
malicious code.

**Risk (Medium — shared with all Python applications):**
This is a standard supply-chain risk not specific to this application.

**Mitigations:**
- `requirements-dev.txt` pins all direct dependencies.
- We recommend verifying checksums (`pip hash`) before production deployments.
- The planned GitHub Actions release workflow can include a dependency audit
  step (`pip-audit`).

---

## Mitigations Implemented

| ID | Mitigation | Where |
| --- | --- | --- |
| M1 | **JSON recipe schema validator** | `pattern_catalog/phrase_transforms.py` → `_validate_recipe_entry()` |
| M2 | **Key allowlist** — step `transform` values must be built-in keys | Same as M1 |
| M3 | **Scalar-only params** — nested objects/arrays in `params` are rejected | Same as M1 |
| M4 | **Safe key format** — recipe keys must match `^[a-z][a-z0-9_]{0,63}$` | Same as M1 |
| M5 | **Python plugin gate** — `.py` files not loaded unless `FUNSCRIPT_PLUGINS_ENABLED=1` | `pattern_catalog/phrase_transforms.py` → `load_user_transforms()` |
| M6 | **Example file exclusion** — `example_*.py` skipped unconditionally | Same as M5 |
| M7 | **Input validation** on funscript files | `assessment/analyzer.py` + `tests/test_input_validation.py` |
| M8 | **Validate-plugins CLI command** — user can check files before loading | `cli.py` → `validate-plugins` subcommand |

---

## Mitigations Considered but Not Implemented

| Approach | Reason not implemented |
| --- | --- |
| **RestrictedPython for plugins** | Complex; the opt-in gate (M5) provides sufficient protection for a local tool; Python plugins require container isolation before they can be safely enabled |
| **Subprocess sandboxing for plugins** | Hard to implement cross-platform (especially Windows); the right solution is a containerised execution environment |
| **File-size limits on funscript input** | Low priority; deferred |
| **Dependency checksum pinning** | Tracked in backlog; not yet part of CI |

---

## Python Plugin Roadmap Decision

Python plugins are **not a local-app feature**.  The code infrastructure exists
(and is tested) but is disabled by default and will not be promoted as a
supported local feature.

**Rationale:**  A local app cannot adequately sandbox arbitrary Python code
without OS-level container isolation.  The risk to the user's machine
(credential theft, file destruction, network exfiltration) is too high to
expose as a general feature.

**Safe enablement requires a containerised environment:**

- Each plugin execution runs in an isolated container destroyed at session end
- No access to the host file system
- Network egress can be blocked at the infrastructure level
- Resource limits (CPU, memory, wall-clock time) are enforced by the runtime
- Code can be scanned (AST analysis, sandboxed test run) before acceptance

**Current status:**

| Feature | Status |
| --- | --- |
| JSON recipes (`user_transforms/`) | Supported |
| Built-in transform catalog | Supported |
| Python plugins (`plugins/`) | Gated — disabled by default; not a supported feature |

---

## Future Hardening (Backlog)

- [ ] `pip-audit` step in GitHub Actions release workflow
- [ ] File-size / action-count cap on funscript input to prevent DoS
- [ ] If Python plugins become widely used: evaluate RestrictedPython or
      subprocess isolation
- [ ] Code-signing for official transform packs (if a community registry is
      ever built)

---

## Reporting a Security Issue

This is a local desktop tool with no server component.  If you discover a
security issue, please open a private issue on the GitHub repository or email
the maintainer directly.  Do not disclose vulnerabilities publicly before a
fix is available.

---

*© 2026 Liquid Releasing. Licensed under the MIT License.*
