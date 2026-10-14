# Labels: `good first issue`, `tests`
# Title: Ship a tiny sample thesis fixture so contributors don't need a real 150-page file

Right now `--selftest` needs a full thesis `.docx` to mutate, which new contributors don't have. Build a minimal `.docx` fixture (a dozen pages: title page, headings, a figure with caption, a table, a list, a couple of intentional violations) plus a script that generates it from scratch with only the standard library.

**Done when:** `python3 purdue_format_check.py tests/sample_thesis.docx --selftest` prints ALL RULES FIRE from a fresh clone with no private files, and CONTRIBUTING points to the fixture.
