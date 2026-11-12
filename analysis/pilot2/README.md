# Social media pilot analysis

Run this after taking a frozen export. It reads files on disk and writes an HTML report, aggregate CSVs and PNG figures to a **new** output directory. There is no request to Heroku or Prolific. A newer cumulative export replaces the older one as input to a new run.

For the portable ZIP, extract it and open PowerShell at the extracted root. It includes the historical coding dictionaries, July aggregate benchmarks, and the IQ calibration lookup. This lets a colleague run the current analysis without the original July data. To recreate the archive from the research computer, run `python analysis/pilot2/make_bundle.py PATH_TO_NEW_ZIP`.

## Run Wave 1

From the root of the survey repository, in PowerShell:

```powershell
$export = Read-Host "Full path of the numbered Live export folder"
$out = Join-Path $export "Analysis"
python analysis/pilot2/run.py --export "$export" --min-slot 13 --cohort no_feed --out "$out"
python analysis/pilot2/verify.py "$out"
Invoke-Item (Join-Path $out "index.html")
```

Use the original three files ending in `participants.csv`, `rounds.csv` and `custom.csv` from the same single-session snapshot. The live session 2us5s6hg had 12 known preflight slots; the first live slot was 13. Override that cutoff for other sessions. To exclude individual testing or adjudicated duplicate visits, repeat `--exclude-code CODE`. The input reader checks unique keys, 45 round records and three custom rows per allocated participant, before dropping unvisited slots, demos and bots. It reads identifiers as strings. Generated outputs omit Prolific IDs, participant codes, raw notes, usernames and images. The message tallies contain stable digests of historical message keys for local joining. Keep outputs with study data.

The package uses Python 3.12 on this computer. Requirements are listed in `requirements.txt`. The original scripts live in `~/Desktop/research/social_media/pilot_1_analysis`. The runner reads the original keyword dictionaries there so note topics, sentiment and motive codes stay consistent. To run on another machine, provide `--legacy-dir PATH` pointing to those scripts. Include the old tidy files in its `data` folder for the July comparison. The IQ calibration table is read from the survey repository. No oTree installation or credentials are required.

## Start here for the meeting

1. `02_sample.csv` separates visited slots, consent, confirmed selfies, identified starts, scored participants and finishers. The last category means reached FinalResults in oTree. Prolific approval/return is a separate administrative outcome.
2. `pilot_comparison.csv` places the July slide sample, July's first two periods, and the current mandatory periods side by side. `18_gap_decomposition.csv` separates actual performance among senders from what they report. The denominator is completed, quantitative social blocks with a recorded report and send decision, including withheld reports.
3. `comparison_group_by_task.csv` and `displayed_iq_by_score.png` show how upper/lower assignment relates to displayed IQ. The figure holds raw score fixed; the table also separates tasks. `effect_estimates.csv` contains the assignment contrasts for mood, satisfaction, perceived standing and sending. `mandatory-periods/index.html` repeats the deck analyses on the first two periods alone.
4. `belief_accuracy_and_correction.csv` keeps questions correct out of 15 and percentage points in separate rows. Compare both revelation arms and their sample sizes. `reaction_opportunities.csv` gives the denominator for reaction use; `observed_reactions_per_historical_message.csv` contains actual responses.
5. `wta_choice_curves.csv` and the paired curve quantify demand for the optional task at each offered rate, with and without social interactions. `wta_switching_bounds.csv` describes complete monotone schedules. All-yes and all-no lists are censored; their missing bounds are intentional.
6. `settled_bonus_check.csv` compares reconstructed task, initial-IQ and comparison-belief bonuses with posted payoffs among finishers. Percentile awards await the later settlement. This is an analysis check, not a payment instruction.

## Historical replication

```powershell
$old = Join-Path $env:TEMP ("social-media-July-" + (Get-Date -Format yyyyMMdd-HHmmss))
python analysis/pilot2/run.py --pilot1 --out "$old"
python analysis/pilot2/verify.py "$old" --historical
```

The source deck is *Social Media Pilot: First Results*, August 2026 (numbered slides 2–35). Its figure script is `make_slide_figures.py`; `build_dataset.py` constructed the old question, block, period and participant files. Other earlier scripts include `order_sets_iv.py`, `sender_selection.py`, `feedback_effort.py`, `followups.py`, and `text_analysis.py`. The numbered outputs reproduce the analyses in the deck. They are tables and selected charts rather than a rebuilt Beamer presentation.

| Slide | Analysis in this package |
|---|---|
| 2–5 | Sample funnel, task × difficulty response-time medians and timeout rates, participant score by tab switching |
| 6–9 | Participant score distribution, score by period/block, expected versus benchmark IQ, share above benchmark and correlation |
| 10–13 | Score by task, tier, perfect-block frequency and individual set means; item-level accuracy in a separate table |
| 14–20 | Exact/over/under reports, signed bias by true score, probability of sending by score/tier/period/block, selection and misreporting components |
| 21–23 | Person fixed effects of others’ mean set score; local sharing curve and participant-bootstrap band; slopes by gender, self-esteem, NPI, competitiveness and social-media use |
| 24–29 | Posted versus true score distribution, midrank of median person-level scores, sending by composed emoji, gender comparisons of sending, satisfaction, beliefs and performance |
| 30–35 | Original topic and sentiment rules, sending by note content, stated reasons against revealed sending, and sending by difficulty among people citing competing motives |

**Comparability.** July had three mandatory periods, parallel item sets, and a send-only interface. The current total score uses the first two mandatory periods (/30), and its overall IQ benchmark averages their two calibrated full-sample estimates. July's deck used all three (/45) and its fitted total-score IQ mapping. Block summaries show actual played periods, including the optional third where labeled. Its participants self-selected. Use the mandatory rows for like-for-like comparisons. With fixed sets there is no within-task/tier randomized instrument: set-difficulty slopes are descriptive. The six current composed emojis are tabulated separately; the old three-category valence coding applies only to the old menu.

## Current-pilot estimands

- **Social interaction, format and order.** Compare mandatory social and control periods within person, with a period effect. A first-period-only specification avoids prior-period exposure. Compare each person's social-minus-control difference across quantitative/qualitative format, reaction availability, selfie/avatar and initial IQ question assignments. Format and order were allocated in balanced enrollment slots. Optional-period observations are reported separately.
- **Image and reaction assignment.** Compare sending, signed and absolute reporting behavior, editing, effort and endline outcomes by assigned arm. Both image arms take a selfie; the contrast concerns which image accompanies messages. Distinguish eligible non-reactions from ineligible views and control periods. Distinguish selected emoji reactions from emojis composed in text. Per-message tallies count real recorded selections and include eligible views without a reaction.
- **IQ noise and peer comparison.** Compare randomly assigned upper versus lower halves per task and period. The IQ shock equals recorded IQ minus calibrated full-pool IQ for the exact task/score. Tests for assigned half adjust for period and task and report control separately. In social periods, the assigned half can move both displayed IQ and message content. Effects per point of realized shock and associations with received scores/emojis are exploratory. Historical messages are drawn at message level within the half and need not come from the exact 20 sampled respondents. For percentile calibration, the analysis benchmark gives ties half weight within the 20 draws. This descriptive benchmark does not settle deferred percentile payments.
- **Beliefs and correction.** Use the stored, pre-revelation guess and the selected period. Quantitative targets are actual mean questions correct for the group, with a one-question accuracy tolerance. Qualitative targets are the share selecting maximum private satisfaction, with a ten-percentage-point tolerance. Their public signal is the share of sent historical messages containing the happy emoji. `earned` is a 0/1 accuracy indicator. The correction comparison covers post-elicitation mood, satisfaction, IQ perception and view of human nature. Change measures use the matching earlier period where available. There is no baseline human-nature item.
- **Effort, subjective difficulty, credibility and behavior.** Compare recorded difficulty and mood with performance and comparison assignment, and reported effort/credibility across arms. Examine next-block performance, response time and timeout after quantitative or qualitative peer messages within a period. Control-period non-exposure is structural. Report IQ-message sending and numerical reporting errors separately from five-question block reports.
- **Demand and motives.** Compare paired WTA decisions at identical dollar rates, actual selected offers and take-up. Report endorsement of each writing, sharing and impact item, and its association with observed sharing. Text codes are overlapping keyword matches and can miss paraphrases. Treat free-text subgroup analyses as exploratory.
- **Ranked feed.** A saved feed snapshot measures exposure. The export-time setting alone does not establish viewing. Separate actual reaction tallies from displayed counts and retain the recorded source (including synthetic previews). Wave 1 cannot identify a ranked-feed effect. When both waves exist, compare eligible quantitative/reaction subjects across sequential recruitment cohorts; time and cohort can confound that contrast. Block decisions precede the feed for that period.

## Two-wave input

For a single frozen wave, run `python analysis/pilot2/expanded.py --export EXPORT_FOLDER --min-slot FIRST_LIVE_SLOT --legacy-dir PILOT1_SOURCE --output EXPANDED.csv` for the additional assignment, incoming-message, correction-size, and credibility interactions. The numerical correction unit is one question. The qualitative unit is ten percentage points. Trust is analyzed both continuously and as 4–5 versus 1–3. Each output row records the fitted formula, sample size, and nominal participant-clustered interval.

Use `--manifest cohorts.json --out NEW_FOLDER` after wave two. The JSON file is a list of objects with `folder`, `cohort` (`no_feed` or `feed`), optional inclusive `min_slot` / `max_slot`, and optionally `exclude_codes`. Use the actual rollout boundary, especially if a single cumulative session export covers both waves. Separate sessions can each start at slot one. The runner rejects overlaps across cohorts and repeated Prolific IDs so neither repeated snapshots nor return visits silently count twice.

## Interpretation and checks

The historical slide replication is finishers-only except for recruitment counts. Current treatment analyses use observed outcomes among identified starts, including usable mandatory-period outcomes from nonfinishers. Each estimate carries its participant and observation counts. Missing responses, declined optional periods, unoffered reactions and absent feed contrasts stay missing. Repeated observations use participant-clustered uncertainty and a t critical value. The package flags small numbers of clusters, single-person arms and unidentifiable contrasts. Treatment tables are exploratory, with nominal 95% intervals and no multiplicity correction. Attrition, particularly during the server interruption, can change who contributes an outcome. Review completion across assignments before interpreting contrasts.

The survey disclosed credibility and full-sample IQ at different points. The debrief and universal selfie collection have no randomized unexposed group in this design. The package verifies saved debrief values against the calibration table when available. It uses saved peer-group and belief targets and does not redraw assignments, reconstruct a hypothetical feed or trigger payments.
