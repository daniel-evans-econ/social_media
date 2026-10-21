# Linked pilot design (October 2026)

New sessions capture a selfie after the IQ explanation/reference-point page and
before the username/image selection page. All participants capture a photo. The 50/50 image assignment
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
**Future change:** sample without replacement once every eligible quintile has
at least 20 respondents. The pilot never substitutes respondents from other
quintiles to fill a message shortage.

Incoming messages must belong to drawn respondents, match the assigned message
format, and not repeat a sender or username/content pair across blocks. A repeated reference
observation does not cause its message to be repeated. When eligible messages are
exhausted, no incoming message is shown; there is no simulated fallback.

Historical reference tasks used different item sets. The final pages describe
them as tasks in an earlier study, not the exact same fifteen questions.

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
The target is the mean actual period score over all 20 reference draws. The
decomposition distinguishes selective sending, numerical misreporting, and
the difference between numerical reporters and the full reference group.
Empty reporting subsets are marked unavailable, not zero.

Qualitative: percentage of happy 😃 emojis among sent qualitative messages;
the target is the percentage among all composed qualitative messages, including
unsent ones. This concerns selection, not verified emotional truthfulness.
All guesses are collected before any revelations. Both revelation arms answer
the same subsequent mood and period-specific satisfaction questions.

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
