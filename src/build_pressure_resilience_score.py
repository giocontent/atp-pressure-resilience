from pathlib import Path
import pandas as pd
import numpy as np

DATA_PATH = Path("data/processed/pressure_type_reliability_atp_2020s.csv")
OUT_PATH = Path("data/processed/pressure_resilience_score_atp_2020s.csv")

df = pd.read_csv(DATA_PATH)

print("Dataset:", df.shape)

# Assicuriamoci che le colonne siano numeriche
num_cols = [
    "n_normal",
    "n_pressure",
    "rate_normal",
    "rate_pressure",
    "delta",
    "delta_pp",
    "se_delta",
    "ci_low_pp",
    "ci_high_pp",
    "z_score",
    "p_value",
    "p_value_fdr",
]

for col in num_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

results = []

for pressure_type, temp in df.groupby("pressure_type"):
    temp = temp.copy()

    # Varianza osservata dei delta
    observed_var = temp["delta"].var(ddof=1)

    # Rumore medio stimato
    noise_var = (temp["se_delta"] ** 2).mean()

    # Varianza reale tra giocatori, stimata in modo semplice
    tau2 = max(observed_var - noise_var, 0.000001)

    # Shrinkage factor:
    # se l'incertezza è alta, il delta viene tirato verso zero
    temp["shrinkage_weight"] = tau2 / (tau2 + temp["se_delta"] ** 2)

    # Delta corretto/shrunk
    temp["shrunk_delta"] = temp["shrinkage_weight"] * temp["delta"]
    temp["shrunk_delta_pp"] = temp["shrunk_delta"] * 100

    # Score leggibile: positivo = meglio sotto pressione, negativo = peggio
    temp["pressure_resilience_score"] = temp["shrunk_delta_pp"]

    # Reliability: 0-100
    temp["reliability_score"] = temp["shrinkage_weight"] * 100

    # Salviamo info sulla categoria
    temp["tau2_pressure_type"] = tau2
    temp["observed_var_delta"] = observed_var
    temp["noise_var_delta"] = noise_var

    results.append(temp)

out = pd.concat(results, ignore_index=True)

# Ordine comodo
out = out.sort_values(["pressure_type", "pressure_resilience_score"], ascending=[True, False])

out.to_csv(OUT_PATH, index=False)

print("Dataset salvato in:", OUT_PATH)
print("Shape:", out.shape)

print("\nMedia reliability per pressure_type:")
print(
    out.groupby("pressure_type")["reliability_score"]
    .mean()
    .sort_values(ascending=False)
)

for pressure_type in ["break_point", "deuce", "30_30", "tiebreak"]:
    temp = out[out["pressure_type"] == pressure_type].copy()

    print("\n" + "=" * 60)
    print(f"{pressure_type.upper()} — TOP 10 Pressure Resilience Score")
    print("=" * 60)

    print(
        temp.sort_values("pressure_resilience_score", ascending=False)
        [
            [
                "server",
                "n_normal",
                "n_pressure",
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
    print(f"{pressure_type.upper()} — BOTTOM 10 Pressure Resilience Score")
    print("=" * 60)

    print(
        temp.sort_values("pressure_resilience_score", ascending=True)
        [
            [
                "server",
                "n_normal",
                "n_pressure",
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

# Score aggregato per giocatore
# Media pesata tra categorie, usando reliability_score come peso
agg = out.copy()
agg["weight"] = agg["reliability_score"]

player_score = (
    agg.groupby("server")
    .apply(
        lambda g: pd.Series(
            {
                "n_categories": g.shape[0],
                "avg_pressure_resilience_score": np.average(
                    g["pressure_resilience_score"], weights=g["weight"]
                )
                if g["weight"].sum() > 0
                else np.nan,
                "avg_reliability_score": g["reliability_score"].mean(),
                "total_pressure_points": g["n_pressure"].sum(),
            }
        )
    )
    .reset_index()
)

player_score = player_score.sort_values("avg_pressure_resilience_score", ascending=False)

PLAYER_OUT_PATH = Path("data/processed/player_pressure_resilience_score_atp_2020s.csv")
player_score.to_csv(PLAYER_OUT_PATH, index=False)

print("\nDataset aggregato giocatore salvato in:", PLAYER_OUT_PATH)

print("\nTOP 20 giocatori per score aggregato:")
print(
    player_score[
        [
            "server",
            "n_categories",
            "total_pressure_points",
            "avg_pressure_resilience_score",
            "avg_reliability_score",
        ]
    ]
    .head(20)
    .to_string(index=False)
)

print("\nBOTTOM 20 giocatori per score aggregato:")
print(
    player_score[
        [
            "server",
            "n_categories",
            "total_pressure_points",
            "avg_pressure_resilience_score",
            "avg_reliability_score",
        ]
    ]
    .tail(20)
    .sort_values("avg_pressure_resilience_score")
    .to_string(index=False)
)