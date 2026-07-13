from pathlib import Path
import pandas as pd

DATA_PATH = Path("data/processed/player_pressure_resilience_score_atp_2020s.csv")
OUT_PATH = Path("data/processed/stable_pressure_leaderboard_atp_2020s.csv")

df = pd.read_csv(DATA_PATH)

print("Dataset:", df.shape)

# Filtri per una classifica più credibile
stable = df[
    (df["n_categories"] >= 4) &
    (df["total_pressure_points"] >= 700) &
    (df["avg_reliability_score"] >= 20)
].copy()

stable = stable.sort_values("avg_pressure_resilience_score", ascending=False)

stable.to_csv(OUT_PATH, index=False)

print("\nStable leaderboard salvata in:", OUT_PATH)
print("Giocatori inclusi:", stable.shape[0])

print("\nTOP 20 stable pressure resilience:")
print(
    stable[
        [
            "server",
            "n_categories",
            "total_pressure_points",
            "avg_pressure_resilience_score",
            "avg_reliability_score",
        ]
    ]
    .head(20)
    .to_string(index=False)
)

print("\nBOTTOM 20 stable pressure resilience:")
print(
    stable[
        [
            "server",
            "n_categories",
            "total_pressure_points",
            "avg_pressure_resilience_score",
            "avg_reliability_score",
        ]
    ]
    .tail(20)
    .sort_values("avg_pressure_resilience_score")
    .to_string(index=False)
)