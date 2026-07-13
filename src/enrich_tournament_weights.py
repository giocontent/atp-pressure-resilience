from pathlib import Path
import pandas as pd
import re

DATA_PATH = Path("data/processed/pressure_points_atp_2020s_v3.csv")
OUT_PATH = Path("data/processed/pressure_points_atp_2020s_v4_weighted.csv")

df = pd.read_csv(DATA_PATH, low_memory=False)

print("Dataset:", df.shape)


def normalize_text(x):
    if pd.isna(x):
        return ""
    return str(x).lower().replace("_", " ").strip()


def classify_tournament(tournament):
    t = normalize_text(tournament)

    # Grand Slam
    slam_patterns = [
        "australian open",
        "roland garros",
        "wimbledon",
        "us open",
    ]

    if any(p in t for p in slam_patterns):
        return "grand_slam"

    # Olympics
    if "olympics" in t:
        return "olympics"

    # ATP Finals
    finals_patterns = [
        "tour finals",
        "atp finals",
    ]

    if any(p in t for p in finals_patterns):
        return "atp_finals"

    # Next Gen Finals
    if "nextgen finals" in t or "next gen finals" in t:
        return "next_gen_finals"

    # Davis Cup
    if "davis cup finals" in t:
        return "davis_cup_finals"

    if "davis cup qualifiers" in t or "davis cup" in t:
        return "davis_cup"

    # Team competitions
    if "united cup" in t or "atp cup" in t:
        return "team_cup"

    # Masters 1000
    masters_patterns = [
        "indian wells",
        "miami",
        "monte carlo",
        "madrid",
        "rome",
        "canada masters",
        "toronto",
        "montreal",
        "cincinnati",
        "shanghai",
        "paris masters",
    ]

    if any(p in t for p in masters_patterns):
        return "masters_1000"

    # ATP 500
    atp_500_patterns = [
        "rotterdam",
        "rio de janeiro",
        "dubai",
        "acapulco",
        "barcelona",
        "halle",
        "queens",
        "hamburg",
        "washington",
        "beijing",
        "tokyo",
        "basel",
        "vienna",
    ]

    if any(p in t for p in atp_500_patterns):
        return "atp_500"

    # Challenger
    # Esempi nel dataset: "Wuning CH", "Sao Paulo CH"
    if "challenger" in t or t.endswith(" ch") or " ch " in t:
        return "challenger"

    # ATP 250 / regular tour events
    atp_250_patterns = [
        "doha",
        "stuttgart",
        "brisbane",
        "montpellier",
        "buenos aires",
        "adelaide",
        "gstaad",
        "marseille",
        "s hertogenbosch",
        "estoril",
        "auckland",
        "antwerp",
        "astana",
        "eastbourne",
        "newport",
        "hong kong",
        "bastad",
        "stockholm",
        "dallas",
        "metz",
        "munich",
        "santiago",
        "geneva",
        "winston salem",
        "bucharest",
        "cordoba",
        "mallorca",
        "los cabos",
        "kitzbuhel",
        "atlanta",
        "delray beach",
        "pune",
        "sofia",
        "marrakech",
        "umag",
        "belgrade",
        "houston",
    ]

    if any(p in t for p in atp_250_patterns):
        return "atp_250"

    return "other"


def tournament_weight(level):
    weights = {
        "grand_slam": 2.00,
        "olympics": 1.80,
        "atp_finals": 1.80,
        "masters_1000": 1.50,
        "davis_cup_finals": 1.45,
        "davis_cup": 1.20,
        "atp_500": 1.25,
        "team_cup": 1.15,
        "next_gen_finals": 1.10,
        "atp_250": 1.00,
        "other": 1.00,
        "challenger": 0.65,
    }

    return weights.get(level, 1.00)


def round_weight(round_name):
    r = normalize_text(round_name).upper()

    # Finale
    if r == "F":
        return 1.30

    # Semifinale
    if r == "SF":
        return 1.20

    # Quarti
    if r == "QF":
        return 1.10

    # Ottavi
    if r in ["R16", "R4"]:
        return 1.05

    # Qualificazioni
    if r in ["Q1", "Q2", "Q3"]:
        return 0.85

    # Tutti gli altri round
    return 1.00


df["tournament_level"] = df["tournament"].apply(classify_tournament)
df["tournament_weight"] = df["tournament_level"].apply(tournament_weight)
df["round_weight"] = df["round"].apply(round_weight)

df["point_weight"] = df["tournament_weight"] * df["round_weight"]

df.to_csv(OUT_PATH, index=False)

print("\nDataset salvato in:", OUT_PATH)
print("Shape:", df.shape)

print("\nDistribuzione tournament_level:")
print(df["tournament_level"].value_counts())

print("\nPeso medio per tournament_level:")
print(
    df.groupby("tournament_level")["point_weight"]
    .agg(["count", "mean", "min", "max"])
    .sort_values("mean", ascending=False)
)

print("\nPrime 40 combinazioni torneo/livello:")
print(
    df[["tournament", "tournament_level", "round", "point_weight"]]
    .drop_duplicates()
    .head(40)
    .to_string(index=False)
)

print("\nTop tornei classificati come other, da controllare:")
other_tournaments = (
    df[df["tournament_level"] == "other"]["tournament"]
    .value_counts()
    .head(50)
)

print(other_tournaments)