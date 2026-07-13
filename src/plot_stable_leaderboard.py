from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

DATA_PATH = Path("data/processed/stable_pressure_leaderboard_atp_2020s.csv")
FIG_DIR = Path("reports/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA_PATH)

# Prendiamo top e bottom
top = df.sort_values("avg_pressure_resilience_score", ascending=False).head(12)
bottom = df.sort_values("avg_pressure_resilience_score", ascending=True).head(12)

plot_df = pd.concat([bottom, top], axis=0)
plot_df = plot_df.drop_duplicates(subset=["server"])
plot_df = plot_df.sort_values("avg_pressure_resilience_score")

plt.figure(figsize=(10, 9))

plt.barh(
    plot_df["server"],
    plot_df["avg_pressure_resilience_score"]
)

plt.axvline(0, linestyle="--", linewidth=1)

plt.xlabel("Pressure Resilience Score")
plt.ylabel("Player")
plt.title("Stable Pressure Resilience Leaderboard — ATP 2020s")

plt.tight_layout()

out_path = FIG_DIR / "stable_pressure_leaderboard.png"
plt.savefig(out_path, dpi=300)
plt.close()

print("Figura salvata in:", out_path)