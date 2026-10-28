# Linked pilot design (October 2026)

With the October 27 changes, new sessions capture a selfie immediately after
consent, before the IQ explanation and username/image selection. All participants
capture a selfie. The 50/50 image assignment
only determines whether a confirmed blurred selfie or a chosen avatar accompanies
their messages. Truth revelation is independently randomized 50/50. Existing
sessions have no new assignment flags and retain their previous page sequence.

## Reference groups and messages

`python -m tools.build_peer_reference <pilot_1_analysis/data>` builds the linked
reference file from completed 15-question periods and block reports. It preserves
all sending decisions for the averages, while only portable, shared qualitative
messages enter the received-message pool. TestBot participants are excluded.
Raw Prolific IDs are not included.
The linked file is encrypted with Fernet before entering the public repository.
Its `PEER_REFERENCE_KEY` belongs only in the ignored local `.env` and the Heroku
runtime configuration. Never commit that key or a plaintext linked reference file.

For each domain, sort by actual performance with a fixed hashed tie-break and
partition into five approximately equal strata. Choose one quintile independently
for each participant-period, then draw 20 observations **with replacement**.
Duplicate observations retain their weight in IQ feedback and averages.
As of 21 October, new quantitative participants draw only from respondents with
three numerical block reports, within the selected full-domain quintile. Reports
were elicited before the send decision, so this includes non-senders. Quintile
boundaries remain defined using the full domain sample. The same 20 draws drive
IQ feedback and the end-of-survey averages. As of October 28, incoming messages
are drawn separately from the entire assigned performance stratum, not only
from those 20 draws.
Qualitative groups retain their existing sampling rule. The participant-level
`peer_group_sampling` flag and group `sampling_policy` record this provisional
change. Existing participants and stored group/average snapshots remain intact.
**Future change:** sample without replacement once every eligible quintile has
at least 20 respondents. The pilot never substitutes respondents from other
quintiles to fill a message shortage.

Incoming messages must belong to respondents in the assigned full-domain
performance stratum and match the assigned message format. Draw uniformly from
distinct username/content pairs, without repeating a pair across blocks or
periods. Different messages from the same sender are provisionally allowed.
The sender need not be in the 20-person IQ draw. Repeated reference observations
do not increase message weights. Previously recorded messages are preserved;
new selections record `performance_stratum_messages_v1` in the message plan.
When eligible messages are exhausted, no incoming message is shown; there is no
simulated fallback. Historical qualitative content filters remain in place.

The local survey still assigns quintiles. Terciles and halves are analysis-only
counterfactuals. Updated simulations and all 95% feedback ranges are in
`analysis/stratum_message_sampling/`. All conditional and pooled IQ distributions
exactly reproduce the preceding calculations: only message eligibility changed.
All 2,000 profiles per format/design received three messages in each social
period with terciles or halves. Quintiles still have sparse cells. End averages
remain statistics for the 20 draws, not averages of the messages displayed.

Historical reference tasks used different item sets; comparisons use those
pilot observations, not performance on the current fixed fifteen questions.

## End-of-survey averages

Period-end difficulty is shuffled with the other subjective questions using the
same stable participant/period seed. It is no longer fixed at the bottom.

Historical peer avatars are randomly assigned within each sender's reported
`gender` from participant_level.csv (woman/man). A stable sender-specific seed
keeps the same portrait across messages and periods. Only the derived avatar
assignment enters the encrypted reference file, not the raw demographic field.
Missing/unsupported demographics and ambiguous legacy username lookups show
initials. There is no username-based gender inference. Received messages and
cached reaction feeds use the same demographics-derived assignment; chosen own
avatars and historical exposure snapshots are preserved.

Quantitative: mean of sent numerical block reports multiplied by three (/15).
The target is the mean actual period score over all 20 reference draws. For new
quantitative-only groups, the reported-minus-actual gap is selective sending
plus numerical misreporting. The legacy `reporting_subset` export field remains
for auditing older mixed groups; it is zero (up to floating-point precision) in
new quantitative-only groups.
Empty reporting subsets are marked unavailable, not zero.

Qualitative (new sessions from 28 October): percentage of happy 😃 emojis among
sent qualitative messages; the target is the percentage of all 20 reference
draws who privately selected satisfaction 5 ("Very much"). Non-senders and
historical control/quantitative respondents are included in this target;
repeated draws carry repeated weight. The reference builder imports `perf_sat`
from period-level data, validates all records, and encrypts it with the existing
reference data. No identity, score, message, avatar, or group draw is changed.
Earlier sessions without `qualitative_target=private_satisfaction_v1` retain
the previous all-composed-messages emoji target and no new incentive.
Wording review: the user's provisional "most positive expressions" sentence
describes the historical happy/neutral/unhappy menu, not today's broader
Facebook-style emoji menu. Sent-message percentages and person-level private
satisfaction also have different units; neither difference is silently equated
with selective sending alone on the new correction page.
All guesses are collected before any revelations. Both revelation arms answer
the same subsequent mood and period-specific satisfaction questions.

### Changes prepared on 27 October

For participants without an existing `average_feedback` snapshot, select one
completed social period uniformly and retain it in `average_period_selection`.
The selection is independent of the revelation treatment, excludes control and
unplayed periods, and is made before checking whether reports are available.
Do not redraw an unavailable period. Beliefs, correction and subsequent
task-specific satisfaction use this same period. Existing multi-period snapshots
and responses are preserved. The custom export includes the selection and its
eligible periods. Both correction arms also answer the final IQ-perception item
using the earlier five-point negative-to-positive scale (IQ-enabled pilots).
These three pages remain immediately before the open-ended experience page.

The qualitative target and accuracy incentive were initially held on 27 October
and approved on 28 October. The new qualitative question pays $0.25 when the
absolute error is at most 10 percentage points, inclusive. The first valid
estimate is locked before correction; the target, answer, error and award are
exported in `average_belief_bonus_json`. The award is included once in the final
payoff and shown as a separate summary row in both truth-treatment arms.
New quantitative sessions also pay $0.25 for an estimate within 0.5 questions
of the actual /15 average, inclusive (`quantitative_estimate_incentive=True`).
The same locked-submission, export and repeat-safe payment mechanism applies.
Earlier snapshots without an incentive retain their original terms. Unavailable comparisons have
no estimate or promised incentive. New randomized final-outcome order is stable
per participant and exported as `average_outcome_order_json`.
Task names within final-question sentences use the same lowercase construct
labels as period-end questions; headings retain capitalized task labels.
Fully filled payment demonstrations require `researcher_preview` plus explicit
`researcher_bonus_preview` amounts. These show all three task bonuses, the new
comparison estimate, initial IQ and percentile-estimate bonuses. Ordinary
participants retain the existing deferred-payment wording for IQ/percentiles.
Period-end difficulty retains its shuffled position but now
has difficulty-specific response labels from "Not at all difficult" to "Very difficult".

Selfie capture is immediately after consent. The blurred confirmation preview
uses a standalone 36-pixel circle (the message mockup was removed on 28 October);
the confirmation question precedes the retake/use buttons. The live camera remains 180
pixels maximum. Fixed blur 10 and storage are unchanged. Consent/camera wording
uses "selfie". Everyone captures one; only display image is randomized.

### Treatment inventory for circulation

1. **Message format:** quantitative numerical reports versus qualitative text
   and composed emojis. Assigned between participants; each participant retains
   the format in their social periods. Session creation balances message format
   and control/social order in four repeating cells; allocation is not an
   independent coin flip for each arriving participant.
2. **Reactions:** 50/50 reaction access versus no reaction access, independent
   of message format. Both formats can react when assigned access. In the current
   pilot, only quantitative + reactions participants also see the ranked feed.
   `ENABLE_REACTION_FEEDBACK` and the session switch can disable that feed. Feed
   counts and other reactors' names remain demonstration values. The intended
   final design pools reactions and the ranked feed as one interactivity treatment
   across both formats; that expansion is not part of the October 27 changes.
3. **Display image:** 50/50 own blurred selfie versus chosen avatar. Everyone
   takes a selfie before reaching this display choice. Historical received
   messages currently use avatars based on reported demographic gender, not
   historical selfies. Thus this pilot does not yet fully cross incoming-peer
   selfie exposure with own-image assignment.
4. **Initial IQ reference point:** 50/50 elicitation versus no elicitation of
   the participant's own IQ estimate before the task; everyone sees the IQ
   explanation. This assignment is independent of the other binary treatments.
5. **Information correction:** 50/50 reveal versus do not reveal the actual
   comparison-group result after the belief elicitation. Both arms provide the
   same subsequent mood, selected-task satisfaction and IQ-perception responses.
6. **Comparison-group performance:** independently choose one of five
   task-specific performance quintiles for each participant-period, then draw
   20 observations with replacement within it. Quantitative participants use
   the provisional quantitative-only pool within the full-domain boundaries;
   qualitative participants use the mixed-format pool. This assignment jointly
   changes IQ feedback and the eligible messages/statistics; it is not a separate
   orthogonal IQ-noise treatment.

In addition, each participant has one control and one social period among the
first two, with order balanced within format. Task order is randomized. The
optional third period is determined by the incentivized WTA mechanism and its
selected scenario. The one-period end elicitation is an independent measurement
selection, not another intervention. The inventory is drafted for Daniel to
circulate; no message has been sent to co-authors.

### Release handoff (28 October)

The October 27 changes were initially held locally at Daniel's request. On
October 28 Daniel explicitly authorized deployment and fresh, shareable Heroku
links opening directly to the changed pages. The release includes the later
whole-stratum message-sampling change. Focused logic checks and desktop/mobile
rendering checks use a synthetic camera; full bot checks cover all pilot modes.
Fresh researcher previews have separate review and QA participants so checking
the deployment never consumes the review links. Consult git and Heroku release
history for the deployed revision.
No schema change or database reset is needed. Use fresh sessions when checking
the changed page sequence; existing oTree sessions retain their page lookup order.

## To do / revisit

- [ ] Restore **no repeated sender** when the reference sample is larger, after
  checking availability separately by task, performance stratum and message
  format across all social periods. From October 28, different messages from
  the same sender are allowed provisionally; the same sender/content pair
  cannot repeat. Duplicate reference draws do not create extra usable messages.
  See `analysis/stratum_message_sampling/` for the latest matched-profile
  availability checks after expanding message eligibility to the whole assigned
  stratum. Deployment was authorized for the October 28 preview release.
- [ ] Revisit the provisional quantitative-only comparison pool after the pilot.
  Confirm whether to retain it and whether qualitative groups should also be
  restricted by historical message format. Assess effects on IQ feedback, the
  comparison-group treatment, and available distinct senders. The full-sample
  performance-quintile boundaries are currently retained.
- [ ] Agree the interpretation and wording of the correction percentage. The
  current quantity is 100 × selective-sending contribution / (reported average
  − actual group average). Even with just two components, underreporting or
  other opposing effects can yield negative shares or shares over 100%; a zero
  gap has no percentage. Do not silently cap these values. A bounded statistic
  would require a different definition and matching participant-facing wording.
- [ ] Replace sampling with replacement when every eligible domain/quintile
  contains at least 20 respondents. Some current quantitative quintiles contain
  only two eligible respondents; preserve no-repeat rules even when messages run out.

## Storage and operations

The consent page requires a separate selfie acknowledgement, recorded with its
UTC timestamp in participant.vars and the custom export. Both the browser and
server block progression until it is recorded. No database reset is required.

Only a confirmed, fixed-blur-10, 512×512 JPEG is sent from the browser.
Raw pixels and camera streams are cleared/stopped after capture. The server
validates JPEG dimensions and re-encodes to remove metadata. Image bytes are
stored once in `participant.vars['selfie']`, not in publicly served static files
or reaction snapshots. The image accompanies the sender's message previews;
future cross-pilot exports must restrict image use to messages actually sent.

Use `python -m tools.manage_selfies` to list retention deadlines and its explicit
deletion options to delete images. Delete at the end of phase two or no later
than six months; the tool conservatively uses 180 days. External backup copies
must also be handled under the retention policy. Routine custom exports exclude
image bytes, but full database backups contain them. No automatic deletion job
is configured, as requested.

The new code does not constitute Prolific approval. Use the deployment for
research-team previews until the proposed collection has been approved.

## Switches and exports

Session config `image_treatment_enabled` and `linked_peer_groups` govern new
assignments. `ENABLE_REACTION_FEEDBACK=0` / session `reaction_feedback_enabled`
continues to disable the ranked feed. Current pilot feed eligibility remains
quantitative + reactions. Image assignment and truth revelation are independent
of message format, reaction assignment, and the existing IQ-prior elicitation.

New data live in participant.vars; no schema reset is needed. The custom export
contains assignment, difficulty, reference draw IDs/scores/quintile, average
snapshots, beliefs and subsequent outcomes, but no photo bytes. Message identities
are stored in `linked_message_plan` for audit.
