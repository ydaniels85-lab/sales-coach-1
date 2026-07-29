# Credit score parser repair

## Problem repaired

The older parser accepted the first three-digit number near the score section. PDF extraction order can move score-band values, exception codes, dates or other numbers ahead of the real client score, which can produce an incorrect Sales Coach route.

## New extraction method

The parser now builds and ranks labelled score candidates. It prioritises:

1. A value explicitly attached to **Final Score**.
2. The final value in the table headed **Score Date / Exception Code / Risk Category / Final Score**.
3. A value attached to **Credit Score**, **Consumer Score**, **Bureau Score**, or a bureau-specific score label.
4. A dated risk-category row.
5. A conservative score-section fallback only when one labelled value exists.

It rejects score-band scales containing multiple ordered values, including the Datanamix `440 530 610 700 780 870 960` scale. It also strips dates before considering numeric candidates.

## Verification controls

Each parsed client now stores and displays:

- Credit score.
- Score source.
- Parser score confidence.
- Exact matched report text.
- Alternative labelled candidates.
- A needs-verification flag.
- A manual-verification flag.

The Client Capture screen allows the consultant to correct the score manually. Saving a corrected score recalculates the Sales Opportunity Engine immediately.

## Supplied report validation

- `REF2788037.pdf`: Final Score **553**, source `Final Score table row`, confidence **99%**.
- `REF2788225.pdf`: Final Score **566**, source `Final Score table row`, confidence **99%**.

Both reports remain password protected and open with the configured company password `DN13084`.
