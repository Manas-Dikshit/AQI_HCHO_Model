from pathlib import Path
import pandas as pd
from src.visualization.export_geospatial_layers import aggregate_to_resolution

root = Path(__file__).resolve().parent.parent
grid_csv = root / 'data' / 'processed' / 'grid_daily_features.csv'
print('grid exists', grid_csv.exists())
df = pd.read_csv(grid_csv)
print('df shape', df.shape)
sub = df[['date','lat','lon','pm25_pred']].dropna()
agg = aggregate_to_resolution(sub, 0.25)
print('\n---- AGG DTYPEs ----')
print(agg.dtypes)
print('\n---- AGG HEAD ----')
print(agg.head().to_string())
print('\n---- AGG COLUMN NAMES ----')
print(list(agg.columns))
