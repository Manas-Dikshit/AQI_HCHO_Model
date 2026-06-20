# ML Model Architecture

This diagram shows the CNN-LSTM (Conv → LSTM) model used to estimate surface PM2.5 (and hence AQI) from multi-source satellite and meteorological features.

```mermaid
flowchart LR
  subgraph Inputs[Multi-source inputs]
    TROP[TROPOMI\n(NO2, HCHO, O3, CO, SO2)]
    INS[INSAT-3D\n(AOD)]
    ERA[ERA5\n(T, RH, U10, V10, BLH, TP)]
    FIR[FIRMS\n(fire_count)]
    CPC[CPCB\n(ground PM2.5)]
  end

  Inputs --> Preproc[Preprocessing & Grid Aggregation]\n`build_dataset_aqi.py` / `build_dataset_hcho.py`
  Preproc --> Seq[Sequence Builder\n(sliding window of T days, per cell)]
  Seq --> Conv[Spatial Encoder\n(Time-distributed Conv layers / shared CNN)]
  Conv --> TD[Time-distributed Features\n(Flatten / pooling per timestep)]
  TD --> LSTM[LSTM / GRU\n(temporal fusion across T timesteps)]
  LSTM --> Dense[Fully-connected layers]
  Dense --> PM25[PM2.5 Prediction]
  PM25 --> AQI[AQI Conversion & Postprocessing]
  AQI --> Output[Gridded AQI map / per-cell predictions]

  subgraph ModelArtifacts
    CKPT[Model checkpoint (.pt / .ckpt)]
    METR[Metrics & eval reports]
  end
  Dense --> CKPT
  Dense --> METR

  style Inputs fill:#f9f,stroke:#333,stroke-width:1px
  style Conv fill:#bbf,stroke:#333,stroke-width:1px
  style LSTM fill:#bfb,stroke:#333,stroke-width:1px
  style PM25 fill:#ffd,stroke:#333,stroke-width:1px
```