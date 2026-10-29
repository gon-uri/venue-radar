## Summary

<!-- What changed and why. Link the official sources reviewed for data changes. -->

## Publication checklist

See `project_docs/development.md` (Publication Checklist). Tick what applies;
write "n/a" with a reason otherwise.

- [ ] Official sources reviewed; `last_checked`, confidence and estimated labels reflect the evidence
- [ ] `data/metadata.yml` `last_updated` set **before** building (reviewed data changes only)
- [ ] `python3 scripts/validate.py`, `python3 -m unittest discover -s tests -v` and `python3 scripts/build_all.py` run (or `python3 scripts/release_check.py`)
- [ ] Regenerated `docs/` committed together with the source change; never hand-edited
- [ ] Browser checks run for UI changes or data changes affecting routes, filters or maps
- [ ] Workbook mirror synchronized, or not affected
- [ ] `project_docs/` updated (status/guides; ADR for a meaningful new decision)
- [ ] No `private_notes/` files staged
- [ ] Event UIDs and edition IDs stable; intentional removals listed in `data/retired_identities.yml`

## Verification notes

<!-- Checks actually performed, and anything not verified. -->
