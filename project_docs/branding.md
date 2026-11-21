# Current Branding

Reviewed: 2026-11-21 (identity v2, ADR-057). This is the implemented identity,
not a design proposal. Regeneration commands are in
[development](development.md#branding-tools).

## Mark

The Ping tile: a petrol-teal rounded tile with three ripples clipped by the
tile edges and a coral blip in the upper right. It reads as "found, and close".
`assets/venue-radar.svg` is the master drawing (48-unit grid, viewBox
`4 4 40 40`):

| Element | Geometry |
| --- | --- |
| Tile | `rect x=4 y=4 w=40 h=40 rx=11` |
| Ripples | circles at (31, 17), r 9.5 / 17 / 24.5, stroke 3.2, opacity 1 / .7 / .45, clipped by the tile, stroked in the surface colour (cut-outs) |
| Blip | circle at (31, 17), r 4.6 |

The SVG uses CSS custom properties with light fallbacks
(`--mark-tile`, `--mark-blip`, `--bg`), so the page inlines it and it follows
the theme. `assets/favicon.svg` is the 16 px variant of the same drawing
(outer ripple dropped) with a `prefers-color-scheme: dark` switch; it is
embedded in the generated page.

| Role | Light | Dark |
| --- | --- | --- |
| Tile | `#0D6064` | `#22989D` |
| Blip | `#C85C62` | `#E8787D` |
| Ripple cut-outs | page background `#F7FBFB` | page background `#101C1F` |

Don'ts: no centred blip (it becomes a bullseye), no outline-only tile, no
calendar frame around it, no mid-teal background behind it.

## Wordmark And Type

- Wordmark: Sora SemiBold (600), letter-spacing -0.02em, no synthetic styles.
  Desktop mark/title 40 px / 28 px; phones 32 px / 22 px.
- Interface: Inter (variable). Countdowns, cutoff times and rank codes: Geist
  Mono with tabular figures.
- Scale: 11, 12, 13, 14, 16, 20, 28 px. Small uppercase column heads track
  +0.06em.

All three are SIL OFL 1.1 Latin subsets from the Fontsource 5.3.0 packages,
embedded as WOFF2 data by `scripts/build_site.py` (no runtime font request).
Notices are in `assets/vendor/*-OFL.txt`, the generated HTML and
`THIRD_PARTY_NOTICES.md`; the fonts keep their own license.

## Colour

Tokens live in `assets/base.css` (`:root`, then a `prefers-color-scheme: dark`
block); components use tokens only. Teal marks interaction; status has its own
palette and every status pill carries a shape: filled dot (open), ring
(scheduled), half dot (opportunity), dashed ring and outline (estimated), bar
(closed), dotted ring (unannounced). Countdowns turn amber with a clock under
7 days and coral with a dot under 48 hours (`data-urgency`). Ranks use a colour
scale (ADR-060): A* solid dark green, A green, B yellow, C orange. `tests/test_site_assets.py` checks WCAG AA for
the documented text pairs in both themes.

## Banners, Social Card And Screenshots

- `assets/branding/venue-radar-banner.png`: 1400x175 white README banner.
- `assets/branding/venue-radar-banner-dark.png`: 1400x175 transparent banner
  for GitHub's dark themes; its ripples are cut in GitHub's dark canvas colour
  `#0D1117`, title `#E6EDF3`.
- `assets/branding/social-card.png`: 1200x630 link-preview card.
- `assets/readme/*.webp`: README screenshots of the real page.

All are rendered from the SVG mark and the embedded fonts by the scripts in
the development guide. In README both banners sit in a bare `<picture>`
(GitHub's renderer pulls the image out of a `<picture>` inside a link), so the
"Open Venue Radar" heading below is the calendar link. Original artwork uses
CC BY 4.0. The previous raster calendar mark and Audiowide title were retired
by ADR-057; the earlier logo candidates under `assets/branding/` are history
only.
