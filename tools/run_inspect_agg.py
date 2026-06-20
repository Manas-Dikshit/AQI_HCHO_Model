import sys
from pathlib import Path

# Ensure project package is importable
sys.path.insert(0, r"c:\Users\manas\Downloads\Spatial-ML-Hub\isro-aqi-hcho")

from src.visualization.export_geospatial_layers import aggregate_to_resolution
import pandas as pd

grid_csv = Path(r"c:\Users\manas\Downloads\Spatial-ML-Hub\isro-aqi-hcho\data\processed\grid_daily_features.csv")
print('grid exists', grid_csv.exists())
df = pd.read_csv(grid_csv)
print('df shape', df.shape)
print('columns:', list(df.columns)[:50])
# Look for an existing prediction column to inspect; if none, use pm25 (observed) or create a small sample
if 'pm25_pred' in df.columns:
	sub = df[['date','lat','lon','pm25_pred']].dropna()
elif 'pm25' in df.columns:
	sub = df[['date','lat','lon','pm25']].dropna()
else:
	# create synthetic pm25_pred in-memory for inspection
	df['pm25_pred'] = 20.0
	sub = df[['date','lat','lon','pm25_pred']].dropna()
agg = aggregate_to_resolution(sub, 0.25)
print('\n---- AGG DTYPEs ----')
print(agg.dtypes)
print('\n---- AGG HEAD ----')
print(agg.head().to_string())
print('\n---- AGG COLUMN NAMES ----')
print(list(agg.columns))
