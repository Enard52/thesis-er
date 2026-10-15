#!/usr/bin/env python3
"""Generate RULES.md and site/rules.js from the checker's single source of truth.

The checker emits findings via self.add("RULE.ID", loc, message[, severity]).
This script parses every such call out of purdue_format_check.py and builds:

  - RULES.md      human-readable catalog of every check, grouped by topic
  - site/rules.js machine-readable copy (RULE_COUNT + RULE_FAMILIES) for the
                  "Current rules" tab, plus the fallback numbers in index.html

Re-run after any checker change:  python3 scripts/generate_rules.py
The script fails loudly if a rule in the source is missing from the output
(or vice versa), so docs can never silently drift from the code.
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKER = os.path.join(HERE, "purdue_format_check.py")
RULES_MD = os.path.join(HERE, "RULES.md")
RULES_JS = os.path.join(HERE, "site", "rules.js")
INDEX_HTML = os.path.join(HERE, "site", "index.html")

# prefix -> (section title, one-line plain-English intro)
FAMILIES = [
    (("H1.4",), "Page size and margins",
     "Every page sits on Letter, Legal, or Tabloid stock with 1-inch margins — the frame everything else hangs on."),
    (("H1.TITLE", "H1.COMMITTEE", "H1.DEDICATION", "H1.ABSTRACT"), "Front-matter pages",
     "Title page, committee page, dedication, and abstract: fixed wording, fixed layout, no improvisation."),
    (("H1.5", "H1.EXTRA"), "Contents and lists",
     "The table of contents and lists of tables/figures/abbreviations must mirror the document — and stay in order."),
    (("H1.8", "H1.9", "H1.10", "H1.11"), "Body text",
     "Times New Roman 12pt, 1.5 spacing, justified, half-inch first-line indents, no empty paragraphs as spacers."),
    (("H1.6", "H1.12"), "Chapters, headings, and page breaks",
     "Every chapter starts on a fresh page; headings follow the numbered ALL-CAPS / centered / sentence-case ladder."),
    (("H1.7",), "Page numbers and the title page",
     "No number on the title page, centered decimal numbering everywhere else — including landscape sections."),
    (("H1.13", "SK"), "Figures and tables",
     "Numbered captions in order, kept with their figure or table, placed after first mention, never split across pages."),
    (("H1.15",), "Cross-references",
     "In-text references (Table 3.1, Figure 4.2) must use Word fields so they survive edits — not typed text."),
    (("H1.16",), "Equations",
     "Numbered equations, right-aligned numbers, 12pt, double spaced — the math must look as careful as it is."),
    (("H1.17", "H1.18"), "Block quotes and footnotes",
     "Long quotations set off and single-spaced; footnotes present and correctly marked."),
    (("H1.21",), "References",
     "Numbered, in order, hanging indent, single-spaced within entries — the section reviewers actually check."),
    (("REV", "TPL"), "Submission hygiene",
     "No tracked changes or comments left in, and the template's own formatting (bold, color) left intact."),
    (("A11Y",), "Accessibility (ADA / WCAG 2.1 AA)",
     "A thesis is a public document: real heading structure, alt text on every figure, readable charts, accessible tables."),
]


def _split_args(text: str) -> list[str]:
    """Split a call's argument text on top-level commas (string/paren aware)."""
    parts, depth, cur = [], 0, ""
    instr, quote = False, ""
    i = 0
    while i < len(text):
        c = text[i]
        if instr:
            cur += c
            if c == "\\" and i + 1 < len(text):
                cur += text[i + 1]
                i += 2
                continue
            if c == quote:
                instr = False
        elif c in "\"'":
            instr, quote, cur = True, c, cur + c
        elif c in "([{":
            depth += 1
            cur += c
        elif c in ")]}":
            depth -= 1
            cur += c
        elif c == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += c
        i += 1
    if cur.strip():
        parts.append(cur.strip())
    return parts


def _string_pieces(arg: str) -> list[str]:
    """Pull the raw contents out of every string literal in an expression."""
    out = []
    for m in re.finditer(r'[furbFURB]{0,3}("""(.*?)"""|"(.*?)"|\'(.*?)\')', arg, re.S):
        piece = next((g for g in (m.group(2), m.group(3), m.group(4)) if g is not None), "")
        out.append(piece)
    return out


def _clean(msg: str) -> str:
    """Turn an f-string template into a plain-English one-liner."""
    prev = None
    while prev != msg:  # nested {...} need repeated passes
        prev = msg
        msg = re.sub(r"\{[^{}]*\}", "\u2026", msg)
    msg = re.sub(r"\s+", " ", msg).strip()
    return msg


def parse_checker(src: str) -> dict[str, dict]:
    """rule id -> {severity, messages[]} from every self.add call in the source."""
    rules: dict[str, dict] = {}
    for m in re.finditer(r"self\.add\(", src):
        i, depth = m.end(), 1
        instr, quote = False, ""
        while depth:
            c = src[i]
            if instr:
                if c == "\\":
                    i += 1
                elif c == quote:
                    instr = False
            elif c in "\"'":
                instr, quote = True, c
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            i += 1
        args = _split_args(src[m.end():i - 1])
        rule = args[0].strip().strip("\"'")
        severity = "ERROR"
        rest = args[1:]
        if rest and re.fullmatch(r'"(ERROR|INFO)"', rest[-1].strip()):
            severity = rest[-1].strip().strip('"')
            rest = rest[:-1]
        loc, msg_args = rest[0], rest[1:]
        template = "".join(p for a in msg_args for p in _string_pieces(a))
        entry = rules.setdefault(rule, {"severity": severity, "messages": []})
        entry["severity"] = severity if severity == "ERROR" else entry["severity"]
        if template:
            entry["messages"].append(_clean(template))
    return rules


def family_of(rule: str) -> int:
    for i, (prefixes, _, _) in enumerate(FAMILIES):
        if any(rule == p or rule.startswith(p + ".") for p in prefixes):
            return i
    raise KeyError(f"rule {rule} matches no family — add its prefix to FAMILIES")


def js_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def main() -> int:
    src = open(CHECKER).read()
    rules = parse_checker(src)

    bad = [r for r, e in rules.items() if not e["messages"]]
    if bad:
        print(f"generate_rules: no message parsed for {bad}", file=sys.stderr)
        return 1

    # every rule in the self-test must exist in the catalog
    tested = set(re.findall(r'\("(A11Y[A-Z0-9.]*|H1[A-Z0-9.]*|REV[A-Z0-9.]*|SK[A-Z0-9.]*|TPL[A-Z0-9.]*)", lambda',
                            src[src.index("def selftest"):]))
    unknown = sorted(tested - set(rules))
    if unknown:
        print(f"generate_rules: self-test references unknown rules {unknown}", file=sys.stderr)
        return 1

    order = sorted(rules, key=lambda r: (family_of(r), r))
    grouped: dict[int, list[str]] = {}
    for r in order:
        grouped.setdefault(family_of(r), []).append(r)
    count = len(order)

    # ---- RULES.md ----
    lines = [
        "# Thesis ER — the checks",
        "",
        f"Every check the tool runs against the Purdue University thesis rules (2026 guidelines),",
        "generated from the checker source so this file can never drift from what the code enforces.",
        f"**{count} checks.** `ERROR` = the handbook requires it, fix before submitting;",
        "`INFO` = needs a human eye, the tool flags it but you decide.",
        "",
    ]
    for fi, members in grouped.items():
        _, title, intro = FAMILIES[fi]
        lines += [f"## {title}", "", intro, ""]
        for r in members:
            e = rules[r]
            desc = sorted(e["messages"], key=len)[0]
            lines.append(f"- **{r}** (`{e['severity']}`) — {desc}")
        lines.append("")
    lines += ["---",
              "_Spotted a rule that's wrong or out of date? "
              "[Open an issue](https://github.com/mogiiee/thesis-er/issues/new) — "
              "you'll help every student who runs this after you._",
              ""]
    open(RULES_MD, "w").write("\n".join(lines))

    # ---- site/rules.js ----
    js = [f"/* GENERATED by scripts/generate_rules.py — do not edit by hand. {count} checks. */",
          f"const RULE_COUNT = {count};", "const RULE_FAMILIES = ["]
    for fi, members in grouped.items():
        _, title, intro = FAMILIES[fi]
        js.append(f'  {{"title": "{js_escape(title)}", "intro": "{js_escape(intro)}", "rules": [')
        for r in members:
            e = rules[r]
            desc = sorted(e["messages"], key=len)[0]
            js.append(f'    {{"rule": "{r}", "severity": "{e["severity"]}", '
                      f'"desc": "{js_escape(desc)}"}},')
        js.append("  ]},")
    js.append("];")
    open(RULES_JS, "w").write("\n".join(js) + "\n")

    # ---- index.html fallback numbers (overwritten with the truth on every run) ----
    html = open(INDEX_HTML).read()
    html2 = re.sub(r'(<[^>]*data-rule-count[^>]*>)\d+(</)', rf"\g<1>{count}\g<2>", html)
    if html2 != html:
        open(INDEX_HTML, "w").write(html2)

    print(f"generate_rules: {count} rules, {len(grouped)} families -> RULES.md + site/rules.js")
    return 0


if __name__ == "__main__":
    sys.exit(main())
