# Thesis ER — the checks

Every check the tool runs against the Purdue University thesis rules (2026 guidelines),
generated from the checker source so this file can never drift from what the code enforces.
**89 checks.** `ERROR` = the handbook requires it, fix before submitting;
`INFO` = needs a human eye, the tool flags it but you decide.

## Page size and margins

Every page sits on Letter, Legal, or Tabloid stock with 1-inch margins — the frame everything else hangs on.

- **H1.4.MARGIN** (`ERROR`) — no page margins defined
- **H1.4.PAGESIZE** (`ERROR`) — page size …x… twips is not Letter, Legal, or Tabloid

## Front-matter pages

Title page, committee page, dedication, and abstract: fixed wording, fixed layout, no improvisation.

- **H1.ABSTRACT** (`INFO`) — abstract is … words; aim for … or fewer
- **H1.COMMITTEE** (`ERROR`) — committee page lines are centered in the template
- **H1.DEDICATION** (`ERROR`) — dedication must be italic
- **H1.TITLE** (`ERROR`) — thesis title must be in ALL CAPS

## Contents and lists

The table of contents and lists of tables/figures/abbreviations must mirror the document — and stay in order.

- **H1.5.TOC** (`ERROR`) — no table of contents entries found
- **H1.5.TOCCAPS** (`ERROR`) — level-1 table of contents entry must be in all caps
- **H1.5.TOCSTALE** (`ERROR`) — table of contents entry … does not match any heading; update the field
- **H1.EXTRA.SORTED** (`ERROR`) — entries … and … are out of alphabetical order

## Body text

Times New Roman 12pt, 1.5 spacing, justified, half-inch first-line indents, no empty paragraphs as spacers.

- **H1.10.EMPTYPARA** (`ERROR`) — empty paragraph used as spacing; remove it and use paragraph spacing
- **H1.10.INDENT** (`ERROR`) — left indent …in on a body paragraph
- **H1.10.PARASPACE** (`ERROR`) — spacing after …pt; indented paragraphs carry no extra space
- **H1.11.ALIGN** (`ERROR`) — list item alignment …; must be justified
- **H1.8.FONT** (`ERROR`) — table text … uses font …
- **H1.8.SIZE** (`ERROR`) — list entry … is …pt; must be 12pt
- **H1.9.FRONT** (`ERROR`) — line spacing …; title, committee, dedication, and table of contents pages are 1.5 lines
- **H1.9.SPACING** (`ERROR`) — list item line spacing …; must be 1.5 lines

## Chapters, headings, and page breaks

Every chapter starts on a fresh page; headings follow the numbered ALL-CAPS / centered / sentence-case ladder.

- **H1.12.CAPS** (`ERROR`) — chapter / major heading must be typed in ALL CAPS
- **H1.12.HEADFMT** (`ERROR`) — heading must be bold
- **H1.12.NORMALHEAD** (`ERROR`) — ACKNOWLEDGMENTS must not appear in the table of contents
- **H1.12.NOSPACE** (`ERROR`) — empty paragraph directly below a heading
- **H1.12.NUMBER** (`ERROR`) — major heading must not be numbered
- **H1.12.NUMFMT** (`ERROR`) — number format … …; template uses … …
- **H1.12.NUMIND** (`ERROR`) — heading numbering level is not defined in numbering.xml
- **H1.12.SENTENCECASE** (`ERROR`) — subheading must start with a capital letter
- **H1.12.STYLE** (`ERROR`) — major heading typed as a normal paragraph
- **H1.12.SUBFMT** (`ERROR`) — subheading lacks …
- **H1.6.BLANKPAGE** (`ERROR`) — heading relies on a stand-alone page-break paragraph; this leaves a blank page whenever the previous page is full. Set 'Page break before' on the heading paragraph instead
- **H1.6.CONTINUOUS** (`ERROR`) — continuous section break is not allowed
- **H1.6.PAGEBREAK** (`ERROR`) — chapter/major heading does not start on a new page (insert a page break before it)

## Page numbers and the title page

No number on the title page, centered decimal numbering everywhere else — including landscape sections.

- **H1.7.LANDSCAPE** (`INFO`) — landscape section: page number must be rotated in the left margin (manual check)
- **H1.7.PAGENUM** (`ERROR`) — footer has no PAGE field
- **H1.7.TITLEPAGE** (`ERROR`) — title page must not carry a page number

## Figures and tables

Numbered captions in order, kept with their figure or table, placed after first mention, never split across pages.

- **H1.13.ALTTEXT** (`ERROR`) — drawing … has no alternative text (WCAG 1.1.1)
- **H1.13.CAPINTABLE** (`ERROR`) — caption placed inside a text box
- **H1.13.CAPKEEP** (`ERROR`) — caption lacks 'keep lines together'; a long caption can otherwise split so its second half lands alone on the next page
- **H1.13.CAPNUM** (`ERROR`) — … ….… out of sequence; expected … ….…
- **H1.13.CAPORDER** (`ERROR`) — table has no table caption directly above it
- **H1.13.CAPSPACE** (`ERROR`) — caption line spacing …; must be single
- **H1.13.CAPSTYLE** (`ERROR`) — picture paragraph carries caption style …
- **H1.13.CAPTION** (`ERROR`) — empty caption paragraph
- **H1.13.FIGCENTER** (`ERROR`) — figure picture paragraph must be centered
- **H1.13.FIGGAP** (`ERROR`) — picture following a paragraph or table needs 24pt spacing above it
- **H1.13.FIGSPACING** (`ERROR`) — picture paragraph line spacing …; must be single
- **H1.13.INLINEPARA** (`ERROR`) — picture is embedded inside a text paragraph; place it before or after the paragraph
- **H1.13.INSERTCAP** (`ERROR`) — caption number is typed by hand; use Insert Caption with 'include chapter number'
- **H1.13.NESTED** (`ERROR`) — nested table inside a table
- **H1.13.NOTE** (`ERROR`) — note must not be indented
- **H1.13.SAMEPAGE** (`ERROR`) — table caption lacks 'keep with next'; caption and table must stay on one page
- **H1.13.TABLETEXT** (`ERROR`) — table text … is …pt; must be 10 to 12pt
- **H1.13.TBLAFTER** (`ERROR`) — no 24pt spacing after the table (next paragraph before=…)
- **H1.13.TBLCENTER** (`ERROR`) — table must be horizontally centered (Table Properties > Center)
- **H1.13.TBLFONTMIX** (`ERROR`) — table mixes font sizes …pt; use one size (10 to 12pt) throughout the table
- **H1.13.TBLHEADER** (`ERROR`) — first row is not marked 'Repeat as header row'; a table that runs onto a second page would continue without its header
- **H1.13.TBLHEADFMT** (`ERROR`) — header row mixes bold and regular cells; format every header cell the same way
- **H1.13.TBLJC** (`ERROR`) — … cell paragraph(s) are justified (inherited from Normal); in a narrow column Word stretches the word gaps into rivers. Set cell text left-aligned
- **H1.13.TBLKEEP** (`ERROR`) — table rows may split across pages (Table Properties > Row > untick 'Allow row to break across pages')
- **H1.13.TBLLONG** (`INFO`) — table is about …in tall and cannot sit on one page; it will continue with its header row repeated. Shorten it, or place it on its own page (section break + vertical centering, landscape if wide)
- **H1.13.TBLNOTE** (`ERROR`) — table note … can be pushed to the next page alone; set 'keep with next' on the last row so the note stays under its table
- **H1.13.TBLSPACING** (`ERROR`) — table cell text … is not single spaced
- **H1.13.WRAP** (`ERROR`) — table text wrapping must be 'None' (table is floating)
- **SK.CAPALIGN** (`INFO`) — estimated one-line caption is not centered (found …); confirm in Word
- **SK.XREFORDER** (`ERROR`) — … is first mentioned after it appears (block …); refer to it before it appears

## Cross-references

In-text references (Table 3.1, Figure 4.2) must use Word fields so they survive edits — not typed text.

- **H1.15.XREF** (`ERROR`) — … is never cross-referenced in the text

## Equations

Numbered equations, right-aligned numbers, 12pt, double spaced — the math must look as careful as it is.

- **H1.16.EQALIGN** (`ERROR`) — equation paragraph must be right aligned with tabs centering the equation
- **H1.16.EQFONT** (`ERROR`) — equation font size must be 12pt
- **H1.16.EQNUM** (`ERROR`) — equation must be numbered (chapter.number) at the right margin
- **H1.16.EQSPACING** (`ERROR`) — equations use double line spacing

## Block quotes and footnotes

Long quotations set off and single-spaced; footnotes present and correctly marked.

- **H1.17.BLOCKQUOTE** (`ERROR`) — block quote must be justified
- **H1.18.FOOTNOTE** (`ERROR`) — footnote must be left or justified

## References

Numbered, in order, hanging indent, single-spaced within entries — the section reviewers actually check.

- **H1.21.REFALIGN** (`ERROR`) — reference alignment …; must match body alignment (justified)
- **H1.21.REFHANG** (`ERROR`) — reference needs a 0.5in hanging indent (found …)
- **H1.21.REFKEEP** (`ERROR`) — reference needs widow/orphan control and keep lines together
- **H1.21.REFLINK** (`ERROR`) — reference must include a DOI or a web link
- **H1.21.REFNUM** (`ERROR`) — reference entry does not start with a [n] number
- **H1.21.REFSPACING** (`ERROR`) — reference line spacing …; must be 1.0, 1.5, or 2.0

## Submission hygiene

No tracked changes or comments left in, and the template's own formatting (bold, color) left intact.

- **REV.TRACKED** (`ERROR`) — comments remain in the document; delete them before submission
- **TPL.COLOR** (`ERROR`) — run … is colored …; template text is black
- **TPL.COMMITTEEBOLD** (`ERROR`) — committee page line must be … as in the template
- **TPL.TITLEBOLD** (`ERROR`) — title page line must be … as in the template (found bold=…)

## Accessibility (ADA / WCAG 2.1 AA)

A thesis is a public document: real heading structure, alt text on every figure, readable charts, accessible tables.

- **A11Y.ALT** (`ERROR`) — drawing … carries Word's automatic alt text …; write what the image conveys (WCAG 1.1.1)
- **A11Y.ALTDUP** (`ERROR`) — drawing … repeats the alt text of another picture …; each panel needs its own description
- **A11Y.CONTRAST** (`ERROR`) — picture … (…) uses chart colors below 3:1 against its background: … (WCAG 1.4.11)
- **A11Y.HEADING** (`ERROR`) — bold stand-alone line used as a heading; apply a built-in Heading style (Heading 2-5) so it appears in the screen-reader outline (WCAG 1.3.1)
- **A11Y.LAYOUTTBL** (`ERROR`) — table holds only pictures and panel labels; a screen reader announces it as a data table with empty headers. Place the panels as inline pictures with the labels in a paragraph below (WCAG 1.3.1)
- **A11Y.SCANNED** (`ERROR`) — picture … fills the page and has no caption; a scanned page is not selectable text (WCAG 1.4.5)
- **A11Y.TBLMERGE** (`INFO`) — data table has merged cells; confirm in the PDF checker that every data cell still resolves to its header
- **A11Y.TEXTBOX** (`ERROR`) — text box … sits outside the reading order; move its text into the body (WCAG 1.3.2)

---
_Spotted a rule that's wrong or out of date? [Open an issue](https://github.com/mogiiee/thesis-er/issues/new) — you'll help every student who runs this after you._
