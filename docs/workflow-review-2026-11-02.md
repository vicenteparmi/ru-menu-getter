# Workflow failures reviewed — 2026-11-02

Reviewed the five failed Daily menu update runs from October 31–November 2 (41165373292, 41220756903, 41270519288, 41331737360, 41385388730). The October 30 Unicamp failure has no downloadable log and was followed by successful runs on the merged branch.

## Causes and changes

- Botânico and Matinhos publish an explicit “O cardápio ainda não foi disponibilizado para hoje” notice. Return no menus and skip writes for that restaurant; this is an unpublished source, not a parser failure.
- Toledo publishes dated headings before their tables. Skip those dates, keeping each available table associated with its own heading. Do not invent meals or mark the restaurant closed. Invalid dates, duplicate menus, unknown meal tables, and unexpected empty pages still fail.
- Run 41165373292 also had `SSL_read: unexpected eof while reading`. Retry this interrupted TLS read within the existing three-attempt limit. Certificate verification errors remain fatal.
- Upgrade checkout, setup-python, upload-artifact, and Google authentication actions to Node 24 versions. Artifact upload was the source of the punycode/url.parse warnings.

## Validation

18 targeted tests passed (68 assertions): UFPR parser, UFPR certificate/HTTP behavior, UFABC HTTP regression suite. Tested the downloaded Botânico, Matinhos, and Toledo pages: the first two return no menus and Toledo returns only its published November 3 menu. Ruby syntax and git diff whitespace checks passed.

The live UFPR dry run completed successfully: 8 restaurants collected, 0 failures; unpublished menus were skipped.

No production database writes or workflow reruns were performed during local validation. The updated actions need a GitHub-hosted run after the branch is published.
