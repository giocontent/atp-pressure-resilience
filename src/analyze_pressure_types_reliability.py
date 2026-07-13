from pathlib import Path
import pandas as pd
import numpy as np
import math

DATA_PATH = Path("data/processed/pressure_points_atp_2020s_v3.csv")
OUT_PATH = Path("data/processed/pressure_type_reliability_atp_2020s.csv")

df = pd.read_csv(DATA_PATH, low_memory=False)

# Booleani puliti
df["server_won_point"] = df["server_won_point"].astype(str).str.lower().map(
    {"true": True, "false": False}
)

print("Dataset:", df.shape)

# Tipi da confrontare con normal
PRESSURE_TYPES = ["break_point", "deuce", "30_30", "tiebreak"]

MIN_NORMAL_POINTS = 500
MIN_PRESSURE_POINTS = {
    "break_point": 100,
    "deuce": 100,
    "30_30": 80,
    "tiebreak": 80,
}


def normal_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def add_fdr_bh(temp, p_col="p_value"):
    """
    Benjamini-Hochberg FDR correction.
    """
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
    print(f"\nAnalizzo: {pressure_type}")

    # Dati normal
    normal = (
        df[df["pressure_type"] == "normal"]
        .groupby("server")
        .agg(
            n_normal=("server_won_point", "size"),
            wins_normal=("server_won_point", "sum"),
            rate_normal=("server_won_point", "mean"),
        )
        .reset_index()
    )

    # Dati pressure type specifico
    target = (
        df[df["pressure_type"] == pressure_type]
        .groupby("server")
        .agg(
            n_pressure=("server_won_point", "size"),
            wins_pressure=("server_won_point", "sum"),
            rate_pressure=("server_won_point", "mean"),
        )
        .reset_index()
    )

    temp = normal.merge(target, on="server", how="inner")

    # Filtri minimi
    temp = temp[
        (temp["n_normal"] >= MIN_NORMAL_POINTS) &
        (temp["n_pressure"] >= MIN_PRESSURE_POINTS[pressure_type])
    ].copy()

    temp["pressure_type"] = pressure_type

    # Delta
    temp["delta"] = temp["rate_pressure"] - temp["rate_normal"]
    temp["delta_pp"] = temp["delta"] * 100

    # Standard error differenza tra proporzioni
    temp["se_delta"] = np.sqrt(
        (temp["rate_normal"] * (1 - temp["rate_normal"]) / temp["n_normal"]) +
        (temp["rate_pressure"] * (1 - temp["rate_pressure"]) / temp["n_pressure"])
    )

    temp["ci_low_pp"] = (temp["delta"] - 1.96 * temp["se_delta"]) * 100
    temp["ci_high_pp"] = (temp["delta"] + 1.96 * temp["se_delta"]) * 100

    temp["z_score"] = temp["delta"] / temp["se_delta"]
    temp["p_value"] = temp["z_score"].apply(
        lambda z: 2 * (1 - normal_cdf(abs(z)))
    )

    temp["significant_5pct"] = temp["p_value"] < 0.05

    # FDR dentro ciascun pressure_type
    temp = add_fdr_bh(temp, "p_value")
    temp["significant_fdr_5pct"] = temp["p_value_fdr"] < 0.05
    temp["significant_fdr_10pct"] = temp["p_value_fdr"] < 0.10

    results.append(temp)

all_results = pd.concat(results, ignore_index=True)

# FDR globale su tutti i test insieme
global_fdr = add_fdr_bh(all_results.copy(), "p_value")
global_fdr = global_fdr.rename(columns={"p_value_fdr": "p_value_fdr_global"})

all_results = all_results.merge(
    global_fdr[["server", "pressure_type", "p_value_fdr_global"]],
    on=["server", "pressure_type"],
    how="left"
)

all_results["significant_global_fdr_10pct"] = all_results["p_value_fdr_global"] < 0.10

# Ordine leggibile
all_results = all_results.sort_values(
    ["pressure_type", "delta_pp"],
    ascending=[True, False]
)

all_results.to_csv(OUT_PATH, index=False)

print("\nDataset salvato in:", OUT_PATH)
print("Shape:", all_results.shape)

print("\nNumero test per pressure_type:")
print(all_results["pressure_type"].value_counts())

print("\nSignificativi nominali 5% per pressure_type:")
print(
    all_results.groupby("pressure_type")["significant_5pct"]
    .sum()
    .sort_values(ascending=False)
)

print("\nSignificativi FDR 10% dentro pressure_type:")
print(
    all_results.groupby("pressure_type")["significant_fdr_10pct"]
    .sum()
    .sort_values(ascending=False)
)

print("\nSignificativi FDR globale 10%:")
print(all_results["significant_global_fdr_10pct"].value_counts())

# Stampa risultati forti per ogni tipo
for pressure_type in PRESSURE_TYPES:
    temp = all_results[all_results["pressure_type"] == pressure_type].copy()

    print(f"\n==============================")
    print(f"{pressure_type.upper()} — TOP positivi per z-score")
    print("==============================")

    positive = temp[temp["delta_pp"] > 0].sort_values("z_score", ascending=False)

    print(
        positive[
            [
                "server",
                "n_normal",
                "n_pressure",
                "rate_normal",
                "rate_pressure",
                "delta_pp",
                "ci_low_pp",
                "ci_high_pp",
                "z_score",
                "p_value",
                "p_value_fdr",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    print(f"\n{pressure_type.upper()} — TOP negativi per z-score")
    print("==============================")

    negative = temp[temp["delta_pp"] < 0].sort_values("z_score")

    print(
        negative[
            [
                "server",
                "n_normal",
                "n_pressure",
                "rate_normal",
                "rate_pressure",
                "delta_pp",
                "ci_low_pp",
                "ci_high_pp",
                "z_score",
                "p_value",
                "p_value_fdr",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

print("\nRisultati che sopravvivono a FDR 10% dentro il loro pressure_type:")
strong = all_results[all_results["significant_fdr_10pct"]].sort_values("p_value_fdr")

if len(strong) == 0:
    print("Nessun risultato sopravvive a FDR 10% dentro pressure_type.")
else:
    print(
        strong[
            [
                "server",
                "pressure_type",
                "n_normal",
                "n_pressure",
                "delta_pp",
                "ci_low_pp",
                "ci_high_pp",
                "p_value",
                "p_value_fdr",
            ]
        ].to_string(index=False)
    )