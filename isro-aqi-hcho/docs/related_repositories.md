# Related Open-Source Repositories & Methodologies

This document compiles, reviews, and compares existing open-source repositories, libraries, and research codebases that align with the objectives of the **ISRO Hackathon: Surface AQI & HCHO Hotspot Detection**. These repositories serve as valuable references for data ingestion, spatiotemporal feature engineering, modeling, and transport analysis.

---

## 📊 Summary Comparison

| Repository | Primary Focus | Region | Key Data Sources | Models / Stack |
| :--- | :--- | :--- | :--- | :--- |
| **[pm25ml](#1-energyandcleanairpm25ml)** | Gridded Daily PM2.5 Estimation | India | TROPOMI (CO, NO2), AOD, ERA5, CPCB | Two-stage ML, Google Earth Engine, Vertex AI |
| **[TROPOMI_EXTRACTS](#2-urbanemissionstropomiextracts)** | TROPOMI Airshed Extraction | India | TROPOMI columns (NO2, SO2, CO, O3, HCHO) | Python, GEE API, Matplotlib |
| **[sentinel5P-automated](#3-sentinel5p-automated)** | Automated L2 to L3 Processing | Global / Custom | Sentinel-5P (all products) | Python, ESA HARP, Copernicus API |
| **[s5p-tools](#4-s5p-tools)** | L2 Download & HARP Resampling | Global / Custom | Sentinel-5P L2 products | Python, HARP, netCDF4 |
| **[Wildfire Dynamics SE Africa](#5-wildfire-dynamics-southeast-africa)** | Biomass Burning & Emissions | Southeast Africa | TROPOMI columns, MODIS Burned Area | GEE, Python, Geopandas |
| **[airfortomorrow](#6-unicefairfortomorrow)** | Surface PM2.5 Forecasting | Thailand & Laos | Sentinel-5P, ERA5, ground stations | XGBoost, Python, Pandas |
| **[PM_Forecast](#7-suki-designpmforecast)** | Spatiotemporal PM2.5 Prediction | Urban / Local | ERA5-Land, ground sensors | TCN (Temporal Conv Network), XGBoost |

---

## 🔍 Detailed Repository Breakdown

### 1. `energyandcleanair/pm25ml`
*   **Source**: [energyandcleanair/pm25ml (GitHub)](https://github.com/energyandcleanair/pm25ml)
*   **Organization**: Center for Research on Energy and Clean Air (CREA)
*   **Scope & Goal**: Generates daily surface PM2.5 estimates at a 10 km resolution across India, linking satellite columns to ground station measurements.
*   **Key Methodology**:
    *   Fuses TROPOMI column metrics ($\text{CO}$, $\text{NO}_2$) and Aerosol Optical Depth (AOD) with ERA5 meteorological parameters, land-use classifications, and elevation datasets.
    *   Implements a two-stage machine learning regression algorithm. The first stage uses random forest or boosting structures to map satellite columns to coarse ground estimates, and the second stage applies local spatial residuals corrections.
    *   Leverages Google Earth Engine (GEE) as the backbone database to query, clean, and extract features before training models on Vertex AI.
*   **Relevance to ISRO PS**: Excellent reference for upgrading from the current single-stage CNN-LSTM to a multi-stage residual spatial correction framework.

---

### 2. `urbanemissions/TROPOMI_EXTRACTS`
*   **Source**: [urbanemissionsinfo/TROPOMI_EXTRACTS (GitHub)](https://github.com/urbanemissionsinfo/TROPOMI_EXTRACTS)
*   **Organization**: Urban Emissions Info
*   **Scope & Goal**: A collection of scripts to extract satellite column products over specific urban airsheds and regions in India.
*   **Key Methodology**:
    *   Utilizes GEE python APIs to filter Sentinel-5P TROPOMI Level-3 datasets.
    *   Extracts spatially averaged time series as CSVs and exports high-resolution gridded TIF (GeoTIFF) files for cities.
    *   Focuses heavily on particulate precursors ($\text{NO}_2$, $\text{SO}_2$, $\text{CO}$, $\text{O}_3$, and $\text{HCHO}$).
*   **Relevance to ISRO PS**: Can serve as a template to replace or upgrade `src/data/download_tropomi.py` with custom boundary-based airshed filters, making ingestion faster.

---

### 3. `sentinel5P-automated`
*   **Source**: [sentinel5P-automated (GitHub)](https://github.com/sk-t/sentinel5P-automated)
*   **Scope & Goal**: End-to-end automation for querying, downloading, and converting Sentinel-5P Level 2 (L2) orbit files to Level 3 (L3) gridded netCDF formats.
*   **Key Methodology**:
    *   Monitors and queries the Copernicus API automatically for new orbits.
    *   Uses **ESA HARP (Data Harmonisation Toolset)** to crop, resample, and bin orbital swath data onto fixed regular grids.
    *   Includes built-in quality assurance ($\text{qa\_value}$) filtering and cloud-masking options.
*   **Relevance to ISRO PS**: Demonstrates how to transition from the GEE cloud catalog to raw Copernicus L2 data streams, which is necessary for near-real-time (NRT) operational pipelines.

---

### 4. `s5p-tools`
*   **Source**: [s5p-tools (GitHub)](https://github.com/n5ro/s5p-tools)
*   **Scope & Goal**: Command-line tools for local preprocessing and resampling of Sentinel-5P datasets.
*   **Key Methodology**:
    *   Uses Python's `harp` binding to apply binning operations.
    *   Simplifies local processing of raw NetCDFs, converting native Sentinel orbit swaths into standard WGS-84 lat-lon projections.
*   **Relevance to ISRO PS**: High-performance local alternative to Google Earth Engine dependencies, particularly useful if the solution needs to run offline or in a secure environment.

---

### 5. `Wildfire-Dynamics-SouthEastAfrica`
*   **Source**: [Wildfire-Dynamics-SouthEastAfrica (GitHub)](https://github.com/Tess-G/Wildfire-Dynamics-SouthEastAfrica)
*   **Scope & Goal**: Analyzes wildfire trends, atmospheric emissions, and forest cover dynamics over decadal timescales.
*   **Key Methodology**:
    *   Correlates satellite fire observations (MODIS Burned Area) with atmospheric emission indicators.
    *   Processes spatial wind vectors to analyze plume dispersion.
    *   Integrates multiple GEE layers for spatiotemporal tracking.
*   **Relevance to ISRO PS**: Provides a references for studying biomass burning plume propagation. Can help refine the HCHO-fire lag correlation and wind transport quiver overlay modules in `src/features/make_features_hcho.py` and the Streamlit dashboard.

---

### 6. `unicef/airfortomorrow`
*   **Source**: [unicef/airfortomorrow (GitHub)](https://github.com/unicef/airfortomorrow)
*   **Organization**: UNICEF East Asia and Pacific
*   **Scope & Goal**: Fuses satellite columns, ERA5 weather data, and ground stations to forecast daily PM2.5 in Thailand and Laos.
*   **Key Methodology**:
    *   Standardizes spatial features into data frames using Python and Pandas.
    *   Trains an extreme gradient boosting (**XGBoost**) regressor to predict PM2.5.
    *   Incorporates temporal cyclical parameters and rolling window statistics as covariates.
*   **Relevance to ISRO PS**: Provides a solid reference for validating model performance, feature importance analysis, and deploying models inside a lightweight dashboard.

---

### 7. `Suki-design/PM_Forecast`
*   **Source**: [Suki-design/PM_Forecast (GitHub)](https://github.com/Suki-design/PM_Forecast)
*   **Scope & Goal**: Spatiotemporal air quality forecasting using deep neural networks and gradient boosting architectures.
*   **Key Methodology**:
    *   Utilizes **Temporal Convolutional Networks (TCN)** and **XGBoost** to forecast ground PM2.5 levels.
    *   Focuses on explainable AI (SHAP values) to interpret meteorological features (ERA5-Land) and historical trends.
*   **Relevance to ISRO PS**: Useful reference for extending the CNN-LSTM and ConvLSTM models (implemented in `src/models/cnn_lstm_aqi.py`) with attention mechanisms or explanation frameworks.

---

## 🛠️ Key Recommendations for Project Enhancement

By analyzing these existing codebases, the following enhancements could improve the current **ISRO AQI & HCHO** pipeline:

1.  **Transition to Copernicus Data Space Ecosystem (CDSE)**:
    Since the Copernicus Open Access Hub has been deprecated, raw data collection modules (like [download_tropomi.py](file:///c:/Users/Dev/Desktop/AQI_HCHO_Model/isro-aqi-hcho/src/data/download_tropomi.py)) should interface with CDSE APIs using token authentication, using libraries like `s5p-tools` or `sentinel5P-automated` as reference architectures.
2.  **Adding Local Spatial Residual Interpolation (Kriging / IDW)**:
    Implement a two-stage regression method similar to `pm25ml`. In Stage 1, use the CNN-LSTM model to generate raw grid estimates. In Stage 2, interpolate prediction residuals at CPCB stations across the grid using Kriging or Inverse Distance Weighting (IDW) to adjust grid predictions based on local ground observations.
3.  **Explainable AI (XAI)**:
    Integrate feature attribution methods (such as SHAP or Integrated Gradients) to explain the deep spatiotemporal predictions, identifying which satellite column (e.g., $\text{NO}_2$ vs. $\text{CO}$) or weather parameter (e.g., wind speeds vs. boundary layer height) has the highest impact on predicted surface AQI.
