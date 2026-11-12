"""Current-pilot contrasts. Mandatory periods anchor the crossover comparisons."""
import hashlib
import numpy as np
import pandas as pd
from data import PERIOD_Y


def current(rep, a, q, b, p, beliefs, choices, feeds):
    tags=["pid","format","image","reactions","reference","social_first","reveal","cohort"]
    for col, target in [("qualitative","format"),("selfie","image")]:
        a[col]=a[target].eq(col+"_social" if col=="qualitative" else col).astype(float).where(a[target].ne(""))
    tags += ["qualitative","selfie"]
    def tag(frame):
        return frame.merge(a[tags],on="pid",validate="many_to_one") if len(frame) else frame
    rep.summary("assignment_and_completion",a,["format","image","reactions","reveal","reference"],["finished"])
    # Only compare fully settled in-survey components for finishers. Later percentile
    # awards are intentionally absent from the exported participant payoff.
    if len(q) and "benchmark" in a:
        pay=a.merge(q.groupby("pid").task_bonus.sum(),on="pid",how="left")
        pay=pay[pay.finished.eq(1)].copy()
        pay["initial_award"]=.50*(pay.reference.eq(1)&(pay.prior_iq-pay.benchmark).abs().le(10))
        wins=beliefs.groupby("pid").earned.sum() if len(beliefs) else pd.Series(dtype=float)
        pay["belief_award"]=.25*pay.pid.map(wins).fillna(0)
        pay["reconstructed"]=pay.task_bonus+pay.initial_award+pay.belief_award
        pay["difference"]=(pay.posted_bonus-pay.reconstructed).round(2)
        pay["mismatch"]=pay.difference.abs().gt(.001).astype(float)
        rep.summary("settled_bonus_check",pay,["cohort"],["task_bonus","initial_award","belief_award",
                    "reconstructed","posted_bonus","difference","mismatch"])
    for x in ("selfie","qualitative","reactions","reference","reveal","social_first"):
        rep.model("completion after ID entry",a,"finished",x,interpretation="among identified starts")
    if p.empty or b.empty:
        rep.table("current_availability",[], "No saved period/block observations for analysis yet.")
        return
    p,b=tag(p),tag(b)
    p["upper"]=p.half.map({"upper":1.,"lower":0.})
    p["shock_abs"]=p.shock.abs()
    p["rank_error_abs"]=p.overplacement.abs()
    p["reference_shortfall"]=p.pid.map(a.set_index("pid").prior_iq)-p.displayed_iq
    group_y=["score15","displayed_iq","shock","shock_abs","perceived_difficulty","rank_error_abs",*PERIOD_Y]
    rep.summary("comparison_group_by_task",p,["task","half","condition"],group_y)
    rep.summary("iq_shock_distribution",p,["half","task","score15"],["shock","displayed_iq"])
    core=p[p.period.le(2)]
    for y in ["score15",*PERIOD_Y,"perceived_difficulty","overplacement"]:
        pairs=core.pivot(index="pid",columns="social",values=y).reindex(columns=[0,1]).dropna()
        pairs["difference"]=pairs[1]-pairs[0]
        comp=tag(pairs.reset_index())
        if len(comp):
            rep.summary("paired_social_control_"+y,comp.rename(columns={0:"control",1:"social"}),
                        ["format"],["control","social","difference"])
        rep.model("mandatory social minus control",core,y,"social",adjust=["period"],within=True,
                  interpretation="person FE with period adjustment; observed mandatory periods")
        for x in ("qualitative","reactions","selfie","reference"):
            rep.model("difference in social minus control",comp,"difference",x,interpretation=y)
    for y in ["displayed_iq","shock","score15","mood","performance_satisfaction","iq_perception_change",
              "perceived_relative_performance","task_enjoyment","perceived_difficulty"]:
        rep.model("upper minus lower comparison group",core,y,"upper",adjust=["task","period"],
                  interpretation="assigned half; combines IQ and peer environment in social periods")
    for status,d in core.groupby("condition"):
        for y in ["shock","mood","performance_satisfaction","iq_perception_change"]:
            rep.model("upper minus lower: "+status,d,y,"upper",adjust=["task","period"])
    for y in ["mood","performance_satisfaction","iq_perception_change","perceived_relative_performance"]:
        for setting, d in core.groupby("social"):
            rep.model("one displayed IQ point above full-pool benchmark",d,y,"shock",
                      adjust=["task","score15","period"],interpretation=f"conditional association, social={setting}")
    rep.summary("optional_period_selected",p[p.period.eq(3)],["condition","half"],group_y)
    rep.summary("belief_calibration_by_confidence",core,["perceived_percentile_confidence"],["overplacement","rank_error_abs"])
    rep.plot("difficulty_vs_score",core,"perceived_difficulty","score15","Mean actual score out of 15","task")
    soc=b[b.social.eq(1)&b.shared.notna()].copy()
    soc["misreported"]=soc.bias.ne(0).astype(float).where(soc.bias.notna())
    soc["absolute_bias"]=soc.bias.abs()
    soc["peer_minus_own"]=soc.peer_score-soc.score
    soc["peer_happy"]=soc.peer_emoji.eq("😃").astype(float).where(soc.peer_emoji.notna())
    core_b=soc[soc.period.le(2)]
    for x in ["selfie","reactions","qualitative"]:
        for y in ["shared","bias"]:
            d=core_b.dropna(subset=[y]).copy()
            d["score_by_assignment"]=d.score*d[x]
            # Own score is discrete; the interaction estimates a difference in linear slopes.
            rep.model("selective reporting gradient by "+x,d,y,"score_by_assignment",
                      adjust=["score",x,"period"],interpretation="change in slope per correct answer")
    for x in ["qualitative","reactions","selfie","reference"]:
        for y in ["shared","absolute_bias","edits"]:
            u=tag(core_b.groupby("pid",as_index=False)[y].mean())
            rep.model("mandatory social-block behavior",u,y,x,interpretation="equal-person means")
    for fmt, g in core_b.groupby("format"):
        for x in ["selfie","reactions"]:
            u=tag(g.groupby("pid",as_index=False)[["shared","misreported"]].mean())
            for y in ["shared","misreported"]:
                rep.model("within "+fmt,u,y,x,interpretation="mandatory social blocks")
    rep.summary("reaction_opportunities",soc,["format","reactions","image"],["exposed","eligible","reacted","shared"])
    eligible=soc[soc.eligible.eq(1)].copy()
    rep.summary("reaction_choice",eligible,["format","reaction"],["score","shared"])
    rep.summary("reaction_by_received_score",eligible,["peer_score"],["reacted"])
    rep.summary("reaction_by_received_emoji",eligible,["peer_emoji"],["reacted"])
    rep.summary("feedback_half_and_sending",core_b,["half","format"],["shared","bias","reacted","peer_score","peer_happy"])
    # Every eligible exposure contributes, including an explicit 'none'; IDs are stable
    # digests of original message IDs, never pooled merely because text is identical.
    tally=eligible.dropna(subset=["historical_id"]).copy()
    tally["message_key"]=tally.historical_id.map(lambda s:hashlib.sha256(str(s).encode()).hexdigest())
    counts=tally.groupby(["format","message_key","reaction"]).size().unstack(fill_value=0)
    counts=counts.reindex(columns=["none","like","love","care","haha","sad","angry"],fill_value=0)
    counts["eligible_views"]=counts.sum(axis=1)
    rep.table("observed_reactions_per_historical_message",counts.reset_index())
    for x in ["peer_score","peer_happy"]:
        for y in ["shared","bias","reacted"]:
            rep.model("received content and own response",core_b,y,x,adjust=["task","difficulty"],
                      interpretation="association conditional on observed message content")
    # Change in next-block effort/performance within a period; never bridge breaks/dropout.
    block_q=q.groupby(["pid","block"],as_index=False).agg(next_score=("correct","sum"),n=("correct","count"),
                   next_rt=("rt","mean"),next_timeout=("timeout","mean"))
    block_q=block_q[block_q.n.eq(5)].copy()
    block_q["block"]-=1
    following=core_b[core_b.block.mod(3).ne(0)].merge(block_q,on=["pid","block"],validate="one_to_one")
    for x in ["peer_score","peer_happy"]:
        for y in ["next_score","next_rt","next_timeout"]:
            rep.model("peer content and next block",following,y,x,adjust=["task","difficulty"],interpretation="association")
    for x in ["selfie","reference","qualitative","reactions"]:
        for y in ["task_effort","care_about_ranking","care_about_iq_score","trust_own_iq_estimate","accepted_optional"]:
            rep.model("participant endpoints",a,y,x)
    # First-period comparisons avoid conditioning on reaching the crossover.
    first=core[core.period.eq(1)].copy()
    for y in ["score15","mood","performance_satisfaction","task_enjoyment","perceived_relative_performance"]:
        rep.model("first period social vs control",first,y,"social",interpretation="no prior experimental period")
    rep.summary("reference_point_and_shortfall",core,["reference","condition"],["reference_shortfall","mood","iq_perception_change"])
    for y in ["mood","performance_satisfaction"]:
        rep.model("within elicited reference subgroup",core,y,"reference_shortfall",adjust=["period","task"],
                  interpretation="observational shortfall from prior")
    rep.summary("iq_message_reporting",p,["condition","period"],["iq_sent","iq_report_bias","overall_sent","overall_report_bias"])
    m=a.set_index("pid").join(core_b.groupby("pid").agg(send_rate=("shared","mean"),numeric_bias=("bias","mean")))
    motive_cols=[k for k in a if k.startswith(("write_","share_","impact_"))]
    rep.summary("stated_motives",a,["format"],motive_cols)
    for x in motive_cols:
        rep.model("revealed sharing and stated motives",m.reset_index(),"send_rate",x,interpretation="descriptive association")
    if len(beliefs):
        v=tag(beliefs.merge(p[["pid","period","mood","performance_satisfaction","iq_perception_change"]],
                           on=["pid","period"],how="left",validate="one_to_one"))
        for k,baseline in [("post_mood","mood"),("post_iq","iq_perception_change"),("post_satisfaction","performance_satisfaction")]:
            v["change_"+k]=v[k]-v[baseline]
        rep.summary("belief_accuracy_and_correction",v,["kind","reveal"],
                    ["reported","actual","guess","error","absolute_error","earned","post_mood","post_iq","post_satisfaction","human_nature"])
        for kind,g in v.groupby("kind"):
            for y in ["post_mood","post_satisfaction","post_iq","human_nature","change_post_mood","change_post_satisfaction","change_post_iq"]:
                # A respondent can be assigned revelation even if there was no usable historical report.
                rep.model("correction assignment: "+kind,g,y,"reveal",interpretation="post-elicitation outcome")
            rep.model("prior guess minus target: "+kind,g,"error","reveal",interpretation="pre-revelation balance")
            signed=g.dropna(subset=["surprise"]).copy()
            signed["news"]=np.select([signed.surprise.gt(0),signed.surprise.lt(0)],
                                       ["target above guess","target below guess"],default="exact guess")
            rep.summary("correction_by_news_"+kind,signed,["news","reveal"],
                        ["post_mood","post_satisfaction","post_iq","human_nature"])
            rep.plot("correction_"+kind,g,"reveal","post_mood","Mean post-elicitation mood (1–5)")
    if len(choices):
        h=tag(choices)
        rep.summary("wta_choice_curves",h,["setting","rate"],["accept"])
        pairs=h.pivot(index=["pid","rate"],columns="setting",values="accept").dropna()
        pairs["social_minus_control"]=pairs.social-pairs.control
        rep.summary("wta_paired_by_rate",pairs.reset_index(),["rate"],["social_minus_control"])
        sched=h.sort_values("rate").groupby(["pid","setting"])
        monotone=sched.accept.apply(lambda x:int(x.is_monotonic_increasing)).rename("monotone")
        rep.summary("wta_monotonicity",monotone.reset_index(),["setting"],["monotone"])
        rep.summary("wta_selected_offer",a[a.accepted_optional.notna()],["offered_column","offered_rate"],["accepted_optional"])
        # Preserve censoring at the endpoints; a switching interval requires a complete monotone list.
        bounds=[]
        for (pid,setting), d in sched:
            if len(d)!=11 or not d.accept.is_monotonic_increasing:
                continue
            yes, no=d[d.accept.eq(1)],d[d.accept.eq(0)]
            bounds.append(dict(pid=pid,setting=setting, first_accepted=yes.rate.min(),
                               last_rejected=no.rate.max(),accept_all=int(no.empty),reject_all=int(yes.empty)))
        rep.summary("wta_switching_bounds",pd.DataFrame(bounds),["setting"],["first_accepted","last_rejected","accept_all","reject_all"])
        rep.plot("wta_acceptance",h,"rate","accept","Fraction accepting the optional task","setting")
    rep.summary("ranked_feed_exposure",p,["cohort","format","reactions","condition"],["feed_seen"])
    if len(feeds):
        rep.summary("displayed_feed_by_rank",feeds,["source","position","own"],["total"])
    quant=core[core["format"].eq("quantitative_social") & core.reactions.eq(1) & core.social.eq(1)].copy()
    quant["feed_wave"]=quant.cohort.eq("feed").astype(int)
    for y in ["feed_seen","mood","performance_satisfaction","task_enjoyment"]:
        rep.model("feed vs no-feed recruitment wave",quant,y,"feed_wave",
                  interpretation="sequential cohort contrast; not individually randomized")
    phases=core_b[core_b["format"].eq("quantitative_social") & core_b.reactions.eq(1)].copy()
    phases["feed_wave"]=phases.cohort.eq("feed").astype(int)
    for y in ["shared","bias","reacted"]:
        rep.model("feed-wave assignment and block behavior",phases,y,"feed_wave",
                  interpretation="cohort association; block decisions precede own end-of-period feed")
    rep.plot("displayed_iq_by_score",core,"score15","displayed_iq","Mean displayed IQ","half")
