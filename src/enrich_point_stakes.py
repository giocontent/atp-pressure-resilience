from pathlib import Path
import pandas as pd
import numpy as np

DATA_PATH = Path("data/processed/pressure_points_atp_2020s_v4_weighted.csv")
OUT_PATH = Path("data/processed/pressure_points_atp_2020s_v5_stakes.csv")

df = pd.read_csv(DATA_PATH, low_memory=False)

print("Dataset iniziale:", df.shape)


def to_bool(series):
    return (
        series.astype(str)
        .str.lower()
        .map({"true": True, "false": False})
        .fillna(False)
    )


# ============================================================
# Basic cleaning
# ============================================================

bool_cols = [
    "server_won_point",
    "is_deuce",
    "is_30_30",
    "is_break_point",
    "is_tiebreak_point",
    "is_pressure_point",
]

for col in bool_cols:
    if col in df.columns:
        df[col] = to_bool(df[col])

numeric_cols = [
    "Set1",
    "Set2",
    "Gm1",
    "Gm2",
    "p1_point_score",
    "p2_point_score",
    "Svr",
]

for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")


# ============================================================
# Infer best-of format
# ============================================================

def infer_sets_to_win(row):
    """
    Approximation:
    - Men's Grand Slam main draw = best of 5, first to 3 sets.
    - Grand Slam qualifying and all other events = best of 3, first to 2 sets.
    """
    tournament_level = str(row.get("tournament_level", "")).lower()
    round_name = str(row.get("round", "")).upper()

    if tournament_level == "grand_slam" and round_name not in ["Q1", "Q2", "Q3"]:
        return 3

    return 2


df["sets_to_win"] = df.apply(infer_sets_to_win, axis=1)


# ============================================================
# Game point / break point logic
# ============================================================

p1 = df["p1_point_score"]
p2 = df["p2_point_score"]

is_tiebreak = df["is_tiebreak_point"]

# Player has game point if winning this point wins the game.
# Normal games only.
df["is_p1_game_point"] = (~is_tiebreak) & (p1 >= 3) & (p1 > p2)
df["is_p2_game_point"] = (~is_tiebreak) & (p2 >= 3) & (p2 > p1)

# Server game point
df["is_server_game_point"] = np.where(
    df["Svr"] == 1,
    df["is_p1_game_point"],
    df["is_p2_game_point"],
)

# Returner game point = break point
df["is_returner_game_point"] = np.where(
    df["Svr"] == 1,
    df["is_p2_game_point"],
    df["is_p1_game_point"],
)

# Check consistency with previous break point variable
df["is_break_point_recomputed"] = df["is_returner_game_point"]

# "Close" server game point: avoids treating 40-0 as high pressure
server_score = np.where(df["Svr"] == 1, p1, p2)
returner_score = np.where(df["Svr"] == 1, p2, p1)

df["is_close_server_game_point"] = (
    df["is_server_game_point"] & (returner_score >= 2)
)

df["is_any_game_point"] = (
    df["is_server_game_point"] | df["is_returner_game_point"]
)


# ============================================================
# Set point logic
# ============================================================

g1 = df["Gm1"]
g2 = df["Gm2"]

# If player 1 wins current game, would they win the set?
p1_games_after = g1 + 1
p2_games_after = g2 + 1

p1_would_win_set_by_game = (
    ((p1_games_after >= 6) & ((p1_games_after - g2) >= 2))
    | ((p1_games_after == 7) & (g2 == 6))
)

p2_would_win_set_by_game = (
    ((p2_games_after >= 6) & ((p2_games_after - g1) >= 2))
    | ((p2_games_after == 7) & (g1 == 6))
)

df["is_p1_set_point_regular"] = df["is_p1_game_point"] & p1_would_win_set_by_game
df["is_p2_set_point_regular"] = df["is_p2_game_point"] & p2_would_win_set_by_game


# ============================================================
# Tiebreak set point logic
# ============================================================

# Extract numeric tiebreak score from Pts, e.g. "6-5", "7-6"
tb_scores = df["Pts"].astype(str).str.extract(r"^(\d+)-(\d+)$")
df["tb_p1_score"] = pd.to_numeric(tb_scores[0], errors="coerce")
df["tb_p2_score"] = pd.to_numeric(tb_scores[1], errors="coerce")

# Standard tiebreak target = 7.
# Approximation: Grand Slam best-of-5 final set tiebreak target = 10.
is_bo5_final_set = (
    (df["sets_to_win"] == 3)
    & (
        ((df["Set1"] == 2) & (df["Set2"] == 2))
    )
)

df["tiebreak_target_points"] = np.where(is_bo5_final_set, 10, 7)

tb1 = df["tb_p1_score"]
tb2 = df["tb_p2_score"]
tb_target = df["tiebreak_target_points"]

df["is_p1_set_point_tiebreak"] = (
    is_tiebreak
    & (tb1 >= (tb_target - 1))
    & (tb1 > tb2)
)

df["is_p2_set_point_tiebreak"] = (
    is_tiebreak
    & (tb2 >= (tb_target - 1))
    & (tb2 > tb1)
)

df["is_p1_set_point"] = (
    df["is_p1_set_point_regular"] | df["is_p1_set_point_tiebreak"]
)

df["is_p2_set_point"] = (
    df["is_p2_set_point_regular"] | df["is_p2_set_point_tiebreak"]
)

df["is_set_point"] = df["is_p1_set_point"] | df["is_p2_set_point"]


# ============================================================
# Match point logic
# ============================================================

df["is_p1_match_point"] = (
    df["is_p1_set_point"] & ((df["Set1"] + 1) >= df["sets_to_win"])
)

df["is_p2_match_point"] = (
    df["is_p2_set_point"] & ((df["Set2"] + 1) >= df["sets_to_win"])
)

df["is_match_point"] = df["is_p1_match_point"] | df["is_p2_match_point"]


# ============================================================
# Server / returner version
# ============================================================

df["is_server_match_point"] = np.where(
    df["Svr"] == 1,
    df["is_p1_match_point"],
    df["is_p2_match_point"],
)

df["is_returner_match_point"] = np.where(
    df["Svr"] == 1,
    df["is_p2_match_point"],
    df["is_p1_match_point"],
)

df["is_server_set_point"] = np.where(
    df["Svr"] == 1,
    df["is_p1_set_point"],
    df["is_p2_set_point"],
)

df["is_returner_set_point"] = np.where(
    df["Svr"] == 1,
    df["is_p2_set_point"],
    df["is_p1_set_point"],
)


# ============================================================
# Detailed stake type
# ============================================================

conditions = [
    df["is_match_point"],
    df["is_set_point"],
    df["is_break_point"],
    df["is_close_server_game_point"],
    df["is_tiebreak_point"],
    df["is_deuce"],
    df["is_30_30"],
]

choices = [
    "match_point",
    "set_point",
    "break_point",
    "close_server_game_point",
    "tiebreak_other",
    "deuce",
    "30_30",
]

df["point_stake_type"] = np.select(
    conditions,
    choices,
    default="normal",
)

# High pressure version, without including every easy 40-0 / 40-15 server game point
df["is_high_pressure_point_v5"] = (
    df["is_match_point"]
    | df["is_set_point"]
    | df["is_break_point"]
    | df["is_close_server_game_point"]
    | df["is_deuce"]
    | df["is_30_30"]
    | df["is_tiebreak_point"]
)


# ============================================================
# Save
# ============================================================

df.to_csv(OUT_PATH, index=False)

print("\nDataset salvato in:", OUT_PATH)
print("Shape:", df.shape)

print("\nConteggi principali:")
print("Game points totali:", int(df["is_any_game_point"].sum()))
print("Server game points:", int(df["is_server_game_point"].sum()))
print("Close server game points:", int(df["is_close_server_game_point"].sum()))
print("Break points:", int(df["is_break_point"].sum()))
print("Set points:", int(df["is_set_point"].sum()))
print("Match points:", int(df["is_match_point"].sum()))

print("\nDistribuzione point_stake_type:")
print(df["point_stake_type"].value_counts())

print("\nCheck break point originale vs ricostruito:")
comparison = pd.crosstab(
    df["is_break_point"],
    df["is_break_point_recomputed"],
    rownames=["original"],
    colnames=["recomputed"],
)
print(comparison)

print("\nServe win rate by point_stake_type:")
summary = (
    df.groupby("point_stake_type")
    .agg(
        n_points=("server_won_point", "size"),
        server_win_rate=("server_won_point", "mean"),
        avg_weight=("point_weight", "mean"),
    )
    .sort_values("server_win_rate", ascending=False)
)

print(summary)