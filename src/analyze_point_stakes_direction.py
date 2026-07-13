from pathlib import Path
import pandas as pd
import numpy as np

DATA_PATH = Path("data/processed/pressure_points_atp_2020s_v5_stakes.csv")
OUT_PATH = Path("data/processed/point_stakes_direction_summary.csv")

df = pd.read_csv(DATA_PATH, low_memory=False)

print("Dataset:", df.shape)

df["server_won_point"] = (
    df["server_won_point"]
    .astype(str)
    .str.lower()
    .map({"true": 1, "false": 0})
)

df["point_weight"] = pd.to_numeric(df["point_weight"], errors="coerce")

df = df.dropna(subset=["server_won_point", "point_weight"])

df["weighted_win"] = df["server_won_point"] * df["point_weight"]

stake_flags = {
    "normal": df["point_stake_type"] == "normal",
    "30_30": df["is_30_30"],
    "deuce": df["is_deuce"],
    "break_point": df["is_break_point"],
    "server_game_point": df["is_server_game_point"],
    "close_server_game_point": df["is_close_server_game_point"],
    "set_point": df["is_set_point"],
    "server_set_point": df["is_server_set_point"],
    "returner_set_point": df["is_returner_set_point"],
    "match_point": df["is_match_point"],
    "server_match_point": df["is_server_match_point"],
    "returner_match_point": df["is_returner_match_point"],
    "tiebreak_point": df["is_tiebreak_point"],
}

rows = []

for stake_name, mask in stake_flags.items():
    temp = df[mask].copy()

    if temp.empty:
        continue

    weighted_points = temp["point_weight"].sum()
    weighted_wins = temp["weighted_win"].sum()

    rows.append(
        {
            "stake": stake_name,
            "raw_points": len(temp),
            "weighted_points": weighted_points,
            "weighted_server_win_rate": weighted_wins / weighted_points,
            "avg_point_weight": temp["point_weight"].mean(),
        }
    )

summary = pd.DataFrame(rows)

normal_rate = summary.loc[
    summary["stake"] == "normal",
    "weighted_server_win_rate"
].iloc[0]

summary["delta_vs_normal_pp"] = (
    summary["weighted_server_win_rate"] - normal_rate
) * 100

summary = summary.sort_values("delta_vs_normal_pp")

summary.to_csv(OUT_PATH, index=False)

print("\nDataset salvato in:", OUT_PATH)

print("\nWeighted serve win rate by stake direction:")
print(
    summary[
        [
            "stake",
            "raw_points",
            "weighted_server_win_rate",
            "delta_vs_normal_pp",
            "avg_point_weight",
        ]
    ].to_string(index=False)
)