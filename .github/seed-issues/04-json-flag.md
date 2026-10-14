# Labels: `good first issue`, `feature`
# Title: Add a --json report flag for CI and editor integrations

The checker prints human-readable text. CI pipelines and editor plugins need machine-readable output: add `--json` so `purdue_format_check.py thesis.docx --json` emits the findings (rule, severity, location, message, counts, verdict) as JSON — the same shape `server.py` already returns from `/api/check`, so reuse that serialization rather than inventing a second format.

**Done when:** `--json` output validates as JSON, contains every finding the text report contains, exits nonzero on errors / zero on pass, and the README documents it.
