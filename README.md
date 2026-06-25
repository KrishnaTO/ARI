# ARI

This repository contains the curated data, ontology artifacts, and generated reports that support the live ARI Disease Metadata Manager:

https://aurint.ca/ari-editor/

The public editor is the main face of this work. It is used to search, review, create, and edit autoimmune disease metadata in a single interface.

## What the editor does

- Search diseases, synonyms, and codes
- Create new disease entries
- Review disease details in a split-pane layout
- Browse diseases alphabetically or by tissue target
- Search by symptoms
- Toggle edit mode
- Adjust settings and theme
- Display ontology metadata in the footer

## What this repository holds

- Master source spreadsheets and archives
- Generated disease reports
- Ontology exports and mapping files
- Notebook scripts used to ground and rebuild the datasets
- Supporting SPARQL queries and intermediate results

## Key directories

- `data/` - source instructions, master spreadsheets, and report outputs
- `data_model/` - immunological data model assets
- `mappings/` - ARI equivalency and SSSOM mapping tables
- `notebook/` - generation scripts and grounding workflows
- `ontologies/` - ontology exports
- `sparql/` - SPARQL queries, results, and term lists

## Working notes

- Treat the curated source files as authoritative.
- Prefer surgical changes to the data or documentation.
- Keep report and ontology outputs aligned with the master list.
- Do not access `.env` files.

## Related documentation

- [Data instructions](data/instructions.md)
- [Data overview](data/README.md)
- [Reports overview](data/4-reports/README.md)

