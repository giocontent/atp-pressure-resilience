from pathlib import Path
import pandas as pd
import numpy as np
import math

DATA_PATH = Path("data/processed/pressure_points_atp_2020s_v4_weighted.csv")

OUT_RELIABILITY = Path("data/processed/weighted_pressure_type_reliability_atp_2020s.csv")
OUT_SCORE = Path("data/processed/weighted_pressure_resilience_score_atp_2020s.csv")
OUT_PLAYER = Path("data/processed/player_weighted_pressure_resilience_score_atp_2020s.csv")
OUT_STABLE = Path("data/processed/stable_weighted_pressure_leaderboard_atp_2020s.csv")

df = pd.read_csv(DATA_PATH, low_memory=False)

print("Dataset:", df.shape)

# Booleani puliti
df["server_won_point"] = df["server_won_point"].astype(str).str.lower().map(
    {"true": True, "false": False}
)

# Sicurezza
df["point_weight"] = pd.to_numeric(df["point_weight"], errors="coerce")
df = df.dropna(subset=["server_won_point", "point_weight", "pressure_type", "server"]).copy()

PRESSURE_TYPES = ["break_point", "deuce", "30_30", "tiebreak"]

MIN_NORMAL_EFFECTIVE_N = 500
MIN_PRESSURE_EFFECTIVE_N = {
    "break_point": 100,
    "deuce": 100,
    "30_30": 80,
    "tiebreak": 80,
}


def normal_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def weighted_summary(data, group_col="server"):
    """
    Calcola:
    - weighted_n: somma dei pesi
    - effective_n: numerosità effettiva Kish = (sum w)^2 / sum(w^2)
    - weighted_win_rate: media pesata di server_won_point
    """
    temp = data.copy()
    temp["weighted_win"] = temp["point_weight"] * temp["server_won_point"].astype(float)
    temp["weight_sq"] = temp["point_weight"] ** 2

    out = (
        temp.groupby(group_col)
        .agg(
            raw_n=("server_won_point", "size"),
            weighted_n=("point_weight", "sum"),
            weight_sq_sum=("weight_sq", "sum"),
            weighted_wins=("weighted_win", "sum"),
        )
        .reset_index()
    )

    out["effective_n"] = (out["weighted_n"] ** 2) / out["weight_sq_sum"]
    out["weighted_win_rate"] = out["weighted_wins"] / out["weighted_n"]

    return out


def add_fdr_bh(temp, p_col="p_value"):
    temp = temp.sort_values(p_col).reset_index(drop=True)
    m = len(temp)

    if m == 0:
        temp["p_value_fdr"] = []
        return temp

    temp["rank_p"] = np.arange(1, m + 1)
    temp["bh_value"] = temp[p_col] * m / temp["rank_p"]
    temp["p_value_fdr"] = temp["bh_value"][::-1].cummin()[::-1]
    temp["p_value_fdr"] = temp["p_value_fdr"].clip(upper=1)

    return temp


results = []

for pressure_type in PRESSURE_TYPES:
    print(f"\nAnalizzo weighted: {pressure_type}")

    normal = weighted_summary(df[df["pressure_type"] == "normal"])
    normal = normal.rename(
        columns={
            "raw_n": "raw_n_normal",
            "weighted_n": "weighted_n_normal",
            "effective_n": "effective_n_normal",
            "weighted_win_rate": "rate_normal",
        }
    )

    target = weighted_summary(df[df["pressure_type"] == pressure_type])
    target = target.rename(
        columns={
            "raw_n": "raw_n_pressure",
            "weighted_n": "weighted_n_pressure",
            "effective_n": "effective_n_pressure",
            "weighted_win_rate": "rate_pressure",
        }
    )

    temp = normal.merge(target, on="server", how="inner")

    temp = temp[
        (temp["effective_n_normal"] >= MIN_NORMAL_EFFECTIVE_N) &
        (temp["effective_n_pressure"] >= MIN_PRESSURE_EFFECTIVE_N[pressure_type])
    ].copy()

    temp["pressure_type"] = pressure_type

    temp["delta"] = temp["rate_pressure"] - temp["rate_normal"]
    temp["delta_pp"] = temp["delta"] * 100

    # Standard error usando effective n
    temp["se_delta"] = np.sqrt(
        (temp["rate_normal"] * (1 - temp["rate_normal"]) / temp["effective_n_normal"]) +
        (temp["rate_pressure"] * (1 - temp["rate_pressure"]) / temp["effective_n_pressure"])
    )

    temp["ci_low_pp"] = (temp["delta"] - 1.96 * temp["se_delta"]) * 100
    temp["ci_high_pp"] = (temp["delta"] + 1.96 * temp["se_delta"]) * 100

    temp["z_score"] = temp["delta"] / temp["se_delta"]
    temp["p_value"] = temp["z_score"].apply(
        lambda z: 2 * (1 - normal_cdf(abs(z)))
    )

    temp["significant_5pct"] = temp["p_value"] < 0.05

    temp = add_fdr_bh(temp, "p_value")
    temp["significant_fdr_10pct"] = temp["p_value_fdr"] < 0.10

    results.append(temp)

reliability = pd.concat(results, ignore_index=True)

# FDR globale su tutti i test
global_fdr = add_fdr_bh(reliability.copy(), "p_value")
global_fdr = global_fdr.rename(columns={"p_value_fdr": "p_value_fdr_global"})

reliability = reliability.merge(
    global_fdr[["server", "pressure_type", "p_value_fdr_global"]],
    on=["server", "pressure_type"],
    how="left",
)

reliability["significant_global_fdr_10pct"] = reliability["p_value_fdr_global"] < 0.10

# ============================================================
# Shrinkage weighted
# ============================================================

score_parts = []

for pressure_type, temp in reliability.groupby("pressure_type"):
    temp = temp.copy()

    observed_var = temp["delta"].var(ddof=1)
    noise_var = (temp["se_delta"] ** 2).mean()

    tau2 = max(observed_var - noise_var, 0.000001)

    temp["shrinkage_weight"] = tau2 / (tau2 + temp["se_delta"] ** 2)
    temp["shrunk_delta"] = temp["shrinkage_weight"] * temp["delta"]
    temp["shrunk_delta_pp"] = temp["shrunk_delta"] * 100

    temp["weighted_pressure_resilience_score"] = temp["shrunk_delta_pp"]
    temp["reliability_score"] = temp["shrinkage_weight"] * 100

    temp["tau2_pressure_type"] = tau2
    temp["observed_var_delta"] = observed_var
    temp["noise_var_delta"] = noise_var

    score_parts.append(temp)

score = pd.concat(score_parts, ignore_index=True)

reliability.to_csv(OUT_RELIABILITY, index=False)
score.to_csv(OUT_SCORE, index=False)

print("\nDataset reliability salvato in:", OUT_RELIABILITY)
print("Shape reliability:", reliability.shape)

print("\nDataset score salvato in:", OUT_SCORE)
print("Shape score:", score.shape)

print("\nMedia reliability weighted per pressure_type:")
print(
    score.groupby("pressure_type")["reliability_score"]
    .mean()
    .sort_values(ascending=False)
)

print("\nSignificativi FDR 10% dentro pressure_type:")
print(
    score.groupby("pressure_type")["significant_fdr_10pct"]
    .sum()
    .sort_values(ascending=False)
)

# ============================================================
# Score aggregato per giocatore
# ============================================================

agg = score.copy()
agg["aggregation_weight"] = agg["reliability_score"]

player_score = (
    agg.groupby("server")
    .apply(
        lambda g: pd.Series(
            {
                "n_categories": g.shape[0],
                "total_raw_pressure_points": g["raw_n_pressure"].sum(),
                "total_weighted_pressure_points": g["weighted_n_pressure"].sum(),
                "total_effective_pressure_points": g["effective_n_pressure"].sum(),
                "avg_weighted_pressure_resilience_score": np.average(
                    g["weighted_pressure_resilience_score"],
                    weights=g["aggregation_weight"],
                )
                if g["aggregation_weight"].sum() > 0
                else np.nan,
                "avg_reliability_score": g["reliability_score"].mean(),
            }
        )
    )
    .reset_index()
)

player_score = player_score.sort_values(
    "avg_weighted_pressure_resilience_score", ascending=False
)

player_score.to_csv(OUT_PLAYER, index=False)

print("\nDataset aggregato giocatore salvato in:", OUT_PLAYER)
print("Giocatori:", player_score.shape[0])

# Stable weighted leaderboard
stable = player_score[
    (player_score["n_categories"] >= 4) &
    (player_score["total_effective_pressure_points"] >= 700) &
    (player_score["avg_reliability_score"] >= 20)
].copy()

stable = stable.sort_values(
    "avg_weighted_pressure_resilience_score", ascending=False
)

stable.to_csv(OUT_STABLE, index=False)

print("\nStable weighted leaderboard salvata in:", OUT_STABLE)
print("Giocatori inclusi:", stable.shape[0])

print("\nTOP 20 stable weighted pressure resilience:")
print(
    stable[
        [
            "server",
            "n_categories",
            "total_raw_pressure_points",
            "total_effective_pressure_points",
            "avg_weighted_pressure_resilience_score",
            "avg_reliability_score",
        ]
    ]
    .head(20)
    .to_string(index=False)
)

print("\nBOTTOM 20 stable weighted pressure resilience:")
print(
    stable[
        [
            "server",
            "n_categories",
            "total_raw_pressure_points",
            "total_effective_pressure_points",
            "avg_weighted_pressure_resilience_score",
            "avg_reliability_score",
        ]
    ]
    .tail(20)
    .sort_values("avg_weighted_pressure_resilience_score")
    .to_string(index=False)
)

# Dettagli per categoria
for pressure_type in PRESSURE_TYPES:
    temp = score[score["pressure_type"] == pressure_type].copy()

    print("\n" + "=" * 60)
    print(f"{pressure_type.upper()} — TOP 10 weighted score")
    print("=" * 60)

    print(
        temp.sort_values("weighted_pressure_resilience_score", ascending=False)
        [
            [
                "server",
                "raw_n_pressure",
                "effective_n_pressure",
                "rate_normal",
                "rate_pressure",
                "delta_pp",
                "shrunk_delta_pp",
                "reliability_score",
                "p_value",
                "p_value_fdr",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    print("\n" + "=" * 60)
    print(f"{pressure_type.upper()} — BOTTOM 10 weighted score")
    print("=" * 60)

    print(
        temp.sort_values("weighted_pressure_resilience_score", ascending=True)
        [
            [
                "server",
                "raw_n_pressure",
                "effective_n_pressure",
                "rate_normal",
                "rate_pressure",
                "delta_pp",
                "shrunk_delta_pp",
                "reliability_score",
                "p_value",
                "p_value_fdr",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )