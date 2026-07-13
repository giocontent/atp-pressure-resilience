from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path("data/raw/tennis_MatchChartingProject")
OUT_DIR = Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)

points = pd.read_csv(DATA_DIR / "charting-m-points-2020s.csv", low_memory=False)

print("Points:", points.shape)
print("Colonne:", points.columns.tolist())


def parse_match_id(match_id):
    """
    match_id example:
    20260521-M-Roland_Garros-Q3-Jesper_De_Jong-Michael_Zheng
    """
    parts = str(match_id).split("-", 5)

    if len(parts) < 6:
        return {
            "date": np.nan,
            "gender": np.nan,
            "tournament": np.nan,
            "round": np.nan,
            "player1": np.nan,
            "player2": np.nan,
        }

    date, gender, tournament, round_, player1, player2 = parts

    return {
        "date": date,
        "gender": gender,
        "tournament": tournament.replace("_", " "),
        "round": round_,
        "player1": player1.replace("_", " "),
        "player2": player2.replace("_", " "),
    }


def parse_point_score(score):
    """
    Converte score tipo '15-30', '40-AD', '0-0'.
    Ritorna due numeri riferiti a Player1 e Player2.
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


def is_tiebreak_score(score):
    """
    Nei game normali lo score è 0/15/30/40/AD.
    Se troviamo score tipo 1-0, 4-3, 6-5, lo trattiamo come tiebreak.
    """
    if pd.isna(score):
        return False

    score = str(score).strip()

    if "-" not in score:
        return False

    left, right = score.split("-", 1)

    regular_scores = {"0", "15", "30", "40", "AD", "A"}

    return left not in regular_scores or right not in regular_scores


def is_deuce_score(p1, p2):
    return p1 == 3 and p2 == 3


def is_30_30_score(p1, p2):
    return p1 == 2 and p2 == 2


def is_break_point(row):
    """
    Break point:
    il returner è a un punto dal vincere il game.
    """
    if row["is_tiebreak_point"]:
        return False

    p1_score = row["p1_point_score"]
    p2_score = row["p2_point_score"]

    if pd.isna(p1_score) or pd.isna(p2_score):
        return False

    try:
        svr = int(row["Svr"])
    except Exception:
        return False

    if svr == 1:
        server_score = p1_score
        returner_score = p2_score
    elif svr == 2:
        server_score = p2_score
        returner_score = p1_score
    else:
        return False

    return returner_score >= 3 and returner_score > server_score


df = points.copy()

# Metadata dal match_id
match_meta = df[["match_id"]].drop_duplicates().copy()
meta_df = match_meta["match_id"].apply(parse_match_id).apply(pd.Series)
match_meta = pd.concat([match_meta, meta_df], axis=1)

df = df.merge(match_meta, on="match_id", how="left")

# Score del punto
df[["p1_point_score", "p2_point_score"]] = df["Pts"].apply(
    lambda x: pd.Series(parse_point_score(x))
)

# Server / returner name
df["server"] = np.where(df["Svr"].astype(str) == "1", df["player1"], df["player2"])
df["returner"] = np.where(df["Svr"].astype(str) == "1", df["player2"], df["player1"])

# Target: il server ha vinto il punto?
df["server_won_point"] = (
    df["PtWinner"].astype(str).str.strip() == df["Svr"].astype(str).str.strip()
)

# Pressure flags
df["is_tiebreak_point"] = df["Pts"].apply(is_tiebreak_score)

df["is_deuce"] = [
    is_deuce_score(a, b) for a, b in zip(df["p1_point_score"], df["p2_point_score"])
]

df["is_30_30"] = [
    is_30_30_score(a, b) for a, b in zip(df["p1_point_score"], df["p2_point_score"])
]

df["is_break_point"] = df.apply(is_break_point, axis=1)

df["is_pressure_point"] = (
    df["is_break_point"]
    | df["is_deuce"]
    | df["is_30_30"]
    | df["is_tiebreak_point"]
)

cols_to_keep = [
    "match_id",
    "date",
    "tournament",
    "round",
    "player1",
    "player2",
    "server",
    "returner",
    "Pt",
    "Set1",
    "Set2",
    "Gm1",
    "Gm2",
    "Pts",
    "Svr",
    "PtWinner",
    "server_won_point",
    "1st",
    "2nd",
    "Notes",
    "p1_point_score",
    "p2_point_score",
    "is_deuce",
    "is_30_30",
    "is_break_point",
    "is_tiebreak_point",
    "is_pressure_point",
]

pressure_df = df[cols_to_keep].copy()

out_path = OUT_DIR / "pressure_points_atp_2020s_v2.csv"
pressure_df.to_csv(out_path, index=False)

print("\nDataset salvato in:", out_path)
print("Shape:", pressure_df.shape)

print("\nPressure points:")
print(pressure_df["is_pressure_point"].value_counts(dropna=False))

print("\nBreak points:")
print(pressure_df["is_break_point"].value_counts(dropna=False))

print("\nTiebreak points:")
print(pressure_df["is_tiebreak_point"].value_counts(dropna=False))

print("\nServer won point:")
print(pressure_df["server_won_point"].value_counts(dropna=False))

print("\nServe win rate normale vs pressure:")
print(
    pressure_df.groupby("is_pressure_point")["server_won_point"]
    .mean()
    .rename("server_win_rate")
)

print("\nPrime righe:")
print(pressure_df.head())
