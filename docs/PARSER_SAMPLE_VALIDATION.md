# Protected Datanamix Parser Validation

The parser was validated against the two supplied encrypted reports using the supplied company report password.

| Sample | Final score | Score source | Score confidence | Parsed accounts | Result |
|---|---:|---|---:|---:|---|
| REF2788037.pdf | 553 | Final Score table row | 99% | 5 | Debt Mediation (R2,344 balances) |
| REF2788225.pdf | 566 | Final Score table row | 99% | 9 | Debt Mediation (R33,119 balances) |

Validated behavior:

- Upload without a password returns `PDF_PASSWORD_REQUIRED`.
- The frontend opens a password text box.
- An incorrect password is rejected and marked as invalid.
- `DN13084` unlocks and parses the supplied reports.
- The score-band scale `440 530 610 700 780 870 960` is ignored.
- The labelled Final Score row is selected.
- Score source, confidence and matched report text are returned.
- A missing or uncertain score is flagged for manual verification.
- A manually corrected score recalculates the Sales Coach.
- Client identity, summary, CPA/NLR accounts and sales routing are returned.

The sample PDFs are not included in the deployment ZIP because they contain sensitive consumer information.

Routing validation: these scores fall inside 100–600, but CPI is not recommended because active balances remain.
