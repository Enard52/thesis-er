# Labels: `good first issue`, `config`
# Title: Move the remaining handbook spacing values into universities/*.json

The first config pass externalized page geometry, fonts, zones, captions, and thresholds. The deeper spacing constants are still hard-coded, so a school with different gap rules still has to touch Python:

- figure/table gaps (`480` / `240` twips before/after)
- body line spacing (`360` = 1.5 lines) and first-line indent (`720` = 0.5 in)
- the accepted line-spacing set (`240, 360, 480`) and caption spacing pairs

**Done when:** every remaining handbook-derived measurement lives in the JSON config with its handbook section noted, `purdue.json` reproduces current behavior exactly (default run + `--selftest` = ALL RULES FIRE), and `universities/README.md` documents the new keys.
