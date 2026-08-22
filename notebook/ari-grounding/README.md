# ARI Disease Grounding (DOID + SNOMED)

Lexical grounding of all ARI core diseases to **DOID** and **SNOMED**, using the same
method as `notebook/build_autoimmune-single.py` — [Gilda](https://github.com/gyorilab/gilda)
lexical matching, which is the matcher `pyobo.get_grounder(...)` uses under the hood.

Unlike the notebook scripts (which download ontologies online via pyobo), these scripts
build the Gilda grounder from **local data only**, to comply with the project rule against
online sources in reports:

- DOID — `data/2-databases/doid.owl` (release 2026-04-30)
- SNOMED — `data/2-databases/snomed/CONCEPT.csv` + `CONCEPT_SYNONYM.csv` (OMOP/Athena export, SNOMED vocabulary)

## Method

For each disease the grounder is queried with the preferred name first, then each synonym;
the highest-scoring Gilda match is kept (`Matched Via` records which string matched). The
grounder terms are built from each ontology's label + synonyms.

SNOMED is restricted to `domain_id = Condition` and `standard_concept = 'S'` (valid standard
concepts), which aligns matches with the curated standard concepts in the master and avoids
inactive/duplicate concepts.

## Scripts

| Script | Purpose |
| --- | --- |
| `parse_doid_local.py` | Parse `doid.owl` (proper XML parsing, handles nested classes) -> `doid_records.json` |
| `ground_doid.py` | Build DOID Gilda grounder, ground all diseases -> `doid_matches_all.csv` |
| `ground_snomed.py` | Build SNOMED Gilda grounder (standard Condition concepts), ground all -> `snomed_matches_all.csv` |
| `make_match_reports.py` | Format CSVs into `data/4-reports/6_DOID_Matches_All.xlsx` and `7_SNOMED_Matches_All.xlsx` |
| `predict_target_matches.py` | Predict a match per (disease, database) pair by cross-reference expansion -> `target_predictions.json` |
| `resolve_target_labels.py` | Resolve a label for every mapped and predicted target id -> `target_labels.json` |
| `build_disease_target_matrix.py` | Cross every disease against every target database -> `data/4-reports/8_Disease_Target_Mappings.xlsx` |

Run order: `parse_doid_local.py` → `ground_doid.py` → `ground_snomed.py` → `make_match_reports.py`.
Requires `gilda`, `openpyxl` (`pip install gilda openpyxl`).

## Results (all 215 core diseases)

- **DOID**: 133 matched, 82 unmatched. Matching resolves synonyms (e.g. Kawasaki, Castleman, Goodpasture).
- **SNOMED**: 193 matched. Of the 201 diseases with an existing master SNOMED code, **188 agree**
  with the Gilda match (validation), **5 differ** (review candidates), 8 had no lexical match.
  No-code diseases were not found in SNOMED standard Condition concepts.

The SNOMED report colour-codes the `Agrees w/ Existing` column: green = agrees with master, amber = differs.

## Disease x target database matrix

`predict_target_matches.py` → `resolve_target_labels.py` → `build_disease_target_matrix.py` produce
`data/4-reports/8_Disease_Target_Mappings.xlsx`: one row per (disease, target database)
pair, so an unmapped pair is as visible as a mapped one. These two scripts are independent
of the Gilda grounding above — they report the **curated** mappings in
`mappings/ari.sssom.tsv`, not lexical matches.

Labels come from the local vocabulary copies wherever one covers the vocabulary. Two
exceptions are read from the EBI OLS4 API, because no usable local copy exists: **Orphanet**
(no ORDO download in `data/2-databases`) and **NCI Thesaurus** (the local OMOP `NCIt`
export only carries AJCC staging chapters, not NCIT concept codes). **UMLS** has no label
source at all here, so a CUI is labelled with the DOID or Mondo term that cross-references
it — the same route `sparql/get_UMLS_id.md` uses to extract CUIs. Every row records which
source produced its label in `Target Mapping Name Source`.

### Predicted matches

Every (disease, database) pair also carries a predicted match, so an unreviewed pair
arrives with a candidate rather than a blank. Two offline routes feed it:

1. **Lexical grounding** — the Gilda matches already in `doid_matches_all.csv` and
   `snomed_matches_all.csv` (DOID, SNOMED, OMOP).
2. **Cross-reference expansion** — Mondo and DOID terms carry equivalence cross-references
   into every other target database. From an anchor (a curated `skos:exactMatch`, or a
   lexical match) the hub term that *is* or *cross-references* that anchor is found, and
   the hub's own cross-references become predictions for the remaining databases. Only
   `MONDO:equivalentTo` / `MONDO:exact` qualified xrefs are used; hierarchy, MEDGEN and
   obsolete-side qualifiers are not equivalence claims.

Each hub is scored by how many of the disease's own identifiers reach it (curated anchors
count double), and candidate ranking sums those scores across routes — so a candidate
corroborated by several hubs outranks one reached through a single broad cross-reference.
Two filters keep the output honest: a term the curators already **rejected** for that
disease and database is never predicted, and predicted SNOMED codes are restricted to
**standard, non-retired** concepts (ontology xrefs still point at codes SNOMED has since
deprecated — that alone accounted for most early false predictions).

Validation against the 367 curated mappings: **330 top predictions reproduce the curated
term**, 22 name a different one, 15 produce nothing; for 18 of the 22 the curated term is
still present further down the candidate list.
