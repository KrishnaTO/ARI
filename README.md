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

| Path | Purpose | In git? |
| --- | --- | --- |
| `data/0-archive/` | Superseded working material | no |
| `data/1-master/` | The curated master list | yes |
| `data/2-databases/` | Large raw ontology release dumps — local scratch, re-downloadable | **no** |
| `data/3-meta-database-sources/` | Supporting source tables | yes |
| `data/4-reports/` | Generated report outputs | yes |
| `data_model/` | Reference spreadsheets and model snapshots | yes |
| `mappings/` | Every curated cross-reference judgment | yes |
| `notebook/` | Notebook-driven data preparation and grounding scripts | yes |
| `ontologies/` | The ARI ontology — the sole authority — as modules (see [Ontology modules](#ontology-modules)) | yes |
| `sparql/` | SPARQL queries and generated term sets | yes |

`data/` mixes both kinds, which is worth knowing before going looking for
something: `2-databases/` holds roughly 11 GB of downloaded release dumps and is
git-ignored in full, while its siblings are curated and tracked. See
[`data/2-databases/README.md`](data/2-databases/README.md).

## Key outputs

- `data/4-reports/1_Core_ARI_Diseases.xlsx`
- `data/4-reports/2_Proposed_Diseases.xlsx`
- `data/4-reports/3_Proposed_Changes.xlsx`
- `data/4-reports/4_Additional_Info_Index.xlsx`
- `data/4-reports/5_DOID_Mapping.xlsx`
- `data/4-reports/6_DOID_Matches_All.xlsx`
- `data/4-reports/7_SNOMED_Matches_All.xlsx`
- `data/4-reports/10_Master_List_Comparison.xlsx`
- `data/4-reports/12_Research_Gaps.xlsx` — what each disease still needs, field by field against the data model

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
| `OWL format` | pull requests touching `ontologies/` or `tools/` | every `ontologies/*.owl` is in the canonical layout (see below) |

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
- Curation that disappears without a decision — a synonym, clinical subtype or changelog
  entry the branch drops rather than adds. A synonym may be retired only by pairing its
  removal with an `ARI_SynonymWithdrawn` marker on the same disease, shaped
  `<synonym> | <reason> | <note>` where `<reason>` is `subtype`, `broader`, `distinct` or
  `non-disease`; the marker is itself append-only, so the review stays on record.
- Disease ids that are not registry ids. Every `ARI_ID` has seven digits (`ARI:0001234`).
  A disease is renumbered by changing its `ARI_ID` and adding an `ARI_FormerID` holding the
  old one, so the deletion check follows the record to its new id. `ARI_FormerID` is
  append-only, and a former id may not still be in use.

The validator reads the ontology as XML, not line by line, so it works on any RDF/XML
layout. With `--since`, an ontology finding counts as new only when the statement on its
line (subject, property, value) is new, so re-laying-out the file reports nothing.

## Ontology modules

The ontology is a set of files in `ontologies/`, one per domain. Each opens on its own in Protégé
and loads in owlready2 with its imports. Open **`ari_disease.owl`**: it imports the rest.

| File | Holds | Edited by |
| --- | --- | --- |
| `ari_core.owl` | The key classes and every property declaration | curators (Protégé) |
| `ari_disease.owl` | Diseases and their per-disease entries (symptoms, antibodies, antigens, biomarkers, tissues) | the editor app, curators |
| `ari_symptoms.owl` | One `ARIS_…` class per symptom, linked to SYMP and HPO | curators (Protégé) |
| `ari_anatomy.owl` | Tissue and system classes, linked to UBERON | curators (Protégé) |
| `ari_biomarkers.owl` | Biomarker concepts (empty for now; see [`notebook/biomarker-concepts/`](notebook/biomarker-concepts/README.md)) | curators (Protégé) |
| `ari_symp.owl`, `ari_uberon.owl` | Slices of SYMP and UBERON, generated, never edited by hand | the builder scripts |
| `ari_pr.owl`, `ari_chebi.owl`, `ari_hgnc.owl`, `ari_loinc.owl` | Slices of the Protein Ontology, ChEBI, HGNC and LOINC, generated, never edited by hand | `build_biomarker_slices.py` |

A per-disease entry points at its shared concept with `sharedConcept`. Every property is declared
once, in the core. [`notebook/ontology-modules/README.md`](notebook/ontology-modules/README.md)
covers opening, loading and which tool writes which file; the design is in
[`docs/superpowers/specs/2026-10-18-ontology-modules-design.md`](docs/superpowers/specs/2026-10-18-ontology-modules-design.md).

## Canonical OWL layout

The app (owlready2), Protégé and scripts each write RDF/XML in their own layout. So that
a diff only ever shows content, every `ontologies/*.owl` is kept in one layout: the one
[ROBOT](https://robot.obolibrary.org/) writes, at the version pinned in
[`tools/robot.version`](tools/robot.version). Same content, same bytes, whichever tool
saved the file.

```bash
tools/format-owl.sh ontologies/ari_disease.owl      # format in place
tools/format-owl.sh --check ontologies/*.owl        # exit 1 if any would change
```

It needs Java 11 or newer on `PATH` (Protégé's bundled Java does not count), and it
downloads the pinned ROBOT jar into `.cache/robot/` on first use. Imports resolve
through [`ontologies/catalog-v001.xml`](ontologies/catalog-v001.xml), which Protégé
also reads.

| Where | What runs |
| --- | --- |
| Your clone | The pre-commit hook formats any staged `ontologies/*.owl`. Install it once: `git config core.hooksPath .githooks` |
| The editor app | Formats the file before it pushes a curator's PR branch |
| `OWL format` workflow | Pull requests touching `ontologies/` or `tools/` — fails if a file is not in the canonical layout |

If the check fails, run `tools/format-owl.sh` on the file it names and push again.
Scripts that change the ontology edit it as XML and leave the layout to the formatter.
Bumping `tools/robot.version` re-lays-out every file, so do it in its own PR with that
reformat commit, and bump the app's `deploy/install-robot.sh` to the same release.

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
