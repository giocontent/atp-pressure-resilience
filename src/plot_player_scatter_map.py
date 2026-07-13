from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# ============================================================
# PATHS
# ============================================================

PLAYER_SCORE_PATH = Path("data/processed/player_weighted_pressure_resilience_score_atp_2020s.csv")
MATCH_COUNTS_PATH = Path("data/processed/player_match_counts_atp_2020s.csv")
ROBUST_PATH = Path("data/processed/final_robust_weighted_pressure_leaderboard.csv")

FIG_DIR = Path("reports/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)

OUT_FIG_1 = FIG_DIR / "30_player_scatter_pressure_map.png"
OUT_FIG_2 = FIG_DIR / "31_robust_players_scatter_map.png"
OUT_FIG_3 = FIG_DIR / "32_score_vs_reliability_all_players.png"

# ============================================================
# LOAD
# ============================================================

scores = pd.read_csv(PLAYER_SCORE_PATH)
match_counts = pd.read_csv(MATCH_COUNTS_PATH)
robust = pd.read_csv(ROBUST_PATH)

print("Scores:", scores.shape)
print("Match counts:", match_counts.shape)
print("Robust:", robust.shape)

# ============================================================
# MERGE
# ============================================================

df = scores.merge(
    match_counts[
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
    ],
    on="server",
    how="left",
)

df["is_robust"] = df["server"].isin(robust["server"])

# teniamo solo giocatori minimamente leggibili
df = df[
    (df["n_categories"] >= 4) &
    (df["total_effective_pressure_points"] >= 250)
].copy()

print("Players after filter:", df.shape[0])

# ============================================================
# POINT SIZE
# ============================================================

# dimensione legata ai match chartati
df["marker_size"] = 25 + df["n_charted_matches"].fillna(0) * 2.1
df["marker_size"] = df["marker_size"].clip(lower=25, upper=650)

# ============================================================
# LABEL SET
# ============================================================

top_positive = (
    df.sort_values("avg_weighted_pressure_resilience_score", ascending=False)
    .head(10)["server"]
    .tolist()
)

top_negative = (
    df.sort_values("avg_weighted_pressure_resilience_score", ascending=True)
    .head(10)["server"]
    .tolist()
)

important_names = [
    "Jannik Sinner",
    "Carlos Alcaraz",
    "Novak Djokovic",
    "Daniil Medvedev",
    "Lorenzo Musetti",
    "Casper Ruud",
    "Hubert Hurkacz",
    "Andrey Rublev",
    "Tommy Paul",
    "Taylor Fritz",
    "Alex De Minaur",
    "Felix Auger Aliassime",
    "Alexander Zverev",
    "Stefanos Tsitsipas",
    "Matteo Berrettini",
]

label_set = set(top_positive + top_negative + important_names)

# ============================================================
# SHARED SETTINGS
# ============================================================

score_min = df["avg_weighted_pressure_resilience_score"].min()
score_max = df["avg_weighted_pressure_resilience_score"].max()
score_abs = max(abs(score_min), abs(score_max))

cmap = plt.cm.coolwarm
norm = plt.Normalize(vmin=-score_abs, vmax=score_abs)

# ============================================================
# 1. MAIN SCATTER MAP
# ============================================================

background = df[~df["is_robust"]].copy()
foreground = df[df["is_robust"]].copy()

plt.figure(figsize=(13, 8))

# giocatori non robust
sc1 = plt.scatter(
    background["total_effective_pressure_points"],
    background["avg_weighted_pressure_resilience_score"],
    s=background["marker_size"],
    c=background["avg_weighted_pressure_resilience_score"],
    cmap=cmap,
    norm=norm,
    alpha=0.35,
    linewidths=0.3,
    edgecolors="none",
    label="Other eligible players",
)

# giocatori robust
sc2 = plt.scatter(
    foreground["total_effective_pressure_points"],
    foreground["avg_weighted_pressure_resilience_score"],
    s=foreground["marker_size"],
    c=foreground["avg_weighted_pressure_resilience_score"],
    cmap=cmap,
    norm=norm,
    alpha=0.95,
    linewidths=0.9,
    edgecolors="black",
    label="Final robust players",
)

plt.axhline(0, linestyle="--", linewidth=1)
plt.axvline(1500, linestyle="--", linewidth=1)

# label selezionate
for i, (_, row) in enumerate(df.iterrows()):
    if row["server"] in label_set:
        offset_x = 5 if i % 2 == 0 else -5
        offset_y = 6 if i % 3 == 0 else -8

        plt.annotate(
            row["server"],
            (
                row["total_effective_pressure_points"],
                row["avg_weighted_pressure_resilience_score"],
            ),
            fontsize=8,
            xytext=(offset_x, offset_y),
            textcoords="offset points",
        )

plt.xscale("log")
plt.xlabel("Effective pressure points (log scale)")
plt.ylabel("Weighted Pressure Resilience Score")
plt.title("ATP Pressure Resilience Map (2020–2026)")
plt.grid(True, alpha=0.18)
plt.legend()

cbar = plt.colorbar(sc2)
cbar.set_label("Weighted Pressure Resilience Score")

# mini legenda dimensioni
size_values = [50, 100, 200]
size_markers = [25 + v * 2.1 for v in size_values]
for size_val, marker in zip(size_values, size_markers):
    plt.scatter([], [], s=marker, label=f"{size_val} charted matches", alpha=0.4)

handles, labels = plt.gca().get_legend_handles_labels()
# togliamo duplicati eventuali
unique = dict(zip(labels, handles))
plt.legend(unique.values(), unique.keys(), loc="best", fontsize=9)

plt.tight_layout()
plt.savefig(OUT_FIG_1, dpi=300, bbox_inches="tight")
plt.close()

print("Figura salvata in:", OUT_FIG_1)

# ============================================================
# 2. ROBUST PLAYERS ONLY
# ============================================================

robust_plot = foreground.sort_values("total_effective_pressure_points").copy()

plt.figure(figsize=(11, 7))

sc = plt.scatter(
    robust_plot["total_effective_pressure_points"],
    robust_plot["avg_weighted_pressure_resilience_score"],
    s=robust_plot["marker_size"],
    c=robust_plot["avg_weighted_pressure_resilience_score"],
    cmap=cmap,
    norm=norm,
    alpha=0.95,
    edgecolors="black",
    linewidths=0.8,
)

plt.axhline(0, linestyle="--", linewidth=1)
plt.axvline(1500, linestyle="--", linewidth=1)

for i, (_, row) in enumerate(robust_plot.iterrows()):
    offset_x = 5 if i % 2 == 0 else -5
    offset_y = 6 if i % 3 == 0 else -8

    plt.annotate(
        row["server"],
        (
            row["total_effective_pressure_points"],
            row["avg_weighted_pressure_resilience_score"],
        ),
        fontsize=8,
        xytext=(offset_x, offset_y),
        textcoords="offset points",
    )

plt.xscale("log")
plt.xlabel("Effective pressure points (log scale)")
plt.ylabel("Weighted Pressure Resilience Score")
plt.title("Final Robust Players — Pressure Resilience Map")
plt.grid(True, alpha=0.18)

cbar = plt.colorbar(sc)
cbar.set_label("Weighted Pressure Resilience Score")

plt.tight_layout()
plt.savefig(OUT_FIG_2, dpi=300, bbox_inches="tight")
plt.close()

print("Figura salvata in:", OUT_FIG_2)

# ============================================================
# 3. SCORE VS RELIABILITY
# ============================================================

plt.figure(figsize=(12, 7))

sc = plt.scatter(
    df["avg_reliability_score"],
    df["avg_weighted_pressure_resilience_score"],
    s=df["marker_size"],
    c=df["avg_weighted_pressure_resilience_score"],
    cmap=cmap,
    norm=norm,
    alpha=0.6,
    linewidths=0.3,
    edgecolors="none",
)

robust_only = df[df["is_robust"]].copy()

plt.scatter(
    robust_only["avg_reliability_score"],
    robust_only["avg_weighted_pressure_resilience_score"],
    s=robust_only["marker_size"],
    c=robust_only["avg_weighted_pressure_resilience_score"],
    cmap=cmap,
    norm=norm,
    alpha=0.95,
    linewidths=0.8,
    edgecolors="black",
)

plt.axhline(0, linestyle="--", linewidth=1)
plt.axvline(25, linestyle="--", linewidth=1)

for i, (_, row) in enumerate(df.iterrows()):
    if row["server"] in label_set:
        offset_x = 5 if i % 2 == 0 else -5
        offset_y = 6 if i % 3 == 0 else -8

        plt.annotate(
            row["server"],
            (
                row["avg_reliability_score"],
                row["avg_weighted_pressure_resilience_score"],
            ),
            fontsize=8,
            xytext=(offset_x, offset_y),
            textcoords="offset points",
        )

plt.xlabel("Average reliability score")
plt.ylabel("Weighted Pressure Resilience Score")
plt.title("Pressure Score vs Reliability")
plt.grid(True, alpha=0.18)

cbar = plt.colorbar(sc)
cbar.set_label("Weighted Pressure Resilience Score")

plt.tight_layout()
plt.savefig(OUT_FIG_3, dpi=300, bbox_inches="tight")
plt.close()

print("Figura salvata in:", OUT_FIG_3)

# ============================================================
# EXTRA TERMINAL OUTPUT
# ============================================================

print("\nTop 15 players in scatter:")
print(
    df[
        [
            "server",
            "n_charted_matches",
            "total_effective_pressure_points",
            "avg_weighted_pressure_resilience_score",
            "avg_reliability_score",
            "is_robust",
        ]
    ]
    .sort_values("avg_weighted_pressure_resilience_score", ascending=False)
    .head(15)
    .to_string(index=False)
)

print("\nBottom 15 players in scatter:")
print(
    df[
        [
            "server",
            "n_charted_matches",
            "total_effective_pressure_points",
            "avg_weighted_pressure_resilience_score",
            "avg_reliability_score",
            "is_robust",
        ]
    ]
    .sort_values("avg_weighted_pressure_resilience_score", ascending=True)
    .head(15)
    .to_string(index=False)
)