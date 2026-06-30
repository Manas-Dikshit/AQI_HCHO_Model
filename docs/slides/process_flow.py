"""Render process-flow diagram as PNG using Pillow."""

from PIL import Image, ImageDraw, ImageFont
import os

W, H = 1920, 1080

# Colors
WHITE = (255, 255, 255)
BLACK = (15, 23, 42)
BLUE_DARK = (30, 58, 95)
BLUE = (37, 99, 235)
BLUE_LIGHT = (219, 234, 254)
BLUE_BORDER = (59, 130, 246)
TEAL = (13, 148, 136)
TEAL_LIGHT = (204, 251, 241)
TEAL_BORDER = (20, 184, 166)
GREEN = (22, 163, 74)
GREEN_LIGHT = (220, 252, 231)
GREEN_BORDER = (74, 222, 128)
AMBER = (217, 119, 6)
AMBER_LIGHT = (254, 243, 199)
AMBER_BORDER = (251, 191, 36)
RED = (220, 38, 38)
RED_LIGHT = (254, 226, 226)
RED_BORDER = (252, 129, 129)
PURPLE = (126, 34, 206)
PURPLE_LIGHT = (243, 232, 255)
PURPLE_BORDER = (192, 132, 252)
GRAY = (100, 116, 139)
GRAY_BG = (248, 250, 252)
GRAY_BORDER = (203, 213, 225)

def get_font(size, bold=False):
    try:
        p = "C:/Windows/Fonts/"
        return ImageFont.truetype(p + ("arialbd.ttf" if bold else "arial.ttf"), size)
    except:
        return ImageFont.load_default()

def center_text(draw, cx, cy, text, font, fill=BLACK):
    bbox = draw.textbbox((0, 0), text, font=font)
    draw.text((cx - (bbox[2]-bbox[0])//2, cy - (bbox[3]-bbox[1])//2), text, font=font, fill=fill)

def rbox(draw, xy, fill, outline=None, radius=8, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)

def arrow_down(draw, cx, y1, y2, color=GRAY):
    draw.line([(cx, y1), (cx, y2)], fill=color, width=2)
    draw.polygon([(cx-7, y2-10), (cx+7, y2-10), (cx, y2)], fill=color)

def arrow_right(draw, x1, y1, x2, y2, color=GRAY):
    draw.line([(x1, y1), (x2, y2)], fill=color, width=2)
    import math
    a = math.atan2(y2-y1, x2-x1)
    draw.polygon([(x2-10*math.cos(a-0.4), y2-10*math.sin(a-0.4)),
                  (x2-10*math.cos(a+0.4), y2-10*math.sin(a+0.4)),
                  (x2, y2)], fill=color)

def main():
    img = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(img)

    f10 = get_font(10)
    f11 = get_font(11)
    f12 = get_font(12)
    f13 = get_font(13)
    f14b = get_font(14, True)
    f16b = get_font(16, True)
    f20b = get_font(20, True)
    f26b = get_font(26, True)
    f32b = get_font(32, True)

    # ===== TITLE =====
    draw.rectangle([(0, 0), (W, 78)], fill=BLUE_DARK)
    center_text(draw, 960, 40, "End-to-End Process Flow — Surface AQI & HCHO Hotspot Detection", f26b, WHITE)

    # ===== STAGE 1: DATA COLLECTION =====
    stage1_x = 60
    rbox(draw, (stage1_x, 110, stage1_x+280, 150), fill=BLUE_LIGHT, outline=BLUE_BORDER, radius=6)
    center_text(draw, stage1_x+140, 130, "STAGE 1: Data Collection", f14b, BLUE_DARK)

    sources = [
        (stage1_x, 165, stage1_x+130, 208, "CPCB CAAQM", "Ground PM\u2082.\u2085, NO\u2082, SO\u2082"),
        (stage1_x+140, 165, stage1_x+270, 208, "Sentinel-5P", "TROPOMI columns"),
        (stage1_x, 218, stage1_x+130, 261, "INSAT-3D", "AOD 550 nm"),
        (stage1_x+140, 218, stage1_x+270, 261, "ERA5", "T, RH, U/V, TP, SP, BLH"),
        (stage1_x, 271, stage1_x+270, 314, "NASA FIRMS / VIIRS", "Fire pixel counts"),
        (stage1_x, 324, stage1_x+270, 367, "Static Layers", "Land cover, elevation, population"),
    ]
    for x1, y1, x2, y2, t, d in sources:
        rbox(draw, (x1, y1, x2, y2), fill=WHITE, outline=BLUE_BORDER, radius=4)
        center_text(draw, (x1+x2)//2, y1+14, t, f12, BLUE_DARK)
        center_text(draw, (x1+x2)//2, y1+34, d, f11, GRAY)

    arrow_down(draw, stage1_x+140, 368, 410)

    # ===== STAGE 2: DATA PREPROCESSING =====
    stage2_x = 60
    rbox(draw, (stage2_x, 410, stage2_x+280, 450), fill=TEAL_LIGHT, outline=TEAL_BORDER, radius=6)
    center_text(draw, stage2_x+140, 430, "STAGE 2: Data Preprocessing", f14b, TEAL)

    tasks2 = [
        (stage2_x, 465, stage2_x+270, 508, "Grid Aggregation", "Snap all to 0.1\u00b0 India grid"),
        (stage2_x, 518, stage2_x+270, 561, "Temporal Alignment", "Daily resampling & interpolation"),
        (stage2_x, 571, stage2_x+270, 614, "Quality Control", "Outlier removal, missing data fill"),
    ]
    for x1, y1, x2, y2, t, d in tasks2:
        rbox(draw, (x1, y1, x2, y2), fill=WHITE, outline=TEAL_BORDER, radius=4)
        center_text(draw, (x1+x2)//2, y1+15, t, f12, (17, 94, 89))
        center_text(draw, (x1+x2)//2, y1+35, d, f11, GRAY)

    arrow_down(draw, stage2_x+140, 615, 655)

    # ===== STAGE 3: FEATURE ENGINEERING =====
    stage3_x = 60
    rbox(draw, (stage3_x, 655, stage3_x+280, 695), fill=GREEN_LIGHT, outline=GREEN_BORDER, radius=6)
    center_text(draw, stage3_x+140, 675, "STAGE 3: Feature Engineering", f14b, GREEN)

    tasks3 = [
        (stage3_x, 710, stage3_x+270, 745, "AQI Features", "Rolling means, sin-cos cycles, 3\u00d73 spatial context"),
        (stage3_x, 755, stage3_x+270, 790, "HCHO Features", "Anomaly (z-score), persistence, wind transport"),
    ]
    for x1, y1, x2, y2, t, d in tasks3:
        rbox(draw, (x1, y1, x2, y2), fill=WHITE, outline=GREEN_BORDER, radius=4)
        center_text(draw, (x1+x2)//2, y1+15, t, f12, (20, 83, 45))
        center_text(draw, (x1+x2)//2, y1+33, d, f11, GRAY)

    arrow_down(draw, stage3_x+140, 791, 830)

    # ===== STAGE 4: MODEL TRAINING =====
    stage4_x = 60
    rbox(draw, (stage4_x, 830, stage4_x+280, 870), fill=AMBER_LIGHT, outline=AMBER_BORDER, radius=6)
    center_text(draw, stage4_x+140, 850, "STAGE 4: Model Training", f14b, AMBER)

    tasks4 = [
        (stage4_x, 885, stage4_x+270, 920, "Baseline ML", "Random Forest, Gradient Boosting (GridSearchCV)"),
        (stage4_x, 930, stage4_x+270, 965, "Deep Learning", "CNN-LSTM / ConvLSTM (PyTorch)"),
        (stage4_x, 975, stage4_x+270, 1010, "Train / Test Split", "2019-2021 Train  ·  2022 Test"),
    ]
    for x1, y1, x2, y2, t, d in tasks4:
        rbox(draw, (x1, y1, x2, y2), fill=WHITE, outline=AMBER_BORDER, radius=4)
        center_text(draw, (x1+x2)//2, y1+15, t, f12, (113, 63, 18))
        center_text(draw, (x1+x2)//2, y1+33, d, f11, GRAY)

    # ===== ARROW branching to parallel tracks =====
    # From Stage 4 to Stage 5 (AQI path)
    arrow_right(draw, 340, 230, 420, 230)

    # ===== RIGHT SIDE: PARALLEL TRACKS =====
    # Track A: AQI Pipeline (top)
    track_a_x = 430
    rbox(draw, (track_a_x, 110, track_a_x+380, 150), fill=BLUE_LIGHT, outline=BLUE_BORDER, radius=6)
    center_text(draw, track_a_x+190, 130, "TRACK A: AQI Prediction Pipeline", f14b, BLUE_DARK)

    aqi_steps = [
        (track_a_x+10, 165, track_a_x+370, 205, "Model Training", "RF / GBM / CNN-LSTM on station data"),
        (track_a_x+10, 218, track_a_x+370, 258, "Hyperparameter Tuning", "GridSearch + ReduceLROnPlateau + EarlyStop"),
        (track_a_x+10, 271, track_a_x+370, 311, "Evaluation", "R\u00b2, RMSE, MAE, scatter & time-series plots"),
        (track_a_x+10, 324, track_a_x+370, 364, "Full-Grid Inference", "Predict PM\u2082.\u2085 over all 0.1\u00b0 India grid cells"),
        (track_a_x+10, 377, track_a_x+370, 417, "AQI Conversion", "CPCB Indian AQI formula from PM\u2082.\u2085"),
    ]
    for i, (x1, y1, x2, y2, t, d) in enumerate(aqi_steps):
        c = [BLUE_BORDER, BLUE_BORDER, BLUE_BORDER, BLUE_BORDER, BLUE_BORDER][i]
        rbox(draw, (x1, y1, x2, y2), fill=WHITE, outline=c, radius=4)
        center_text(draw, (x1+x2)//2, y1+16, t, f12, BLUE_DARK)
        center_text(draw, (x1+x2)//2, y1+35, d, f11, GRAY)
        if i < len(aqi_steps)-1:
            arrow_down(draw, (x1+x2)//2, y2+2, y2+14)

    # Track B: HCHO Pipeline (bottom)
    track_b_x = 430
    rbox(draw, (track_b_x, 500, track_b_x+380, 540), fill=RED_LIGHT, outline=RED_BORDER, radius=6)
    center_text(draw, track_b_x+190, 520, "TRACK B: HCHO Hotspot Pipeline", f14b, RED)

    hcho_steps = [
        (track_b_x+10, 555, track_b_x+370, 595, "HCHO + Fire Fusion", "Join TROPOMI HCHO + FIRMS fire counts"),
        (track_b_x+10, 608, track_b_x+370, 648, "Hotspot Thresholding", "90th-percentile anomaly flagging"),
        (track_b_x+10, 661, track_b_x+370, 701, "DBSCAN Clustering", "Spatial cluster identification + persistence"),
        (track_b_x+10, 714, track_b_x+370, 754, "Wind Transport Analysis", "Wind quiver overlays, trajectory mapping"),
        (track_b_x+10, 767, track_b_x+370, 807, "Export Hotspot Products", "Cluster GeoJSON · Top-N regions CSV"),
    ]
    for i, (x1, y1, x2, y2, t, d) in enumerate(hcho_steps):
        c = [RED_BORDER, RED_BORDER, RED_BORDER, RED_BORDER, RED_BORDER][i]
        rbox(draw, (x1, y1, x2, y2), fill=WHITE, outline=c, radius=4)
        center_text(draw, (x1+x2)//2, y1+16, t, f12, (127, 29, 29))
        center_text(draw, (x1+x2)//2, y1+35, d, f11, GRAY)
        if i < len(hcho_steps)-1:
            arrow_down(draw, (x1+x2)//2, y2+2, y2+14)

    # ===== MERGE TO OUTPUT =====
    arrow_right(draw, 432, 410, 810, 410)
    arrow_right(draw, 432, 810, 810, 810)
    arrow_right(draw, 810, 410, 810, 440)

    # ===== STAGE 5: OUTPUT GENERATION =====
    stage5_x = 830
    arrow_down(draw, stage5_x + 250, 438, 468)

    rbox(draw, (stage5_x, 470, stage5_x+500, 510), fill=PURPLE_LIGHT, outline=PURPLE_BORDER, radius=6)
    center_text(draw, stage5_x+250, 490, "STAGE 5: Output Generation & Export", f14b, PURPLE)

    outputs = [
        (stage5_x, 525, stage5_x+240, 575, "AQI Outputs", "NetCDF grids · GeoTIFF rasters"),
        (stage5_x+255, 525, stage5_x+495, 575, "HCHO Outputs", "Cluster GeoJSON · Top-N CSV"),
        (stage5_x, 590, stage5_x+240, 640, "Model Artifacts", ".pt checkpoints · .joblib models"),
        (stage5_x+255, 590, stage5_x+495, 640, "Metrics & Reports", "Evaluation plots · Feature importance"),
    ]
    for x1, y1, x2, y2, t, d in outputs:
        rbox(draw, (x1, y1, x2, y2), fill=WHITE, outline=PURPLE_BORDER, radius=4)
        center_text(draw, (x1+x2)//2, y1+18, t, f12, (107, 33, 168))
        center_text(draw, (x1+x2)//2, y1+38, d, f11, GRAY)

    arrow_down(draw, stage5_x+250, 641, 680)

    # ===== STAGE 6: DASHBOARD =====
    rbox(draw, (stage5_x, 680, stage5_x+500, 720), fill=BLUE_DARK, outline=BLACK, radius=8)
    center_text(draw, stage5_x+250, 700, "STAGE 6: Streamlit Dashboard", f16b, WHITE)

    dash_pages = [
        (stage5_x, 735, stage5_x+155, 775, "AQI Maps", "Gridded + choropleth"),
        (stage5_x+165, 735, stage5_x+320, 775, "HCHO Maps", "Clusters + quivers"),
        (stage5_x+330, 735, stage5_x+495, 775, "Time Series", "City + regional plots"),
        (stage5_x, 788, stage5_x+155, 828, "Performance", "Metrics + importance"),
        (stage5_x+165, 788, stage5_x+320, 828, "Seasonal", "IMD convention"),
        (stage5_x+330, 788, stage5_x+495, 828, "Data Explorer", "Raw data viewer"),
    ]
    for x1, y1, x2, y2, t, d in dash_pages:
        rbox(draw, (x1, y1, x2, y2), fill=WHITE, outline=BLUE_BORDER, radius=4)
        center_text(draw, (x1+x2)//2, y1+16, t, f12, BLUE_DARK)
        center_text(draw, (x1+x2)//2, y1+34, d, f11, GRAY)

    # ===== ORCHESTRATION BAR at bottom =====
    rbox(draw, (830, 860, 1330, 900), fill=GRAY_BG, outline=GRAY_BORDER, radius=6)
    center_text(draw, 1080, 878, "Orchestration: scripts/run_pipeline.py  (download → build → train → export)", f13, GRAY)

    # ===== KEY METRICS BOX =====
    rbox(draw, (830, 915, 1330, 980), fill=GRAY_BG, outline=GRAY_BORDER, radius=6)
    center_text(draw, 1080, 935, "Key Design Decisions", f14b, BLUE_DARK)
    decisions = [
        "0.1\u00b0 regular grid over India (68-97.5\u00b0E, 8-37.5\u00b0N)",
        "Temporal split: 2019-2021 (train), 2022 (test) — no leakage",
        "Synthetic fallback when real data unavailable (demo mode)",
        "Config-driven: paths.yaml · aqi_training.yaml · hcho_hotspot.yaml",
    ]
    for i, d in enumerate(decisions):
        draw.text((845, 955 + i*14), f"  \u2022  {d}", font=f11, fill=GRAY)

    # ===== FOOTER =====
    center_text(draw, 960, 1070, "ISRO Smart India Hackathon 2024 — Surface AQI & HCHO Hotspot Detection using Satellite Data", f11, (148, 163, 184))

    out = os.path.join(os.path.dirname(__file__), "process_flow.png")
    img.save(out, "PNG")
    print(f"Saved: {out} ({W}x{H})")

if __name__ == "__main__":
    main()
