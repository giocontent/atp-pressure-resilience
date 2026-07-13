from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

DATA_PATH = Path("data/processed/pressure_stats_fdr_atp_2020s.csv")
FIG_DIR = Path("reports/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA_PATH)

# Teniamo solo giocatori con abbastanza punti pressure
df = df.copy()

# Ordiniamo per effetto
top_positive = df.sort_values("pressure_delta_pp", ascending=False).head(15)
top_negative = df.sort_values("pressure_delta_pp", ascending=True).head(15)

plot_df = pd.concat([top_positive, top_negative], axis=0)
plot_df = plot_df.sort_values("pressure_delta_pp")

# Error bars asimmetriche
x = plot_df["pressure_delta_pp"]
xerr_low = x - plot_df["ci_low_pp"]
xerr_high = plot_df["ci_high_pp"] - x

plt.figure(figsize=(10, 9))

plt.errorbar(
    x=plot_df["pressure_delta_pp"],
    y=plot_df["server"],
    xerr=[xerr_low, xerr_high],
    fmt="o",
    capsize=3,
)

plt.axvline(0, linestyle="--", linewidth=1)

plt.xlabel("Pressure effect on serve win rate (percentage points)")
plt.ylabel("Player")
plt.title("Serve performance under pressure — ATP 2020s")

plt.tight_layout()

out_path = FIG_DIR / "pressure_effects_top_bottom.png"
plt.savefig(out_path, dpi=300)
plt.close()

print("Figura salvata in:", out_path)

# Figura solo giocatori significativi prima della FDR
sig = df[df["significant_5pct"] == True].copy()
sig = sig.sort_values("pressure_delta_pp")

if len(sig) > 0:
    x = sig["pressure_delta_pp"]
    xerr_low = x - sig["ci_low_pp"]
    xerr_high = sig["ci_high_pp"] - x

    plt.figure(figsize=(10, 6))

    plt.errorbar(
        x=sig["pressure_delta_pp"],
        y=sig["server"],
        xerr=[xerr_low, xerr_high],
        fmt="o",
        capsize=3,
    )

    plt.axvline(0, linestyle="--", linewidth=1)

    plt.xlabel("Pressure effect on serve win rate (percentage points)")
    plt.ylabel("Player")
    plt.title("Players with nominally significant pressure effect")

    plt.tight_layout()

    out_path = FIG_DIR / "pressure_effects_significant_nominal.png"
    plt.savefig(out_path, dpi=300)
    plt.close()

    print("Figura salvata in:", out_path)

# Figura FDR
sig_fdr = df[df["significant_fdr_10pct"] == True].copy()
sig_fdr = sig_fdr.sort_values("pressure_delta_pp")

if len(sig_fdr) > 0:
    x = sig_fdr["pressure_delta_pp"]
    xerr_low = x - sig_fdr["ci_low_pp"]
    xerr_high = sig_fdr["ci_high_pp"] - x

    plt.figure(figsize=(8, 3))

    plt.errorbar(
        x=sig_fdr["pressure_delta_pp"],
        y=sig_fdr["server"],
        xerr=[xerr_low, xerr_high],
        fmt="o",
        capsize=3,
    )

    plt.axvline(0, linestyle="--", linewidth=1)

    plt.xlabel("Pressure effect on serve win rate (percentage points)")
    plt.ylabel("Player")
    plt.title("Pressure effects surviving FDR correction")

    plt.tight_layout()

    out_path = FIG_DIR / "pressure_effects_fdr.png"
    plt.savefig(out_path, dpi=300)
    plt.close()

    print("Figura salvata in:", out_path)