from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re

# ============================================================
# PATHS
# ============================================================

POINTS_PATH = Path("data/processed/pressure_points_atp_2020s_v6_surface.csv")
SCORE_PATH = Path("data/processed/weighted_pressure_resilience_score_atp_2020s.csv")
ROBUST_PATH = Path("data/processed/final_robust_weighted_pressure_leaderboard.csv")

OUT_DIR = Path("reports/player_profiles")
FIG_DIR = OUT_DIR / "figures"

OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

OUT_SUMMARY = OUT_DIR / "player_pressure_profiles_summary.csv"
OUT_INDEX = OUT_DIR / "README_player_profiles.md"

TOP_N_PLAYERS = 20

# ============================================================
# LOAD
# ============================================================

points = pd.read_csv(POINTS_PATH, low_memory=False)
score = pd.read_csv(SCORE_PATH)
robust = pd.read_csv(ROBUST_PATH)

print("Points:", points.shape)
print("Score:", score.shape)
print("Robust leaderboard:", robust.shape)

# ============================================================
# CLEANING
# ============================================================

def to_bool(series):
    return (
        series.astype(str)
        .str.lower()
        .map({"true": True, "false": False})
        .fillna(False)
    )


bool_cols = [
    "server_won_point",
    "is_30_30",
    "is_deuce",
    "is_break_point",
    "is_tiebreak_point",
    "is_close_server_game_point",
    "is_server_game_point",
    "is_returner_game_point",
    "is_set_point",
    "is_server_set_point",
    "is_returner_set_point",
    "is_match_point",
    "is_server_match_point",
    "is_returner_match_point",
]

for col in bool_cols:
    if col in points.columns:
        points[col] = to_bool(points[col])

points["server_won_point_num"] = points["server_won_point"].astype(int)
points["point_weight"] = pd.to_numeric(points["point_weight"], errors="coerce")
points = points.dropna(subset=["point_weight", "server_won_point_num", "server"])

# ============================================================
# HELPERS
# ============================================================

def slugify(name):
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = name.strip("_")
    return name


def weighted_rate(df):
    if df.empty:
        return np.nan

    weighted_points = df["point_weight"].sum()

    if weighted_points == 0:
        return np.nan

    weighted_wins = (df["point_weight"] * df["server_won_point_num"]).sum()
    return weighted_wins / weighted_points


def weighted_summary(masked_df):
    if masked_df.empty:
        return {
            "raw_points": 0,
            "weighted_points": 0,
            "weighted_serve_win_rate": np.nan,
        }

    weighted_points = masked_df["point_weight"].sum()
    weighted_wins = (masked_df["point_weight"] * masked_df["server_won_point_num"]).sum()

    return {
        "raw_points": len(masked_df),
        "weighted_points": weighted_points,
        "weighted_serve_win_rate": weighted_wins / weighted_points if weighted_points > 0 else np.nan,
    }


def save_fig(filename):
    out_path = FIG_DIR / filename
    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print("Figura salvata:", out_path)


def format_pct(x):
    if pd.isna(x):
        return "NA"
    return f"{x * 100:.2f}%"


def format_pp(x):
    if pd.isna(x):
        return "NA"
    return f"{x:+.2f}"


# ============================================================
# MAIN PROFILE FUNCTION
# ============================================================

def build_player_profile(player_name):
    slug = slugify(player_name)

    player_points = points[points["server"] == player_name].copy()
    player_score = score[score["server"] == player_name].copy()
    player_robust = robust[robust["server"] == player_name].copy()

    if player_points.empty or player_robust.empty:
        print(f"Salto {player_name}: dati insufficienti.")
        return None

    robust_row = player_robust.iloc[0]

    # ------------------------------------------------------------
    # Overall normal serve baseline
    # ------------------------------------------------------------

    normal_points = player_points[player_points["pressure_type"] == "normal"].copy()
    normal_rate = weighted_rate(normal_points)

    # ------------------------------------------------------------
    # Pressure type profile
    # ------------------------------------------------------------

    pressure_order = ["break_point", "deuce", "30_30", "tiebreak"]

    pressure_profile = player_score[
        player_score["pressure_type"].isin(pressure_order)
    ].copy()

    pressure_profile["pressure_type"] = pd.Categorical(
        pressure_profile["pressure_type"],
        categories=pressure_order,
        ordered=True,
    )

    pressure_profile = pressure_profile.sort_values("pressure_type")

    # ------------------------------------------------------------
    # Directional stake profile
    # ------------------------------------------------------------

    stake_masks = {
        "normal": player_points["point_stake_type"] == "normal",
        "30_30": player_points["is_30_30"],
        "deuce": player_points["is_deuce"],
        "break_point": player_points["is_break_point"],
        "close_server_game_point": player_points["is_close_server_game_point"],
        "server_set_point": player_points["is_server_set_point"],
        "returner_set_point": player_points["is_returner_set_point"],
        "server_match_point": player_points["is_server_match_point"],
        "returner_match_point": player_points["is_returner_match_point"],
        "tiebreak_point": player_points["is_tiebreak_point"],
    }

    stake_rows = []

    for stake, mask in stake_masks.items():
        temp = player_points[mask].copy()
        summary = weighted_summary(temp)

        delta = (
            (summary["weighted_serve_win_rate"] - normal_rate) * 100
            if not pd.isna(summary["weighted_serve_win_rate"]) and not pd.isna(normal_rate)
            else np.nan
        )

        stake_rows.append(
            {
                "stake": stake,
                "raw_points": summary["raw_points"],
                "weighted_points": summary["weighted_points"],
                "weighted_serve_win_rate": summary["weighted_serve_win_rate"],
                "delta_vs_player_normal_pp": delta,
            }
        )

    stake_profile = pd.DataFrame(stake_rows)

    # ------------------------------------------------------------
    # Surface profile
    # ------------------------------------------------------------

    surface_points = player_points[
        player_points["surface_group"].isin(["hard", "clay", "grass"])
    ].copy()

    surface_profile = (
        surface_points.groupby("surface_group")
        .agg(
            raw_points=("server_won_point_num", "size"),
            weighted_points=("point_weight", "sum"),
            weighted_wins=("server_won_point_num", lambda x: np.nan),
        )
        .reset_index()
    )

    # calcolo pesato manuale
    surface_rows = []

    for surface in ["hard", "clay", "grass"]:
        temp = surface_points[surface_points["surface_group"] == surface].copy()
        summary = weighted_summary(temp)

        surface_rows.append(
            {
                "surface_group": surface,
                "raw_points": summary["raw_points"],
                "weighted_points": summary["weighted_points"],
                "surface_share": len(temp) / len(surface_points) if len(surface_points) > 0 else np.nan,
                "weighted_serve_win_rate": summary["weighted_serve_win_rate"],
            }
        )

    surface_profile = pd.DataFrame(surface_rows)

    # ------------------------------------------------------------
    # Tournament level profile
    # ------------------------------------------------------------

    tournament_profile = (
        player_points.groupby("tournament_level")
        .agg(raw_points=("server_won_point_num", "size"))
        .reset_index()
    )

    tournament_profile["share"] = (
        tournament_profile["raw_points"] / tournament_profile["raw_points"].sum()
    )

    tournament_profile = tournament_profile.sort_values("raw_points", ascending=False)

    # ------------------------------------------------------------
    # Best / worst pressure area
    # ------------------------------------------------------------

    pressure_valid = pressure_profile.dropna(subset=["weighted_pressure_resilience_score"]).copy()

    if not pressure_valid.empty:
        best_pressure = pressure_valid.sort_values(
            "weighted_pressure_resilience_score",
            ascending=False,
        ).iloc[0]

        worst_pressure = pressure_valid.sort_values(
            "weighted_pressure_resilience_score",
            ascending=True,
        ).iloc[0]
    else:
        best_pressure = None
        worst_pressure = None

    stake_valid = stake_profile[
        (stake_profile["stake"] != "normal") &
        (stake_profile["raw_points"] >= 20)
    ].dropna(subset=["delta_vs_player_normal_pp"]).copy()

    if not stake_valid.empty:
        best_stake = stake_valid.sort_values(
            "delta_vs_player_normal_pp",
            ascending=False,
        ).iloc[0]

        worst_stake = stake_valid.sort_values(
            "delta_vs_player_normal_pp",
            ascending=True,
        ).iloc[0]
    else:
        best_stake = None
        worst_stake = None

    dominant_surface = (
        surface_profile.sort_values("surface_share", ascending=False).iloc[0]["surface_group"]
        if not surface_profile.empty
        else "unknown"
    )

    # ============================================================
    # PLOTS
    # ============================================================

    # 1. Pressure type score
    plt.figure(figsize=(8, 5))

    plot_pressure = pressure_profile.sort_values("weighted_pressure_resilience_score")

    plt.barh(
        plot_pressure["pressure_type"].astype(str),
        plot_pressure["weighted_pressure_resilience_score"],
    )

    plt.axvline(0, linestyle="--", linewidth=1)
    plt.xlabel("Weighted Pressure Resilience Score")
    plt.ylabel("Pressure type")
    plt.title(f"{player_name} — Pressure Type Profile")

    pressure_fig = f"{slug}_01_pressure_type_profile.png"
    save_fig(pressure_fig)

    # 2. Stake direction
    plot_stakes = stake_profile[
        stake_profile["stake"].isin(
            [
                "returner_match_point",
                "server_match_point",
                "returner_set_point",
                "server_set_point",
                "break_point",
                "close_server_game_point",
                "deuce",
                "30_30",
                "tiebreak_point",
            ]
        )
    ].copy()

    plot_stakes = plot_stakes[plot_stakes["raw_points"] >= 10]
    plot_stakes = plot_stakes.sort_values("delta_vs_player_normal_pp")

    plt.figure(figsize=(8, 6))

    plt.barh(
        plot_stakes["stake"],
        plot_stakes["delta_vs_player_normal_pp"],
    )

    plt.axvline(0, linestyle="--", linewidth=1)
    plt.xlabel("Delta vs player's normal serve points (percentage points)")
    plt.ylabel("Point stake")
    plt.title(f"{player_name} — High-Stake Direction Profile")

    stake_fig = f"{slug}_02_stake_direction_profile.png"
    save_fig(stake_fig)

    # 3. Surface mix
    plot_surface = surface_profile.copy()
    plot_surface = plot_surface.sort_values("surface_share")

    plt.figure(figsize=(7, 4))

    plt.barh(
        plot_surface["surface_group"],
        plot_surface["surface_share"] * 100,
    )

    plt.xlabel("Share of charted service points (%)")
    plt.ylabel("Surface")
    plt.title(f"{player_name} — Surface Mix")

    surface_fig = f"{slug}_03_surface_mix.png"
    save_fig(surface_fig)

    # ============================================================
    # MARKDOWN PROFILE
    # ============================================================

    md_path = OUT_DIR / f"{slug}_profile.md"

    if robust_row["avg_weighted_pressure_resilience_score"] > 0.5:
        overall_label = "positive pressure profile"
    elif robust_row["avg_weighted_pressure_resilience_score"] < -0.5:
        overall_label = "negative pressure profile"
    else:
        overall_label = "near-neutral pressure profile"

    interpretation_lines = []

    interpretation_lines.append(
        f"{player_name} has a **{overall_label}** in the final robust sample."
    )

    if best_pressure is not None:
        interpretation_lines.append(
            f"His strongest pressure type is **{best_pressure['pressure_type']}** "
            f"with a score of **{best_pressure['weighted_pressure_resilience_score']:+.2f}**."
        )

    if worst_pressure is not None:
        interpretation_lines.append(
            f"His weakest pressure type is **{worst_pressure['pressure_type']}** "
            f"with a score of **{worst_pressure['weighted_pressure_resilience_score']:+.2f}**."
        )

    if best_stake is not None:
        interpretation_lines.append(
            f"Among high-stake situations, his best relative area is **{best_stake['stake']}** "
            f"({best_stake['delta_vs_player_normal_pp']:+.2f} percentage points vs normal)."
        )

    if worst_stake is not None:
        interpretation_lines.append(
            f"His weakest high-stake area is **{worst_stake['stake']}** "
            f"({worst_stake['delta_vs_player_normal_pp']:+.2f} percentage points vs normal)."
        )

    interpretation_lines.append(
        f"His dominant surface exposure in the charted sample is **{dominant_surface}**."
    )

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Player Pressure Profile — {player_name}\n\n")

        f.write("## Overall\n\n")
        f.write(f"- **Weighted Pressure Resilience Score:** {robust_row['avg_weighted_pressure_resilience_score']:+.2f}\n")
        f.write(f"- **Average reliability score:** {robust_row['avg_reliability_score']:.2f}\n")
        f.write(f"- **Charted matches:** {int(robust_row['n_charted_matches'])}\n")
        f.write(f"- **Effective pressure points:** {robust_row['total_effective_pressure_points']:.0f}\n")
        f.write(f"- **Sample period:** {robust_row['first_date']} to {robust_row['last_date']}\n")
        f.write(f"- **Normal weighted serve win rate:** {format_pct(normal_rate)}\n\n")

        f.write("## Interpretation\n\n")
        for line in interpretation_lines:
            f.write(f"- {line}\n")

        f.write("\n## Pressure type profile\n\n")
        f.write(pressure_profile[
            [
                "pressure_type",
                "raw_n_pressure",
                "effective_n_pressure",
                "rate_normal",
                "rate_pressure",
                "delta_pp",
                "weighted_pressure_resilience_score",
                "reliability_score",
            ]
        ].to_markdown(index=False))

        f.write("\n\n")
        f.write(f"![Pressure type profile](figures/{pressure_fig})\n\n")

        f.write("## High-stake direction profile\n\n")
        f.write(stake_profile[
            [
                "stake",
                "raw_points",
                "weighted_serve_win_rate",
                "delta_vs_player_normal_pp",
            ]
        ].to_markdown(index=False))

        f.write("\n\n")
        f.write(f"![Stake direction profile](figures/{stake_fig})\n\n")

        f.write("## Surface mix\n\n")
        f.write(surface_profile[
            [
                "surface_group",
                "raw_points",
                "surface_share",
                "weighted_serve_win_rate",
            ]
        ].to_markdown(index=False))

        f.write("\n\n")
        f.write(f"![Surface mix](figures/{surface_fig})\n\n")

        f.write("## Tournament exposure\n\n")
        f.write(tournament_profile[
            [
                "tournament_level",
                "raw_points",
                "share",
            ]
        ].to_markdown(index=False))

        f.write("\n")

    # ============================================================
    # RETURN COMPACT SUMMARY
    # ============================================================

    return {
        "server": player_name,
        "score": robust_row["avg_weighted_pressure_resilience_score"],
        "reliability": robust_row["avg_reliability_score"],
        "n_charted_matches": robust_row["n_charted_matches"],
        "effective_pressure_points": robust_row["total_effective_pressure_points"],
        "normal_weighted_serve_win_rate": normal_rate,
        "best_pressure_type": best_pressure["pressure_type"] if best_pressure is not None else np.nan,
        "best_pressure_score": best_pressure["weighted_pressure_resilience_score"] if best_pressure is not None else np.nan,
        "worst_pressure_type": worst_pressure["pressure_type"] if worst_pressure is not None else np.nan,
        "worst_pressure_score": worst_pressure["weighted_pressure_resilience_score"] if worst_pressure is not None else np.nan,
        "best_stake": best_stake["stake"] if best_stake is not None else np.nan,
        "best_stake_delta_pp": best_stake["delta_vs_player_normal_pp"] if best_stake is not None else np.nan,
        "worst_stake": worst_stake["stake"] if worst_stake is not None else np.nan,
        "worst_stake_delta_pp": worst_stake["delta_vs_player_normal_pp"] if worst_stake is not None else np.nan,
        "dominant_surface": dominant_surface,
        "profile_path": str(md_path),
    }


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    players = (
        robust.sort_values("avg_weighted_pressure_resilience_score", ascending=False)
        .head(TOP_N_PLAYERS)["server"]
        .tolist()
    )

    summaries = []

    for player in players:
        print("\n" + "=" * 80)
        print("Building profile:", player)
        print("=" * 80)

        result = build_player_profile(player)

        if result is not None:
            summaries.append(result)

    summary_df = pd.DataFrame(summaries)
    summary_df = summary_df.sort_values("score", ascending=False)
    summary_df.to_csv(OUT_SUMMARY, index=False)

    print("\nSummary salvato in:", OUT_SUMMARY)

    # Index markdown
    with open(OUT_INDEX, "w", encoding="utf-8") as f:
        f.write("# Player Pressure Profiles\n\n")
        f.write(
            "This folder contains individual pressure profiles for players included "
            "in the final robust leaderboard.\n\n"
        )

        f.write("## Profiles\n\n")

        for _, row in summary_df.iterrows():
            slug = slugify(row["server"])
            f.write(
                f"- [{row['server']}]({slug}_profile.md): "
                f"score {row['score']:+.2f}, "
                f"reliability {row['reliability']:.1f}, "
                f"best area {row['best_pressure_type']}, "
                f"weakest area {row['worst_pressure_type']}\n"
            )

    print("Index profili salvato in:", OUT_INDEX)

    print("\nCompact summary:")
    print(
        summary_df[
            [
                "server",
                "score",
                "reliability",
                "n_charted_matches",
                "best_pressure_type",
                "best_pressure_score",
                "worst_pressure_type",
                "worst_pressure_score",
                "best_stake",
                "worst_stake",
                "dominant_surface",
            ]
        ].to_string(index=False)
    )