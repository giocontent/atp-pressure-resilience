from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

DATA_PATH = Path("data/processed/point_stakes_direction_summary.csv")
FIG_DIR = Path("reports/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA_PATH)

# Ordine utile per lettura narrativa
stake_order = [
    "returner_match_point",
    "close_server_game_point",
    "deuce",
    "returner_set_point",
    "match_point",
    "break_point",
    "server_game_point",
    "30_30",
    "set_point",
    "normal",
    "tiebreak_point",
    "server_set_point",
    "server_match_point",
]

df["stake"] = pd.Categorical(df["stake"], categories=stake_order, ordered=True)
df = df.sort_values("stake")


def save_current_figure(filename):
    out_path = FIG_DIR / filename
    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print("Figura salvata in:", out_path)


# ============================================================
# 1. Delta vs normal by stake direction
# ============================================================

plt.figure(figsize=(10, 7))

plot_df = df.sort_values("delta_vs_normal_pp")

plt.barh(
    plot_df["stake"].astype(str),
    plot_df["delta_vs_normal_pp"],
)

plt.axvline(0, linestyle="--", linewidth=1)

plt.xlabel("Delta vs normal points (percentage points)")
plt.ylabel("Point stake")
plt.title("Directional Pressure Effect on Serve Win Rate")

save_current_figure("10_directional_stake_delta_vs_normal.png")


# ============================================================
# 2. Weighted serve win rate by stake direction
# ============================================================

plt.figure(figsize=(10, 7))

plot_df = df.sort_values("weighted_server_win_rate")

plt.barh(
    plot_df["stake"].astype(str),
    plot_df["weighted_server_win_rate"] * 100,
)

plt.xlabel("Weighted server win rate (%)")
plt.ylabel("Point stake")
plt.title("Weighted Serve Win Rate by Point Stake")

save_current_figure("11_directional_stake_serve_win_rate.png")


# ============================================================
# 3. Server vs returner decisive points
# ============================================================

focus_stakes = [
    "server_game_point",
    "break_point",
    "server_set_point",
    "returner_set_point",
    "server_match_point",
    "returner_match_point",
]

focus = df[df["stake"].astype(str).isin(focus_stakes)].copy()

focus["stake"] = pd.Categorical(
    focus["stake"].astype(str),
    categories=focus_stakes,
    ordered=True,
)

focus = focus.sort_values("stake")

plt.figure(figsize=(10, 5))

plt.bar(
    focus["stake"].astype(str),
    focus["weighted_server_win_rate"] * 100,
)

plt.axhline(
    df.loc[df["stake"].astype(str) == "normal", "weighted_server_win_rate"].iloc[0] * 100,
    linestyle="--",
    linewidth=1,
)

plt.xticks(rotation=30, ha="right")
plt.ylabel("Weighted server win rate (%)")
plt.xlabel("Point type")
plt.title("Serving to Close vs Serving to Survive")

save_current_figure("12_server_vs_returner_decisive_points.png")


# ============================================================
# 4. Raw sample size by stake
# ============================================================

plt.figure(figsize=(10, 7))

sample_df = df.sort_values("raw_points")

plt.barh(
    sample_df["stake"].astype(str),
    sample_df["raw_points"],
)

plt.xlabel("Number of points")
plt.ylabel("Point stake")
plt.title("Sample Size by Point Stake")

save_current_figure("13_point_stake_sample_size.png")


print("\nGrafici stake generati in:", FIG_DIR)