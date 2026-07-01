"""Generate the IQ normal-distribution figure shown on the "Before you begin" page.

The plot spans exactly 60-140 on the x-axis and the data area fills the full
width of the image, so a 60-140 HTML range slider placed directly beneath it
lines up with the curve. Run after changing the styling:

    python tools/build_iq_distribution_plot.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "social_media" / "static" / "images" / "iq_distribution.png"

MEAN, SD = 100.0, 15.0
XMIN, XMAX = 60.0, 140.0
BLUE = "#004488"

# Band edges (in SD units from the mean): tails, ±1-2 SD, ±1 SD.
EDGES = [60, 70, 85, 100, 115, 130, 140]
# Percentage of the distribution in each band and the alpha used to shade it.
BAND_PCT = ["2%", "14%", "34%", "34%", "14%", "2%"]
BAND_ALPHA = [0.15, 0.28, 0.45, 0.45, 0.28, 0.15]


def normal_pdf(x):
    return np.exp(-0.5 * ((x - MEAN) / SD) ** 2) / (SD * np.sqrt(2 * np.pi))


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)

    x = np.linspace(XMIN, XMAX, 1000)
    y = normal_pdf(x)

    fig, ax = plt.subplots(figsize=(8.4, 2.7), dpi=150)
    # Data area fills the full width so the HTML slider lines up with the curve.
    fig.subplots_adjust(left=0.0, right=1.0, top=0.99, bottom=0.20)

    ax.plot(x, y, color=BLUE, linewidth=2)

    ymax = float(y.max())
    for i in range(len(EDGES) - 1):
        lo, hi = EDGES[i], EDGES[i + 1]
        mask = (x >= lo) & (x <= hi)
        ax.fill_between(x[mask], 0, y[mask], color=BLUE, alpha=BAND_ALPHA[i], linewidth=0)
        # Light separators between bands.
        if i > 0:
            ax.axvline(lo, color="#ffffff", linewidth=1.0, alpha=0.7)
        # Percentage label, nudged up from the curve.
        mid = (lo + hi) / 2.0
        ax.text(mid, normal_pdf(mid) + 0.0016, BAND_PCT[i],
                ha="center", va="bottom", fontsize=10, color=BLUE, fontweight="bold")

    ax.set_xlim(XMIN, XMAX)
    ax.set_ylim(0, ymax * 1.22)
    ax.set_yticks([])
    for spine in ("top", "left", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#888")

    # Show every band edge, including the 60 / 140 endpoints. The data area is
    # full-bleed (for slider alignment), so anchor the two end labels inward
    # (left edge -> left-aligned, right edge -> right-aligned) to avoid clipping.
    ax.set_xticks([60, 70, 85, 100, 115, 130, 140])
    ax.tick_params(axis="x", colors="#444", labelsize=9, length=4)
    ax.set_xlabel("IQ score", fontsize=11, color="#222", labelpad=4)
    labels = ax.get_xticklabels()
    if labels:
        labels[0].set_horizontalalignment("left")
        labels[-1].set_horizontalalignment("right")

    fig.savefig(OUT, transparent=True)
    plt.close(fig)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
