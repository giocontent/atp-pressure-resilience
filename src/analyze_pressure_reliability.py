from pathlib import Path
import pandas as pd
import numpy as np
import math

DATA_PATH = Path("data/processed/pressure_stats_by_server_atp_2020s.csv")
OUT_PATH = Path("data/processed/pressure_stats_reliable_atp_2020s.csv")

df = pd.read_csv(DATA_PATH)

# Sicurezza: convertiamo in numerico
numeric_cols = [
    "normal_points",
    "pressure_points",
    "normal_serve_win_rate",
    "pressure_serve_win_rate",
    "pressure_delta_pp",
]

for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Ricostruiamo vittorie stimate
df["normal_wins"] = df["normal_points"] * df["normal_serve_win_rate"]
df["pressure_wins"] = df["pressure_points"] * df["pressure_serve_win_rate"]

p_normal = df["normal_serve_win_rate"]
p_pressure = df["pressure_serve_win_rate"]
n_normal = df["normal_points"]
n_pressure = df["pressure_points"]

# Standard error della differenza tra due proporzioni
df["se_delta"] = np.sqrt(
    (p_normal * (1 - p_normal) / n_normal) +
    (p_pressure * (1 - p_pressure) / n_pressure)
)

df["pressure_delta"] = p_pressure - p_normal
df["pressure_delta_pp"] = df["pressure_delta"] * 100

# Intervallo di confidenza 95%
df["ci_low_pp"] = (df["pressure_delta"] - 1.96 * df["se_delta"]) * 100
df["ci_high_pp"] = (df["pressure_delta"] + 1.96 * df["se_delta"]) * 100

# z-score: quanto è grande il delta rispetto al rumore
df["z_score"] = df["pressure_delta"] / df["se_delta"]

# p-value approssimato senza scipy
def normal_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

df["p_value"] = df["z_score"].apply(lambda z: 2 * (1 - normal_cdf(abs(z))))

# Segnale "statisticamente forte" in modo semplice
df["significant_5pct"] = df["p_value"] < 0.05

# Teniamo una versione ordinata
df = df.sort_values("pressure_delta_pp", ascending=False)

df.to_csv(OUT_PATH, index=False)

print("Dataset salvato in:", OUT_PATH)
print("Giocatori:", df.shape[0])

print("\nTOP 20 per delta grezzo:")
print(
    df[
        [
            "server",
            "normal_points",
            "pressure_points",
            "normal_serve_win_rate",
            "pressure_serve_win_rate",
            "pressure_delta_pp",
            "ci_low_pp",
            "ci_high_pp",
            "z_score",
            "p_value",
        ]
    ]
    .head(20)
    .to_string(index=False)
)

print("\nBOTTOM 20 per delta grezzo:")
print(
    df.sort_values("pressure_delta_pp")
    [
        [
            "server",
            "normal_points",
            "pressure_points",
            "normal_serve_win_rate",
            "pressure_serve_win_rate",
            "pressure_delta_pp",
            "ci_low_pp",
            "ci_high_pp",
            "z_score",
            "p_value",
        ]
    ]
    .head(20)
    .to_string(index=False)
)

print("\nTOP giocatori con segnale positivo più forte, ordinati per z-score:")
positive = df[df["pressure_delta_pp"] > 0].sort_values("z_score", ascending=False)

print(
    positive[
        [
            "server",
            "normal_points",
            "pressure_points",
            "pressure_delta_pp",
            "ci_low_pp",
            "ci_high_pp",
            "z_score",
            "p_value",
        ]
    ]
    .head(20)
    .to_string(index=False)
)

print("\nBOTTOM giocatori con segnale negativo più forte, ordinati per z-score:")
negative = df[df["pressure_delta_pp"] < 0].sort_values("z_score")

print(
    negative[
        [
            "server",
            "normal_points",
            "pressure_points",
            "pressure_delta_pp",
            "ci_low_pp",
            "ci_high_pp",
            "z_score",
            "p_value",
        ]
    ]
    .head(20)
    .to_string(index=False)
)

print("\nQuanti giocatori hanno effetto significativo al 5%?")
print(df["significant_5pct"].value_counts())