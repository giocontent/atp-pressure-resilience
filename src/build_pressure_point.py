from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path("data/raw/tennis_MatchChartingProject")
OUT_DIR = Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)

matches = pd.read_csv(DATA_DIR / "charting-m-matches.csv")
points = pd.read_csv(DATA_DIR / "charting-m-points-2020s.csv", low_memory=False)

print("Matches:", matches.shape)
print("Points:", points.shape)

print("\nColonne disponibili:")
print(points.columns.tolist())


def parse_point_score(score):
    """
    Converte score tipo '15-30', '40-AD', '0-0' in due valori.
    Ritorna None se lo score è mancante o strano.
    """
    if pd.isna(score):
        return None, None

    score = str(score).strip()

    if "-" not in score:
        return None, None

    left, right = score.split("-", 1)

    mapping = {
        "0": 0,
        "15": 1,
        "30": 2,
        "40": 3,
        "AD": 4,
        "A": 4,
    }

    return mapping.get(left), mapping.get(right)


def is_deuce_score(p1, p2):
    return p1 == 3 and p2 == 3


def is_30_30_score(p1, p2):
    return p1 == 2 and p2 == 2


def is_break_point(row):
    """
    Break point semplice:
    il returner è a un punto dal vincere il game.
    Usiamo Svr per capire chi serve.
    Svr = 1 significa player 1 al servizio.
    Svr = 2 significa player 2 al servizio.
    """
    p1_score, p2_score = parse_point_score(row.get("Pts"))

    if p1_score is None or p2_score is None:
        return False

    svr = row.get("Svr")

    try:
        svr = int(svr)
    except Exception:
        return False

    # Escludiamo tie-break per ora
    if "TB?" in row and row.get("TB?") == 1:
        return False

    # Se serve player 1, il returner è player 2
    if svr == 1:
        server_score = p1_score
        returner_score = p2_score
    # Se serve player 2, il returner è player 1
    elif svr == 2:
        server_score = p2_score
        returner_score = p1_score
    else:
        return False

    # Il returner ha almeno 40/AD e il server è dietro
    return returner_score >= 3 and returner_score > server_score


def classify_pressure(row):
    p1_score, p2_score = parse_point_score(row.get("Pts"))

    is_deuce = is_deuce_score(p1_score, p2_score)
    is_30_30 = is_30_30_score(p1_score, p2_score)
    bp = is_break_point(row)

    tb = False
    if "TB?" in row:
        tb = row.get("TB?") == 1

    return bp or is_deuce or is_30_30 or tb


# Copia base
df = points.copy()

# Indicatori base
df["p1_point_score"], df["p2_point_score"] = zip(*df["Pts"].apply(parse_point_score))

df["is_deuce"] = [
    is_deuce_score(a, b) for a, b in zip(df["p1_point_score"], df["p2_point_score"])
]

df["is_30_30"] = [
    is_30_30_score(a, b) for a, b in zip(df["p1_point_score"], df["p2_point_score"])
]

df["is_break_point"] = df.apply(is_break_point, axis=1)
df["is_pressure_point"] = df.apply(classify_pressure, axis=1)

# Variabile target base: il server ha vinto il punto?
if "isSvrWinner" in df.columns:
    df["server_won_point"] = df["isSvrWinner"]
else:
    df["server_won_point"] = np.nan

# Teniamo solo alcune colonne utili per iniziare
cols_to_keep = [
    "match_id",
    "Pt",
    "Set1",
    "Set2",
    "Gm1",
    "Gm2",
    "Pts",
    "Svr",
    "Serving",
    "PtWinner",
    "isSvrWinner",
    "server_won_point",
    "rallyCount",
    "p1_point_score",
    "p2_point_score",
    "is_deuce",
    "is_30_30",
    "is_break_point",
    "is_pressure_point",
]

existing_cols = [c for c in cols_to_keep if c in df.columns]
pressure_df = df[existing_cols].copy()

out_path = OUT_DIR / "pressure_points_atp_2020s.csv"
pressure_df.to_csv(out_path, index=False)

print("\nDataset salvato in:", out_path)
print("Shape:", pressure_df.shape)

print("\nDistribuzione pressure point:")
print(pressure_df["is_pressure_point"].value_counts(dropna=False))

print("\nBreak point:")
print(pressure_df["is_break_point"].value_counts(dropna=False))

print("\nPrime righe:")
print(pressure_df.head())