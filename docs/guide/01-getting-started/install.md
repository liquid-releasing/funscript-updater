# Install FunscriptForge

**Your journey:**
[Get a funscript](../00-overview/index.md) →
**Install** →
[Load your script](./your-first-funscript.md) →
[Read your assessment](../02-understand-your-script/reading-the-assessment.md) →
[Select phrases](../02-understand-your-script/phrases-at-a-glance.md) →
[Apply transforms](../03-improve-your-script/apply-a-transform.md) →
[Preview](../03-improve-your-script/preview-your-changes.md) →
[Export](../04-export-and-use/export.md)

---

## Overview

This step gets FunscriptForge running on your machine. You will download the app,
launch it, and confirm that it opens correctly in your browser. The whole process
takes about two minutes.

FunscriptForge runs as a local web app — it opens in your browser, but all processing
happens on your computer. Nothing is uploaded anywhere.

---

## Why do this first

You cannot do anything else in this guide until the app is installed and running.
This step has no prerequisites.

**What to expect:** Download is ~150 MB. First launch takes 5–10 seconds while the app
starts up. After that, launches are fast.

---

## Prerequisites

- A computer running Windows 10/11, macOS 10.15+, or Linux (x86-64)
- 4 GB RAM minimum (8 GB recommended)
- A modern browser (Chrome or Edge recommended; Firefox and Safari work)
- A `.funscript` file you want to work on — you will need this in the next step

> **Don't have a funscript yet?** The [overview page](../00-overview/index.md) explains
> where funscripts come from and what tools create them. Come back here once you have one.

---

## Steps

### 1. Download FunscriptForge

Go to the [FunscriptForge releases page](https://github.com/liquid-releasing/funscriptforge/releases)
and download the file for your operating system:

| Operating system | File to download |
| --- | --- |
| Windows 10 / 11 | `FunscriptForge-windows.zip` |
| macOS | `FunscriptForge-macos.zip` |
| Linux (x86-64) | `FunscriptForge-linux.tar.gz` |

> **TODO: insert screenshot — GitHub Releases page with download buttons highlighted**

---

### 2. Extract the app

**Windows:**
Right-click `FunscriptForge-windows.zip` → **Extract All…** → choose a folder you can
find again, for example `C:\Program Files\FunscriptForge\` or your Desktop.

**macOS:**
Double-click the zip. You will get `FunscriptForge.app`. Drag it to your **Applications**
folder.

**Linux:**

```bash
tar -xzf FunscriptForge-linux.tar.gz
cd FunscriptForge
```

---

### 3. Launch the app

**Windows:**
Double-click **FunscriptForge.exe** inside the extracted folder.
A terminal window may flash briefly — that is normal.

**macOS — first launch only:**
macOS will block an unsigned app on the first open. Right-click (or Control-click)
**FunscriptForge.app** → **Open** → click **Open** in the dialog that appears.
This is a one-time step. After the first approval you can double-click normally.

> If macOS says the app is "damaged", open Terminal and run:
>
> ```bash
> xattr -cr /Applications/FunscriptForge.app
> ```
>
> Then try launching again.

**Linux:**

```bash
./FunscriptForge
```

---

### 4. Confirm it opened

Within 5–10 seconds your default browser should open automatically to the FunscriptForge
app. You will see the main interface with a sidebar and a chart area.

> **TODO: insert screenshot — the app open in browser, empty state (no funscript loaded yet)**

If the browser does not open automatically, go to `http://localhost:6789` manually.

---

## You should see

A browser window open to `http://localhost:6789` showing the FunscriptForge interface.
The sidebar on the left has a file path input. The main area says something like
"No funscript loaded" or shows a blank chart.

If you see this — you are done. The app is running.

---

## What you did

You downloaded FunscriptForge, extracted it, and launched it. The app is now running
as a local server on your machine. Your browser is the interface — you can bookmark
`http://localhost:6789` if you want a shortcut for next time.

FunscriptForge stays running in the background as long as the terminal / launcher window
is open. Close that window to shut the app down.

---

## Troubleshooting

| Symptom | What to do |
| --- | --- |
| Browser opens but shows "refused to connect" | Wait a few more seconds and refresh the tab — the server is still starting |
| App is slow on first load | Normal — the app compiles templates once on startup; subsequent loads are faster |
| Windows Defender / antivirus blocks the exe | Add a folder exception, or see [Antivirus false positives](../../INSTALL.md#antivirus--gatekeeper-false-positives) |
| macOS — "app is damaged" | Run `xattr -cr /Applications/FunscriptForge.app` in Terminal |
| macOS — blocked on first launch | Right-click → Open → Open (one-time approval) |
| Browser doesn't open automatically | Go to `http://localhost:6789` manually |
| App crashes immediately | Check that you have at least 4 GB RAM free; close other heavy apps |

Still stuck? [Ask the help assistant →](https://funscriptforge.com/help) *(coming soon)*

---

## Next step

[Load your first funscript →](./your-first-funscript.md)

---

## You might be wondering

- [What if the browser opens but the app shows an error?](https://funscriptforge.com/help?q=Browser+opens+but+app+shows+error)
- [Can I run FunscriptForge on more than one computer?](https://funscriptforge.com/help?q=Run+FunscriptForge+on+multiple+computers)
- [Where does FunscriptForge store my files?](https://funscriptforge.com/help?q=Where+does+FunscriptForge+store+files)

[Ask your own question →](https://funscriptforge.com/help)

---

## Related concepts

| | |
| --- | --- |
| **[System requirements](../../INSTALL.md#system-requirements)** | Full hardware and OS compatibility details |
| **[What is FunscriptForge?](../00-overview/index.md)** | The big picture before you dive in |

---

```mermaid
flowchart LR
    A[Get a funscript] --> B[Install]:::here
    B --> C[Load your script]
    C --> D[Read your assessment]
    D --> E[Select phrases]
    E --> F[Apply transforms]
    F --> G[Preview]
    G --> H[Export]
    classDef here fill:#6c63ff,color:#fff,stroke:#6c63ff
```

*© 2026 [Liquid Releasing](https://github.com/liquid-releasing). All rights reserved.*
