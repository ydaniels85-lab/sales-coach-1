# Protected Datanamix Parser Validation

The parser was validated against the two supplied encrypted reports using the supplied company report password.

| Sample | Encrypted | Parsed accounts | Result |
|---|---:|---:|---|
| REF2788037.pdf | Yes | 5 | Passed |
| REF2788225.pdf | Yes | 9 | Passed |

Validated behavior:

- Upload without a password returns `PDF_PASSWORD_REQUIRED`.
- The frontend opens a password text box.
- An incorrect password is rejected and marked as invalid.
- The correct password unlocks and parses the report.
- Client identity, score, summary, CPA/NLR accounts and sales routing are returned.
- Datanamix bureau identification is confirmed.

The sample PDFs themselves are not included in the deployment ZIP because they contain sensitive consumer information.
