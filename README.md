# ARI Disease Metadata Manager

Public editor: https://aurint.ca/ari-editor/

This repository contains the curated data, ontology artifacts, mapping tables, and generated reports that support the ARI Disease Metadata Manager v2 shown on the public site.

The editor is the primary interface for reviewing and maintaining autoimmune disease metadata. It exposes the curated registry as a searchable, editable catalog with disease detail panels and source-linked outputs.

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

The grounding pipeline in `notebook/ari-grounding/` builds local DOID and SNOMED matches from repository data only.

Scripts are run in this order:

1. `parse_doid_local.py`
2. `ground_doid.py`
3. `ground_snomed.py`
4. `make_match_reports.py`

## Source data

Primary inputs are the master list in `data/1-master/` and the supporting files in `data/3-meta-database-sources/`, `ontologies/`, `mappings/`, and `sparql/results/`.

## Working rules

- Prefer the curated master list as the source of truth.
- Keep changes surgical and focused on one data path at a time.
- Use local ontology and report artifacts rather than online sources when generating matching outputs.
- Do not read `.env` files unless explicitly authorized.

## Related documentation

- [Data instructions](data/instructions.md)
- [Data overview](data/README.md)
- [Reports overview](data/4-reports/README.md)
