"""Draw one coefficient plot per treatment from the expanded model output."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PANELS = [
    ("qualitative", "Qualitative", "Quantitative", "assignment", "qualitative"),
    ("reactions", "Emoji reactions", "No emoji reactions", "assignment", "reactions"),
    ("selfie", "Selfie", "Avatar", "assignment", "selfie"),
    ("upper", "Upper comparison half", "Lower comparison half", "assignment", "upper"),
    ("reference", "Initial IQ estimate elicited", "No initial IQ elicitation", "assignment", "reference"),
    ("social", "Social interactions", "Period without social interactions", "social period assignment", "social"),
    ("correct_score", "Correction of the numerical average", "No correction (quantitative messages)", "correction assignment score", "reveal"),
    ("correct_satisfaction", "Correction of the satisfaction share", "No correction (qualitative messages)", "correction assignment satisfaction", "reveal"),
]
LABELS = {
    "score15": "Correct answers (out of 15)",
    "seconds": "Time per question (seconds)",
    "task_effort": "Reported effort (0–100)",
    "mood": "Mood (1–5)",
    "performance_satisfaction": "Performance satisfaction (1–5)",
    "perceived_relative_performance": "Perceived percentile (0–100)",
    "iq_perception_change": "Change in perceived intelligence (1–5)",
    "displayed_iq": "Displayed IQ (IQ points)",
    "shared": "Messages sent (percentage points)",
    "words": "Words per qualitative note",
    "absolute_bias": "Numerical reporting error (absolute)",
    "edits": "Revisions per message",
    "task_enjoyment": "Task enjoyment (1–5)",
    "post_mood": "Mood (1–5)",
    "post_satisfaction": "Performance satisfaction (1–5)",
    "post_iq": "Change in perceived intelligence (1–5)",
    "human_nature": "View of human nature (1–5)",
}


def draw_panels(estimates, output):
    output = Path(output)
    series = []
    for key, name, reference, family, term in PANELS:
        rows = estimates.loc[(estimates.family == family) & (estimates.term == term)].set_index("outcome")
        outcomes = [y for y in LABELS if y in rows.index]
        if key != "upper" and "displayed_iq" in outcomes:
            outcomes.remove("displayed_iq")
        if key != "qualitative" and "edits" in outcomes:
            outcomes.remove("edits")
        if key != "social" and "task_enjoyment" in outcomes:
            outcomes.remove("task_enjoyment")
        rows = rows.loc[outcomes].copy()
        if rows.empty or not (rows.reference_sd > 0).all() or rows[["estimate","lower","upper"]].isna().any().any():
            raise ValueError(f"Missing estimate or positive reference-group SD for {name}")
        for field in ("estimate","lower","upper"):
            rows[field+"_sd"] = rows[field] / rows.reference_sd
        series.append((key, name, reference, rows))
    bound = max(np.abs(rows[["lower_sd","upper_sd"]]).to_numpy().max() for _, _, _, rows in series)
    bound = max(1, np.ceil(bound * 2) / 2)
    for key, name, reference, rows in series:
        fig, ax = plt.subplots(figsize=(10, 5.15))
        fig.subplots_adjust(left=.37, right=.83, top=.85, bottom=.17)
        fig.text(.025,.93,"Reference group: "+reference, fontsize=13, color="#333333")
        ax.text(1.17,1.045,"Original units",transform=ax.transAxes,ha="center",fontsize=12)
        ax.axvline(0,color="#777777",linestyle="--",linewidth=1)
        y = np.arange(len(rows))
        ax.hlines(y, rows.lower_sd, rows.upper_sd, color="#004488", linewidth=1.8)
        ax.plot(rows.estimate_sd,y,"o",color="#004488",markersize=6)
        for pos, value in zip(y, rows.estimate):
            ax.text(1.17,pos,f"{value:+.2f}",transform=ax.get_yaxis_transform(),ha="center",va="center",fontsize=12)
        ax.set(yticks=y,yticklabels=[LABELS[o] for o in rows.index],ylim=(len(rows)-.4,-.6),
               xlim=(-bound,bound),xlabel="Treatment minus reference group\n(reference-group standard deviations, 95% CI)")
        ax.tick_params(axis="y",length=0,labelsize=12)
        ax.tick_params(axis="x",labelsize=11)
        for side in ["top","right","left"]:
            ax.spines[side].set_visible(False)
        ax.grid(False)
        fig.savefig(output/("treatment_"+key+".pdf"),bbox_inches="tight",pad_inches=.1)
        plt.close(fig)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("estimates", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    draw_panels(pd.read_csv(args.estimates), args.output)
