# Contributing

Thanks for helping fellow thesis writers avoid rejected submissions. Small, focused PRs get reviewed fastest.

## How to contribute

1. Pick an open issue (or file one). `good first issue` marks the best starting points.
2. Fork, branch, and keep the change narrow: **one rule or one fix per PR**.
3. Every new checker rule needs a self-test mutation proving it fires — find the `selftest` section in `purdue_format_check.py` and add yours alongside the existing ones.
4. School-specific values go in config, not in code (see the rule-config issues).
5. Run before you push:
   ```bash
   python3 purdue_format_check.py <any-thesis>.docx --selftest   # must print ALL RULES FIRE
   python3 purdue_format_check.py <any-thesis>.docx              # no new false positives
   ```

## Review bar

- Self-test passes; no thesis-specific or personal content in the diff.
- New rules follow the existing ID scheme (`H1.*` handbook, `TPL` template, `A11Y` accessibility, `REV` hygiene) and say what is wrong *and* what the handbook wants instead.
- Deterministic: same input, same output. No network calls, no LLM calls in the checker.

## Ground rules

- MIT-licensed project: your contributions are accepted under the same license.
- Be kind in reviews. Many contributors are students under deadline pressure.

## Requesting (or adding) your university

Only Purdue is supported today. To request your school, [open a university-request issue](https://github.com/mogiiee/thesis-er/issues/new?template=university-request.md)
with your graduate school's handbook — the maintainer will help turn its requirements into a config.
If you'd rather write the config yourself, copy `universities/purdue.json` (see `universities/README.md`)
and send it as a pull request; handbook quotes for every value make review fast.
