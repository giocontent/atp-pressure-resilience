from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

DATA_PATH = Path("data/processed/pressure_points_atp_2020s_v6_surface.csv")
STABLE_PATH = Path("data/processed/stable_weighted_pressure_leaderboard_atp_2020s.csv")

OUT_SUMMARY = Path("data/processed/surface_pressure_summary.csv")
OUT_PLAYER_MIX = Path("data/processed/player_surface_mix_stable.csv")

FIG_DIR = Path("reports/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA_PATH, low_memory=False)
stable = pd.read_csv(STABLE_PATH)

print("Dataset:", df.shape)
print("Stable players:", stable.shape)

# Pulizia
df["server_won_point_num"] = (
    df["server_won_point"]
    .astype(str)
    .str.lower()
    .map({"true": 1, "false": 0})
)

df["point_weight"] = pd.to_numeric(df["point_weight"], errors="coerce")

df = df.dropna(subset=["server_won_point_num", "point_weight", "surface_group", "pressure_type"])

# Escludiamo other: sono solo 189 punti, non vale la pena sporcare l'analisi
df = df[df["surface_group"].isin(["hard", "clay", "grass"])].copy()

df["weighted_win"] = df["server_won_point_num"] * df["point_weight"]


def save_current_figure(filename):
    out_path = FIG_DIR / filename
    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print("Figura salvata in:", out_path)


# ============================================================
# 1. Surface summary generale
# ============================================================

surface_summary = (
    df.groupby("surface_group")
    .agg(
        raw_points=("server_won_point_num", "size"),
        weighted_points=("point_weight", "sum"),
        weighted_wins=("weighted_win", "sum"),
        avg_point_weight=("point_weight", "mean"),
    )
    .reset_index()
)

surface_summary["weighted_server_win_rate"] = (
    surface_summary["weighted_wins"] / surface_summary["weighted_points"]
)

surface_summary = surface_summary.sort_values(
    "weighted_server_win_rate",
    ascending=False,
)

print("\nWeighted serve win rate by surface:")
print(
    surface_summary[
        [
            "surface_group",
            "raw_points",
            "weighted_server_win_rate",
            "avg_point_weight",
        ]
    ].to_string(index=False)
)


# ============================================================
# 2. Pressure type x surface
# ============================================================

pressure_surface = (
    df.groupby(["surface_group", "pressure_type"])
    .agg(
        raw_points=("server_won_point_num", "size"),
        weighted_points=("point_weight", "sum"),
        weighted_wins=("weighted_win", "sum"),
    )
    .reset_index()
)

pressure_surface["weighted_server_win_rate"] = (
    pressure_surface["weighted_wins"] / pressure_surface["weighted_points"]
)

# Normal rate per superficie
normal_rates = (
    pressure_surface[pressure_surface["pressure_type"] == "normal"]
    [["surface_group", "weighted_server_win_rate"]]
    .rename(columns={"weighted_server_win_rate": "normal_surface_rate"})
)

pressure_surface = pressure_surface.merge(normal_rates, on="surface_group", how="left")

pressure_surface["delta_vs_surface_normal_pp"] = (
    pressure_surface["weighted_server_win_rate"] -
    pressure_surface["normal_surface_rate"]
) * 100

pressure_surface.to_csv(OUT_SUMMARY, index=False)

print("\nPressure effect by surface:")
print(
    pressure_surface.sort_values(["surface_group", "pressure_type"])
    [
        [
            "surface_group",
            "pressure_type",
            "raw_points",
            "weighted_server_win_rate",
            "delta_vs_surface_normal_pp",
        ]
    ].to_string(index=False)
)


# ============================================================
# 3. Player surface mix for stable leaderboard
# ============================================================

stable_players = stable["server"].unique().tolist()

stable_points = df[df["server"].isin(stable_players)].copy()

player_surface = (
    stable_points.groupby(["server", "surface_group"])
    .agg(raw_points=("server_won_point_num", "size"))
    .reset_index()
)

player_total = (
    stable_points.groupby("server")
    .agg(total_points=("server_won_point_num", "size"))
    .reset_index()
)

player_surface = player_surface.merge(player_total, on="server", how="left")
player_surface["surface_share"] = player_surface["raw_points"] / player_surface["total_points"]

player_surface = player_surface.merge(
    stable[
        [
            "server",
            "avg_weighted_pressure_resilience_score",
            "avg_reliability_score",
        ]
    ],
    on="server",
    how="left",
)

player_surface.to_csv(OUT_PLAYER_MIX, index=False)

print("\nPlayer surface mix salvato in:", OUT_PLAYER_MIX)


# ============================================================
# 4. Grafico: serve win rate by surface
# ============================================================

plot_df = surface_summary.sort_values("weighted_server_win_rate")

plt.figure(figsize=(7, 5))
plt.barh(
    plot_df["surface_group"],
    plot_df["weighted_server_win_rate"] * 100,
)

plt.xlabel("Weighted server win rate (%)")
plt.ylabel("Surface")
plt.title("Weighted Serve Win Rate by Surface")

save_current_figure("14_weighted_serve_win_rate_by_surface.png")


# ============================================================
# 5. Grafico: pressure effect by surface
# ============================================================

plot_pressure = pressure_surface[
    pressure_surface["pressure_type"].isin(["30_30", "deuce", "break_point", "tiebreak"])
].copy()

pressure_order = ["30_30", "deuce", "break_point", "tiebreak"]
surface_order = ["clay", "hard", "grass"]

plot_pressure["pressure_type"] = pd.Categorical(
    plot_pressure["pressure_type"],
    categories=pressure_order,
    ordered=True,
)

plot_pressure["surface_group"] = pd.Categorical(
    plot_pressure["surface_group"],
    categories=surface_order,
    ordered=True,
)

pivot = plot_pressure.pivot(
    index="pressure_type",
    columns="surface_group",
    values="delta_vs_surface_normal_pp",
)

pivot = pivot.reindex(pressure_order)

x = np.arange(len(pivot.index))
width = 0.25

plt.figure(figsize=(10, 6))

for i, surface in enumerate(surface_order):
    plt.bar(
        x + (i - 1) * width,
        pivot[surface],
        width,
        label=surface,
    )

plt.axhline(0, linestyle="--", linewidth=1)
plt.xticks(x, pivot.index)

plt.xlabel("Pressure type")
plt.ylabel("Delta vs normal on same surface (percentage points)")
plt.title("Pressure Effect by Surface")
plt.legend(title="Surface")

save_current_figure("15_pressure_effect_by_surface.png")


# ============================================================
# 6. Grafico: surface mix for selected players
# ============================================================

selected_players = [
    "Jannik Sinner",
    "Carlos Alcaraz",
    "Novak Djokovic",
    "Lorenzo Musetti",
    "Andy Murray",
    "Daniil Medvedev",
    "Rafael Nadal",
    "Andrey Rublev",
    "Ben Shelton",
]

mix = player_surface[player_surface["server"].isin(selected_players)].copy()

pivot_mix = mix.pivot(
    index="server",
    columns="surface_group",
    values="surface_share",
).fillna(0)

pivot_mix = pivot_mix.reindex([p for p in selected_players if p in pivot_mix.index])
pivot_mix = pivot_mix[[c for c in surface_order if c in pivot_mix.columns]]

bottom = np.zeros(len(pivot_mix))

plt.figure(figsize=(11, 6))

for surface in surface_order:
    if surface in pivot_mix.columns:
        plt.bar(
            pivot_mix.index,
            pivot_mix[surface] * 100,
            bottom=bottom,
            label=surface,
        )
        bottom += pivot_mix[surface].values * 100

plt.xticks(rotation=35, ha="right")
plt.ylabel("Share of charted points (%)")
plt.xlabel("Player")
plt.title("Surface Mix of Selected Stable Players")
plt.legend(title="Surface")

save_current_figure("16_selected_players_surface_mix.png")


# ============================================================
# 7. Grafico: score vs clay share
# ============================================================

clay_share = (
    player_surface[player_surface["surface_group"] == "clay"]
    [["server", "surface_share"]]
    .rename(columns={"surface_share": "clay_share"})
)

scatter_df = stable.merge(clay_share, on="server", how="left")
scatter_df["clay_share"] = scatter_df["clay_share"].fillna(0)

plt.figure(figsize=(8, 6))
plt.scatter(
    scatter_df["clay_share"] * 100,
    scatter_df["avg_weighted_pressure_resilience_score"],
)

plt.axhline(0, linestyle="--", linewidth=1)

label_players = {
    "Jannik Sinner",
    "Carlos Alcaraz",
    "Novak Djokovic",
    "Lorenzo Musetti",
    "Andy Murray",
    "Daniil Medvedev",
    "Rafael Nadal",
    "Andrey Rublev",
    "Ben Shelton",
}

for _, row in scatter_df.iterrows():
    if row["server"] in label_players:
        plt.annotate(
            row["server"],
            (
                row["clay_share"] * 100,
                row["avg_weighted_pressure_resilience_score"],
            ),
            fontsize=8,
            xytext=(4, 4),
            textcoords="offset points",
        )

plt.xlabel("Clay share of charted points (%)")
plt.ylabel("Weighted Pressure Resilience Score")
plt.title("Pressure Score vs Clay Exposure")

save_current_figure("17_pressure_score_vs_clay_share.png")


print("\nAnalisi superficie completata.")
print("Output summary:", OUT_SUMMARY)
print("Output player mix:", OUT_PLAYER_MIX)
print("Figure salvate in:", FIG_DIR)