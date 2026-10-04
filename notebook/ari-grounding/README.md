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

Diseases, preferred names and synonyms are read from `ontologies/ari_t1d.owl`
(`ari_diseases.py`): the curated, non-retired diseases and their current `ARI_Synonym`
values, so a synonym withdrawn by the synonym review no longer produces matches. The
existing SNOMED codes the SNOMED match is checked against are the ontology's `ARI_SNOMED`.

For each disease the grounder is queried with the preferred name first, then each synonym;
the highest-scoring Gilda match is kept (`Matched Via` records which string matched). The
grounder terms are built from each ontology's label + synonyms.

SNOMED is restricted to `domain_id = Condition` and `standard_concept = 'S'` (valid standard
concepts), which aligns matches with the curated standard concepts in the master and avoids
inactive/duplicate concepts.

## Scripts

| Script | Purpose |
| --- | --- |
| `ari_diseases.py` | Diseases, names, synonyms and SNOMED codes from the ontology, shared by the grounders and the matrix |
| `parse_doid_local.py` | Parse `doid.owl` (proper XML parsing, handles nested classes) -> `doid_records.json` |
| `ground_doid.py` | Build DOID Gilda grounder, ground all diseases -> `doid_matches_all.csv` |
| `ground_snomed.py` | Build SNOMED Gilda grounder (standard Condition concepts), ground all -> `snomed_matches_all.csv` |
| `make_match_reports.py` | Format CSVs into `data/4-reports/6_DOID_Matches_All.xlsx` and `7_SNOMED_Matches_All.xlsx` |
| `predict_target_matches.py` | Predict a match per (disease, database) pair by cross-reference expansion -> `target_predictions.json` |
| `resolve_target_labels.py` | Resolve a label for every mapped and predicted target id -> `target_labels.json` |
| `build_disease_target_matrix.py` | Cross every disease against every target database -> `data/4-reports/8_Disease_Target_Mappings.xlsx` |

Run order: `parse_doid_local.py` → `ground_doid.py` → `ground_snomed.py` → `make_match_reports.py`.
Requires `gilda`, `openpyxl` (`pip install gilda openpyxl`).

## Results (all 213 active ontology diseases)

- **DOID**: 128 matched, 85 unmatched. Matching resolves synonyms (e.g. Kawasaki, Castleman, Goodpasture).
- **SNOMED**: 189 matched; 185 agree with a SNOMED code the ontology already stores.

The SNOMED report colour-codes the `Agrees w/ Existing` column: green = agrees with the ontology's code, amber = differs.

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
An anchor that more than four hub terms cross-reference (`MAX_ANCHOR_HUBS`) is too broad
to expand at all: ICD-10 `E10` is an xref of 22 DOID terms, one per type 1 diabetes subtype,
and would otherwise predict each of them and its OMIM locus (#111). Every other anchor reaches
one to four hubs.
Three filters keep the output honest. A term the curators already **rejected** for that
disease and database is never predicted. Neither is a term they **confirmed for the
disease's parent or subtype** (`hasParentDisease`), since a term that is exactly one of the
pair is not exactly the other (unless the curators confirmed it for both), and a hub term excluded either way is not expanded. Predicted
SNOMED codes are restricted to **standard, non-retired** concepts (ontology xrefs still point
at codes SNOMED has since deprecated — that alone accounted for most early false
predictions). SSSOM rows marked `Superseded by the …` are past judgements and are ignored.

Validation against the 715 curated confirmed mappings (2026-09-27): **651 top predictions
reproduce the curated term**, 28 name a different one, 36 produce nothing; for 17 of the 28
the curated term is still present further down the candidate list. Grounding from the
ontology's current synonyms instead of the master-list snapshot moved this from 641 / 38 / 34
(measured on the 713 mappings before PR #104 added two).

Re-measured on 2026-10-04 over every live confirmed row in `ari.sssom.tsv` (1,359): **1,227 top
predictions reproduce the curated term**, 54 name a different one, 78 produce nothing. Without the
parent/subtype and superseded-row filters the same rows give 1,229 / 55 / 75. Each top match
those filters lose had been reached only through a hub term the curators rejected for the
disease, or one confirmed for its subtype.

After the ARI#108 review and the fan-out cap (2026-10-04), over 1,363 live confirmed rows:
**1,230** reproduce the curated term, 55 name a different one, 78 produce nothing. The cap
changes none of these; it only removes 20 low-support DOID and 20 OMIM candidates from type 1
diabetes.
