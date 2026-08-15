# Changelog

## remove-icd9-codes

- Removed ICD9 and ICD9CM from `data/3-meta-database-sources/meta-databases.csv` (issue #55: superseded by ICD-10 mapping).
- Removed ICD9/ICD-9 from the xref grouping in `notebook/ari-grounding/make_match_reports.py`; the "ICD xrefs" report column now only picks up ICD10/ICD-10.
- Removed the ICD9 node from `connecting_ontologies.drawio`.

## docs-ari-editor-readme

- Added a root `README.md` focused on the ARI editor at `https://aurint.ca/ari-editor/`.
- Documented the editor workflow, visible UI panels, and supporting project areas.
- Added this root `changelog.md` to track branch-level updates.
