# Current Branding

Reviewed: 2026-10-29. This is the implemented identity, not a design proposal.
Regeneration commands are in [development](development.md#branding-tools).

## Logo And Banner

Venue Radar uses a calendar outline containing radar arcs and a filled sector
sweep, with the location dot inside the sector. Preserve the existing geometry.

| Role | Color |
| --- | --- |
| Calendar border | `#263238` |
| Radar arcs, center and sector | `#38A6B0` |
| Location dot | `#C85C62` |
| Calendar interior and banner background | `#FFFFFF` |

The exterior and space above the binding tabs remain transparent in the PNG
logo. Alpha antialiasing does not introduce additional nontransparent RGB colors.
`scripts/recolor_logo.mjs` preserves source foreground positions/alpha and fills
the calendar interior white; it does not redraw or trace the mark.

- `assets/venue-radar-original.png`: original raster generation provenance.
- `assets/branding/venue-radar-source.png`: immutable 256px pre-recolor source.
- `assets/venue-radar.png`: current header mark.
- `assets/branding/venue-radar-banner.png`: 1400x175 white README banner pairing
  the current mark with the actual Audiowide title face.
- `assets/favicon.svg`: separate radar-only mark on opaque white, not the full
  calendar logo. It is embedded in the generated page.
- `assets/branding/social-card.png`: 1200x630 link-preview card (logo, Audiowide
  title, short description) rendered by `scripts/build_social_card.mjs`.
- `assets/readme/*.webp`: README screenshots of the real page (desktop/phone
  hero and host-city map), rendered by `scripts/build_readme_images.mjs`.
  They illustrate the site rather than certify current dates.

Do not recolor an already transformed output. The banner uses website
proportions/optical alignment scaled by 1.5 and links to the calendar in README.
Original artwork uses CC BY 4.0; preserve the separate third-party notices.

## Title Typography And Alignment

The title uses Audiowide's native weight 400 with synthetic styling disabled.
Body/table fonts are unchanged. The Latin WOFF2 is embedded from
`assets/vendor/audiowide-latin.woff2` by `scripts/build_site.py`, with a system
fallback and `font-display: swap`; there is no runtime Google Fonts request.

The font's SIL OFL 1.1 notice is in `assets/vendor/Audiowide-OFL.txt` and the
generated HTML, with attribution in `THIRD_PARTY_NOTICES.md`. This third-party
font is not covered by the project's original-artwork license.

- Desktop title/logo: 42px / 82px; title optical offset: 2px.
- Mobile title/logo: 34px / 66px; title optical offset: 1.5px.
- Mobile brand padding: 4px, retaining subtitle separation for wrapped titles.
- Letter spacing: zero. Check visible mark/letter alignment, not just line boxes.

Logo/banner scripts verify geometry/palette, while browser regressions check
the loaded embedded font, unchanged body font, responsive alignment and bounds.
Current assets/tests are authoritative if a historical preview differs. Font
specimens and rejected logo/copy options are optional local working history,
not prerequisites for maintaining the identity.
