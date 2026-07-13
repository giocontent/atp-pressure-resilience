from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

POINTS_PATH = Path("data/processed/pressure_points_atp_2020s_v6_surface.csv")
STABLE_PATH = Path("data/processed/stable_weighted_pressure_leaderboard_atp_2020s.csv")

OUT_PATH = Path("data/processed/final_robust_weighted_pressure_leaderboard.csv")
FIG_PATH = Path("reports/figures/18_final_robust_weighted_leaderboard.png")

MIN_CHARTED_MATCHES = 75
MIN_EFFECTIVE_PRESSURE_POINTS = 1500
MIN_RELIABILITY = 25

df = pd.read_csv(POINTS_PATH, low_memory=False)
stable = pd.read_csv(STABLE_PATH)

# ============================================================
# Date parsing corretto
# ============================================================

date_str = (
    df["date"]
    .astype(str)
    .str.extract(r"(\d{8})")[0]
)

df["date_clean"] = pd.to_datetime(date_str, format="%Y%m%d", errors="coerce")
df["year"] = df["date_clean"].dt.year

print("Dataset period corrected:")
print("Min date:", df["date_clean"].min())
print("Max date:", df["date_clean"].max())

print("\nUnique matches by year:")
print(
    df.drop_duplicates("match_id")
    .groupby("year")
    .agg(n_matches=("match_id", "nunique"))
    .reset_index()
    .to_string(index=False)
)

# ============================================================
# Match counts per player
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
        first_date=("date_clean", "min"),
        last_date=("date_clean", "max"),
        n_years=("year", "nunique"),
    )
    .reset_index()
)

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

player_counts["total_pressure_points"] = (
    player_counts["total_pressure_points"].fillna(0).astype(int)
)

player_counts["pressure_matches"] = (
    player_counts["pressure_matches"].fillna(0).astype(int)
)

leaderboard = stable.merge(player_counts, on="server", how="left")

# ============================================================
# Final robust filter
# ============================================================

robust = leaderboard[
    (leaderboard["n_charted_matches"] >= MIN_CHARTED_MATCHES)
    & (leaderboard["total_effective_pressure_points"] >= MIN_EFFECTIVE_PRESSURE_POINTS)
    & (leaderboard["avg_reliability_score"] >= MIN_RELIABILITY)
].copy()

robust = robust.sort_values(
    "avg_weighted_pressure_resilience_score",
    ascending=False,
)

robust.to_csv(OUT_PATH, index=False)

print("\nFinal robust leaderboard salvata in:", OUT_PATH)
print("Giocatori inclusi:", robust.shape[0])

print("\nFINAL ROBUST LEADERBOARD:")
print(
    robust[
        [
            "server",
            "n_charted_matches",
            "total_effective_pressure_points",
            "avg_weighted_pressure_resilience_score",
            "avg_reliability_score",
            "first_date",
            "last_date",
        ]
    ].to_string(index=False)
)

print("\nPlayers excluded from previous stable leaderboard:")
excluded = leaderboard[~leaderboard["server"].isin(robust["server"])].copy()
excluded = excluded.sort_values("avg_weighted_pressure_resilience_score", ascending=False)

print(
    excluded[
        [
            "server",
            "n_charted_matches",
            "total_effective_pressure_points",
            "avg_weighted_pressure_resilience_score",
            "avg_reliability_score",
        ]
    ].to_string(index=False)
)

# ============================================================
# Plot final robust leaderboard
# ============================================================

plot_df = robust.sort_values("avg_weighted_pressure_resilience_score")

plt.figure(figsize=(10, 8))

plt.barh(
    plot_df["server"],
    plot_df["avg_weighted_pressure_resilience_score"],
)

plt.axvline(0, linestyle="--", linewidth=1)

plt.xlabel("Weighted Pressure Resilience Score")
plt.ylabel("Player")
plt.title("Final Robust Weighted Pressure Resilience Leaderboard")

plt.tight_layout()
plt.savefig(FIG_PATH, dpi=300, bbox_inches="tight")
plt.close()

print("\nFigura salvata in:", FIG_PATH)