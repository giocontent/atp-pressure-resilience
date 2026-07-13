from pathlib import Path
import pandas as pd
import numpy as np

POINTS_PATH = Path("data/processed/pressure_points_atp_2020s_v5_stakes.csv")
MATCHES_PATH = Path("data/raw/tennis_MatchChartingProject/charting-m-matches.csv")
OUT_PATH = Path("data/processed/pressure_points_atp_2020s_v6_surface.csv")

points = pd.read_csv(POINTS_PATH, low_memory=False)
matches = pd.read_csv(MATCHES_PATH, low_memory=False)

print("Points:", points.shape)
print("Matches:", matches.shape)

surface_col = "Surface"

if surface_col not in matches.columns:
    raise ValueError("Colonna Surface non trovata in charting-m-matches.csv")


def normalize_surface(x):
    if pd.isna(x):
        return "unknown"

    s = str(x).strip().lower()

    if s in ["hard", "outdoor hard", "hardcourt", "hard court"]:
        return "hard"

    if s in ["indoor hard", "indoor"]:
        return "indoor_hard"

    if s in ["clay", "red clay", "green clay"]:
        return "clay"

    if s == "grass":
        return "grass"

    if s == "carpet":
        return "carpet"

    return "unknown"


def surface_group(surface):
    if surface in ["hard", "indoor_hard", "clay", "grass", "carpet"]:
        return surface
    return "other"


# ============================================================
# 1. Costruisci tabella superficie pulita
# ============================================================

matches_surface_raw = matches[["match_id", surface_col]].copy()
matches_surface_raw = matches_surface_raw.rename(columns={surface_col: "surface_raw"})

matches_surface_raw["surface"] = matches_surface_raw["surface_raw"].apply(normalize_surface)
matches_surface_raw["surface_group"] = matches_surface_raw["surface"].apply(surface_group)

print("\nDistribuzione surface grezza normalizzata:")
print(matches_surface_raw["surface"].value_counts(dropna=False))

print("\nRighe con superficie non riconosciuta:")
print(
    matches_surface_raw[matches_surface_raw["surface"] == "unknown"]
    [["match_id", "surface_raw"]]
    .head(20)
    .to_string(index=False)
)


# ============================================================
# 2. Risolvi duplicati: una sola riga per match_id
# ============================================================

def resolve_one_surface(group):
    """
    Se un match_id ha più righe:
    - preferisce superfici valide: hard/clay/grass/indoor_hard/carpet
    - se ce ne sono più di una, prende la più frequente
    - se non esiste superficie valida, assegna unknown
    """
    valid = group[group["surface"] != "unknown"]

    if len(valid) > 0:
        chosen_surface = valid["surface"].mode().iloc[0]
        chosen_raw = valid.loc[valid["surface"] == chosen_surface, "surface_raw"].iloc[0]
    else:
        chosen_surface = "unknown"
        chosen_raw = group["surface_raw"].iloc[0]

    return pd.Series(
        {
            "surface_raw": chosen_raw,
            "surface": chosen_surface,
            "surface_group": surface_group(chosen_surface),
        }
    )


matches_surface = (
    matches_surface_raw
    .groupby("match_id", as_index=False)
    .apply(resolve_one_surface, include_groups=False)
    .reset_index(drop=True)
)

print("\nMatches surface pulito:", matches_surface.shape)

print("\nControllo duplicati match_id dopo pulizia:")
print(matches_surface["match_id"].duplicated().sum())

print("\nDistribuzione surface_group nel file matches pulito:")
print(matches_surface["surface_group"].value_counts(dropna=False))


# ============================================================
# 3. Merge many-to-one controllato
# ============================================================

df = points.merge(
    matches_surface,
    on="match_id",
    how="left",
    validate="many_to_one",
)

df["surface_raw"] = df["surface_raw"].fillna("unknown")
df["surface"] = df["surface"].fillna("unknown")
df["surface_group"] = df["surface_group"].fillna("other")

print("\nShape dopo merge:", df.shape)

if df.shape[0] != points.shape[0]:
    raise ValueError(
        f"Errore: il merge ha cambiato il numero di righe. "
        f"Prima {points.shape[0]}, dopo {df.shape[0]}"
    )

df.to_csv(OUT_PATH, index=False)

print("\nDataset salvato in:", OUT_PATH)
print("Shape:", df.shape)

print("\nDistribuzione punti per surface_group:")
print(df["surface_group"].value_counts(dropna=False))

print("\nDistribuzione punti per surface:")
print(df["surface"].value_counts(dropna=False))


# ============================================================
# 4. Analisi rapida: weighted serve win rate per superficie
# ============================================================

df["server_won_point_num"] = (
    df["server_won_point"]
    .astype(str)
    .str.lower()
    .map({"true": 1, "false": 0})
)

df["point_weight"] = pd.to_numeric(df["point_weight"], errors="coerce")

df = df.dropna(subset=["server_won_point_num", "point_weight"])

df["weighted_win"] = df["server_won_point_num"] * df["point_weight"]

surface_summary = (
    df.groupby("surface_group")
    .agg(
        raw_points=("server_won_point_num", "size"),
        weighted_points=("point_weight", "sum"),
        weighted_wins=("weighted_win", "sum"),
        avg_point_weight=("point_weight", "mean"),
    )
    .reset_index()
)

surface_summary["weighted_server_win_rate"] = (
    surface_summary["weighted_wins"] / surface_summary["weighted_points"]
)

surface_summary = surface_summary.sort_values(
    "weighted_server_win_rate",
    ascending=False,
)

print("\nWeighted serve win rate by surface_group:")
print(
    surface_summary[
        [
            "surface_group",
            "raw_points",
            "weighted_server_win_rate",
            "avg_point_weight",
        ]
    ].to_string(index=False)
)


# ============================================================
# 5. Pressure type x surface
# ============================================================

pressure_surface = (
    df.groupby(["surface_group", "pressure_type"])
    .agg(
        raw_points=("server_won_point_num", "size"),
        weighted_points=("point_weight", "sum"),
        weighted_wins=("weighted_win", "sum"),
    )
    .reset_index()
)

pressure_surface["weighted_server_win_rate"] = (
    pressure_surface["weighted_wins"] / pressure_surface["weighted_points"]
)

print("\nWeighted serve win rate by surface_group and pressure_type:")
print(
    pressure_surface.sort_values(["surface_group", "pressure_type"])
    [
        [
            "surface_group",
            "pressure_type",
            "raw_points",
            "weighted_server_win_rate",
        ]
    ].to_string(index=False)
)