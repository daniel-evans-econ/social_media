"""Draw one coefficient plot per treatment from the expanded model output."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.textpath import TextPath
from matplotlib.transforms import blended_transform_factory
import numpy as np
import pandas as pd


PANELS = [
    ("qualitative", "Qualitative", "Quantitative", "assignment", "qualitative"),
    ("reactions", "Emoji reactions", "No emoji reactions", "assignment", "reactions"),
    ("selfie", "Selfie", "Avatar", "assignment", "selfie"),
    ("upper", "High-IQ comparison group", "Low-IQ comparison group", "assignment", "upper"),
    ("reference", "Initial IQ estimate elicited", "No initial IQ elicitation", "assignment", "reference"),
    ("social", "Social interactions", "Period without social interactions", "social period assignment", "social"),
    ("correct_score", "Correction of the numerical average", "No correction (quantitative messages)", "correction assignment score", "reveal"),
    ("iq_news", "Overall IQ feedback relative to initial IQ guess", None, "overall IQ news", "news10"),
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
    "timeout": "Questions timed out (pp)",
    "payment_satisfaction": "Payment satisfaction (1–5)",
    "perceived_percentile_confidence": "Confidence in percentile guess (0–100)",
    "iq_sent_pct": "Period IQ messages sent (pp)",
    "overall_sent_pct": "Overall IQ message sent (pp)",
    "care_about_ranking": "Care about performance ranking (1–5)",
    "care_about_iq_score": "Care about IQ score (1–5)",
    "accepted_optional_pct": "Accepted optional task (pp)",
    "trust": "Trust in own IQ estimates (1–5)",
    "explains_pct": "Explains own performance (pp)",
}

GROUPS = {
    "Effort &\nperformance": ["score15", "seconds", "timeout", "task_effort", "accepted_optional_pct"],
    "Mood &\nsatisfaction": ["mood", "performance_satisfaction", "task_enjoyment", "payment_satisfaction",
                              "post_mood", "post_satisfaction"],
    "Perceived\nperformance": ["perceived_relative_performance", "perceived_percentile_confidence",
                               "iq_perception_change", "post_iq", "trust"],
    "Message\nsending": ["shared", "iq_sent_pct", "overall_sent_pct", "words", "explains_pct", "absolute_bias", "edits"],
    "Ego-\nrelevance": ["care_about_ranking", "care_about_iq_score"],
}


def group_positions(rows):
    positions, spans = [], []
    start = 0.
    for label, outcomes in GROUPS.items():
        count = sum(outcome in rows.index for outcome in outcomes)
        if count:
            end = start + count - 1
            pad = .6 if count == 1 else .38
            positions.extend(np.arange(count) + start)
            spans.append((label, start-pad, end+pad))
            start = end + 1.7
    return np.array(positions), spans

def draw_panels(estimates, output):
    output = Path(output)
    series = []
    for key, name, reference, family, term in PANELS:
        rows = estimates.loc[(estimates.family == family) & (estimates.term == term)].set_index("outcome")
        outcomes = [y for group in GROUPS.values() for y in group if y in rows.index]
        if key != "qualitative" and "edits" in outcomes:
            outcomes.remove("edits")
        rows = rows.loc[outcomes].copy()
        scale = rows.reference_sd if reference else rows.sample_sd
        if rows.empty or not (scale > 0).all() or rows[["estimate","lower","upper"]].isna().any().any():
            raise ValueError(f"Missing estimate or positive outcome SD for {name}")
        for field in ("estimate","lower","upper"):
            rows[field+"_sd"] = rows[field] / scale
        series.append((key, name, reference, rows))
    bound = max(np.abs(rows[["lower_sd","upper_sd"]]).to_numpy().max() for _, _, _, rows in series)
    bound = max(1, np.ceil(bound * 2) / 2)
    label_width = max(TextPath((0, 0), LABELS[o], size=12).get_extents().width
                      for _, _, _, rows in series for o in rows.index)
    for key, name, reference, rows in series:
        fig, ax = plt.subplots(figsize=(11.6, 6.65))
        fig.subplots_adjust(left=.425, right=.86, top=.90, bottom=.11)
        header = ("Reference group: "+reference if reference else
                  "Per 10 IQ points higher: displayed overall IQ minus initial guess")
        points_per_width = 72 * fig.get_figwidth()
        x = fig.subplotpars.left - (label_width + 16) / points_per_width
        fig.text(x - 30/points_per_width,.95,header, fontsize=14, color="#333333")
        ax.text(1.13,1.045,"Original units",transform=ax.transAxes,ha="center",fontsize=12)
        ax.axvline(0,color="#777777",linestyle="--",linewidth=1)
        y, spans = group_positions(rows)
        # The JMP uses a square bracket outside the outcome labels, with 4 pt caps
        # and the group name rotated 90 degrees to its left.
        trans = blended_transform_factory(fig.transFigure, ax.transData)
        cap = 4 / points_per_width
        for label, top, bottom in spans:
            ax.plot([x+cap,x,x,x+cap],[top,top,bottom,bottom],transform=trans,
                    clip_on=False,color="black",linewidth=.8)
            ax.text(x-.022,(top+bottom)/2,label,rotation=90,transform=trans,
                    va="center",ha="center",fontsize=10,linespacing=.98,clip_on=False)
        ax.hlines(y, rows.lower_sd, rows.upper_sd, color="#004488", linewidth=1.8)
        ax.plot(rows.estimate_sd,y,"o",color="#004488",markersize=6)
        for pos, value in zip(y, rows.estimate):
            ax.text(1.13,pos,f"{value:+.2f}",transform=ax.get_yaxis_transform(),ha="center",va="center",fontsize=12)
        xlabel = ("Treatment minus reference group (reference-group SDs, 95% CI)" if reference else
                  "Difference per 10 IQ points (outcome SDs, 95% CI)")
        ax.set(yticks=y,yticklabels=[LABELS[o] for o in rows.index],ylim=(y[-1]+.8,-.8),
               xlim=(-bound,bound),xlabel=xlabel)
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
