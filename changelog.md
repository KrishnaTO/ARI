# Changelog

## port-icd9-retirement-to-main

- Ports #57 to `main`. That PR retired ICD-9 but merged into
  `feature/metadata-manager_v2/ARI`, so none of it reached this branch — `main` still
  listed ICD9/ICD9CM as active sources, still grouped ICD-9 into the report's ICD column,
  and still drew the ICD9 node in the ontology diagram.
- Removed the `ICD9` and `ICD9CM` rows from `data/3-meta-database-sources/meta-databases.csv`.
- Narrowed the xref grouping in `notebook/ari-grounding/make_match_reports.py` from
  `["ICD10", "ICD9", "ICD-10", "ICD-9"]` to `["ICD10", "ICD-10"]`, so the report's "ICD
  xrefs" column stops picking up ICD-9.
- Removed the ICD9 node and its edge from `connecting_ontologies.drawio`.
- Carries no data change. The ICD-9 codes themselves are removed separately.

## remove-false-xref-mappings

- Removed **140 database cross-reference ids across 32 diseases** that curators had already flagged as wrong. Flagging a mapping on the [cross-reference review page](https://aurint.ca/ari-editor/ref-edits/) records the judgment in `mappings/ari.sssom.tsv` as an `skos:exactMatch` row with `predicate_modifier: Not`, but it never removed the id from the ontology — so 125 negative judgments had accumulated with the wrong ids still stored and still served.
- Scope is exactly the ids explicitly flagged negative; unreviewed ids were left alone. Verified before and after against the curated positives: no confirmed mapping was affected (the 25 confirmed-but-unstored ids all pre-date this change). Stored cross-reference ids: 1639 -> 1499.
- By database: SNOMED 36, DXCODE 38, OMOP 37, ICD-10 14, UMLS 4, DOID 4, MeSH 3, NCI 1, MONDO 1, Orphanet 1, OMIM 1. DXCODE is included because it shares SNOMED's CURIE prefix and mirrors its values, so a wrong SNOMED code would otherwise survive under a second property.
- **19 database/disease pairs are now empty** because every id they held was flagged — Chronic Lyme disease loses all its SNOMED, DOID and ICD-10 codes; Immune thrombocytopenia its only DOID and both ICD-10 codes. Those cells now read as "no term recorded", which is the honest state.
- Annotation values that pack several ids into one comma-separated string were filtered and rejoined in place, so the diff stays confined to the affected `ARI_*` properties. No changelog annotations were appended to the individual diseases — the SSSOM negatives already carry each judgment and its author.
- Advances #23 ("Remove multiple IDs in favour of exact matches to disease"); the remaining subtasks on that issue are untouched.

## docs/ari-editor-readme

- Added a root `README.md` focused on the public ARI Disease Metadata Manager at `https://aurint.ca/ari-editor/`.
- Documented the editor's visible workflow, project scope, key outputs, and local grounding process.
- Added this root `changelog.md` to track branch-level updates.
