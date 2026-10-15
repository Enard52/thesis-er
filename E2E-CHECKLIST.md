# E2E checklist — thesis-er site

Run this pass against the deployed URL before every release. Anything marked
**auto** is covered by `node scripts/smoke_frontend.js`, `python3
scripts/check_links.py`, or the backend matrix below; the rest needs a human
with a browser. File failures as site bugs with steps to reproduce — never fix
inside this pass.

## Tab deck (auto: smoke §6 + human: motion)

- [ ] All five nav tabs bring their card forward; the old card visibly recedes
- [ ] Deep link `#rules` (etc.) opens the right card on load; back/forward works
- [ ] Unknown hash falls back to the checker card, no blank page
- [ ] Background cards are `inert` — Tab key never enters them
- [ ] `prefers-reduced-motion`: no 3D, no float, background cards hidden
- [ ] Hero ("Will your thesis pass review?") is never overlapped by a card

## Uploader (human + backend matrix)

- [ ] Drag valid `.docx` → queued with name + size; picker path identical
- [ ] Reject: non-`.docx` extension, renamed non-zip, over 50 MB — each with its own plain-English message
- [ ] Stray drop outside the zone never navigates the page away
- [ ] Remove button clears queue and resets the picker
- [ ] Run with no file → "Choose a .docx file first."
- [ ] Backend offline → run-locally guidance, never a dead button

## Report (auto: smoke §5 + human)

- [ ] FAIL and PASS verdicts render with the right color band
- [ ] ADA section and Formatting section split findings by `A11Y` prefix
- [ ] Empty sections say "No issues found in this section."
- [ ] Copy summary writes verdict + every rule to the clipboard
- [ ] Download full report saves valid JSON
- [ ] "Report looks wrong?" opens a pre-filled issue with filename + page URL

## Links (auto: check_links.py)

- [ ] Zero dead links: fragments, relative files, repo blobs, issue templates, portfolio

## Backend matrix (run against the live backend)

```bash
BASE=https://<render-service>
curl -s $BASE/api/universities                                  # {"universities": ["purdue"]}
curl -s -X POST $BASE/api/check -F "file=@t.docx" -F "university=purdue"   # verdict JSON
curl -s -X POST $BASE/api/check -F "file=@t.txt;filename=t.docx"          # 400 not a .docx
curl -s -X POST $BASE/api/check -F "file=@t.docx" -F "university=nope"    # 400 unknown school
```

- [ ] Valid thesis returns verdict + ada/formatting groups; temp file deleted (server log line)
- [ ] Each error case returns JSON `{"error": ...}`, never a stack trace

## Keyboard + small screen (human)

- [ ] Full pass with keyboard only: nav, picker, run, copy, download, every link
- [ ] 360px wide: no horizontal scroll, no control mouse-only or overflowing
