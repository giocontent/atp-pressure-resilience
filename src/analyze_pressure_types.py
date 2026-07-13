from pathlib import Path
import pandas as pd
import numpy as np

DATA_PATH = Path("data/processed/pressure_points_atp_2020s_v3.csv")
OUT_DIR = Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA_PATH, low_memory=False)

df["server_won_point"] = df["server_won_point"].astype(str).str.lower().map(
    {"true": True, "false": False}
)

print("Dataset:", df.shape)

# ============================================================
# 1. Global serve win rate by pressure type
# ============================================================

global_summary = (
    df.groupby("pressure_type")
    .agg(
        n_points=("server_won_point", "size"),
        server_win_rate=("server_won_point", "mean"),
    )
    .reset_index()
)

normal_rate = global_summary.loc[
    global_summary["pressure_type"] == "normal", "server_win_rate"
].iloc[0]

global_summary["delta_vs_normal_pp"] = (
    global_summary["server_win_rate"] - normal_rate
) * 100

global_summary = global_summary.sort_values("delta_vs_normal_pp")

out_global = OUT_DIR / "pressure_type_global_summary.csv"
global_summary.to_csv(out_global, index=False)

print("\nGLOBAL SUMMARY")
print(global_summary.to_string(index=False))

# ============================================================
# 2. Player-level summary by pressure type
# ============================================================

player_type = (
    df.groupby(["server", "pressure_type"])
    .agg(
        n_points=("server_won_point", "size"),
        serve_win_rate=("server_won_point", "mean"),
    )
    .reset_index()
)

# Wide format
wide_n = player_type.pivot(
    index="server", columns="pressure_type", values="n_points"
).add_prefix("n_")

wide_rate = player_type.pivot(
    index="server", columns="pressure_type", values="serve_win_rate"
).add_prefix("rate_")

wide = pd.concat([wide_n, wide_rate], axis=1).reset_index()

# Delta vs normal per ogni pressure type
for t in ["30_30", "deuce", "break_point", "tiebreak"]:
    if f"rate_{t}" in wide.columns and "rate_normal" in wide.columns:
        wide[f"delta_{t}_pp"] = (wide[f"rate_{t}"] - wide["rate_normal"]) * 100

out_player = OUT_DIR / "pressure_type_by_server_atp_2020s.csv"
wide.to_csv(out_player, index=False)

print("\nDataset player-type salvato in:", out_player)
print("Shape:", wide.shape)

# ============================================================
# 3. Classifiche più interessanti
# ============================================================

def print_ranking(df_wide, pressure_type, min_normal=500, min_type=100, top_n=15):
    n_col = f"n_{pressure_type}"
    delta_col = f"delta_{pressure_type}_pp"
    rate_col = f"rate_{pressure_type}"

    if n_col not in df_wide.columns:
        print(f"\nTipo {pressure_type} non presente.")
        return

    temp = df_wide[
        (df_wide["n_normal"] >= min_normal) &
        (df_wide[n_col] >= min_type)
    ].copy()

    temp = temp.sort_values(delta_col, ascending=False)

    print(f"\nTOP {top_n} - {pressure_type} vs normal")
    print(
        temp[
            [
                "server",
                "n_normal",
                n_col,
                "rate_normal",
                rate_col,
                delta_col,
            ]
        ]
        .head(top_n)
        .to_string(index=False)
    )

    print(f"\nBOTTOM {top_n} - {pressure_type} vs normal")
    print(
        temp[
            [
                "server",
                "n_normal",
                n_col,
                "rate_normal",
                rate_col,
                delta_col,
            ]
        ]
        .tail(top_n)
        .sort_values(delta_col)
        .to_string(index=False)
    )


print_ranking(wide, "break_point", min_normal=500, min_type=100)
print_ranking(wide, "deuce", min_normal=500, min_type=100)
print_ranking(wide, "30_30", min_normal=500, min_type=80)
print_ranking(wide, "tiebreak", min_normal=500, min_type=80)