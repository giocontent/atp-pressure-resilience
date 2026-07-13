from pathlib import Path
import pandas as pd
import numpy as np

DATA_PATH = Path("data/processed/pressure_stats_reliable_atp_2020s.csv")
OUT_PATH = Path("data/processed/pressure_stats_fdr_atp_2020s.csv")

df = pd.read_csv(DATA_PATH)

# Ordina per p-value
df = df.sort_values("p_value").reset_index(drop=True)

m = len(df)
df["rank_p"] = np.arange(1, m + 1)

# Benjamini-Hochberg adjusted p-value
df["bh_value"] = df["p_value"] * m / df["rank_p"]

# Rendiamo monotona la correzione BH
df["p_value_fdr"] = df["bh_value"][::-1].cummin()[::-1]
df["p_value_fdr"] = df["p_value_fdr"].clip(upper=1)

df["significant_fdr_5pct"] = df["p_value_fdr"] < 0.05
df["significant_fdr_10pct"] = df["p_value_fdr"] < 0.10

# Ritorniamo a ordinare per delta
df = df.sort_values("pressure_delta_pp", ascending=False)

df.to_csv(OUT_PATH, index=False)

print("Dataset salvato in:", OUT_PATH)
print("Giocatori:", df.shape[0])

print("\nSignificativi senza FDR:")
print(df["significant_5pct"].value_counts())

print("\nSignificativi con FDR 5%:")
print(df["significant_fdr_5pct"].value_counts())

print("\nSignificativi con FDR 10%:")
print(df["significant_fdr_10pct"].value_counts())

print("\nTOP positivi dopo FDR 10%:")
positive = df[
    (df["pressure_delta_pp"] > 0) &
    (df["significant_fdr_10pct"])
].sort_values("pressure_delta_pp", ascending=False)

print(
    positive[
        [
            "server",
            "normal_points",
            "pressure_points",
            "pressure_delta_pp",
            "ci_low_pp",
            "ci_high_pp",
            "p_value",
            "p_value_fdr",
        ]
    ].to_string(index=False)
)

print("\nTOP negativi dopo FDR 10%:")
negative = df[
    (df["pressure_delta_pp"] < 0) &
    (df["significant_fdr_10pct"])
].sort_values("pressure_delta_pp")

print(
    negative[
        [
            "server",
            "normal_points",
            "pressure_points",
            "pressure_delta_pp",
            "ci_low_pp",
            "ci_high_pp",
            "p_value",
            "p_value_fdr",
        ]
    ].to_string(index=False)
)