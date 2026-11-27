"""Figures for the IEEE paper, built only from saved Restart 9 results (no refitting)."""
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "restart9_0/results"
OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({"font.family": "serif", "font.size": 7.5, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
                     "hatch.linewidth": 0.6, "pdf.fonttype": 42})


def chicago_performance():
    m = pd.read_csv(RES / "metrics.csv")
    s = pd.read_csv(RES / "weightage/results_by_seed.csv")
    s2 = s[s.step.str.startswith("2")].groupby("model")[["ap", "roc_auc"]].mean()
    designs = ["NYC only", "NYC + 10%\nChicago 2024", "NYC + all\nChicago 2024"]
    models = [("LR-M0", "Logistic, past crime (baseline)", "Logistic past crime only (baseline)", BLUE, ""),
              ("LGBM-M0", "LightGBM, past crime", "LightGBM past crime only", ORANGE, "////"),
              ("LGBM-M9", "LightGBM, past crime + attributes", "LightGBM + attributes", AQUA, "....")]
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.3), sharey=False)
    for ax, metric, title in zip(axes, ("ap", "roc_auc"), ("Average precision", "ROC-AUC")):
        x = np.arange(len(designs))
        w = 0.26
        for j, (code, label, seedname, color, hatch) in enumerate(models):
            vals = [m[(m.design == "D1") & (m.target == "Chicago") & (m.outcome == "O1") & (m.model == code)][metric].iloc[0],
                    s2.loc[seedname, metric],
                    m[(m.design == "D2") & (m.target == "Chicago") & (m.outcome == "O1") & (m.model == code)][metric].iloc[0]]
            xs = x + (j - 1) * w
            ax.plot(xs, vals, linestyle="none", marker=("o", "s", "D")[j], markersize=6, color=color,
                    markeredgecolor="white", markeredgewidth=1.2, label=label)
            for xx, v in zip(xs, vals):
                ax.text(xx, v + 0.006, f"{v:.3f}", ha="center", va="bottom", fontsize=5.8, color=INK)
        ax.set_xticks(x, designs)
        ax.set_ylim(0.70, 0.82)
        ax.set_xlim(-0.5, len(designs) - 0.5)
        ax.set_title(title, fontsize=8, color=INK, loc="left")
        ax.yaxis.grid(True, color=GRID, linewidth=0.5)
        ax.set_axisbelow(True)
        ax.tick_params(length=0)
    axes[0].set_ylabel("Chicago 2025 score")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.04))
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(OUT / "chicago_performance.pdf", bbox_inches="tight")


def weightage():
    w1 = pd.read_csv(RES / "weightage/step1_weightage_nyc_only.csv")
    w2 = pd.read_csv(RES / "weightage/step2_weightage_nyc_plus_10pct_chicago.csv")[["feature", "gain_pct"]].rename(columns={"gain_pct": "g2"})
    w = w1.merge(w2, on="feature").sort_values("gain_pct")
    w = w[(w.gain_pct > 0.05) | (w.g2 > 0.05)]
    y = np.arange(len(w))
    h = 0.38
    fig, ax = plt.subplots(figsize=(3.45, 3.0))
    ax.barh(y + h / 2, w.gain_pct, h - 0.04, color=BLUE, edgecolor="white", linewidth=0.5, label="NYC only")
    ax.barh(y - h / 2, w.g2, h - 0.04, color=ORANGE, hatch="////", edgecolor="white", linewidth=0.5, label="NYC + 10% Chicago")
    for yy, a, b in zip(y, w.gain_pct, w.g2):
        ax.text(max(a, b) + 0.6, yy, f"{a:.1f} / {b:.1f}", va="center", fontsize=5.6, color=MUTED)
    ax.set_yticks(y, w.attribute, fontsize=6.3)
    ax.set_xlabel("Share of LightGBM total gain (%)")
    ax.set_xlim(0, 34)
    ax.xaxis.grid(True, color=GRID, linewidth=0.5)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    ax.legend(loc="lower center", bbox_to_anchor=(0.35, 1.0), ncol=2, frameon=False, fontsize=6.3)
    fig.tight_layout()
    fig.savefig(OUT / "weightage.pdf", bbox_inches="tight")


if __name__ == "__main__":
    chicago_performance()
    weightage()
    print("figures written to", OUT)
