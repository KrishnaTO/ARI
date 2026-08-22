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
| `resolve_target_labels.py` | Resolve a label for every `object_id` in `mappings/ari.sssom.tsv` -> `target_labels.json` |
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

`resolve_target_labels.py` → `build_disease_target_matrix.py` produce
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
