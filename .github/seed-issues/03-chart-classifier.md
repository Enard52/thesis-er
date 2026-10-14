# Labels: `good first issue`, `accessibility`
# Title: Teach the contrast check to tell charts apart from photo crops

The contrast fixer notes (in a `ponytail:` comment) that a photo crop beside a plain legend can pass the "few significant colors + light background" chart test, so a handful of background tones get remapped harmlessly. Harmless is not correct.

**Done when:** the chart/photo classifier from the fixer handles legend-heavy photo crops without remapping photographic tones, all existing self-test mutations still fire, and a regression case (photo crop + legend) is added to the self-test.
