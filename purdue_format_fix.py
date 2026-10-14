#!/usr/bin/env python3
"""Deterministic fixer for the violations that `purdue_format_check.py` reports.

Each fix is keyed by the rule ID it resolves and edits the OOXML directly, so
the same input always produces the same output. The script alternates
check -> fix -> check until the checker reports no change, then writes the
result and prints the checker output of every iteration.

Usage:
    python3 purdue_format_fix.py <in.docx> <out.docx>
    python3 purdue_format_fix.py <in.docx> <out.docx> --university purdue
    (also --config path/to/uni.json, --keep-track-changes)
"""
from __future__ import annotations

import copy
import re
import sys
import zipfile

from lxml import etree

from collections import Counter

import purdue_format_check
from purdue_format_check import (CAP_RE, HEADING_LEVEL, NS, REVISION_TAGS, TABLE_FITS_PT, TEMPLATE_HEADING_NUM,
                                 TEXT_WIDTH_PT, W, WP, Checker, Document, image_palette, local, low_contrast_colors,
                                 parse_ppr, parse_rpr, q, recolor_targets, report, wval)


def parse_ppr_r(r):
    return parse_rpr(r.find("w:rPr", NS))

PPR_ORDER = ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl", "numPr",
             "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap",
             "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd",
             "snapToGrid", "spacing", "ind", "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc",
             "textDirection", "textAlignment", "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr",
             "sectPr", "pPrChange"]
RPR_ORDER = ["rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike", "dstrike", "outline",
             "shadow", "emboss", "imprint", "noProof", "snapToGrid", "vanish", "webHidden", "color", "spacing",
             "w", "kern", "position", "sz", "szCs", "highlight", "u", "effect", "bdr", "shd", "fitText",
             "vertAlign", "rtl", "cs", "em", "lang", "eastAsianLayout", "specVanish", "oMath"]
TBLPR_ORDER = ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize", "tblStyleColBandSize",
               "tblW", "jc", "tblCellSpacing", "tblInd", "tblBorders", "shd", "tblLayout", "tblCellMar",
               "tblLook", "tblCaption", "tblDescription"]
TRPR_ORDER = ["cnfStyle", "divId", "gridBefore", "gridAfter", "wBefore", "wAfter", "cantSplit", "trHeight",
              "tblHeader", "tblCellSpacing", "jc", "hidden", "ins", "del", "trPrChange"]
LVLPPR_ORDER = ["tabs", "ind"]  # the only pPr children a numbering level carries here

REF_LINKS = {  # references the handbook requires a link for; verified to resolve on 2026-10-09
    30: "Available: https://docs.lib.purdue.edu/dissertations/AAI30502384/.",
    34: "Available: https://arxiv.org/abs/2407.10441.",
    61: "doi: 10.25394/pgs.12227372.v1.",
}


def _ordered_child(parent, tag, order):
    """Return parent/w:tag, creating it at the schema-correct position."""
    el = parent.find(f"w:{tag}", NS)
    if el is not None:
        return el
    el = etree.Element(q(tag))
    pos = order.index(tag)
    for i, child in enumerate(parent):
        name = local(child)
        if name in order and order.index(name) > pos:
            parent.insert(i, el)
            return el
    parent.append(el)
    return el


def ppr(p):
    el = p.find("w:pPr", NS)
    if el is None:
        el = etree.Element(q("pPr"))
        p.insert(0, el)
    return el


def set_spacing(p, **kw):
    sp = _ordered_child(ppr(p), "spacing", PPR_ORDER)
    for k, v in kw.items():
        if v is None:
            sp.attrib.pop(q(k), None)
        else:
            sp.set(q(k), str(v))
    if not sp.attrib:
        sp.getparent().remove(sp)


def drop_ppr(p, tag):
    pp = p.find("w:pPr", NS)
    if pp is None:
        return
    for el in pp.findall(f"w:{tag}", NS):
        pp.remove(el)


def set_ind(p, **kw):
    ind = _ordered_child(ppr(p), "ind", PPR_ORDER)
    for k, v in kw.items():
        if v is None:
            ind.attrib.pop(q(k), None)
        else:
            ind.set(q(k), str(v))
    if not ind.attrib:
        ind.getparent().remove(ind)


def set_flag(p, tag, on=True):
    el = _ordered_child(ppr(p), tag, PPR_ORDER)
    if on:
        el.attrib.pop(q("val"), None)
    else:
        el.set(q("val"), "0")


def set_jc(p, val):
    _ordered_child(ppr(p), "jc", PPR_ORDER).set(q("val"), val)


def runs_with_text(p):
    for r in p.iter(q("r")):
        if r.find("w:t", NS) is not None:
            yield r


def rpr(r):
    el = r.find("w:rPr", NS)
    if el is None:
        el = etree.Element(q("rPr"))
        r.insert(0, el)
    return el


def set_run_flag(r, tag):
    el = _ordered_child(rpr(r), tag, RPR_ORDER)
    el.attrib.pop(q("val"), None)


def drop_rpr(r, tag):
    rp = r.find("w:rPr", NS)
    if rp is None:
        return
    for el in rp.findall(f"w:{tag}", NS):
        rp.remove(el)


def remove_paragraph(p):
    """Delete an empty paragraph, carrying bookmarks and sectPr to a neighbour."""
    keep = [c for c in p if local(c) in ("bookmarkStart", "bookmarkEnd")]
    sect = p.find("w:pPr/w:sectPr", NS)
    nxt = p.getnext()
    if sect is not None or p.getparent() is None:
        return False  # never delete a section-break carrier; skip if already removed
    for c in keep:
        if nxt is not None:
            nxt.insert(0, c) if local(nxt) == "p" else nxt.addprevious(c)
    p.getparent().remove(p)
    return True


def page_break_paragraph():
    p = etree.Element(q("p"))
    r = etree.SubElement(p, q("r"))
    br = etree.SubElement(r, q("br"))
    br.set(q("type"), "page")
    return p


def tr_pr(tr):
    el = tr.find("w:trPr", NS)
    if el is None:
        el = etree.Element(q("trPr"))
        ex = tr.find("w:tblPrEx", NS)
        ex.addnext(el) if ex is not None else tr.insert(0, el)
    return el


def set_row_flag(tr, tag):
    _ordered_child(tr_pr(tr), tag, TRPR_ORDER).attrib.pop(q("val"), None)


def style_ppr(doc: Document, sid: str):
    st = next(s for s in doc.styles.root.findall("w:style", NS) if s.get(q("styleId")) == sid)
    el = st.find("w:pPr", NS)
    if el is None:
        el = etree.Element(q("pPr"))
        # pPr follows name/aliases/basedOn/next/link/.../rsid and precedes rPr
        rp = st.find("w:rPr", NS)
        rp.addprevious(el) if rp is not None else st.append(el)
    return el


def set_run_size(r, half_points):
    for tag in ("sz", "szCs"):
        _ordered_child(rpr(r), tag, RPR_ORDER).set(q("val"), str(half_points))


def set_weight(p, bold=None, italic=None):
    for r in runs_with_text(p):
        for flag, tags in ((bold, ("b", "bCs")), (italic, ("i", "iCs"))):
            if flag is None:
                continue
            for tag in tags:
                set_run_flag(r, tag) if flag else drop_rpr(r, tag)


def drop_page_break_before(heading_p):
    """Remove a stand-alone page-break paragraph before `heading_p` and mark the heading 'page break before'."""
    prev = heading_p.getprevious()
    if prev is not None and local(prev) == "p" and prev.find("w:pPr/w:sectPr", NS) is None:
        content = [c for c in prev if local(c) not in ("pPr", "bookmarkStart", "bookmarkEnd")]
        only_break = all(local(c) == "r" and all(local(x) == "br" or local(x) == "rPr" for x in c) for c in content)
        if only_break and remove_paragraph(prev):
            pass
        else:
            for br in [x for x in prev.iter(q("br")) if x.get(q("type")) == "page"]:
                br.getparent().remove(br)
    set_flag(heading_p, "pageBreakBefore")


def accept_revisions(doc: Document) -> int:
    n = 0
    for el in list(doc.doc.iter()):
        t = local(el)
        if t not in REVISION_TAGS or el.getparent() is None:
            continue
        parent = el.getparent()
        if t in ("ins", "moveTo") and local(parent) not in ("rPr", "trPr", "tblPr", "sectPr"):
            idx = parent.index(el)
            for child in list(el):
                parent.insert(idx, child)
                idx += 1
        parent.remove(el)
        n += 1
    if doc.settings is not None:
        for tr in doc.settings.findall("w:trackRevisions", NS):
            doc.settings.remove(tr)
            n += 1
    return n


# ---------------------------------------------------------------- accessibility fixes
TEXT_WIDTH_TW = int(TEXT_WIDTH_PT * 20)
PANEL_GAP_TW = 120  # two spaces at 12pt between side-by-side panels


def caption_for(doc: Document, b):
    """The figure caption that closes the figure group `b` belongs to (pictures, panel labels, layout tables)."""
    nb = b
    while nb is not None:
        if nb.pkind == "figcap":
            return nb.text
        if nb.kind == "p" and nb.pkind not in ("figure", "panel"):
            return ""
        nb = doc.next(nb)
    return ""


def panel_alt(caption: str, letter: str | None) -> str:
    """Deterministic two-part alt text: short identification (+ panel segment), then a pointer to the long
    description, which the handbook already requires to exist as the paragraph that cites the figure."""
    m = CAP_RE.match(caption)
    figno = f"{m.group(1)} {m.group(2)}.{m.group(3)}" if m else "This figure"
    if letter:
        parts = re.split(r"\(([a-z])\)", caption)
        segs = {parts[i]: parts[i + 1].strip(" ;,.:") for i in range(1, len(parts) - 1, 2)}
        seg = segs.get(letter)
        if seg:
            return f"{figno}, panel ({letter}): {seg}. Long description: see the text that cites {figno}."
        return f"{figno}, panel ({letter}). {caption} Long description: see the text that cites {figno}."
    return f"{caption} Long description: see the text that cites {figno}."


def set_alt_texts(doc: Document, b) -> int:
    """Give every picture in block `b` its own alt text derived from the caption and the panel label under it."""
    caption = caption_for(doc, b)
    if not caption:
        return 0
    labels = []
    nxt = doc.next(b)
    if nxt is not None and nxt.pkind == "panel":
        labels = re.findall(r"\(?([a-z])\)", nxt.text)
    n = 0
    for i, dr in enumerate(b.el.iter(q("drawing"))):
        dp = dr.find(f".//{{{WP}}}docPr")
        if dp is None:
            continue
        letter = labels[i] if i < len(labels) else None
        dp.set("descr", panel_alt(caption, letter))
        n += 1
    return n


def _drawing_runs(tc):
    seen, out = set(), []
    for dr in tc.iter(q("drawing")):
        r = dr
        while r is not None and local(r) != "r":
            r = r.getparent()
        if r is not None and id(r) not in seen:
            seen.add(id(r))
            out.append(r)
    return out


def _text_run(text, rpr=None):
    r = etree.Element(q("r"))
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    t = etree.SubElement(r, q("t"))
    t.text = text
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    return r


def unpack_layout_table(tbl) -> list:
    """Rewrite a picture grid as paragraphs: one centered paragraph per picture row (pictures side by side),
    one tab-aligned paragraph per label row with each label centered under its picture. Printed layout is kept;
    the screen reader meets pictures and labels in reading order instead of an empty data table."""
    new, widths = [], []
    for tr in tbl.findall("w:tr", NS):
        cells = tr.findall("w:tc", NS)
        p = etree.Element(q("p"))
        pp = etree.SubElement(p, q("pPr"))
        etree.SubElement(pp, q("keepNext"))
        sp = etree.SubElement(pp, q("spacing"))
        sp.set(q("after"), "0"); sp.set(q("line"), "240"); sp.set(q("lineRule"), "auto")
        if tr.find(".//w:drawing", NS) is not None:
            widths = []
            for tc in cells:
                for r in _drawing_runs(tc):
                    if widths:
                        p.append(_text_run("  "))
                    ext = r.find(f".//{{{WP}}}extent")
                    widths.append(int(ext.get("cx")) // 635 if ext is not None else 0)  # EMU -> twips
                    p.append(copy.deepcopy(r))
            etree.SubElement(pp, q("jc")).set(q("val"), "center")
        else:
            labels = [Document.ptext(tc) for tc in cells]
            labels = [l for l in labels if l]
            total = sum(widths) + PANEL_GAP_TW * max(len(widths) - 1, 0)
            x = (TEXT_WIDTH_TW - total) // 2
            tabs = etree.Element(q("tabs"))
            for w_ in widths:
                tab = etree.SubElement(tabs, q("tab"))
                tab.set(q("val"), "center"); tab.set(q("pos"), str(x + w_ // 2))
                x += w_ + PANEL_GAP_TW
            pp.insert(1, tabs)
            etree.SubElement(pp, q("jc")).set(q("val"), "left")
            rpr = None
            for tc in cells:
                rr = tc.find(".//w:r/w:rPr", NS)
                if rr is not None:
                    rpr = rr
                    break
            for lab in labels:
                r = etree.Element(q("r"))
                if rpr is not None:
                    r.append(copy.deepcopy(rpr))
                etree.SubElement(r, q("tab"))
                t = etree.SubElement(r, q("t")); t.text = lab
                p.append(r)
        new.append(p)
    for p in new:
        tbl.addprevious(p)
    tbl.getparent().remove(tbl)
    return new


def recolor_image(data: bytes) -> bytes | None:
    """Darken every low-contrast chromatic color of a chart to CONTRAST_MIN against its background, hue kept.
    Anti-aliased pixels between the background and a bad color are moved by the same proportion."""
    import io
    import numpy as np
    from PIL import Image
    targets = recolor_targets(data)
    if not targets or not low_contrast_colors(data):
        return None
    _, bg, _ = image_palette(data)
    im = Image.open(io.BytesIO(data))
    fmt = im.format
    mode = "RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB"
    arr = np.asarray(im.convert(mode)).astype(np.float32)
    rgb = arr[..., :3]
    bgv = np.array(bg, dtype=np.float32)
    out = rgb.copy()
    best = np.full(rgb.shape[:2], np.inf, dtype=np.float32)
    for c, repl in targets:
        v = np.array(c, dtype=np.float32) - bgv
        v2 = float(v @ v) or 1.0
        d = rgb - bgv
        a = np.clip((d @ v) / v2, 0.0, 1.0)
        resid = np.linalg.norm(d - a[..., None] * v, axis=-1)
        tgt = np.array(repl, dtype=np.float32) - bgv
        hit = (resid < 28) & (a > 0.08) & (resid < best)
        best = np.where(hit, resid, best)
        out[hit] = bgv + a[hit, None] * tgt
        # pixels blended with a neighbouring object rather than with the background: shift them by the same offset
        dist = np.linalg.norm(rgb - np.array(c, dtype=np.float32), axis=-1)
        near = (dist < 40) & ~hit & (dist < best)
        best = np.where(near, dist, best)
        out[near] = rgb[near] + (np.array(repl, dtype=np.float32) - np.array(c, dtype=np.float32))
    arr[..., :3] = out
    res = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode)
    buf = io.BytesIO()
    if fmt == "JPEG":
        res.convert("RGB").save(buf, "JPEG", quality=95)
    else:
        res.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def fix_floating(p) -> int:
    """Delete empty floating text boxes; turn any other floating drawing into an inline one."""
    n = 0
    for anc in list(p.iter(f"{{{WP}}}anchor")):
        if anc.find(".//w:txbxContent", NS) is not None and not Document.ptext(anc):
            r = anc
            while r is not None and local(r) != "r":
                r = r.getparent()
            if r is not None:
                r.getparent().remove(r)
                n += 1
                continue
        for child in list(anc):
            if local(child) not in ("extent", "effectExtent", "docPr", "cNvGraphicFramePr", "graphic"):
                anc.remove(child)
        for k in list(anc.attrib):
            if k not in ("distT", "distB", "distL", "distR"):
                del anc.attrib[k]
        anc.tag = f"{{{WP}}}inline"
        n += 1
    return n


# ---------------------------------------------------------------- fix pass
KEEP_REVISIONS = False  # --keep-track-changes: leave the author's tracked edits in place for the reviewer


def fix_once(doc: Document) -> int:
    """Apply one round of fixes to the parsed document. Returns the number of edits."""
    chk = Checker(doc)
    issues = chk.run()
    edits = 0
    by_block = {}
    for it in issues:
        m = re.match(r"block (\d+)", it.loc)
        if m:
            by_block.setdefault(int(m.group(1)), []).append(it)
        elif it.rule in ("H1.12.NUMIND", "H1.12.NUMFMT"):
            m = re.search(r"for (Heading\d) \(numId=(\d+) ilvl=(\d+)\)", it.loc)
            if m:
                lvl = doc.numbering.level(int(m.group(2)), int(m.group(3)))
                fmt, text, left, hanging = TEMPLATE_HEADING_NUM[HEADING_LEVEL[m.group(1)]]
                _ordered_child(lvl, "numFmt", ["start", "numFmt", "lvlRestart", "pStyle", "isLgl", "suff", "lvlText", "lvlPicBulletId", "legacy", "lvlJc", "pPr", "rPr"]).set(q("val"), fmt)
                _ordered_child(lvl, "lvlText", ["start", "numFmt", "lvlRestart", "pStyle", "isLgl", "suff", "lvlText", "lvlPicBulletId", "legacy", "lvlJc", "pPr", "rPr"]).set(q("val"), text)
                lp = lvl.find("w:pPr", NS)
                if lp is None:
                    lp = etree.SubElement(lvl, q("pPr"))
                for tabs in lp.findall("w:tabs", NS):
                    lp.remove(tabs)
                ind = _ordered_child(lp, "ind", LVLPPR_ORDER)
                ind.attrib.clear()
                ind.set(q("left"), str(left))
                ind.set(q("hanging") if hanging else q("firstLine"), str(hanging) if hanging else "0")
                edits += 1
        elif it.rule == "REV.TRACKED" and not KEEP_REVISIONS:
            edits += accept_revisions(doc)
    blocks = doc.blocks

    def fig_table(b):
        return b.kind == "tbl" and b.el.find(".//w:drawing", NS) is not None

    for idx, items in sorted(by_block.items(), reverse=True):  # reverse so deletions do not shift earlier indices
        b = blocks[idx]
        rules = {it.rule for it in items}
        msgs = {}
        for it in items:
            msgs[it.rule] = msgs.get(it.rule, "") + " | " + it.msg
        p = b.el
        prev, nxt = doc.prev(b), doc.next(b)

        if "H1.10.EMPTYPARA" in rules or ("H1.12.NOSPACE" in rules and b.pkind == "empty"):
            # carry the gap the empty paragraph used to provide
            if prev is not None and nxt is not None and prev.kind == "tbl" and not fig_table(prev) and nxt.kind == "p" and nxt.pkind in ("body", "list"):
                set_spacing(nxt.el, before=480)
            if remove_paragraph(p):
                edits += 1
            continue
        if "H1.12.NOSPACE" in rules and b.pkind in ("heading1", "major", "sub"):
            for nb in (prev, nxt):
                if nb is not None and nb.kind == "p" and nb.pkind == "empty" and remove_paragraph(nb.el):
                    edits += 1
            continue
        if "H1.13.CAPTION" in rules:  # empty caption paragraph
            if remove_paragraph(p):
                edits += 1
            continue
        if "H1.6.PAGEBREAK" in rules or "H1.6.BLANKPAGE" in rules:
            drop_page_break_before(p)  # 'page break before' on the heading can never leave a blank page
            edits += 1
        if "TPL.TITLEBOLD" in rules or "TPL.COMMITTEEBOLD" in rules:
            for it in items:
                if it.rule.startswith("TPL."):
                    if "must be bold" in it.msg:
                        set_weight(p, bold=True)
                    elif "regular weight" in it.msg:
                        set_weight(p, bold=False)
                    elif "must be italic" in it.msg:
                        set_weight(p, italic=True)
                    elif "upright" in it.msg:
                        set_weight(p, italic=False)
            edits += 1
        if "H1.10.INDENT" in rules and b.pkind == "body":
            set_ind(p, firstLine=720, left=None, start=None, hanging=None)
            edits += 1
        if "H1.10.PARASPACE" in rules:
            allow_before = prev is not None and (prev.kind == "tbl" or prev.pkind in ("figure", "panel", "note"))
            allow_after = nxt is not None and (nxt.pkind == "figure" or fig_table(nxt))
            eff = doc.eff(b)
            set_spacing(p, before=None if not allow_before or eff.get("before") != 480 else 480,
                        after=None if not allow_after or eff.get("after") != 480 else 480)
            edits += 1
        if "H1.9.SPACING" in rules:
            set_spacing(p, line=None, lineRule=None)
            edits += 1
        if "H1.11.ALIGN" in rules:
            drop_ppr(p, "jc")
            edits += 1
        if "H1.12.HEADFMT" in rules or "H1.12.SUBFMT" in rules:
            drop_ppr(p, "spacing")  # the heading style carries the template spacing
            drop_ppr(p, "jc")       # ... and the template alignment
            if "H1.12.SUBFMT" in rules:
                set_flag(p, "keepNext"); set_flag(p, "keepLines")
                if HEADING_LEVEL.get(b.style, 0) >= 3 and "alignment" in msgs.get("H1.12.SUBFMT", ""):
                    # fix the style once: Normal is justified, so levels 2 to 4 must say 'left' themselves
                    _ordered_child(style_ppr(doc, b.style), "jc", PPR_ORDER).set(q("val"), "left")
            edits += 1
        if "H1.8.SIZE" in rules and b.pkind in ("heading1", "major", "sub"):
            for r in runs_with_text(p):
                drop_rpr(r, "sz"); drop_rpr(r, "szCs")
            edits += 1
        if "H1.8.FONT" in rules:
            for r in runs_with_text(p):
                rf = r.find("w:rPr/w:rFonts", NS)
                if rf is not None:
                    for k in ("asciiTheme", "hAnsiTheme", "cstheme", "eastAsiaTheme"):
                        rf.attrib.pop(q(k), None)
                    rf.set(q("ascii"), "Times New Roman"); rf.set(q("hAnsi"), "Times New Roman")
            edits += 1
        if "H1.13.CAPSPACE" in rules and b.pkind in ("tablecap", "figcap"):
            drop_ppr(p, "spacing"); set_ind(p, firstLine=None)
            edits += 1
        if "SK.CAPALIGN" in rules:
            eff = doc.eff(b)
            from purdue_format_check import line_count
            set_jc(p, "center" if line_count(b.text) == 1 else "both")
            edits += 1
        if "H1.13.SAMEPAGE" in rules:
            set_flag(p, "keepNext")
            edits += 1
        if "H1.13.CAPKEEP" in rules:
            set_flag(p, "keepLines")
            edits += 1
        if "H1.13.CAPSTYLE" in rules and b.pkind == "figure":
            drop_ppr(p, "pStyle")
            edits += 1
        if "H1.13.FIGGAP" in rules:
            if b.kind == "p":
                set_spacing(p, before=480, line=240, lineRule="auto")
            elif prev is not None and prev.kind == "p":
                set_spacing(prev.el, after=480)
            edits += 1
        if "H1.13.FIGSPACING" in rules or "H1.13.FIGCENTER" in rules:
            set_spacing(p, line=240, lineRule="auto")
            set_jc(p, "center"); set_ind(p, firstLine=None, left=None)
            edits += 1
        if "H1.13.NOTE" in rules:
            set_spacing(p, before=120, after=480, line=240, lineRule="auto")
            set_ind(p, firstLine=None)
            set_jc(p, "left")
            for r in runs_with_text(p):
                set_run_flag(r, "i"); set_run_flag(r, "iCs")
            edits += 1
        # -- accessibility (both paragraph and table blocks)
        if "H1.13.WRAP" in rules and b.kind == "p":
            edits += fix_floating(p)
        if "A11Y.LAYOUTTBL" in rules and b.kind == "tbl":
            unpack_layout_table(b.el)
            edits += 1
            continue  # the table is gone; its pictures get alt text on the next pass
        if rules & {"A11Y.ALT", "A11Y.ALTDUP", "H1.13.ALTTEXT"}:
            edits += set_alt_texts(doc, b)
        if "A11Y.CONTRAST" in rules:
            for dr in b.el.iter(q("drawing")):
                media = doc.drawing_media(dr)
                if media:
                    new = recolor_image(doc.media[media])  # a second pass catches blends the first one exposed
                    if new:
                        doc.media[media] = new
                        doc.media_dirty.add(media)
                        doc._palette_cache.pop(media, None)
                        edits += 1
        if b.kind == "tbl":
            tblpr = _ordered_child(b.el, "tblPr", ["tblPr", "tblGrid", "tr"])
            if "H1.13.TBLCENTER" in rules:
                _ordered_child(tblpr, "jc", TBLPR_ORDER).set(q("val"), "center")
                edits += 1
            if "H1.13.TBLSPACING" in rules:
                for cp in b.el.iter(q("p")):
                    set_spacing(cp, line=240, lineRule="auto")
                edits += 1
            if "H1.13.TBLAFTER" in rules and nxt is not None and nxt.kind == "p":
                set_spacing(nxt.el, before=480)
                edits += 1
            if "H1.13.WRAP" in rules:
                for fl in tblpr.findall("w:tblpPr", NS):
                    tblpr.remove(fl)
                edits += 1
            rows = b.el.findall("w:tr", NS)
            if "H1.13.TBLKEEP" in rules and rows:
                if doc.table_height_pt(b.el) <= TABLE_FITS_PT:
                    for tr in rows:
                        set_row_flag(tr, "cantSplit")
                    chain = rows[:-1]
                else:
                    chain = rows[:1]  # long table: only the header stays with the first data row
                for tr in chain:
                    for cp in tr.iter(q("p")):
                        set_flag(cp, "keepNext")
                edits += 1
            if "H1.13.TBLJC" in rules:
                for cp in b.el.iter(q("p")):
                    if doc.styles.eff_ppr(parse_ppr(cp.find("w:pPr", NS))).get("jc") in ("both", "distribute"):
                        _ordered_child(ppr(cp), "jc", PPR_ORDER).set(q("val"), "left")
                edits += 1
            if "H1.13.TBLNOTE" in rules and rows:
                for cp in rows[-1].iter(q("p")):
                    set_flag(cp, "keepNext")
                edits += 1
            if "H1.13.TBLHEADER" in rules and rows:
                set_row_flag(rows[0], "tblHeader")
                edits += 1
            if "H1.13.TBLFONTMIX" in rules:
                sizes = Counter(doc.styles.eff_rpr(parse_ppr(cp.find("w:pPr", NS)).get("pStyle"), parse_ppr_r(r)).get("sz")
                                for cp in b.el.iter(q("p")) for r in runs_with_text(cp))
                size = sizes.most_common(1)[0][0] or 24
                for cp in b.el.iter(q("p")):
                    for r in runs_with_text(cp):
                        set_run_size(r, size)
                # A REF field re-inserts the source text in the source's size whenever Word updates it, which
                # undoes the fix on the next open/export. \* CHARFORMAT makes the result take the field code's size.
                for it in b.el.iter(q("instrText")):
                    code = it.text or ""
                    if code.strip().upper().startswith("REF ") and "\\*" not in code:
                        it.text = code.rstrip() + " \\* CHARFORMAT "
                    set_run_size(it.getparent(), size)
                edits += 1
            if "H1.13.TBLHEADFMT" in rules and rows:
                for cp in rows[0].iter(q("p")):
                    set_weight(cp, bold=True)
                edits += 1
        if "H1.21.REFKEEP" in rules:
            set_flag(p, "keepLines"); set_flag(p, "widowControl")
            edits += 1
        if "H1.21.REFLINK" in rules:
            m = re.match(r"^\[(\d+)\]", b.text)
            link = REF_LINKS.get(int(m.group(1))) if m else None
            if link:
                last = list(runs_with_text(p))[-1]
                new = copy.deepcopy(last)
                nt = new.find("w:t", NS)
                nt.text = " " + link
                nt.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                last.addnext(new)
                edits += 1
        if "H1.21.REFSPACING" in rules:
            set_spacing(p, before=None, after=120, line=240, lineRule="auto")  # single, 0 before, 6pt after
            edits += 1
        if "H1.21.REFALIGN" in rules:
            set_jc(p, "both")
            edits += 1
        if "H1.21.REFHANG" in rules:
            set_ind(p, left=720, hanging=720, firstLine=None)
            edits += 1
    return edits


def _issues(doc):
    found = Checker(doc).run()
    return [i for i in found if not (KEEP_REVISIONS and i.rule == "REV.TRACKED")]


def main(argv):
    global KEEP_REVISIONS, TEXT_WIDTH_TW
    KEEP_REVISIONS = "--keep-track-changes" in argv
    for i, a in enumerate(argv[1:], 1):
        if a in ("--university", "--config") and i + 1 < len(argv):
            cfg = purdue_format_check.load_university(argv[i + 1])
            purdue_format_check.apply_config(cfg)              # the checker's rule logic
            purdue_format_check.apply_config(cfg, ns=globals())  # this file's own uses
            TEXT_WIDTH_TW = int(TEXT_WIDTH_PT * 20)
    positional = []
    skip_next = False
    for a in argv[1:]:
        if skip_next:
            skip_next = False
        elif a in ("--university", "--config"):
            skip_next = True
        elif not a.startswith("--"):
            positional.append(a)
    src, dst = positional
    doc = Document(src)
    for it in range(1, 8):
        issues = _issues(doc)
        n_err = report(issues, f"ITERATION {it}: check before fixing", limit=3)
        if n_err == 0:
            break
        edits = fix_once(doc)
        print(f"--- iteration {it}: {edits} fix edits applied\n")
        doc.styles.refresh()
        doc.blocks, doc.sects = [], []
        doc._walk()
        if edits == 0:
            print("no automatic fix available for the remaining issues")
            break
    # write every part the fixer may have touched
    parts = {"word/document.xml": doc.doc, "word/styles.xml": doc.styles.root,
             "word/numbering.xml": doc.numbering.root, "word/settings.xml": doc.settings}
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            tree = parts.get(item.filename)
            if tree is not None:
                zout.writestr(item, etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True))
            elif item.filename in doc.media_dirty:
                zout.writestr(item, doc.media[item.filename])
            else:
                zout.writestr(item, zin.read(item.filename))
    if doc.media_dirty:
        print(f"recolored {len(doc.media_dirty)} picture(s) for 3:1 contrast: {', '.join(sorted(m.rsplit('/', 1)[-1] for m in doc.media_dirty))}")
    print("wrote", dst)
    final = _issues(Document(dst))
    return 0 if report(final, "FINAL CHECK of written file", limit=5) == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
