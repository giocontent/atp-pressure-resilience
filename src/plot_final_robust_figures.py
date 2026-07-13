from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# ============================================================
# PATHS
# ============================================================

FIG_DIR = Path("reports/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)

ROBUST_PATH = Path("data/processed/final_robust_weighted_pressure_leaderboard.csv")
SCORE_PATH = Path("data/processed/weighted_pressure_resilience_score_atp_2020s.csv")
POINTS_PATH = Path("data/processed/pressure_points_atp_2020s_v6_surface.csv")
STAKES_PATH = Path("data/processed/point_stakes_direction_summary.csv")
SURFACE_SUMMARY_PATH = Path("data/processed/surface_pressure_summary.csv")

robust = pd.read_csv(ROBUST_PATH)
score = pd.read_csv(SCORE_PATH)
points = pd.read_csv(POINTS_PATH, low_memory=False)

print("Robust leaderboard:", robust.shape)
print("Score by pressure type:", score.shape)
print("Points:", points.shape)


def save_current_figure(filename):
    out_path = FIG_DIR / filename
    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print("Figura salvata in:", out_path)


# ============================================================
# 1. FINAL ROBUST LEADERBOARD
# ============================================================

def plot_final_robust_leaderboard():
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

    save_current_figure("18_final_robust_weighted_leaderboard.png")


# ============================================================
# 2. TOP / BOTTOM ROBUST PLAYERS
# ============================================================

def plot_top_bottom_robust_players():
    top = robust.sort_values(
        "avg_weighted_pressure_resilience_score",
        ascending=False,
    ).head(8)

    bottom = robust.sort_values(
        "avg_weighted_pressure_resilience_score",
        ascending=True,
    ).head(8)

    plot_df = pd.concat([bottom, top], axis=0)
    plot_df = plot_df.drop_duplicates("server")
    plot_df = plot_df.sort_values("avg_weighted_pressure_resilience_score")

    plt.figure(figsize=(10, 7))

    plt.barh(
        plot_df["server"],
        plot_df["avg_weighted_pressure_resilience_score"],
    )

    plt.axvline(0, linestyle="--", linewidth=1)

    plt.xlabel("Weighted Pressure Resilience Score")
    plt.ylabel("Player")
    plt.title("Top and Bottom Robust Pressure Resilience Players")

    save_current_figure("19_top_bottom_robust_players.png")


# ============================================================
# 3. SCORE VS RELIABILITY
# ============================================================

def plot_score_vs_reliability():
    plt.figure(figsize=(9, 6))

    plt.scatter(
        robust["avg_reliability_score"],
        robust["avg_weighted_pressure_resilience_score"],
        s=robust["n_charted_matches"] * 1.5,
        alpha=0.75,
    )

    plt.axhline(0, linestyle="--", linewidth=1)

    label_players = [
        "Lorenzo Musetti",
        "Jannik Sinner",
        "Carlos Alcaraz",
        "Daniil Medvedev",
        "Novak Djokovic",
        "Andrey Rublev",
        "Tommy Paul",
        "Casper Ruud",
        "Hubert Hurkacz",
    ]

    for _, row in robust.iterrows():
        if row["server"] in label_players:
            plt.annotate(
                row["server"],
                (
                    row["avg_reliability_score"],
                    row["avg_weighted_pressure_resilience_score"],
                ),
                fontsize=8,
                xytext=(5, 5),
                textcoords="offset points",
            )

    plt.xlabel("Average reliability score")
    plt.ylabel("Weighted Pressure Resilience Score")
    plt.title("Pressure Resilience vs Reliability")

    save_current_figure("20_score_vs_reliability_robust.png")


# ============================================================
# 4. SCORE VS CHARTED MATCHES
# ============================================================

def plot_score_vs_charted_matches():
    plt.figure(figsize=(9, 6))

    plt.scatter(
        robust["n_charted_matches"],
        robust["avg_weighted_pressure_resilience_score"],
        s=robust["avg_reliability_score"] * 8,
        alpha=0.75,
    )

    plt.axhline(0, linestyle="--", linewidth=1)

    label_players = [
        "Lorenzo Musetti",
        "Jannik Sinner",
        "Carlos Alcaraz",
        "Daniil Medvedev",
        "Novak Djokovic",
        "Andrey Rublev",
        "Hubert Hurkacz",
        "Felix Auger Aliassime",
    ]

    for _, row in robust.iterrows():
        if row["server"] in label_players:
            plt.annotate(
                row["server"],
                (
                    row["n_charted_matches"],
                    row["avg_weighted_pressure_resilience_score"],
                ),
                fontsize=8,
                xytext=(5, 5),
                textcoords="offset points",
            )

    plt.xlabel("Number of charted matches")
    plt.ylabel("Weighted Pressure Resilience Score")
    plt.title("Pressure Score vs Charted Exposure")

    save_current_figure("21_score_vs_charted_matches.png")


# ============================================================
# 5. PRESSURE TYPE PROFILE — SELECTED ROBUST PLAYERS
# ============================================================

def plot_selected_pressure_profiles():
    selected_players = [
        "Lorenzo Musetti",
        "Felix Auger Aliassime",
        "Casper Ruud",
        "Jannik Sinner",
        "Carlos Alcaraz",
        "Daniil Medvedev",
        "Novak Djokovic",
        "Andrey Rublev",
        "Tommy Paul",
    ]

    pressure_order = ["break_point", "deuce", "30_30", "tiebreak"]

    profile = score[
        score["server"].isin(selected_players)
        & score["pressure_type"].isin(pressure_order)
    ].copy()

    profile["pressure_type"] = pd.Categorical(
        profile["pressure_type"],
        categories=pressure_order,
        ordered=True,
    )

    pivot = profile.pivot(
        index="server",
        columns="pressure_type",
        values="weighted_pressure_resilience_score",
    )

    pivot = pivot.reindex([p for p in selected_players if p in pivot.index])

    x = np.arange(len(pivot.index))
    width = 0.18

    plt.figure(figsize=(13, 6))

    for i, pressure_type in enumerate(pressure_order):
        if pressure_type in pivot.columns:
            plt.bar(
                x + (i - 1.5) * width,
                pivot[pressure_type],
                width,
                label=pressure_type,
            )

    plt.axhline(0, linestyle="--", linewidth=1)
    plt.xticks(x, pivot.index, rotation=35, ha="right")

    plt.xlabel("Player")
    plt.ylabel("Weighted Pressure Resilience Score")
    plt.title("Pressure Profile by Point Type — Selected Robust Players")
    plt.legend(title="Pressure type")

    save_current_figure("22_selected_robust_pressure_profiles.png")


# ============================================================
# 6. TOP / BOTTOM BY PRESSURE TYPE
# ============================================================

def plot_pressure_type_top_bottom():
    robust_players = robust["server"].unique()

    pressure_order = ["deuce", "30_30", "tiebreak"]

    for pressure_type in pressure_order:
        temp = score[
            (score["server"].isin(robust_players))
            & (score["pressure_type"] == pressure_type)
        ].copy()

        if temp.empty:
            continue

        top = temp.sort_values(
            "weighted_pressure_resilience_score",
            ascending=False,
        ).head(6)

        bottom = temp.sort_values(
            "weighted_pressure_resilience_score",
            ascending=True,
        ).head(6)

        plot_df = pd.concat([bottom, top], axis=0)
        plot_df = plot_df.drop_duplicates("server")
        plot_df = plot_df.sort_values("weighted_pressure_resilience_score")

        plt.figure(figsize=(9, 6))

        plt.barh(
            plot_df["server"],
            plot_df["weighted_pressure_resilience_score"],
        )

        plt.axvline(0, linestyle="--", linewidth=1)

        plt.xlabel("Weighted Pressure Resilience Score")
        plt.ylabel("Player")
        plt.title(f"Top and Bottom Robust Players — {pressure_type}")

        filename = f"23_top_bottom_{pressure_type}_robust.png"
        save_current_figure(filename)


# ============================================================
# 7. DIRECTIONAL STAKE DELTA VS NORMAL
# ============================================================

def plot_directional_stakes():
    stakes = pd.read_csv(STAKES_PATH)

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

    stakes["stake"] = pd.Categorical(
        stakes["stake"],
        categories=stake_order,
        ordered=True,
    )

    plot_df = stakes.sort_values("delta_vs_normal_pp")

    plt.figure(figsize=(10, 7))

    plt.barh(
        plot_df["stake"].astype(str),
        plot_df["delta_vs_normal_pp"],
    )

    plt.axvline(0, linestyle="--", linewidth=1)

    plt.xlabel("Delta vs normal points (percentage points)")
    plt.ylabel("Point stake")
    plt.title("Directional Pressure Effect on Serve Win Rate")

    save_current_figure("24_directional_stake_delta_vs_normal.png")


# ============================================================
# 8. SERVING TO CLOSE VS SERVING TO SURVIVE
# ============================================================

def plot_serving_to_close_vs_survive():
    stakes = pd.read_csv(STAKES_PATH)

    focus = stakes[
        stakes["stake"].isin(
            [
                "server_game_point",
                "break_point",
                "server_set_point",
                "returner_set_point",
                "server_match_point",
                "returner_match_point",
            ]
        )
    ].copy()

    order = [
        "server_game_point",
        "break_point",
        "server_set_point",
        "returner_set_point",
        "server_match_point",
        "returner_match_point",
    ]

    focus["stake"] = pd.Categorical(
        focus["stake"],
        categories=order,
        ordered=True,
    )

    focus = focus.sort_values("stake")

    normal_rate = stakes.loc[
        stakes["stake"] == "normal",
        "weighted_server_win_rate",
    ].iloc[0]

    plt.figure(figsize=(10, 5))

    plt.bar(
        focus["stake"].astype(str),
        focus["weighted_server_win_rate"] * 100,
    )

    plt.axhline(
        normal_rate * 100,
        linestyle="--",
        linewidth=1,
    )

    plt.xticks(rotation=30, ha="right")
    plt.ylabel("Weighted server win rate (%)")
    plt.xlabel("Point type")
    plt.title("Serving to Close vs Serving to Survive")

    save_current_figure("25_serving_to_close_vs_survive.png")


# ============================================================
# 9. SERVE WIN RATE BY SURFACE
# ============================================================

def plot_serve_win_rate_by_surface():
    points_clean = points.copy()

    points_clean = points_clean[
        points_clean["surface_group"].isin(["hard", "clay", "grass"])
    ].copy()

    points_clean["server_won_point_num"] = (
        points_clean["server_won_point"]
        .astype(str)
        .str.lower()
        .map({"true": 1, "false": 0})
    )

    points_clean["point_weight"] = pd.to_numeric(
        points_clean["point_weight"],
        errors="coerce",
    )

    points_clean = points_clean.dropna(
        subset=["server_won_point_num", "point_weight"]
    )

    points_clean["weighted_win"] = (
        points_clean["server_won_point_num"] * points_clean["point_weight"]
    )

    summary = (
        points_clean.groupby("surface_group")
        .agg(
            raw_points=("server_won_point_num", "size"),
            weighted_points=("point_weight", "sum"),
            weighted_wins=("weighted_win", "sum"),
        )
        .reset_index()
    )

    summary["weighted_server_win_rate"] = (
        summary["weighted_wins"] / summary["weighted_points"]
    )

    summary = summary.sort_values("weighted_server_win_rate")

    plt.figure(figsize=(7, 5))

    plt.barh(
        summary["surface_group"],
        summary["weighted_server_win_rate"] * 100,
    )

    plt.xlabel("Weighted server win rate (%)")
    plt.ylabel("Surface")
    plt.title("Weighted Serve Win Rate by Surface")

    save_current_figure("26_weighted_serve_win_rate_by_surface.png")


# ============================================================
# 10. PRESSURE EFFECT BY SURFACE
# ============================================================

def plot_pressure_effect_by_surface():
    if SURFACE_SUMMARY_PATH.exists():
        surface_summary = pd.read_csv(SURFACE_SUMMARY_PATH)
    else:
        points_clean = points.copy()
        points_clean = points_clean[
            points_clean["surface_group"].isin(["hard", "clay", "grass"])
        ].copy()

        points_clean["server_won_point_num"] = (
            points_clean["server_won_point"]
            .astype(str)
            .str.lower()
            .map({"true": 1, "false": 0})
        )

        points_clean["point_weight"] = pd.to_numeric(
            points_clean["point_weight"],
            errors="coerce",
        )

        points_clean = points_clean.dropna(
            subset=["server_won_point_num", "point_weight"]
        )

        points_clean["weighted_win"] = (
            points_clean["server_won_point_num"] * points_clean["point_weight"]
        )

        surface_summary = (
            points_clean.groupby(["surface_group", "pressure_type"])
            .agg(
                raw_points=("server_won_point_num", "size"),
                weighted_points=("point_weight", "sum"),
                weighted_wins=("weighted_win", "sum"),
            )
            .reset_index()
        )

        surface_summary["weighted_server_win_rate"] = (
            surface_summary["weighted_wins"] / surface_summary["weighted_points"]
        )

        normal_rates = (
            surface_summary[surface_summary["pressure_type"] == "normal"]
            [["surface_group", "weighted_server_win_rate"]]
            .rename(columns={"weighted_server_win_rate": "normal_surface_rate"})
        )

        surface_summary = surface_summary.merge(
            normal_rates,
            on="surface_group",
            how="left",
        )

        surface_summary["delta_vs_surface_normal_pp"] = (
            surface_summary["weighted_server_win_rate"]
            - surface_summary["normal_surface_rate"]
        ) * 100

    pressure_order = ["30_30", "deuce", "break_point", "tiebreak"]
    surface_order = ["clay", "hard", "grass"]

    plot_df = surface_summary[
        surface_summary["pressure_type"].isin(pressure_order)
        & surface_summary["surface_group"].isin(surface_order)
    ].copy()

    plot_df["pressure_type"] = pd.Categorical(
        plot_df["pressure_type"],
        categories=pressure_order,
        ordered=True,
    )

    plot_df["surface_group"] = pd.Categorical(
        plot_df["surface_group"],
        categories=surface_order,
        ordered=True,
    )

    pivot = plot_df.pivot(
        index="pressure_type",
        columns="surface_group",
        values="delta_vs_surface_normal_pp",
    )

    pivot = pivot.reindex(pressure_order)

    x = np.arange(len(pivot.index))
    width = 0.25

    plt.figure(figsize=(10, 6))

    for i, surface in enumerate(surface_order):
        if surface in pivot.columns:
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

    save_current_figure("27_pressure_effect_by_surface.png")


# ============================================================
# 11. ROBUST PLAYER SURFACE MIX
# ============================================================

def plot_robust_player_surface_mix():
    selected_players = [
        "Lorenzo Musetti",
        "Felix Auger Aliassime",
        "Casper Ruud",
        "Jannik Sinner",
        "Carlos Alcaraz",
        "Daniil Medvedev",
        "Novak Djokovic",
        "Andrey Rublev",
    ]

    temp = points[
        points["server"].isin(selected_players)
        & points["surface_group"].isin(["clay", "hard", "grass"])
    ].copy()

    mix = (
        temp.groupby(["server", "surface_group"])
        .agg(raw_points=("match_id", "size"))
        .reset_index()
    )

    totals = (
        temp.groupby("server")
        .agg(total_points=("match_id", "size"))
        .reset_index()
    )

    mix = mix.merge(totals, on="server", how="left")
    mix["share"] = mix["raw_points"] / mix["total_points"]

    pivot = mix.pivot(
        index="server",
        columns="surface_group",
        values="share",
    ).fillna(0)

    surface_order = ["clay", "hard", "grass"]

    pivot = pivot.reindex([p for p in selected_players if p in pivot.index])
    pivot = pivot[[c for c in surface_order if c in pivot.columns]]

    bottom = np.zeros(len(pivot))

    plt.figure(figsize=(11, 6))

    for surface in surface_order:
        if surface in pivot.columns:
            plt.bar(
                pivot.index,
                pivot[surface] * 100,
                bottom=bottom,
                label=surface,
            )
            bottom += pivot[surface].values * 100

    plt.xticks(rotation=35, ha="right")
    plt.ylabel("Share of charted service points (%)")
    plt.xlabel("Player")
    plt.title("Surface Mix of Selected Robust Players")
    plt.legend(title="Surface")

    save_current_figure("28_robust_players_surface_mix.png")


# ============================================================
# 12. TOURNAMENT LEVEL DISTRIBUTION
# ============================================================

def plot_tournament_level_distribution():
    summary = (
        points.groupby("tournament_level")
        .agg(raw_points=("match_id", "size"))
        .reset_index()
        .sort_values("raw_points")
    )

    plt.figure(figsize=(9, 6))

    plt.barh(
        summary["tournament_level"],
        summary["raw_points"],
    )

    plt.xlabel("Number of points")
    plt.ylabel("Tournament level")
    plt.title("Point Distribution by Tournament Level")

    save_current_figure("29_tournament_level_distribution.png")


# ============================================================
# RUN ALL
# ============================================================

if __name__ == "__main__":
    plot_final_robust_leaderboard()
    plot_top_bottom_robust_players()
    plot_score_vs_reliability()
    plot_score_vs_charted_matches()
    plot_selected_pressure_profiles()
    plot_pressure_type_top_bottom()
    plot_directional_stakes()
    plot_serving_to_close_vs_survive()
    plot_serve_win_rate_by_surface()
    plot_pressure_effect_by_surface()
    plot_robust_player_surface_mix()
    plot_tournament_level_distribution()

    print("\nTutti i grafici finali sono stati generati in:", FIG_DIR)