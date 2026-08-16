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
## fix-remaining-mapping-errors

- Clears the last 25 validation errors. The audit is now **0 errors, 17 warnings**.
- **Removed 9 `null` cross-reference rows from each export.** Four were flagged-wrong rows,
  which recorded a curator rejecting nothing at all. Five were *confirmations* — a mapping
  asserted to exist against an identifier that was never written. The rows are removed
  rather than repaired: supplying the real id is a curation judgment, and asserting
  `NoTermFound` instead would claim the vocabulary has no term, which is demonstrably
  false in at least one case. The nine pairs need re-review: ARI:0001005 and ARI:0001010
  (NCIt), ARI:0001017, ARI:0001094 and ARI:0003 (DOID), ARI:0001105, ARI:0001110 and
  ARI:0001113 (MeSH), ARI:0001108 (OMIM).
- Worth noting on that last point: #49 supplied `mesh:C580192` for ARI:0001105 by review
  suggestion on 2026-08-03, and a `mesh:null` row dated 2026-08-07 has since replaced it.
  A hand-corrected value was overwritten by the same defect four days later, which is the
  regression the new CI check exists to stop.
- **`MONDO:MONDO:0014523` → `MONDO:0014523`** in both exports — the prefix had been
  concatenated onto a value that already carried it.
- **`DOID:111157` → `DOID:0111157`** in `ari.equivalencies.tsv`, resolving the last drift
  between the two exports. The ontology stores `0111157` for ARI:0001011, so the leading
  zeros were lost on the equivalencies side, not invented on the SSSOM side.
- **Two `ARI_MONDO` values de-prefixed** in the ontology — ARI:0001080 and ARI:0002 stored
  `MONDO:0005147` and `MONDO:0011027` where the other 55 MONDO values are bare digits.
- **Removed the ICD-10 range `I00-I02`** from Rheumatic fever (ARI:0001182). Nothing is
  lost: the disease already records `I00` as a single code alongside it, and a range is
  not an exact match.
- The 17 remaining warnings are unchanged and non-blocking: 11 confirmed mappings that are
  not stored on their disease, and 6 diseases holding a DXCODE with no SNOMED counterpart.

## fix-ari-id-padding

- Zero-padded the `source_id` column on **69 rows in `mappings/ari.equivalencies.tsv`**,
  covering 12 diseases that were written as `1001` where the ontology and
  `mappings/ari.sssom.tsv` both spell them `0001001`.
- The ontology's `ARI_ID` is the one spelling; the fix reads the correct form from
  `ontologies/ari_t1d.owl` rather than assuming a width, which matters because ARI:0002
  and ARI:0003 are genuinely four digits there and must not be re-padded to seven.
- Nothing else changed — only column 2 differs on every rewritten row, and no row was
  added or removed. The effect is that all three files now join on disease id without
  normalisation, which is what made the earlier drift between the two exports hard to see.

## remove-icd9-codes-from-data

- Removed **89 ICD-9-CM codes** filed under ICD-10 fields: 61 `ARI_ICD10` values in
  `ontologies/ari_t1d.owl` across 53 diseases, and the 14 matching rows in each of
  `mappings/ari.sssom.tsv` and `mappings/ari.equivalencies.tsv`.
- The rule is unambiguous: every ICD-10-CM code begins with a letter, so a digit-led value
  in an ICD-10 field is an ICD-9 code under the wrong vocabulary. `446.1`, `720.0` and
  `390-392.99` are ICD-9; `M30.3`, `M45` and `E10` are not. Letter-led values were left
  alone, including the range `I00-I02` on Rheumatic fever, which is a separate problem.
- **4 diseases now have no ICD-10 code at all** because every code they held was ICD-9:
  ARI:0001032, ARI:0001033, ARI:0001119 and ARI:0001201. Those cells now read as no term
  recorded, which is the honest state.
- Of the 14 mapping rows, 4 were confirmations and **10 were negative judgments** — a
  curator had already reviewed the code and rejected it. Dropping them removes a record,
  but a rejection of a code that cannot be represented in the target vocabulary carries no
  information forward; 9 of the 10 already had no stored id to guard. The affected
  diseases are ARI:0001012, 0001014, 0001061, 0001062, 0001063, 0001065, 0001068,
  0001073, 0001074 and 0001107.
- Three unrelated errors fall out of this. `ARI:0001012 -> icd10cm:720.0` was recorded as
  both confirmed and flagged wrong, and was the one id still stored after #60 despite
  being flagged; both rows and the stored value are ICD-9, so all three go together. Two
  of the six cross-file drifts (`362.50`/`362.5` and `720.0`/`720`) go with them.
- Note that #57 retired ICD-9 from `meta-databases.csv`, `make_match_reports.py` and the
  ontology diagram, but it merged into `feature/metadata-manager_v2/ARI` rather than
  `main`, so none of that reached this branch. This change covers the data only; porting
  #57 to `main` is still outstanding.

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
