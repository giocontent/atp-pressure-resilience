from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np

FIG_DIR = Path("reports/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)

STABLE_PATH = Path("data/processed/stable_weighted_pressure_leaderboard_atp_2020s.csv")
SCORE_PATH = Path("data/processed/weighted_pressure_resilience_score_atp_2020s.csv")
POINTS_PATH = Path("data/processed/pressure_points_atp_2020s_v4_weighted.csv")

mpl.rcParams.update(
    {
        "figure.facecolor": "#f8faf7",
        "figure.dpi": 110,
        "axes.facecolor": "#ffffff",
        "axes.edgecolor": "#cbd5c1",
        "axes.labelcolor": "#1f2937",
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": "#d7e0d1",
        "grid.linestyle": ":",
        "grid.linewidth": 0.9,
        "grid.alpha": 0.8,
        "xtick.color": "#334155",
        "ytick.color": "#334155",
        "text.color": "#111827",
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.titlesize": 16,
        "axes.titleweight": "bold",
        "axes.labelsize": 12,
        "legend.fontsize": 10,
        "legend.title_fontsize": 10,
        "savefig.facecolor": "#f8faf7",
        "savefig.edgecolor": "#f8faf7",
    }
)

PRESSURE_COLORS = {
    "normal": "#64748b",
    "30_30": "#d97706",
    "deuce": "#2563eb",
    "break_point": "#dc2626",
    "tiebreak": "#7c3aed",
}


def _style_axes(ax, title, xlabel, ylabel, xgrid=True):
    ax.set_title(title, loc="left", pad=12)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(axis="x" if xgrid else "y", linestyle=":", linewidth=0.9, alpha=0.7)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#cbd5c1")
    ax.spines["bottom"].set_color("#cbd5c1")


def _annotate_barh(ax, fmt="{:.2f}", pad=0.012):
    x_min, x_max = ax.get_xlim()
    x_span = x_max - x_min if x_max != x_min else 1.0
    offset = x_span * pad

    for bar in ax.patches:
        value = bar.get_width()
        y_pos = bar.get_y() + bar.get_height() / 2
        if value >= 0:
            x_pos = value + offset
            align = "left"
        else:
            x_pos = value - offset
            align = "right"

        ax.annotate(
            fmt.format(value),
            (x_pos, y_pos),
            va="center",
            ha=align,
            fontsize=9,
            color="#1f2937",
        )


def _annotate_barv(ax, fmt="{:.0f}"):
    for bar in ax.patches:
        value = bar.get_height()
        x_pos = bar.get_x() + bar.get_width() / 2
        ax.annotate(
            fmt.format(value),
            (x_pos, value),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
            color="#1f2937",
        )


def _score_colors(values):
    values = pd.Series(values).astype(float)
    if values.min() < 0 and values.max() > 0:
        norm = mpl.colors.TwoSlopeNorm(vmin=values.min(), vcenter=0, vmax=values.max())
        cmap = mpl.cm.get_cmap("RdYlGn")
    else:
        norm = mpl.colors.Normalize(vmin=values.min(), vmax=values.max())
        cmap = mpl.cm.get_cmap("YlGn")
    return cmap(norm(values))


def _pressure_colors(series):
    return [PRESSURE_COLORS.get(item, "#0f766e") for item in series]


def _finish_figure(fig, filename):
    out_path = FIG_DIR / filename
    fig.tight_layout()
    fig.savefig(out_path, dpi=320, bbox_inches="tight")
    plt.close(fig)
    print("Figura salvata in:", out_path)


def _soft_bar_colors(values, positive="#166534", negative="#b91c1c"):
    return [positive if value >= 0 else negative for value in values]


def _vibrant_bar_colors(values):
    values = pd.Series(values).astype(float)
    return _score_colors(values)


# ============================================================
# 1. Stable weighted leaderboard: top + bottom
# ============================================================

def plot_stable_weighted_leaderboard():
    df = pd.read_csv(STABLE_PATH)

    top = df.sort_values("avg_weighted_pressure_resilience_score", ascending=False).head(12)
    bottom = df.sort_values("avg_weighted_pressure_resilience_score", ascending=True).head(12)

    plot_df = pd.concat([bottom, top], axis=0)
    plot_df = plot_df.drop_duplicates(subset=["server"])
    plot_df = plot_df.sort_values("avg_weighted_pressure_resilience_score")

    fig, ax = plt.subplots(figsize=(10.5, 9))
    colors = _soft_bar_colors(plot_df["avg_weighted_pressure_resilience_score"])
    ax.barh(
        plot_df["server"],
        plot_df["avg_weighted_pressure_resilience_score"],
        color=colors,
        edgecolor="#ffffff",
        linewidth=0.8,
    )
    ax.axvline(0, linestyle="--", linewidth=1, color="#475569")

    _style_axes(
        ax,
        "Stable Weighted Pressure Resilience Leaderboard — ATP 2020s",
        "Weighted Pressure Resilience Score",
        "Player",
        xgrid=True,
    )
    _annotate_barh(ax)

    _finish_figure(fig, "01_stable_weighted_leaderboard.png")


# ============================================================
# 2. Reliability by pressure type
# ============================================================

def plot_reliability_by_pressure_type():
    score = pd.read_csv(SCORE_PATH)

    summary = (
        score.groupby("pressure_type")
        .agg(mean_reliability=("reliability_score", "mean"))
        .reset_index()
    )

    order = ["break_point", "deuce", "30_30", "tiebreak"]
    summary["pressure_type"] = pd.Categorical(
        summary["pressure_type"],
        categories=order,
        ordered=True,
    )
    summary = summary.sort_values("pressure_type")

    fig, ax = plt.subplots(figsize=(8.5, 5.4))
    pressure_labels = summary["pressure_type"].astype(str)
    ax.bar(
        pressure_labels,
        summary["mean_reliability"],
        color=_pressure_colors(pressure_labels),
        edgecolor="#ffffff",
        linewidth=0.9,
    )

    _style_axes(
        ax,
        "Reliability of Pressure Effects by Point Type",
        "Pressure type",
        "Average reliability score",
        xgrid=False,
    )
    _annotate_barv(ax, fmt="{:.3f}")

    _finish_figure(fig, "02_reliability_by_pressure_type.png")


# ============================================================
# 3. Global weighted serve win rate by pressure type
# ============================================================

def plot_global_weighted_serve_win_rate():
    df = pd.read_csv(POINTS_PATH, low_memory=False)

    df["server_won_point"] = (
        df["server_won_point"].astype(str).str.lower().map({"true": 1, "false": 0})
    )
    df["point_weight"] = pd.to_numeric(df["point_weight"], errors="coerce")

    df = df.dropna(subset=["server_won_point", "point_weight", "pressure_type"])

    df["weighted_win"] = df["server_won_point"] * df["point_weight"]

    summary = (
        df.groupby("pressure_type")
        .agg(
            weighted_wins=("weighted_win", "sum"),
            weighted_points=("point_weight", "sum"),
            raw_points=("server_won_point", "size"),
        )
        .reset_index()
    )

    summary["weighted_serve_win_rate"] = (
        summary["weighted_wins"] / summary["weighted_points"]
    )

    normal_rate = summary.loc[
        summary["pressure_type"] == "normal",
        "weighted_serve_win_rate"
    ].iloc[0]

    summary["delta_vs_normal_pp"] = (
        summary["weighted_serve_win_rate"] - normal_rate
    ) * 100

    order = ["normal", "30_30", "deuce", "break_point", "tiebreak"]
    summary["pressure_type"] = pd.Categorical(
        summary["pressure_type"],
        categories=order,
        ordered=True,
    )
    summary = summary.sort_values("pressure_type")

    fig, ax = plt.subplots(figsize=(9, 5.6))
    pressure_labels = summary["pressure_type"].astype(str)
    ax.bar(
        pressure_labels,
        summary["weighted_serve_win_rate"] * 100,
        color=_pressure_colors(pressure_labels),
        edgecolor="#ffffff",
        linewidth=0.9,
    )

    _style_axes(
        ax,
        "Global Weighted Serve Win Rate by Pressure Type",
        "Pressure type",
        "Weighted serve win rate (%)",
        xgrid=False,
    )
    _annotate_barv(ax, fmt="{:.1f}")

    _finish_figure(fig, "03_global_weighted_serve_win_rate.png")

    # Second figure: delta vs normal
    delta_df = summary[summary["pressure_type"].astype(str) != "normal"].copy()

    fig, ax = plt.subplots(figsize=(9, 5.6))
    pressure_labels = delta_df["pressure_type"].astype(str)
    delta_colors = _soft_bar_colors(delta_df["delta_vs_normal_pp"])
    ax.bar(
        pressure_labels,
        delta_df["delta_vs_normal_pp"],
        color=delta_colors,
        edgecolor="#ffffff",
        linewidth=0.9,
    )
    ax.axhline(0, linestyle="--", linewidth=1, color="#475569")

    _style_axes(
        ax,
        "Global Weighted Pressure Effect vs Normal Points",
        "Pressure type",
        "Delta vs normal points (percentage points)",
        xgrid=False,
    )
    _annotate_barv(ax, fmt="{:.2f}")

    _finish_figure(fig, "04_global_weighted_delta_vs_normal.png")


# ============================================================
# 4. Selected player pressure profile
# ============================================================

def plot_selected_player_profiles():
    score = pd.read_csv(SCORE_PATH)

    selected_players = [
        "Jannik Sinner",
        "Carlos Alcaraz",
        "Novak Djokovic",
        "Lorenzo Musetti",
        "Andy Murray",
        "Andrey Rublev",
        "Rafael Nadal",
    ]

    order = ["break_point", "deuce", "30_30", "tiebreak"]

    profile = score[score["server"].isin(selected_players)].copy()
    profile["pressure_type"] = pd.Categorical(
        profile["pressure_type"],
        categories=order,
        ordered=True,
    )
    profile = profile.sort_values(["server", "pressure_type"])

    pivot = profile.pivot(
        index="server",
        columns="pressure_type",
        values="weighted_pressure_resilience_score",
    )

    # Manteniamo l'ordine scelto manualmente
    pivot = pivot.reindex(selected_players)
    pivot = pivot.dropna(how="all")

    x = np.arange(len(pivot.index))
    width = 0.18

    fig, ax = plt.subplots(figsize=(12, 6.5))
    palette = {
        "break_point": PRESSURE_COLORS["break_point"],
        "deuce": PRESSURE_COLORS["deuce"],
        "30_30": PRESSURE_COLORS["30_30"],
        "tiebreak": PRESSURE_COLORS["tiebreak"],
    }

    for i, pressure_type in enumerate(order):
        if pressure_type in pivot.columns:
            ax.bar(
                x + (i - 1.5) * width,
                pivot[pressure_type],
                width,
                label=pressure_type,
                color=palette.get(pressure_type, "#0f766e"),
                edgecolor="#ffffff",
                linewidth=0.7,
            )

    ax.axhline(0, linestyle="--", linewidth=1, color="#475569")
    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index, rotation=35, ha="right")

    _style_axes(
        ax,
        "Pressure Profile by Point Type — Selected Players",
        "Player",
        "Weighted Pressure Resilience Score",
        xgrid=False,
    )
    ax.legend(title="Pressure type", frameon=False, ncol=2)

    _finish_figure(fig, "05_selected_player_pressure_profiles.png")


# ============================================================
# 5. Score vs reliability scatter
# ============================================================

def plot_score_vs_reliability():
    stable = pd.read_csv(STABLE_PATH)

    fig, ax = plt.subplots(figsize=(9.5, 6.6))
    scatter = ax.scatter(
        stable["avg_reliability_score"],
        stable["avg_weighted_pressure_resilience_score"],
        c=stable["avg_weighted_pressure_resilience_score"],
        cmap="RdYlGn",
        s=55,
        alpha=0.85,
        edgecolors="#ffffff",
        linewidths=0.6,
    )

    ax.axhline(0, linestyle="--", linewidth=1, color="#475569")
    ax.axvline(stable["avg_reliability_score"].median(), linestyle=":", linewidth=1, color="#94a3b8")

    # Etichettiamo solo estremi e nomi importanti
    label_players = {
        "Andy Murray",
        "Lorenzo Musetti",
        "Jannik Sinner",
        "Carlos Alcaraz",
        "Novak Djokovic",
        "Rafael Nadal",
        "Andrey Rublev",
        "Ben Shelton",
        "Daniil Medvedev",
    }

    for _, row in stable.iterrows():
        if (
            row["server"] in label_players
            or row["avg_weighted_pressure_resilience_score"] > 1.0
            or row["avg_weighted_pressure_resilience_score"] < -1.5
        ):
            ax.annotate(
                row["server"],
                (
                    row["avg_reliability_score"],
                    row["avg_weighted_pressure_resilience_score"],
                ),
                fontsize=8,
                xytext=(4, 4),
                textcoords="offset points",
            )

    _style_axes(
        ax,
        "Weighted Pressure Score vs Reliability — Stable Players",
        "Average reliability score",
        "Weighted Pressure Resilience Score",
        xgrid=True,
    )
    cbar = fig.colorbar(scatter, ax=ax, pad=0.01)
    cbar.set_label("Weighted Pressure Resilience Score")

    _finish_figure(fig, "06_score_vs_reliability.png")


# ============================================================
# 6. Tournament level distribution
# ============================================================

def plot_tournament_level_distribution():
    df = pd.read_csv(POINTS_PATH, low_memory=False)

    summary = (
        df.groupby("tournament_level")
        .agg(
            raw_points=("server_won_point", "size"),
            avg_point_weight=("point_weight", "mean"),
        )
        .reset_index()
        .sort_values("raw_points", ascending=True)
    )

    fig, ax = plt.subplots(figsize=(9.5, 6.4))
    colors = _vibrant_bar_colors(summary["raw_points"])
    ax.barh(
        summary["tournament_level"],
        summary["raw_points"],
        color=colors,
        edgecolor="#ffffff",
        linewidth=0.8,
    )

    _style_axes(
        ax,
        "Point Distribution by Tournament Level — ATP 2020s",
        "Number of points",
        "Tournament level",
        xgrid=True,
    )
    _annotate_barh(ax, fmt="{:.0f}")

    _finish_figure(fig, "07_tournament_level_distribution.png")


# ============================================================
# 7. Top players only: clean positive leaderboard
# ============================================================

def plot_top_positive_stable_players():
    stable = pd.read_csv(STABLE_PATH)

    top = stable.sort_values(
        "avg_weighted_pressure_resilience_score",
        ascending=False,
    ).head(15)

    top = top.sort_values("avg_weighted_pressure_resilience_score")

    fig, ax = plt.subplots(figsize=(9.5, 6.2))
    colors = _soft_bar_colors(top["avg_weighted_pressure_resilience_score"])
    ax.barh(
        top["server"],
        top["avg_weighted_pressure_resilience_score"],
        color=colors,
        edgecolor="#ffffff",
        linewidth=0.8,
    )

    ax.axvline(0, linestyle="--", linewidth=1, color="#475569")

    _style_axes(
        ax,
        "Top Stable Pressure Resilience Players — ATP 2020s",
        "Weighted Pressure Resilience Score",
        "Player",
        xgrid=True,
    )
    _annotate_barh(ax)

    _finish_figure(fig, "08_top_stable_weighted_players.png")


# ============================================================
# 8. Bottom players only: clean negative leaderboard
# ============================================================

def plot_bottom_negative_stable_players():
    stable = pd.read_csv(STABLE_PATH)

    bottom = stable.sort_values(
        "avg_weighted_pressure_resilience_score",
        ascending=True,
    ).head(15)

    bottom = bottom.sort_values("avg_weighted_pressure_resilience_score", ascending=False)

    fig, ax = plt.subplots(figsize=(9.5, 6.2))
    colors = _soft_bar_colors(bottom["avg_weighted_pressure_resilience_score"])
    ax.barh(
        bottom["server"],
        bottom["avg_weighted_pressure_resilience_score"],
        color=colors,
        edgecolor="#ffffff",
        linewidth=0.8,
    )

    ax.axvline(0, linestyle="--", linewidth=1, color="#475569")

    _style_axes(
        ax,
        "Lowest Stable Pressure Resilience Players — ATP 2020s",
        "Weighted Pressure Resilience Score",
        "Player",
        xgrid=True,
    )
    _annotate_barh(ax)

    _finish_figure(fig, "09_bottom_stable_weighted_players.png")


# ============================================================
# Run all
# ============================================================

if __name__ == "__main__":
    plot_stable_weighted_leaderboard()
    plot_reliability_by_pressure_type()
    plot_global_weighted_serve_win_rate()
    plot_selected_player_profiles()
    plot_score_vs_reliability()
    plot_tournament_level_distribution()
    plot_top_positive_stable_players()
    plot_bottom_negative_stable_players()

    print("\nTutti i grafici sono stati generati in:", FIG_DIR)