from pathlib import Path
import pandas as pd
import numpy as np

DATA_PATH = Path("data/processed/pressure_points_atp_2020s_v2.csv")
OUT_DIR = Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA_PATH, low_memory=False)

print("Dataset:", df.shape)
print("Colonne:", df.columns.tolist())

# Controllo veloce
print("\nPressure distribution:")
print(df["is_pressure_point"].value_counts(dropna=False))

# Assicuriamoci che siano booleani veri
df["is_pressure_point"] = df["is_pressure_point"].astype(bool)
df["server_won_point"] = df["server_won_point"].astype(bool)

# Statistiche per server e tipo di punto
stats = (
    df.groupby(["server", "is_pressure_point"])
    .agg(
        n_points=("server_won_point", "size"),
        serve_win_rate=("server_won_point", "mean"),
    )
    .reset_index()
)

# Da formato lungo a formato wide
wide = stats.pivot(
    index="server",
    columns="is_pressure_point",
    values=["n_points", "serve_win_rate"]
)

# Appiattiamo i nomi delle colonne
wide.columns = [
    "normal_points" if col == ("n_points", False) else
    "pressure_points" if col == ("n_points", True) else
    "normal_serve_win_rate" if col == ("serve_win_rate", False) else
    "pressure_serve_win_rate"
    for col in wide.columns
]

wide = wide.reset_index()

# Teniamo solo giocatori con abbastanza dati
MIN_NORMAL_POINTS = 300
MIN_PRESSURE_POINTS = 100

wide = wide[
    (wide["normal_points"] >= MIN_NORMAL_POINTS) &
    (wide["pressure_points"] >= MIN_PRESSURE_POINTS)
].copy()

# Effetto pressione
wide["pressure_delta"] = (
    wide["pressure_serve_win_rate"] - wide["normal_serve_win_rate"]
)

wide["pressure_delta_pp"] = wide["pressure_delta"] * 100

# Ordiniamo
wide = wide.sort_values("pressure_delta", ascending=False)

out_path = OUT_DIR / "pressure_stats_by_server_atp_2020s.csv"
wide.to_csv(out_path, index=False)

print("\nDataset salvato in:", out_path)
print("Giocatori inclusi:", wide.shape[0])

print("\nTOP 20: giocatori che migliorano di più al servizio sotto pressione")
print(
    wide[
        [
            "server",
            "normal_points",
            "pressure_points",
            "normal_serve_win_rate",
            "pressure_serve_win_rate",
            "pressure_delta_pp",
        ]
    ]
    .head(20)
    .to_string(index=False)
)

print("\nBOTTOM 20: giocatori che peggiorano di più al servizio sotto pressione")

bottom_20 = wide.sort_values("pressure_delta").head(20)

print(
    bottom_20[
        [
            "server",
            "normal_points",
            "pressure_points",
            "normal_serve_win_rate",
            "pressure_serve_win_rate",
            "pressure_delta_pp",
        ]
    ].to_string(index=False)
)

print("\nMedia generale filtrata:")
print(
    wide[
        [
            "normal_serve_win_rate",
            "pressure_serve_win_rate",
            "pressure_delta_pp",
        ]
    ].mean()
)