# ARI Disease Metadata Manager

Public editor: https://aurint.ca/ari-editor/

The ARI project is a curated autoimmune disease metadata registry. This repository
contains the source data, ontology/mapping artifacts, grounding notebooks, and generated
reports that support the editor shown on the public ARI site.

## What the editor does

The public editor is a disease metadata manager for the Autoimmune Registry. It provides:

- Search across diseases, synonyms, and codes
- Creation of new disease entries
- Symptom-based lookup
- Alphabetical and tissue-target tree views
- Disease detail panels
- Edit mode for record maintenance
- Settings, theme toggle, and supporting panels/graphs

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
| `mappings/` | ARI equivalence and SSSOM mapping exports |
| `ontologies/` | ARI ontology artifacts |
| `notebook/` | Notebook-driven data preparation and grounding scripts |
| `sparql/` | SPARQL queries and generated term sets |
| `data_model/` | Reference spreadsheets and model snapshots |

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
from repository data only. The scripts are run in this order:

1. `parse_doid_local.py`
2. `ground_doid.py`
3. `ground_snomed.py`
4. `make_match_reports.py`

## Source data

Primary inputs are the master list in `data/1-master/` and the supporting files in
`data/3-meta-database-sources/`, `ontologies/`, `mappings/`, and `sparql/results/`.

## Working rules

- Prefer the curated master list as the source of truth.
- Keep changes surgical and focused on one data path at a time.
- Use local ontology and report artifacts rather than online sources when generating
  matching outputs.
- Do not read `.env` files unless explicitly authorized.

