"""Exploratory mandatory-period treatment, message-exposure and correction contrasts."""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import t


def expanded(a, q, b, p, belief, coding=None):
    a = a.copy()
    a["selfie"] = a.image.map({"selfie": 1, "avatar": 0})
    a["qualitative"] = a["format"].map({"qualitative_social": 1, "quantitative_social": 0})
    a["trust"] = a.trust_own_iq_estimate
    keys = ["pid", "reactions", "selfie", "qualitative", "reference", "reveal", "trust", "task_effort"]
    all_periods = p
    p = p[p.period.le(2)].merge(a[keys], on="pid")
    b = b[b.period.le(2) & b.social.eq(1) & b.shared.notna()].merge(a[keys], on="pid")
    q = q[q.period.le(2)]
    for d in [p, b]:
        d["upper"] = d.half.map({"upper": 1, "lower": 0})
    period_keys = ["pid", "period"]
    effort = q.groupby(period_keys).agg(seconds=("rt","mean"), timeout=("timeout","mean")).reset_index()
    p = p.merge(effort, on=period_keys)
    b["words"] = b.note.str.split().str.len().where(b.qualitative.eq(1))
    b["own_laugh"] = b.emoji.eq("😆").astype(float).where(b.qualitative.eq(1))
    b["absolute_bias"] = b.bias.abs().where(b.qualitative.eq(0))
    b["shared"] *= 100
    b["own_laugh"] *= 100
    b["reaction_pct"] = 100*b.reacted
    # Positive and negative word lists are the same ones used to score notes in the replication.
    from replicate import literal
    import re
    if coding is not None:
        b["sentiment"] = (b.note.str.count(literal(coding,"POS_LEX"),flags=re.I) -
                          b.note.str.count(literal(coding,"NEG_LEX"),flags=re.I)).where(b.qualitative.eq(1))
    p["timeout"] *= 100
    b["peer_happy"] = b.peer_emoji.eq("😃").astype(float).where(b.peer_emoji.fillna("").ne("") & b.exposed.eq(1))
    b["peer_score"] = b.peer_score.where(b.exposed.eq(1))
    # Participant-period exposure weights every eligible message within that period equally.
    pk = b.groupby(period_keys)[["peer_score", "peer_happy"]].mean().reset_index()
    social = p[p.social.eq(1)].merge(pk, on=period_keys)
    rows = []

    def fit(family, frame, outcome, term, rhs, units="", scope=""):
        import patsy
        design_y, design_x = patsy.dmatrices(outcome+" ~ "+rhs, frame, return_type="dataframe")
        ds = frame.loc[design_x.index]
        n = ds.pid.nunique()
        r = dict(family=family, outcome=outcome, term=term, units=units, scope=scope,
                 participants=n, observations=len(ds), formula=rhs)
        rows.append(r)
        if n < 5 or term not in design_x or len(ds) <= design_x.shape[1] or np.linalg.matrix_rank(design_x) < design_x.shape[1] or design_y.iloc[:,0].nunique()<2:
            r["status"] = "insufficient variation"
            return
        m = smf.ols(outcome+" ~ "+rhs, ds).fit(cov_type="cluster", cov_kwds={"groups":ds.pid})
        se = m.bse[term]
        delta = se*t.ppf(.975,n-1)
        r.update(estimate=m.params[term], lower=m.params[term]-delta, upper=m.params[term]+delta, status="estimated")

    period_y = ["seconds","timeout","score15","mood","performance_satisfaction","task_enjoyment",
                "perceived_relative_performance","iq_perception_change","displayed_iq"]
    block_y = ["shared","edits","words","own_laugh","absolute_bias"] + (["sentiment"] if "sentiment" in b else [])
    for x in ["upper","reactions","selfie","qualitative","reference"]:
        # Most treatments are experienced in social periods. One social period per person.
        for y in period_y:
            d = p if x=="upper" else social
            fit("assignment", d, y, x, x+" + C(task) + C(period)", scope="both mandatory periods" if x=="upper" else "mandatory social period")
        for y in block_y:
            if x=="qualitative" and y in ("words","own_laugh","absolute_bias","sentiment"):
                continue
            fit("assignment", b, y, x, x+" + C(task) + C(period) + C(difficulty)", scope="mandatory social blocks")
        d = social if x=="upper" else a
        fit("assignment",d,"task_effort",x,x,scope="endline; upper is assignment in mandatory social period")
    for x,arm in [("peer_score",0),("peer_happy",1)]:
        g=b[b.qualitative.eq(arm)].copy()
        for y in ["shared","edits","reaction_pct"]+(["claim","bias"] if arm==0 else ["words","own_laugh"]+(["sentiment"] if "sentiment" in g else [])):
            fit("received block message",g,y,x,x+" + score + upper + C(task) + C(difficulty)")
        g["relative_own"] = g.score - g.score.mean()
        fit("peer content by own score",g,"shared",x+":relative_own",x+" * relative_own + upper + C(task) + C(difficulty)")
        for y in ["shared","edits"]:
            fit("peer content by reaction availability",g,y,x+":reactions",x+" * reactions + score + upper + C(task) + C(difficulty)")
        # Next-block outcomes exclude between-period transitions.
        nxt=q.groupby(["pid","period","block"]).agg(next_score=("correct","sum"),next_seconds=("rt","mean"),
              next_timeout=("timeout","mean"),answered=("correct","count")).reset_index()
        nxt=nxt[nxt.answered.eq(5)].copy()
        nxt["block"]-=1
        nxt.next_timeout*=100
        pairs=g.merge(nxt,on=["pid","period","block"])
        for y in ["next_score","next_seconds","next_timeout"]:
            fit("received message and next block",pairs,y,x,x+" + score + upper + C(task) + C(difficulty)")
        for y in ["mood","performance_satisfaction","perceived_relative_performance","iq_perception_change","task_effort"]:
            fit("mean received content",social[social.qualitative.eq(arm)],y,x,x+" + score15 + upper + C(task) + C(period)")
    v=belief.merge(a[keys],on="pid").merge(all_periods[period_keys+["mood","performance_satisfaction","iq_perception_change"]],on=period_keys,how="left")
    base={"post_mood":"mood","post_satisfaction":"performance_satisfaction","post_iq":"iq_perception_change","human_nature":None}
    for kind,g in v.groupby("kind"):
        g=g.copy()
        increment=10 if kind=="satisfaction" else 1
        g["size"]=g.absolute_error/increment
        g["signed_news"]=g.surprise/increment
        for y,baseline in base.items():
            adj=" + "+baseline if baseline else ""
            for x in ["size","signed_news"]:
                fit("reveal interaction "+kind,g,y,"reveal:"+x,"reveal * "+x+adj,scope="reveal minus no reveal gradient")
                fit("revealed only "+kind,g[g.reveal.eq(1)],y,x,x+adj,scope="within revealed arm")
            fit("credibility and reveal "+kind,g,y,"reveal:trust","reveal * trust"+adj)
    for x in ["upper","selfie","reactions","qualitative","reference"]:
        for y in ["mood","performance_satisfaction","perceived_relative_performance","score15","seconds","iq_perception_change"]:
            d=p if x=="upper" else social
            fit("credibility by assignment",d,y,x+":trust",x+" * trust + C(task) + C(period)")
        fit("credibility by assignment",b,"shared",x+":trust",x+" * trust + C(task) + C(period) + C(difficulty)")
    for d in [p,social,b,v]:
        d["high_trust"]=d.trust.ge(4).astype(float).where(d.trust.notna())
    for x in ["upper","selfie","reactions","qualitative","reference"]:
        for y in ["mood","performance_satisfaction","perceived_relative_performance","score15","seconds","iq_perception_change","shared"]:
            d=b if y=="shared" else p if x=="upper" else social
            fit("high vs lower credibility",d,y,x+":high_trust",x+" * high_trust + C(task) + C(period)")
    for k,g in v.groupby("kind"):
        for y,baseline in base.items():
            fit("high vs lower credibility: reveal "+k,g,y,"reveal:high_trust",
                "reveal * high_trust"+(" + "+baseline if baseline else ""))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    import argparse
    from pathlib import Path
    from data import load

    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--export", required=True, type=Path)
    cli.add_argument("--min-slot", required=True, type=int)
    cli.add_argument("--legacy-dir", required=True, type=Path)
    cli.add_argument("--output", required=True, type=Path)
    args = cli.parse_args()
    (_, (people, questions, blocks, periods, beliefs, _, _), _, _) = load(args.export, args.min_slot, [])
    estimates = expanded(people, questions, blocks, periods, beliefs, args.legacy_dir / "notes_coding.py")
    estimates.to_csv(args.output, index=False)
