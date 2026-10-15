# LinkedIn post 1 — launch story

I almost missed my thesis deadline over formatting — not research, formatting.

Purdue's thesis format review is strict: fonts, margins, heading numbering,
caption order, figure placement — and accessibility on top of it. Word will
not check those requirements for you. So I built the tool I wish I had:
upload a thesis Word file and get every formatting and accessibility finding,
each with its location and what the handbook expects instead.

- 89 deterministic checks drawn from the handbook and template
- ADA/WCAG 2.1 AA findings: alt text, chart contrast, heading structure,
  accessible tables, and reading order
- Nothing stored: the file is deleted as soon as analysis finishes
- Free and open source under the MIT License

Try Thesis ER:
https://mogiiee.github.io/thesis-er/

Source code and contributions:
https://github.com/mogiiee/thesis-er

Purdue is the first supported university. The rules are configurable, so
other graduate schools can be added without rewriting the checker. If your
school should be next, open an issue with its formatting handbook.

Unofficial community project. Not sponsored by, endorsed by, or affiliated
with Purdue University. Always confirm findings against the official handbook
before submitting.
