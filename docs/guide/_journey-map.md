# Journey Map — Canonical Reference

> This file defines the task-based journey map used as a footer on every tutorial page.
> Copy the appropriate version (with the correct node highlighted) into each page.
> Do not render this file directly.

---

## The journey (8 tasks)

```
Get a funscript → Install → Load your script → Read your assessment →
Select phrases → Apply transforms → Preview → Export
```

---

## Mermaid snippets — one per page

### 00-overview/index.md  (Get a funscript)
```mermaid
flowchart LR
    A[Get a funscript]:::here --> B[Install]
    B --> C[Load your script]
    C --> D[Read your assessment]
    D --> E[Select phrases]
    E --> F[Apply transforms]
    F --> G[Preview]
    G --> H[Export]
    classDef here fill:#6c63ff,color:#fff,stroke:#6c63ff
```

### 01-getting-started/install.md  (Install)
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

### 01-getting-started/your-first-funscript.md  (Load your script)
```mermaid
flowchart LR
    A[Get a funscript] --> B[Install]
    B --> C[Load your script]:::here
    C --> D[Read your assessment]
    D --> E[Select phrases]
    E --> F[Apply transforms]
    F --> G[Preview]
    G --> H[Export]
    classDef here fill:#6c63ff,color:#fff,stroke:#6c63ff
```

### 02-understand-your-script/reading-the-assessment.md  (Read your assessment)
```mermaid
flowchart LR
    A[Get a funscript] --> B[Install]
    B --> C[Load your script]
    C --> D[Read your assessment]:::here
    D --> E[Select phrases]
    E --> F[Apply transforms]
    F --> G[Preview]
    G --> H[Export]
    classDef here fill:#6c63ff,color:#fff,stroke:#6c63ff
```

### 02-understand-your-script/phrases-at-a-glance.md  (Select phrases)
```mermaid
flowchart LR
    A[Get a funscript] --> B[Install]
    B --> C[Load your script]
    C --> D[Read your assessment]
    D --> E[Select phrases]:::here
    E --> F[Apply transforms]
    F --> G[Preview]
    G --> H[Export]
    classDef here fill:#6c63ff,color:#fff,stroke:#6c63ff
```

### 03-improve-your-script/apply-a-transform.md  (Apply transforms)
```mermaid
flowchart LR
    A[Get a funscript] --> B[Install]
    B --> C[Load your script]
    C --> D[Read your assessment]
    D --> E[Select phrases]
    E --> F[Apply transforms]:::here
    F --> G[Preview]
    G --> H[Export]
    classDef here fill:#6c63ff,color:#fff,stroke:#6c63ff
```

### 03-improve-your-script/preview-your-changes.md  (Preview)
```mermaid
flowchart LR
    A[Get a funscript] --> B[Install]
    B --> C[Load your script]
    C --> D[Read your assessment]
    D --> E[Select phrases]
    E --> F[Apply transforms]
    F --> G[Preview]:::here
    G --> H[Export]
    classDef here fill:#6c63ff,color:#fff,stroke:#6c63ff
```

### 04-export-and-use/export.md  (Export)
```mermaid
flowchart LR
    A[Get a funscript] --> B[Install]
    B --> C[Load your script]
    C --> D[Read your assessment]
    D --> E[Select phrases]
    E --> F[Apply transforms]
    F --> G[Preview]
    G --> H[Export]:::here
    classDef here fill:#6c63ff,color:#fff,stroke:#6c63ff
```
