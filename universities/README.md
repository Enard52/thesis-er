# `universities/` — one JSON file per school

`purdue.json` is the default. To support another university, copy it and change the values — no Python needed:

1. Copy `purdue.json` to `<yourschool>.json` in this folder.
2. Update the `school`, `handbook`, and rule values (page size, margins, font, heading names, caption pattern, word limits, contrast threshold, …).
3. Run it: `python3 purdue_format_check.py MyThesis.docx --university yourschool`
   (or `--config path/to/yourschool.json` from anywhere).
4. Send it as a pull request so students at your school can use it too.

Rules for a new file:

- Only override keys the school actually changes; anything absent keeps the built-in default. Unknown keys are rejected loudly so typos fail instead of silently doing nothing.
- `caption_pattern` is a regular expression with the same groups as Purdue's: `(Label) (part).(number).(space)`.
- `heading_numbering` maps levels 1–5 to `[number-format, level-text, indent-left-twips, indent-hanging-twips]` (twips = twentieths of a point; 1440 = 1 inch).
- Accessibility thresholds (`contrast_min` etc.) follow WCAG 2.1 AA and rarely need changing; leave them unless your school's guide says otherwise.
