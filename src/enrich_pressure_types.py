from pathlib import Path
import pandas as pd
import numpy as np

DATA_PATH = Path("data/processed/pressure_points_atp_2020s_v2.csv")
OUT_PATH = Path("data/processed/pressure_points_atp_2020s_v3.csv")

df = pd.read_csv(DATA_PATH, low_memory=False)

print("Dataset iniziale:", df.shape)

# Convertiamo booleani letti da CSV
bool_cols = [
    "server_won_point",
    "is_deuce",
    "is_30_30",
    "is_break_point",
    "is_tiebreak_point",
    "is_pressure_point",
]

for col in bool_cols:
    df[col] = df[col].astype(str).str.lower().map({"true": True, "false": False})

# Tipo di pressione
# Priorità: break point > tiebreak > deuce > 30-30 > normal
conditions = [
    df["is_break_point"],
    df["is_tiebreak_point"],
    df["is_deuce"],
    df["is_30_30"],
]

choices = [
    "break_point",
    "tiebreak",
    "deuce",
    "30_30",
]

df["pressure_type"] = np.select(conditions, choices, default="normal")

# Una versione numerica semplice, utile dopo per modelli
pressure_order = {
    "normal": 0,
    "30_30": 1,
    "deuce": 2,
    "tiebreak": 2,
    "break_point": 3,
}

df["pressure_level"] = df["pressure_type"].map(pressure_order)

df.to_csv(OUT_PATH, index=False)

print("Dataset salvato in:", OUT_PATH)
print("Shape:", df.shape)

print("\nDistribuzione pressure_type:")
print(df["pressure_type"].value_counts())

print("\nServe win rate per pressure_type:")
summary = (
    df.groupby("pressure_type")
    .agg(
        n_points=("server_won_point", "size"),
        server_win_rate=("server_won_point", "mean"),
    )
    .sort_values("server_win_rate", ascending=False)
)

print(summary)