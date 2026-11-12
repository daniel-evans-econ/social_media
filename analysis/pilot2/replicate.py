"""August deck analyses shared by both pilots."""
import ast
import re
import warnings

import numpy as np
import pandas as pd


def literal(path, name):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t,"id","")==name for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError(f"Missing original coding rule {name} in {path}")


def coded_text(rep, folder, a, qual, social):
    notes = folder/"notes_coding.py"
    figures = folder/"make_slide_figures.py"
    cats, labels = literal(notes,"CATS"), literal(notes,"SLIDE_LABELS")
    noteset = qual.loc[qual.note.fillna("").str.strip().ne("")].copy()
    text = noteset.note.str.lower()
    noteset["sentiment"] = (text.str.count(literal(notes,"POS_LEX"),flags=re.I)
                            -text.str.count(literal(notes,"NEG_LEX"),flags=re.I))
    reasons = []
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="This pattern is interpreted as a regular expression.*")
        for key, label in labels.items():
            match = text.str.contains(cats[key],case=False,na=False)
            reasons.append(dict(category=label, notes=len(noteset), hits=int(match.sum()),
                                fraction=match.mean(), share_rate=noteset.loc[match,"shared"].mean()))
        rep.table("30_33_note_topics_and_sending", reasons)
        for group in ("score","difficulty","task"):
            rep.summary("31_32_sentiment_by_"+group,noteset,[group],["sentiment"])
        rows = []
        g = a[a.feedback_text.fillna("").str.strip().ne("")].copy()
        for label, pattern in literal(figures,"REASONS").items():
            matches = g[g.feedback_text.str.contains(pattern,case=False,na=False)]
            rows.append(dict(reason=label, respondents=len(g), matched=len(matches),
                             mean_person_share=matches.shared.mean()))
        rep.table("34_stated_reasons_and_sharing", rows)
        parts = [social.assign(motive="Everyone")]
        for label, pattern in literal(figures,"MOTIVE_PAT").items():
            ids = g.loc[g.feedback_text.str.contains(pattern,case=False,na=False),"pid"]
            parts.append(social[social.pid.isin(ids)].assign(motive=label))
        rep.summary("35_competing_motives",pd.concat(parts),["motive","difficulty"],["shared"])


def smooth(rep, social):
    """Pilot 1's Gaussian bandwidth, local support rules and participant bootstrap."""
    d = social.dropna(subset=["others","shared"])
    if d.empty:
        rep.table("22_local_sharing",[])
        return
    grid = np.linspace(d.others.min(), d.others.max(), 150)
    distance = abs(grid[:,None]-d.others.to_numpy())
    ok = (distance.min(axis=1)<=.20) & ((distance<=.45).sum(axis=1)>=25)
    grid, distance = grid[ok], distance[ok]
    if not len(grid):
        rep.table("22_local_sharing", [], "No grid points met the original minimum support of 25 blocks.")
        return
    weights = np.exp(-.5*(distance/.45)**2)
    ids = pd.get_dummies(d.pid,dtype=float).to_numpy()
    denom = weights@ids
    numer = (weights*d.shared.to_numpy())@ids
    k = ids.shape[1]
    draws = np.random.default_rng(7).multinomial(k,np.full(k,1/k),size=500).T
    with np.errstate(divide="ignore",invalid="ignore"):
        draws_y = (numer@draws)/(denom@draws)
    rep.table("22_local_sharing",dict_rows(grid, numer.sum(1)/denom.sum(1), draws_y))


def dict_rows(grid, mean, draws):
    lo, hi = np.nanquantile(draws,[.025,.975],axis=1)
    return pd.DataFrame(dict(others_score=grid, share=mean, ci_low=lo, ci_high=hi))


def legacy(rep, a, q, b, p, folder, total_items):
    # Match the slide deck's finishers-only restriction. Current mandatory and optional
    # periods are shown separately; denominator labels identify each analysis population.
    subs = a.loc[a.finished.eq(1)].copy()
    q,b,p = [v[v.pid.isin(subs.pid)].copy() for v in (q,b,p)]
    if q.empty or b.empty:
        rep.table("legacy_availability", [], "No completed records with scored blocks.")
        return
    coreq = q if total_items==45 else q[q.period<=2]
    totals = coreq.groupby("pid").agg(total=("correct","sum"), items=("correct","count"),
                                       switches=("switches","sum")).query("items == @total_items")
    subs = subs.merge(totals, on="pid", how="left")
    subs["switcher"] = subs.switches.gt(0).where(subs.switches.notna())
    rep.summary("03_04_question_time_timeouts",q,["task","difficulty"],["rt","timeout","correct"])
    rep.summary("05_performance_by_switching",subs,["switcher"],["total"])
    rep.summary("06_total_correct",subs,[],["total"])
    rep.table("06_score_distribution",subs.total.value_counts().sort_index().rename_axis("score").reset_index(name="people"))
    for slide, group in [("07","period"),("08","block"),("10","task"),("11_12","difficulty")]:
        rep.summary(slide+"_score_by_"+group,b.assign(perfect=b.score.eq(5).astype(float)),[group],["score","perfect"])
    rep.summary("13_sets",b,["task","difficulty","set_id"],["score"])
    rep.summary("item_accuracy",q,["task","difficulty","item"],["correct","rt","timeout"])
    ref = subs.dropna(subset=["prior_iq","benchmark"])
    rep.table("09_initial_iq_calibration",[dict(people=len(ref),mean_prior=ref.prior_iq.mean(),
              mean_benchmark=ref.benchmark.mean(), mean_shortfall=(ref.prior_iq-ref.benchmark).mean(),
              share_above=(ref.prior_iq>ref.benchmark).mean(),
              correlation=ref.prior_iq.corr(ref.benchmark) if len(ref)>1 and ref.benchmark.nunique()>1 and ref.prior_iq.nunique()>1 else np.nan)])
    keys=["task","difficulty","set_id"]
    group=b.groupby(keys).score
    b["others"]=(group.transform("sum")-b.score)/(group.transform("count")-1).replace(0,np.nan)
    soc=b[b.shared.notna() & b.condition.ne("control")].copy()
    quant=soc[soc.condition.eq("quantitative_social") & soc.claim.notna()].copy()
    qual=soc[soc.condition.eq("qualitative_social")].copy()
    posted=quant[quant.shared.eq(1)]
    rep.table("14_quantitative_exact_over_under", [dict(direction=lab,reports=len(v),fraction=len(v)/len(quant) if len(quant) else np.nan)
              for lab,v in [("exact",quant[quant.bias.eq(0)]),("over",quant[quant.bias.gt(0)]),("under",quant[quant.bias.lt(0)])]])
    rep.summary("15_reporting_bias",quant,["score"],["bias"])
    for slide, group in [("16","score"),("17","difficulty"),("19","period"),("20","block")]:
        rep.summary(slide+"_sharing_by_"+group,soc,[group],["shared"])
    truth, selected, as_posted=quant.score.mean(),posted.score.mean(),posted.claim.mean()
    rep.table("18_gap_decomposition",[dict(reports=len(quant),sent=len(posted),all_truth=truth,
              sent_truth=selected,posted=as_posted,selection=selected-truth,misreporting=as_posted-selected,
              total_gap=as_posted-truth)])
    rep.table("24_score_distributions",pd.concat(
        [(v.value_counts().reindex(range(6),fill_value=0)/(len(v) or np.nan)).rename(k)
         for k,v in [("all_true",quant.score),("as_posted",posted.claim)]],axis=1).rename_axis("score").reset_index())
    true_means=quant.groupby("pid").score.mean()
    median_post=posted.groupby("pid").claim.mean().median()
    rep.table("25_median_person_rank",[dict(people=len(true_means),senders=posted.pid.nunique(),
              basis=k, median=value, percentile=(100*((true_means<value).mean()+.5*(true_means==value).mean())
              if pd.notna(value) else np.nan)) for k,value in [("truth",true_means.median()),("posted",median_post)]])
    rep.summary("26_emoji_sharing",qual,["emoji"],["shared","score"])
    subs=subs.merge(soc.groupby("pid").shared.mean(),on="pid",how="left").merge(
        p.groupby("pid")[["performance_satisfaction","perceived_relative_performance"]].mean(),on="pid",how="left")
    rep.summary("27_29_gender",subs,["gender"],["shared","performance_satisfaction","prior_iq","benchmark","total","perceived_relative_performance"])
    rep.model("21 others' mean score and sending",soc,"shared","others",within=True,interpretation="descriptive person FE")
    smooth(rep,soc)
    for key in ["gender","self_esteem","npi","competitiveness","social_media_hours"]:
        levels = subs[["pid",key]].dropna().copy()
        if key!="gender":
            split=levels[key].median()
            high=levels[key].gt(split) if key in ("npi","competitiveness") else levels[key].ge(split)
            levels[key]=np.where(high,f"higher (cut {split:g})",f"lower (cut {split:g})")
        for label, g in levels.groupby(key):
            rep.model(f"23 {key}: {label}",soc[soc.pid.isin(g.pid)],"shared","others",within=True,interpretation="descriptive subgroup")
    coded_text(rep,folder,subs,qual,soc)
    rep.plot("sharing_by_score",soc,"score","shared","Fraction of blocks sent","condition")
    rep.plot("mean_score_across_blocks",b,"block","score","Mean number correct out of five")


def historical(folder):
    data=folder/"data"
    def read(stem):
        return pd.read_csv(data/(stem+"_level.csv")).rename(columns={"pcode":"pid"})
    a=read("participant").rename(columns={"iq_reference_score":"prior_iq","rses":"self_esteem","npi8":"npi",
                                          "realism_feedback":"feedback_text"}).drop(columns="share_rate")
    iq=pd.read_csv(data/"iq_score_map.csv").query("component=='overall'").set_index("score").iq
    a["benchmark"]=a.total_correct.map(iq)
    q=read("question").rename(columns={"tab_switches":"switches","block_global":"block","item_id":"item"})
    b=read("block").rename(columns={"report_message":"note","block_global":"block","emoji_label":"emoji"})
    p=read("period").rename(columns={"perf_sat":"performance_satisfaction","pct_guess":"perceived_relative_performance"})
    return a,q,b,p


def comparison_row(label, a, q, b, mandatory):
    finish=set(a.loc[a.finished.eq(1),"pid"])
    q=q[q.pid.isin(finish)]
    b=b[b.pid.isin(finish)]
    if mandatory:
        q,b=q[q.period.le(2)],b[b.period.le(2)]
    social=b[b.condition.ne("control") & b.shared.notna()]
    quant=social[social.claim.notna() & social.condition.eq("quantitative_social")]
    sent=quant[quant.shared.eq(1)]
    return dict(sample=label, participants=len(finish),items=len(q),accuracy=q.correct.mean(),
                median_seconds=q.rt.median(),timeouts=q.timeout.mean(),social_blocks=len(social),
                shared=social.shared.mean(),quant_reports=len(quant),exact=quant.bias.eq(0).mean(),
                senders_truth_minus_all=sent.score.mean()-quant.score.mean(),
                posted_minus_senders_truth=sent.claim.mean()-sent.score.mean())
