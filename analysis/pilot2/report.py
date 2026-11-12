"""Aggregate-only tables and lightweight local HTML report."""
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import t
import statsmodels.api as sm


class Report:
    def __init__(self, out):
        self.out = Path(out)
        self.out.mkdir(parents=True, exist_ok=False)
        self.sections = []
        self.models = []

    def table(self, name, frame, note=""):
        frame = pd.DataFrame(frame)
        frame.to_csv(self.out / (name+".csv"), index=False)
        self.sections.append((name, frame, note))

    def summary(self, name, df, groups, measures, note=""):
        rows = []
        if not df.empty:
            cells = df.groupby(groups, observed=True) if groups else [((), df)]
            for key, cell in cells:
                key = key if isinstance(key, tuple) else (key,)
                for y in measures:
                    valid = cell.loc[cell[y].notna(), ["pid", y]]
                    rows.append(dict(**dict(zip(groups,key)), outcome=y, people=valid.pid.nunique(),
                                     observations=len(valid), mean=valid[y].mean(), median=valid[y].median(),
                                     sd=valid[y].std()))
        self.table(name, rows, note)

    def model(self, family, df, y, x, *, adjust=(), within=False, interpretation=""):
        """OLS, CR1 covariance by person, t interval with G-1 df. Never fit an aliased contrast."""
        result = dict(family=family, outcome=y, contrast=x, interpretation=interpretation)
        self.models.append(result)
        cols = ["pid", y, x, *adjust]
        if df.empty or any(c not in df for c in cols):
            result["status"] = "no observations"
            return
        d = df[cols].dropna().copy()
        if within:
            d = d[d.groupby("pid").pid.transform("size")>1]
        people = d.pid.nunique()
        result.update(observations=len(d), people=people)
        for value in [0,1]:
            if set(d[x].unique()) <= {0,1}:
                result[f"people_x{value}"] = d.loc[d[x]==value,"pid"].nunique()
        if d[x].nunique()<2 or people<2:
            result["status"] = "insufficient variation or participants"
            return
        controls = list(adjust) + (["pid"] if within else [])
        X = d[[x]].astype(float)
        if controls:
            X = X.join(pd.get_dummies(d[controls].astype(str), drop_first=True, dtype=float))
        X = sm.add_constant(X, has_constant="add")
        if len(d)<=X.shape[1] or np.linalg.matrix_rank(X.to_numpy())<X.shape[1]:
            result["status"] = "insufficient residual degrees of freedom or aliased design"
            return
        fit = sm.OLS(d[y].astype(float), X).fit(cov_type="cluster", cov_kwds={"groups":d.pid})
        b, se = fit.params[x], fit.bse[x]
        if d[y].nunique()<2 or (set(d[x].unique())=={0,1} and
                                min(result["people_x0"], result["people_x1"])<2):
            result.update(estimate=b,status="point only: constant outcome or single-person arm")
            return
        margin = t.ppf(.975,people-1)*se
        result.update(estimate=b, se=se, ci_low=b-margin, ci_high=b+margin,
                      status="estimated" if people>=20 else "exploratory: fewer than 20 clusters")

    def plot(self, stem, df, x, y, ylabel, split=None):
        if df.empty or df[y].isna().all():
            return
        fig, ax = plt.subplots(figsize=(6.8,3.6), layout="constrained")
        for label, d in (df.groupby(split) if split else [("",df)]):
            v = d.groupby(x)[y].mean().dropna()
            if len(v):
                ax.plot(v.index, v, marker="o", label=str(label))
        if split:
            ax.legend(frameon=False)
        ax.set(xlabel=x.replace("_"," "), ylabel=ylabel)
        ax.spines[["top","right"]].set_visible(False)
        fig.savefig(self.out/(stem+".png"), dpi=150)
        plt.close(fig)

    def finish(self, title):
        self.table("effect_estimates", self.models,
                   "95% intervals clustered by participant. Binary outcome effects are probability differences.")
        outcomes = {"mood":"Mood","performance_satisfaction":"Performance satisfaction",
                    "task_enjoyment":"Task enjoyment","iq_perception_change":"IQ perception"}
        for family,stem,caption in [
                ("mandatory social minus control","social_period_effects","Social minus control period"),
                ("upper minus lower comparison group","comparison_half_effects","Upper minus lower comparison group")]:
            rows = [r for r in self.models if r["family"]==family and r["outcome"] in outcomes
                    and np.isfinite(r.get("ci_low",np.nan)) and np.isfinite(r.get("ci_high",np.nan))]
            if not rows:
                continue
            fig, ax = plt.subplots(figsize=(7,3),layout="constrained")
            for i,r in enumerate(rows):
                ax.plot([r["ci_low"],r["ci_high"]],[i,i],color="#004488")
                ax.plot(r["estimate"],i,"o",color="#004488")
            ax.axvline(0,color="#777777",ls="--",lw=.8)
            ax.set_yticks(range(len(rows)),[outcomes[r["outcome"]]+f' (n={r["people"]})' for r in rows])
            ax.invert_yaxis()
            ax.set(title=caption,xlabel="Difference on the 1–5 response scale (95% interval)")
            ax.spines[["top","right"]].set_visible(False)
            fig.savefig(self.out/(stem+".png"),dpi=150)
            plt.close(fig)
        html = ['<!doctype html><meta charset="utf-8"><style>body{max-width:1000px;margin:3em auto;font:16px system-ui}td,th{padding:.3em .6em;text-align:left}summary{cursor:pointer}img{max-width:48%}</style>',
                f"<h1>{escape(title)}</h1>"]
        if (self.out/"mandatory-periods/index.html").exists():
            html.append('<p><a href="mandatory-periods/index.html">Repeat the slide analyses on mandatory periods only</a></p>')
        for name, frame, _ in self.sections:
            if name in ("02_sample","18_gap_decomposition") and len(frame):
                html.append("<h2>"+("Sample" if name=="02_sample" else "Quantitative block reports")+"</h2>")
                html.append(frame.to_html(index=False,float_format=lambda x:f"{x:.3f}",na_rep=""))
        for png in sorted(self.out.glob("*.png")):
            html.append(f'<img src="{png.name}" alt="{escape(png.stem)}">')
        for name,frame,note in self.sections:
            html.append(f'<details><summary>{escape(name.replace("_"," "))} ({len(frame)} rows)</summary>'
                        f'<p>{escape(note)}</p><a href="{name}.csv">Full CSV</a>')
            html.append(frame.head(100).to_html(index=False, float_format=lambda x:f"{x:.3f}", na_rep="")+"</details>")
        (self.out/"index.html").write_text("\n".join(html), encoding="utf-8")
