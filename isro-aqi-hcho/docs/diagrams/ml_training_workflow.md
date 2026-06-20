# ML Training & Deployment Workflow

This diagram outlines the end-to-end workflow: data ingestion → feature engineering → sequence generation → model training → evaluation → export → dashboard/serving.

```mermaid
flowchart TD
  subgraph DataSources
    S5[TROPOMI]
    INS[INSAT-3D]
    ERA[ERA5]
    FIR[FIRMS]
    CPC[CPCB]
  end

  S5 & INS & ERA & FIR & CPC --> DL[Downloaders & Collectors\n(`src/data/*_download*.py`)]
  DL --> FE[Feature Engineering\n`build_dataset_aqi.py`, `build_dataset_hcho.py`]
  FE --> STORE[data/processed/*.csv / netCDF]
  STORE --> SEQ[Sequence generation\n(sliding-window, context features)]
  SEQ --> TRAIN[Train Pipeline\n`src/models/train_aqi.py`]
  TRAIN --> CKPT[Saved checkpoint (.pt)]
  TRAIN --> EVAL[Evaluation & metrics]
  EVAL --> EXPORT[Export predictions, GeoJSON, netCDF]
  EXPORT --> DASH[Dashboard & Visualization\n`src/webapp/app.py`]
  STORE --> DASH

  subgraph Automation
    PIPE[Orchestrator: `scripts/run_pipeline.py`]
    PIPE --> DL
    PIPE --> FE
    PIPE --> TRAIN
  end

  classDef infra fill:#fff2cc,stroke:#cc9900
  classDef compute fill:#e6f7ff,stroke:#66a3ff
  class PIPE infra
  class DL infra
  class TRAIN compute
```