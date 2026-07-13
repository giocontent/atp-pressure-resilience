from pathlib import Path
import pandas as pd
import numpy as np

POINTS_PATH = Path("data/processed/pressure_points_atp_2020s_v6_surface.csv")
STABLE_PATH = Path("data/processed/stable_weighted_pressure_leaderboard_atp_2020s.csv")

OUT_PLAYER_COUNTS = Path("data/processed/player_match_counts_atp_2020s.csv")
OUT_STABLE_WITH_COUNTS = Path("data/processed/stable_weighted_leaderboard_with_match_counts.csv")

df = pd.read_csv(POINTS_PATH, low_memory=False)
stable = pd.read_csv(STABLE_PATH)

print("Points:", df.shape)
print("Stable leaderboard:", stable.shape)

# ============================================================
# Date cleaning
# ============================================================

if "date" not in df.columns:
    raise ValueError("Colonna date non trovata nel dataset processed.")

df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["year"] = df["date"].dt.year

print("\nDataset period:")
print("Min date:", df["date"].min())
print("Max date:", df["date"].max())

print("\nUnique matches by year:")
matches_by_year = (
    df.drop_duplicates("match_id")
    .groupby("year")
    .agg(n_matches=("match_id", "nunique"))
    .reset_index()
)

print(matches_by_year.to_string(index=False))

print("\nPoints by year:")
points_by_year = (
    df.groupby("year")
    .agg(n_points=("match_id", "size"))
    .reset_index()
)

print(points_by_year.to_string(index=False))


# ============================================================
# Player match counts
# ============================================================

df["server_won_point_num"] = (
    df["server_won_point"]
    .astype(str)
    .str.lower()
    .map({"true": 1, "false": 0})
)

player_counts = (
    df.groupby("server")
    .agg(
        n_charted_matches=("match_id", "nunique"),
        total_service_points=("server_won_point_num", "size"),
        first_date=("date", "min"),
        last_date=("date", "max"),
        n_years=("year", "nunique"),
    )
    .reset_index()
)

# Pressure points secondo la nostra definizione principale
pressure_counts = (
    df[df["pressure_type"] != "normal"]
    .groupby("server")
    .agg(
        total_pressure_points=("server_won_point_num", "size"),
        pressure_matches=("match_id", "nunique"),
    )
    .reset_index()
)

player_counts = player_counts.merge(
    pressure_counts,
    on="server",
    how="left",
)

player_counts["total_pressure_points"] = player_counts["total_pressure_points"].fillna(0).astype(int)
player_counts["pressure_matches"] = player_counts["pressure_matches"].fillna(0).astype(int)

player_counts = player_counts.sort_values("n_charted_matches", ascending=False)

player_counts.to_csv(OUT_PLAYER_COUNTS, index=False)

print("\nTop 30 players by charted matches:")
print(
    player_counts[
        [
            "server",
            "n_charted_matches",
            "pressure_matches",
            "total_service_points",
            "total_pressure_points",
            "first_date",
            "last_date",
            "n_years",
        ]
    ]
    .head(30)
    .to_string(index=False)
)


# ============================================================
# Stable leaderboard + match counts
# ============================================================

stable_counts = stable.merge(
    player_counts,
    on="server",
    how="left",
)

stable_counts.to_csv(OUT_STABLE_WITH_COUNTS, index=False)

print("\nStable leaderboard with match counts:")
print(
    stable_counts[
        [
            "server",
            "n_charted_matches",
            "pressure_matches",
            "total_effective_pressure_points",
            "avg_weighted_pressure_resilience_score",
            "avg_reliability_score",
            "first_date",
            "last_date",
        ]
    ]
    .sort_values("avg_weighted_pressure_resilience_score", ascending=False)
    .to_string(index=False)
)


# ============================================================
# Andy Murray audit
# ============================================================

print("\nAndy Murray row:")
print(
    stable_counts[stable_counts["server"] == "Andy Murray"]
    [
        [
            "server",
            "n_charted_matches",
            "pressure_matches",
            "total_service_points",
            "total_pressure_points",
            "total_effective_pressure_points",
            "avg_weighted_pressure_resilience_score",
            "avg_reliability_score",
            "first_date",
            "last_date",
            "n_years",
        ]
    ]
    .to_string(index=False)
)


# ============================================================
# Sensitivity: different minimum match thresholds
# ============================================================

thresholds = [10, 15, 20, 25, 30, 35, 40, 50]

print("\nSensitivity by minimum charted matches:")
for threshold in thresholds:
    temp = stable_counts[stable_counts["n_charted_matches"] >= threshold].copy()

    print("\n" + "=" * 70)
    print(f"Minimum charted matches >= {threshold}")
    print("Players included:", temp.shape[0])

    if temp.empty:
        continue

    print("\nTop 10:")
    print(
        temp[
            [
                "server",
                "n_charted_matches",
                "avg_weighted_pressure_resilience_score",
                "avg_reliability_score",
            ]
        ]
        .sort_values("avg_weighted_pressure_resilience_score", ascending=False)
        .head(10)
        .to_string(index=False)
    )

    print("\nBottom 10:")
    print(
        temp[
            [
                "server",
                "n_charted_matches",
                "avg_weighted_pressure_resilience_score",
                "avg_reliability_score",
            ]
        ]
        .sort_values("avg_weighted_pressure_resilience_score", ascending=True)
        .head(10)
        .to_string(index=False)
    )