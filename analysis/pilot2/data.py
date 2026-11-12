"""Read one frozen, single-session export. No connection to oTree is needed."""
import ast
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
COMPONENT = {"working_memory": "working_memory", "ravens": "fluid", "sequences": "numerical"}
PERIOD_Y = ["mood", "performance_satisfaction", "task_enjoyment", "payment_satisfaction",
            "iq_perception_change", "perceived_relative_performance", "perceived_percentile_confidence"]
PERSON_Y = ["task_effort", "care_about_ranking", "care_about_iq_score", "trust_own_iq_estimate",
            "competitiveness", "social_media_hours", "age", "survey_reliability"]


def unpack(value, default):
    if value == "":
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return ast.literal_eval(value)  # standard wide export uses Python repr


def num(value):
    return np.nan if value in ("", None) else float(value)


def flag(value):
    if value in ("", None):
        return np.nan
    v = str(value).lower()
    if v not in {"1", "0", "true", "false", "yes", "no"}:
        raise ValueError(f"Unexpected boolean {value!r}")
    return int(v in {"1", "true", "yes"})


def single(folder, suffix):
    files = list(folder.glob(f"*{suffix}.csv"))
    if len(files) != 1:
        raise ValueError(f"Expected one *{suffix}.csv in {folder}, found {len(files)}")
    return files[0]


def load(folder, min_slot, exclude, max_slot=None):
    opts = dict(dtype=str, keep_default_na=False, encoding="utf-8-sig")
    wcols = ["participant.code", "session.code", "participant.period_1_condition",
             "participant.period_2_condition", "participant.social_media_summary"]
    wide = pd.read_csv(single(folder, "participants"), usecols=wcols, **opts).set_index("participant.code")
    rounds = pd.read_csv(single(folder, "rounds"), **opts)
    rounds.columns = rounds.columns.str.removeprefix("player.")
    rounds = rounds.rename(columns={"participant.code": "pid", "subsession.round_number": "round"})
    custom = pd.read_csv(single(folder, "custom"), **opts).set_index(["participant_code", "period"])
    if not wide.index.is_unique or not custom.index.is_unique or rounds.duplicated(["pid", "round"]).any():
        raise ValueError("Duplicate participant, round or custom-period keys. Use one snapshot at a time.")
    sessions = set(rounds["session.code"])
    if len(sessions) != 1 or sessions != set(wide["session.code"]) or set(rounds.pid) != set(wide.index):
        raise ValueError("Inconsistent round and wide files or multiple sessions")
    expected = {(p, str(i)) for p in wide.index for i in range(1, 4)}
    if set(custom.index) != expected or not rounds.groupby("pid")["round"].apply(
            lambda x: set(map(int, x)) == set(range(1, 46))).all():
        raise ValueError("Incomplete round/custom export or mismatched files")
    rounds["round"] = rounds["round"].astype(int)
    starts = rounds[rounds["round"].eq(1)]
    starts = starts[starts["participant.visited"].map(flag).eq(1)
                    & starts["participant._is_bot"].map(flag).ne(1)
                    & starts["session.is_demo"].map(flag).ne(1)
                    & starts["participant.id_in_session"].astype(int).ge(min_slot)
                    & starts["participant.id_in_session"].astype(int).le(max_slot or np.inf)
                    & ~starts.pid.isin(exclude)]
    # ID is elicited after consent and capture. Keep pre-ID starts in the funnel.
    entered = starts[starts.prolific_id.ne("")]
    if entered.prolific_id.duplicated().any():
        raise ValueError("Repeat Prolific ID: reconcile repeat visits with --exclude-code before inference")
    flow = dict(visited=len(starts), consent=int(starts.consent.map(flag).eq(1).sum()),
                confirmed_selfie=sum(bool(custom.loc[(p, "1"), "selfie_confirmed_at"]) for p in starts.pid),
                entered_id=len(entered))
    lookup = json.loads((ROOT / "social_media/data/iq_distribution_initial.json").read_text())
    people, items, blocks, periods, guesses, wta, feeds = [], [], [], [], [], [], []
    for pid, rows in rounds[rounds.pid.isin(entered.pid)].sort_values("round").groupby("pid"):
        r1, r30, last = (rows.iloc[n] for n in (0, 29, 44))
        w = wide.loc[pid]
        c = custom.loc[(pid, "1")]
        conditions = [w["participant.period_1_condition"], w["participant.period_2_condition"]]
        if conditions.count("control") != 1:
            raise ValueError("Expected one mandatory social period and one control")
        a = dict(pid=pid, finished=int(last["participant._current_page_name"] == "FinalResults"),
                 format=next(x for x in conditions if x != "control"), social_first=int(conditions[0] != "control"),
                 image=c.image_treatment, reactions=flag(c.reaction_treatment), reveal=flag(c.truth_treatment),
                 reference=flag(r1.iq_reference_asked), prior_iq=num(r1.iq_reference_score),
                 gender=last.gender, feedback_text=last.realism_feedback, behavior_text=last.realism_behavior)
        for k in PERSON_Y:
            observed = rows.loc[rows[k].ne(""), k]
            a[k] = num(observed.iloc[-1]) if len(observed) else np.nan
        a["npi"] = sum(num(last[f"npi_{i}"]) for i in range(1, 9))
        a["self_esteem"] = sum(3-num(last[f"rses_{i}"]) if i in (2,5,6,8,9)
                               else num(last[f"rses_{i}"]) for i in range(1, 11))
        for k in last.index:
            if k.startswith(("write_", "share_", "impact_")):
                a[k] = num(last[k])
        summary = unpack(w["participant.social_media_summary"], {})
        a["accepted_optional"] = flag(summary.get("selected_for_retake"))
        a["offered_rate"] = num(summary.get("selected_wta_amount"))
        a["offered_column"] = summary.get("selected_wta_column", "")
        a["posted_bonus"] = num(last["participant.payoff"])
        for i, rate in enumerate([.01,.05,.10,.15,.20,.25,.30,.35,.40,.45,.50], 1):
            for col, condition in [("t","social"), ("c","control")]:
                value = r30[f"wta_{col}_{i}"]
                if value:
                    wta.append(dict(pid=pid, rate=rate, setting=condition, accept=flag(value)))
        people.append(a)
        debrief = {x["period"]:x for x in unpack(c.full_sample_iq_debrief_json,[])}
        plan = unpack(c.linked_message_plan_json, {})
        outcomes = unpack(c.average_outcomes_json, {})
        beliefs = unpack(c.average_beliefs_json, {})
        for f in unpack(c.average_feedback_json, []):
            per = f["period"]
            guess = num(beliefs.get(str(per)))
            target = num(f.get("actual"))
            reported = num(f.get("reported"))
            guesses.append(dict(pid=pid, period=per, kind=f["kind"], reported=reported, actual=target,
                                guess=guess, error=guess-target, absolute_error=abs(guess-target),
                                information_gap=target-reported, surprise=target-guess,
                                earned=(float(abs(target-guess) <= (1 if f["kind"]=="score" else 10))
                                        if np.isfinite(target-guess) else np.nan),
                                post_mood=num(outcomes.get("mood")), post_iq=num(outcomes.get("iq_perception")),
                                post_satisfaction=num(outcomes.get(f"satisfaction_{per}")),
                                human_nature=num(outcomes.get("human_nature"))))
        for per in (1, 2, 3):
            cr = custom.loc[(pid, str(per))]
            group = unpack(cr.peer_group_json, {})
            subset = rows[rows["round"].between(15*per-14, 15*per)]
            scored = subset[subset.q_task.ne("")]
            if scored.empty:
                continue
            task = scored.iloc[0].q_task
            if group and (group["strata"] != 2 or len(group["scores"]) != 20 or group["task"] != task):
                raise ValueError("Unexpected comparison-group design")
            design = dict(pid=pid, period=per, task=task, condition=cr.condition,
                          half={1:"lower",2:"upper"}.get(group.get("stratum")), social=int(cr.condition!="control"))
            end = subset.iloc[-1]
            total = sum(scored.q_correct.map(flag))
            full_iq = round(lookup[COMPONENT[task]][str(int(total))]) if len(scored)==15 else np.nan
            displayed = num(end.iq_estimate)
            if per in debrief:
                recorded = debrief[per]
                if (full_iq,total,displayed)!=(recorded["iq"],recorded["correct"],recorded["earlier_iq"]):
                    raise ValueError("Stored debrief and reconstructed IQ disagree")
            pool = np.asarray(group.get("scores", []))
            rank = (100*((pool<total).mean()+.5*(pool==total).mean())
                    if len(pool) and len(scored)==15 else np.nan)
            iq = unpack(end.iq_feedback_snapshot, {})
            feed = unpack(cr.feedback_snapshot_json, {})
            pr = dict(**design, n_items=len(scored), score15=total if len(scored)==15 else np.nan,
                      full_iq=full_iq, displayed_iq=displayed, shock=displayed-full_iq, actual_pct=rank,
                      perceived_difficulty=num(cr.difficulty), feed_seen=int(bool(feed)),
                      iq_sent=flag(iq.get("shared")) if design["social"] and iq else np.nan,
                      iq_claim=num(iq.get("sent_iq")), overall_displayed=num(end.global_iq_estimate),
                      overall_claim=num(end.global_report_iq),
                      overall_sent=flag(end.global_report_shared) if end.global_report_message else np.nan)
            pr.update({k:num(end[k]) for k in PERIOD_Y})
            pr["overplacement"] = pr["perceived_relative_performance"]-rank
            pr["iq_report_bias"] = pr["iq_claim"]-displayed
            pr["overall_report_bias"] = pr["overall_claim"]-pr["overall_displayed"]
            periods.append(pr)
            for pos, message in enumerate(feed.get("messages", []), 1):
                feeds.append(dict(pid=pid, period=per, position=pos, source=feed.get("source"),
                                  own=int(message["is_own"]), total=message["total"]))
            for _, r in scored.iterrows():
                n = int(r["round"])
                info = dict(**design, block=(n-1)//5+1, difficulty=r.q_difficulty, set_id=r.q_set_id)
                correct, switches = flag(r.q_correct), num(r.q_tab_switches)
                rate = .25 if per<=2 else a["offered_rate"]
                items.append(dict(**info, item=r.q_item_id, correct=correct, timeout=flag(r.q_timeout),
                                  rt=num(r.q_response_time), switches=switches,
                                  task_bonus=rate*correct*int(switches==0)))
                b = unpack(r.feedback_snapshot, {})
                if not b:
                    continue
                signal = b.get("signal") or {}
                source = plan.get(str(n)) or {}
                score = b["block_score"]
                check = scored.loc[scored["round"].between(n-4,n), "q_correct"].map(flag)
                if n%5 or len(check)!=5 or check.sum()!=score:
                    raise ValueError("Block feedback disagrees with scored questions")
                claim = num(b.get("sent_number"))
                exposed = signal.get("type") in ("quantitative","qualitative")
                can_react = bool(exposed and a["reactions"]==1)
                reaction = b.get("received_reaction","none") if can_react else None
                blocks.append(dict(**info, score=score, claim=claim, bias=claim-score,
                                   shared=flag(b.get("shared")) if design["social"] else np.nan,
                                   emoji=b.get("sent_emoji"), note=b.get("sent_message") or "",
                                   edits=b.get("edit_back_count"), exposed=int(exposed), eligible=int(can_react),
                                   reacted=int(reaction!="none") if can_react else np.nan, reaction=reaction,
                                   peer_score=num(signal.get("number")), peer_emoji=signal.get("emoji"),
                                   historical_id=source.get("id") if exposed else None))
    frames = tuple(pd.DataFrame(x) for x in (people, items, blocks, periods, guesses, wta, feeds))
    return flow, frames, set(starts.pid), set(entered.prolific_id)
