from pathlib import Path
import pandas as pd

DATA_DIR = Path("data/raw/tennis_MatchChartingProject")

matches_path = DATA_DIR / "charting-m-matches.csv"
points_path = DATA_DIR / "charting-m-points-2020s.csv"

matches = pd.read_csv(matches_path)
points = pd.read_csv(points_path, low_memory=False)

print("MATCHES:", matches.shape)
print("POINTS:", points.shape)

print("\nColonne matches:")
print(matches.columns.tolist())

print("\nColonne points:")
print(points.columns.tolist())

print("\nPrime righe points:")
print(points.head())