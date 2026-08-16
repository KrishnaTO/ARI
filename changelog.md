# Changelog

## ci-workflows-mapping-files

- Added `.github/scripts/validate_mappings.py` and two workflows that run it. The checks
  were derived from problems that actually reached `main` — the `mesh:null` and
  `DOID:null` ids caught by hand in code review on #49 and #52, the ICD-9 codes #57
  retired from the source list but not from the data, the `MONDO:MONDO:0014523` double
  prefix, and the flagged-but-still-stored ids #60 had to clear out.
- **`Validate mappings`** gates pull requests that touch `mappings/` or `ontologies/`. It
  reports only rows the branch added or rewrote, so a curator submitting one disease is
  never blocked by debt they did not introduce. Findings appear as inline annotations on
  the changed line.
- **`Audit mappings`** runs the same checks over every row, weekly and on demand, so the
  standing backlog stays visible without turning every merge red.
- The validator is standard library only, so CI needs no install step, and it runs
  locally with `python .github/scripts/validate_mappings.py`.
- The first full audit against `main` reports **193 errors and 17 warnings**, all
  pre-existing and none corrected here. Two follow-up branches clear the bulk mechanically
  — `remove-icd9-codes-from-data` (88 ICD-9 codes filed under ICD-10 fields) and
  `fix-ari-id-padding` (69 rows whose ARI id is not padded the way the ontology spells
  it) — which takes the audit to **25 errors and 17 warnings**.
- What remains after those is the part that needs a curator, not a script: 18 literal
  `null` identifiers, the `MONDO:MONDO:0014523` double prefix, two MONDO values stored
  with their prefix where the other 55 are bare, the ICD-10 range `I00-I02`, and one
  cross-file drift where `ari.sssom.tsv` has `DOID:0111157` against the equivalencies
  export's `DOID:111157`.

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
