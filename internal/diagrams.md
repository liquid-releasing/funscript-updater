# FunscriptForge — Mermaid Diagrams

All diagrams render natively on GitHub and in any Mermaid-compatible viewer.

---

## 1. Deployment architectures

### Local mode

```mermaid
graph TB
    subgraph UserMachine["User's machine"]
        Browser["Browser\n(localhost:8501)"]
        Streamlit["Streamlit app\nui/streamlit/app.py"]
        Pipeline["Core pipeline\nassessment · transforms · customization"]
        FS["Local filesystem\ntest_funscript/  output/"]
    end

    Browser -->|HTTP| Streamlit
    Streamlit --> Pipeline
    Pipeline --> FS
```

### Self-hosted Docker mode

```mermaid
graph TB
    subgraph Docker["Docker Compose"]
        UI["Frontend\nStreamlit :8501"]
        API["FastAPI\n:8000"]
        Pipeline["Core Pipeline\nassessment · transforms\ncustomization · catalog"]
        MinIO["MinIO\nObject Storage"]
        DB["SQLite / Postgres"]
    end

    Browser["Browser"] -->|HTTP| UI
    Browser -->|HTTP| API
    UI --> API
    API --> Pipeline
    Pipeline --> MinIO
    Pipeline --> DB
```

### Cloud SaaS mode

```mermaid
graph TB
    Users["Users / Browsers"]
    CDN["CDN\nCloudFront / Cloudflare"]
    LB["Load Balancer\nALB"]

    subgraph Services["Cloud services (ECS / Cloud Run)"]
        FE["React / Next.js\nFrontend"]
        API["FastAPI\nAPI workers"]
        Workers["Celery\nBackground workers"]
    end

    subgraph Data["Data layer"]
        S3["S3\nFile storage"]
        PG["PostgreSQL\nUsers · projects · billing"]
        Redis["Redis\nQueue · session cache"]
    end

    Auth["Auth0\nIdentity"]
    Stripe["Stripe\nBilling"]

    Users --> CDN --> LB
    LB --> FE
    LB --> API
    API --> Workers
    Workers --> S3
    Workers --> PG
    API --> Redis
    API --> Auth
    API --> Stripe
```

---

## 2. Core pipeline flow

```mermaid
flowchart TD
    A["📂 .funscript file"] --> B["Parse actions\n(timestamp + position pairs)"]
    B --> C["Detect phases\n(up / down / flat segments)"]
    C --> D["Detect cycles\n(one complete oscillation)"]
    D --> E["Detect patterns\n(cycles with same direction + similar duration)"]
    E --> F["Detect phrases\n(consecutive runs of same pattern)"]
    F --> G["Compute BPM transitions\n(where tempo changes significantly)"]
    G --> H["Behavioral classification\n(tag each phrase: stingy · drone · frantic…)"]
    H --> I["Assessment JSON"]

    style A fill:#4a90d9,color:#fff
    style I fill:#27ae60,color:#fff
```

---

## 3. User workflow — Phrase Editor

```mermaid
sequenceDiagram
    participant U as User
    participant UI as Phrase Editor
    participant FS as FunscriptForge

    U->>UI: Load funscript
    UI->>FS: Run assessment pipeline
    FS-->>UI: Assessment JSON (phrases + tags)
    UI-->>U: Colour-coded chart with phrase boxes

    U->>UI: Click a phrase
    UI-->>U: Detail panel opens (Original chart)

    U->>UI: Select transform + adjust sliders
    UI->>FS: Compute preview
    FS-->>UI: Transformed actions
    UI-->>U: Before / After preview

    alt Accept
        U->>UI: Click ✓ Accept
        UI-->>U: Transform stored; return to selector
    else Cancel
        U->>UI: Click ✕ Cancel
        UI-->>U: Discard; return to selector (others unaffected)
    else Split
        U->>UI: Click ✂ Split phrase
        UI-->>U: Cycle slider + dashed split line on chart
        U->>UI: Drag to cycle boundary + confirm
        UI-->>U: Two new phrases created; navigate to A
    end
```

---

## 4. User workflow — Pattern Editor (batch fix)

```mermaid
flowchart LR
    A["Select\nbehavioral tag\ne.g. 'drone'"] --> B["View all\nmatching phrases"]
    B --> C["Select instance\nPrev / Next"]
    C --> D["Choose transform\nadjust sliders"]
    D --> E{"Apply scope"}
    E -->|This instance| F["Mark Done\n(this phrase only)"]
    E -->|Apply to all| G["Copy transform\nto every checked instance"]
    G --> H["All instances\nmarked Done"]
    F --> I["Next instance?"]
    H --> I
    I -->|Yes| C
    I -->|No| J["Export tab →\nDownload"]

    style A fill:#8e44ad,color:#fff
    style J fill:#27ae60,color:#fff
```

---

## 5. User workflow — Export

```mermaid
flowchart TD
    A["Export tab"] --> B["Preview chart\n(full proposed output)"]
    B --> C["Completed transforms\n(Phrase + Pattern Editor)"]
    B --> D["Recommended transforms\n(auto-suggested, unaccepted)"]

    C --> E{"Review each row"}
    E -->|Keep| F["✅ Included"]
    E -->|Reject 🗑| G["❌ Excluded (strikethrough)"]
    E -->|Restore ↩| F

    D --> H{"Explicitly accept?"}
    H -->|✓ Accept| I["✅ Added to export"]
    H -->|Ignore| J["⬜ Not included"]
    H -->|Edit ✏| K["Opens Phrase Editor\nfor that phrase"]

    F --> L["Optional post-processing"]
    I --> L
    L --> M{"Add blended seams?"}
    M -->|Yes| N["blend_seams LPF\nat style boundaries"]
    M -->|No| O["Skip"]
    N --> P{"Final smooth?"}
    O --> P
    P -->|Yes| Q["Light global LPF\nstrength 0.10"]
    P -->|No| R["Skip"]
    Q --> S["⬇ Download .funscript"]
    R --> S

    style S fill:#27ae60,color:#fff
```

---

## 6. Behavioral classification — decision tree

```mermaid
flowchart TD
    A["Phrase"] --> B{"BPM > 200?"}
    B -->|Yes| FRANTIC["🔴 frantic\n→ halve_tempo"]
    B -->|No| C{"Amplitude span < 30?"}
    C -->|Yes| D{"Centre ≈ 50?"}
    D -->|Yes| GIGGLE["🟡 giggle\n→ normalize"]
    D -->|No| HALFS["🟠 half_stroke\n→ recenter"]
    C -->|No| E{"Peak position < 40?"}
    E -->|Yes| STINGY["🔵 stingy\n→ amplitude_scale ↓"]
    E -->|No| F{"Velocity variance low?"}
    F -->|Yes| G{"Duration > 60s?"}
    G -->|Yes| DRONE["🟣 drone\n→ beat_accent"]
    G -->|No| PLATEAU["🟤 plateau\n→ amplitude_scale ↑"]
    F -->|No| H{"Centre displaced > 15?"}
    H -->|Yes| DRIFT["🟢 drift\n→ recenter"]
    H -->|No| I{"BPM < threshold?"}
    I -->|Yes| LAZY["⚪ lazy\n→ amplitude_scale ↑"]
    I -->|No| UNTAGGED["— untagged\n→ suggest by BPM rules"]
```

---

## 7. Transform catalog — groups

```mermaid
mindmap
  root((Transforms))
    Passthrough
      passthrough
    Amplitude shaping
      amplitude_scale
      normalize
      boost_contrast
    Position adjustment
      shift
      recenter
      clamp_upper
      clamp_lower
      invert
    Smoothing
      smooth
      blend_seams
      final_smooth
    Break / Recovery
      break
    Performance
      performance
    Rhythmic
      beat_accent
      three_one
    Structural tempo
      halve_tempo
    Timing / Sync
      nudge
```

---

## 8. Agentic AI pipeline (vision)

```mermaid
flowchart TD
    Video["🎬 Raw video"] --> Orchestrator

    subgraph Orchestrator["Orchestrator Agent (Claude)"]
        Plan["Plan pipeline\nsteps"]
        Validate["Validate output\nquality score"]
        Explain["Generate\nsession report"]
    end

    Orchestrator --> SceneAgent
    Orchestrator --> AudioAgent
    Orchestrator --> MotionAgent
    Orchestrator --> ForgeAgent
    Orchestrator --> DeviceAgent

    subgraph SceneAgent["Scene Analysis Agent"]
        CLIP["CLIP scene tags"]
        SceneDetect["SceneDetect\ncut boundaries"]
    end

    subgraph AudioAgent["Audio Agent"]
        Librosa["Beat grid\nBPM curve"]
        Whisper["Speech timing\nVocal peaks"]
    end

    subgraph MotionAgent["Motion Generation Agent"]
        PythonDancer["PythonDancer\nOptical flow → funscript"]
    end

    subgraph ForgeAgent["FunscriptForge Agent"]
        Assess["assess\n(classify phrases)"]
        Transform["export-plan --apply\n(auto-transform)"]
        QualityGate["Quality gate\n(score ≥ threshold?)"]
    end

    subgraph DeviceAgent["Multi-Device Agent"]
        Restim["Restim\nestim patterns"]
        MFP["MultiFunPlayer\ndevice routing config"]
    end

    SceneAgent --> MotionAgent
    AudioAgent --> MotionAgent
    MotionAgent --> ForgeAgent
    ForgeAgent --> QualityGate
    QualityGate -->|Pass| DeviceAgent
    QualityGate -->|Fail| Plan

    DeviceAgent --> Output["📦 Output bundle\n.funscript · .restim · .mfp config\n+ session report"]

    style Video fill:#e74c3c,color:#fff
    style Output fill:#27ae60,color:#fff
    style Orchestrator fill:#2980b9,color:#fff
```

---

## 9. SaaS data flow

```mermaid
sequenceDiagram
    participant U as User (browser)
    participant FE as Frontend (React)
    participant API as FastAPI
    participant Q as Celery queue
    participant W as Worker
    participant S3 as S3 storage
    participant DB as PostgreSQL

    U->>FE: Upload .funscript
    FE->>API: POST /assess (multipart)
    API->>S3: Store raw file (user/project/raw.funscript)
    API->>Q: Enqueue assessment job
    API-->>FE: { job_id }

    Q->>W: Dispatch job
    W->>S3: Fetch raw file
    W->>W: Run FunscriptAnalyzer
    W->>S3: Store assessment.json
    W->>DB: Update job status = complete
    W-->>Q: Done

    FE->>API: GET /job/{job_id}/status (polling or websocket)
    API->>DB: Check status
    API-->>FE: { status: complete, assessment_url }

    FE->>S3: Fetch assessment (presigned URL)
    FE-->>U: Render phrase chart + tags

    U->>FE: Apply transforms + click Download
    FE->>API: POST /export (transform plan JSON)
    API->>Q: Enqueue export job
    Q->>W: Dispatch
    W->>S3: Fetch raw + assessment
    W->>W: Apply transforms + seam blend
    W->>S3: Store result.funscript
    W->>DB: Update job done
    FE->>API: GET /job/{job_id}/download
    API->>S3: Generate presigned download URL
    API-->>FE: Redirect to presigned URL
    FE-->>U: ⬇ Download result.funscript
```
