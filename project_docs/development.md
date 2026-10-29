# Development And Publication

Reviewed: 2026-10-08. Run commands from the repository root. See
[the documentation index](README.md) for data ownership and task guides.
The public README remains nontechnical. This project needs no dev server,
backend, npm app build, secret, paid hosting or OpenAI API.

## Required Setup And Checks

Use an available Python 3 runtime with PyYAML; CI uses Python 3.12. A local
virtual environment is optional and keeps dependencies isolated:

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

Do not reinstall dependencies unnecessarily if the configured environment
already has them. Standard verification is:

```sh
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
python3 scripts/build_all.py
```

Run standalone validation even though the build also validates: it explicitly
checks all family/city/series registries. CI runs all three steps; it does not
commit regenerated files or independently confirm organizer facts.

Open `docs/index.html` directly for preview. Builders embed local assets;
no development server is required. Never manually edit generated HTML/ICS.
Source plus generated output belong in the same data/UI release.

## Browser Verification

Use browser smoke when adding conferences changes route/filter/map data or
when editing public UI. Inspect representative desktop and mobile screenshots.
Documentation-only edits can use unit/link/example checks and prove all public
artifacts unchanged without repeating an unrelated browser run.

`tests/browser_smoke.mjs` imports the submission, mobile-card, expansion and
venue-feature (cutoff clocks, focus, search, empty states, successors,
calendar menu, tablet and no-JS) suites. It freezes a reference date and checks desktop/mobile at
1440/1051/1050/768/390/320px, route/countdown/gate transitions, independent card
expansion, filters/scope matching, maps, branding, accessibility and overflow.
Catalog-specific expected counts/IDs need review after additions; derive them
from built data at the frozen date. Do not weaken semantics to satisfy old counts.
It blocks Giscus requests and never signs in, comments, posts on X or stars.

Browser checks need optional Playwright and an existing compatible browser.
In Codex, discover the configured Node/dependency paths through the workspace-
dependencies tool; otherwise use an isolated local maintainer installation.
Set `NODE_BIN` to the executable, `NODE_DEPENDENCIES` to its module directory
containing Playwright, and `CHROME_BIN` to an existing Chrome executable when
Playwright's default browser is unavailable. Do not add app dependencies merely
for this QA step. An isolated install outside the repository works, e.g.
`PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm install playwright@1.48.2` in a scratch
folder, with `CHROME_BIN` pointing at the system Chrome.

```sh
TOOLS_DIR="$(mktemp -d "${TMPDIR:-/tmp}/venue-radar-tools.XXXXXX")"
ln -s "$NODE_DEPENDENCIES" "$TOOLS_DIR/node_modules"
cp tests/*.mjs "$TOOLS_DIR/"
CHROME_BIN="$CHROME_BIN" SCREENSHOT_DIR="$TOOLS_DIR/previews" "$NODE_BIN" "$TOOLS_DIR/browser_smoke.mjs"
```

With no URL argument, the runner correctly builds a file URL from the current
checkout, including paths with spaces. To verify a published site, supply
`https://gon-uri.github.io/venue-radar/` as its final argument. Report unavailable
browser tooling rather than claiming checks ran. Keep helper imports together.

## Workbook Synchronization

The workbook is a review mirror, not a second database. Synchronize when
exported latest-edition fields, ranks/rates, topics or scope profiles change.
A correction to dates alone may not alter its mirrored columns. No workbook
rewrite is needed for documentation-only work.

The maintained helper uses optional `@oai/artifact-tool`, not a required Python
or browser dependency. It must be available in `NODE_DEPENDENCIES`. Reuse the
isolated `TOOLS_DIR` above, or prepare a fresh one with that module symlink.
In Codex, follow the spreadsheet skill's import/render/inspect workflow.

```sh
python3 scripts/export_catalog.py --output "$TOOLS_DIR/catalog.json"
cp scripts/sync_workbook.mjs "$TOOLS_DIR/"
"$NODE_BIN" "$TOOLS_DIR/sync_workbook.mjs" "$PWD/data/core_conferences_normalized_tags.xlsx" "$TOOLS_DIR/catalog.json" "$TOOLS_DIR/workbook-previews"
```

The exporter chooses the maximum edition year per exact series. The helper
preserves existing series order/native table formatting and definitions,
appends new series, synchronizes Catalog/Tag Vocabulary/Conference Scope,
refuses unexplained removals, checks values/formula errors and renders previews.
Add definitions for approved new leaves to its definition map as needed.
CCF's workbook source column retains PDF/page evidence; public rank links use
the separate webpage. This difference is intentional.

Inspect all three sheets for wrapping/clipping, numeric percentage/date formats
and preserved tables. Re-import the exported XLSX and compare catalog,
vocabulary and scope values/counts with the JSON/YAML, including new rows.
A successful export alone is not enough. If optional tooling is unavailable,
keep YAML authoritative and report the unsynchronized mirror; do not silently
replace the workbook or import old spreadsheet values into YAML.

## Branding Tools

Brand changes require their own approved scope. The logo and README banner are
derived from immutable sources under `assets/branding/`; do not recolor an
already recolored/resized output. Sharp verifies the four RGB colors and
unchanged foreground geometry/alpha; Playwright renders the real Audiowide font.
Both are optional maintainer dependencies, not runtime requirements.

With the same isolated runtime:

```sh
cp scripts/recolor_logo.mjs scripts/build_readme_banner.mjs "$TOOLS_DIR/"
"$NODE_BIN" "$TOOLS_DIR/recolor_logo.mjs" "$PWD"
CHROME_BIN="$CHROME_BIN" "$NODE_BIN" "$TOOLS_DIR/build_readme_banner.mjs" "$PWD"
python3 scripts/build_all.py
```

Inspect logo, banner, licensing notices and desktop/mobile results. Do not
regenerate artwork during a conference-data or documentation-only update.

## Publication Checklist

1. Review the diff and preserve unrelated local work. Check official evidence,
   metadata review dates and companion-file completeness. Update dataset
   `last_updated` **before** generation for reviewed data changes; do not change
   it merely because a build or documentation edit happened.
2. Synchronize mirrored fields as applicable. Run standalone validation, all
   Python tests and the full build; perform affected browser/visual checks.
   Rebuild twice if needed to confirm deterministic output.
3. Review generated HTML/feed links, estimated versus confirmed labels,
   gated countdowns, archive/map placement and existing UID stability.
   Source changes without rebuilt committed output are not a published update.
4. Check non-ICS whitespace with the following command. ICS intentionally uses
   CRLF and folded content spaces; separately inspect its line folding, event
   UIDs and timing instead of trimming whitespace mechanically:

   ```sh
   git diff --check -- . ':!docs/*.ics' ':!docs/conferences/*.ics' ':!docs/tags/*.ics'
   ```

5. Update affected current guides, dated evidence and material verification in
   public status; add an ADR only for a meaningful technical decision. Keep
   detailed session logs in ignored local notes and public README simple.
   Documentation-only work should leave `data/`, `assets/`, `scripts/`, `docs/`
   and the public README byte-identical; new documentation tests are acceptable.
   Follow [documentation policy](documentation_policy.md) and check
   `git ls-files -- private_notes/` is empty; never force-add private notes.
6. When publication is requested, commit source/data/output/docs together and
   push the intended branch. Current Pages deployment is `main/docs`; changing
   that configuration is not part of a routine update.
7. Verify both GitHub Build and Pages, then compare live HTML and representative
   aggregate/topic/edition feeds with the tested files. Run affected live
   browser checks when appropriate. A successful push alone is not proof of a
   deployed page. Record workflow IDs/results and any unresolved limitations;
   material results belong in public status, the detailed diary stays local.

Giscus authentication/posting is deliberately outside smoke tests. Owner setup
and rename safeguards are in [project services](data_maintenance.md#project-services).
The monthly maintenance process is editorial, never authorization to publish
unverified scraped dates or silently mutate the repository on a schedule.
