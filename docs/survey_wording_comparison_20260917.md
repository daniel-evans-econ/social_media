# Survey wording: original and current

Original means the version immediately before the meeting-note implementation (commit `08b456b`, parent of `203426a`). Current includes the follow-up edits of 17 September 2026. This lists every participant-facing wording change in that implementation and follow-up; layout-only changes are noted at the end. Dynamic task names appear as [component]; the number of compulsory periods is two in the IQ pilot and three when no optional third period is used.

## Before you begin: second paragraph

**Original (also restored in the current version):**

> Your responses to these questions can be used to calculate components of IQ scores. An IQ score is a measure of intelligence used by psychologists. These questions will appear across two periods.

**Interim version, now removed from this paragraph:**

> Your responses to these questions can be used to calculate components of your IQ compared with 20 other Prolific respondents. We use a separately drawn comparison group for each component. An IQ score is a measure of intelligence used by psychologists. These questions will appear across two periods.

## Before you begin: text below the IQ distribution

**Original:**

> After the survey, we will calculate your average IQ score across the two tested components of IQ. We will also do this for another 25 Prolific respondents.

**Current, directly below the distribution image:**

> After the survey, we will calculate your average IQ score across the two tested components of IQ compared with 20 other Prolific respondents.

The optional question asking participants to predict their IQ, and its payment wording, are unchanged.

## Further instructions: reactions (reaction-treatment arm only)

**Original:**

> You can also 👍 like any message you receive. We will share the messages you send with other participants and follow up with you to tell you how many likes your messages received.

**Current:**

> You can also 👍 like or 👎 dislike any message you receive. We will share the messages you send with other participants and follow up with you to tell you how many likes and dislikes your messages received.

On feedback pages, the original button displayed “👍 Like”, changing to “👍 Liked” when selected. The current buttons show only 👍 and 👎; accessible labels remain “Like” and “Dislike”.

## Performance estimate: question

**Original:**

> Imagine 100 other participants who answered the same fifteen questions that you just did. How do you think your performance, in terms of the number of [component] questions answered correctly, ranks compared to these 100 other participants?

**Current:**

> Imagine 20 other participants who answered the same fifteen questions that you just did. How do you think your performance, in terms of the number of [component] questions answered correctly, ranks compared to these 20 other participants?

## Performance estimate: instructions and anchors

**Original:**

> Move the slider from 0 to 100. For example:
>
> • 0 means you think you did worse than every other participant.
>
> • 50 means you think you did better than half of the other participants, and worse than the other half.
>
> • 100 means you think you did better than every other participant.

**Current:**

> How many of these 20 participants do you think you performed better than? Move the slider from 0 to 20. For example:
>
> • 0 means you think you performed better than nobody in the comparison group.
>
> • 10 means you think you did better than half of the other participants.
>
> • 20 means you think you did better than every other participant.

Original labels below the slider: “0: I am worse than everyone else” and “100: I am better than everyone else”.

Current labels: “0: Nobody”, “10: Half”, and “20: Everybody”.

Original readout after interaction:

> I think I have a higher [component] than X% of the other participants.

Current readout after interaction:

> I think I performed better than X% of the other participants.

The current X is the selected count divided by 20, multiplied by 100. The $0.25 bonus wording and ten-percentage-point tolerance are unchanged. Accessible labels were added: “Activate performance estimate slider” and “Number of participants you think you outperformed”.

## IQ effect response scale

**Original:** “Neutral/not much effect”

**Current:** “Not much effect”

The other response labels are unchanged.

## Optional task (WTA): implementation sentence

**Original:**

> We will then randomly select and implement your decision for one of the scenarios listed below.

**Current:**

> We will then implement your decision on a randomly selected scenario from the list below.

The following sentence about making choices in line with true preferences is unchanged.

## Optional task (WTA): headings and results

Original headings: “With messages” and “Without messages”.

Current headings: “With social interactions” and “Without social interactions”.

The selected-scenario description on the results page makes the same substitution:

**Original:**

> The selected scenario was: [amount] per correct answer, with messages.

or “without messages”.

**Current:**

> The selected scenario was: [amount] per correct answer, with social interactions.

or “without social interactions”. The remaining results-page wording is unchanged.

## Your experience: writing introduction

**Original:**

> Now we’ll ask you about the content of the messages you wrote.

**Current:**

> Now we’ll ask you about the **content** of the messages you wrote to other participants regarding how you did on the IQ tasks.

“Content” is now bold and dark red.

## Writing motives: peer did well / peer did poorly

Under both “When another participant said they did well” and “When another participant said they did poorly”, the following item changed:

**Original:**

> I was less likely to write positively about my own performance.

**Current:**

> I was more likely to write critically about my own performance.

The paired item is unchanged:

> I was more likely to write positively about my own performance.

## Writing motives: new items

There were no original counterparts to these two additions under “When another participant said they did poorly”:

> I tried to reassure them.

> I tried to rub it in.

These were subsequently replaced, following approval, with:

> I tried to write messages that would help them feel better about their performance.

> I tended to emphasize that I had performed better than they had.

The second suggestion measures emphasizing a favorable comparison, rather than explicitly intending to make the other person feel worse.

Two further items were then added under “When another participant said they did well” (also with no original counterparts):

> I tried to write messages that acknowledged how well they had done.

> I tended to emphasize that I had performed just as well as or better than they had.

## Layout changes with no wording changes

- Big Five: “I see myself as someone who…” stays with the response labels while scrolling.
- Self-esteem: “There are no right or wrong answers. Please choose the option that best describes you.” stays with the response labels while scrolling.
- Narcissism: “There are no right or wrong answers. For each pair of statements below, please choose the option that best describes you.” is unchanged; the sticky behavior has now been removed.
- WTA: the block heading, block description, “Payment per correct answer”, and “Your choice” remain visible together within each block.
- Reactions: each emoji is in its own small rounded bubble, centered across the bottom border of the received-message bubble.

## Reference groups: confirmed implementation

For each participant and IQ component, a separate seeded draw now selects 20 reference observations without replacement. The seed contains the participant code and component name. Refreshing preserves the draw. Each reference observation can appear only once within a group; distinct respondents can have identical scores. Independently drawn groups across participants or tasks can overlap and are not constrained to be unique or disjoint. Each task in this experiment corresponds to a different IQ component. This replaces the earlier with-replacement rule.
