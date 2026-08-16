# ARI Disease Metadata Manager

Public editor: https://aurint.ca/ari-editor/

This repository contains the curated autoimmune disease data, ontology artifacts, and
generated reports that support the ARI Disease Metadata Manager v2 shown on the public
site.

The editor is the main interface for reviewing and maintaining autoimmune disease
metadata. It presents the curated registry as a searchable, editable catalog with disease
detail panels and source-linked outputs.

## What the editor does

- Search diseases, synonyms, and codes
- Create new disease entries
- Search by symptoms
- Browse diseases alphabetically or by tissue target
- Review disease details in a split-pane layout
- Toggle edit mode for record maintenance
- Adjust settings and theme
- Display supporting panels, graphs, and ontology metadata in the footer

## Project scope

This repository supports the curated disease model behind the editor:

- Core disease records with ARI IDs and IRIs
- Synonyms, subtypes, definitions, and evidence metadata
- SNOMED, OMOP, DX code, and DOID mappings
- Proposed diseases and proposed changes
- Supplemental per-disease reports and indexes
- Grounding workflows for local ontology matching

## Main directories

| Path | Purpose |
| --- | --- |
| `data/` | Master list instructions, report outputs, and supporting source tables |
| `data_model/` | Reference spreadsheets and model snapshots |
| `mappings/` | ARI equivalency and SSSOM mapping exports |
| `notebook/` | Notebook-driven data preparation and grounding scripts |
| `ontologies/` | ARI ontology artifacts |
| `sparql/` | SPARQL queries and generated term sets |

## Key outputs

- `data/4-reports/1_Core_ARI_Diseases.xlsx`
- `data/4-reports/2_Proposed_Diseases.xlsx`
- `data/4-reports/3_Proposed_Changes.xlsx`
- `data/4-reports/4_Additional_Info_Index.xlsx`
- `data/4-reports/5_DOID_Mapping.xlsx`
- `data/4-reports/6_DOID_Matches_All.xlsx`
- `data/4-reports/7_SNOMED_Matches_All.xlsx`

## Grounding workflow

The grounding pipeline in `notebook/ari-grounding/` builds local DOID and SNOMED matches
from repository data only.

Scripts run in this order:

1. `parse_doid_local.py`
2. `ground_doid.py`
3. `ground_snomed.py`
4. `make_match_reports.py`

## Source data

Primary inputs are the master list in `data/1-master/` and the supporting files in
`data/3-meta-database-sources/`, `ontologies/`, `mappings/`, and `sparql/results/`.

## Mapping validation

`.github/scripts/validate_mappings.py` checks the two mapping exports against each other
and against the ontology. It needs only the standard library:

```bash
python .github/scripts/validate_mappings.py
```

Add `--since main` to report only the rows a branch changed. Two workflows run it:

| Workflow | Trigger | Scope |
| --- | --- | --- |
| `Validate mappings` | pull requests touching `mappings/` or `ontologies/` | rows the branch added or rewrote — fails the check |
| `Audit mappings` | Mondays 07:00 UTC, or on demand | every row, so the standing backlog stays visible |

What it catches:

- Structural damage — wrong header, wrong column count, stray tabs, mixed line endings,
  a byte-order mark, a prefix missing from the SSSOM `curie_map`.
- Identifiers that are not identifiers — `mesh:null` and other placeholders, doubled
  prefixes such as `MONDO:MONDO:0014523`, ids that do not fit their vocabulary's shape,
  and ICD-9 codes filed under the `icd10cm` prefix.
- Contradictions — the same pair recorded as both confirmed and flagged wrong, duplicate
  rows, one disease under two different labels, dates in the future, unattributed edits.
- Drift between `ari.sssom.tsv` and `ari.equivalencies.tsv`, which is how spreadsheet
  round-trips show up: `362.50` losing its trailing zero, `0111157` losing its leading
  ones.
- Disagreement with the ontology — a disease id or label that does not match, a
  cross-reference the curators flagged wrong that is still stored and still served, or a
  confirmed one that was never stored.

## Working rules

- Prefer the curated master list as the source of truth.
- Keep changes surgical and focused on one data path at a time.
- Use local ontology and report artifacts rather than online sources when generating
  matching outputs.
- Do not read `.env` files unless explicitly authorized.

## Related documentation

- [Data instructions](data/instructions.md)
- [Data overview](data/README.md)
- [Reports overview](data/4-reports/README.md)
