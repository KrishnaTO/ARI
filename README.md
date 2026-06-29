# ARI

Repository for the Autoimmune Registry Information (ARI) editor and the disease metadata
work displayed at `https://aurint.ca/ari-editor/`.

The public editor is the main user-facing surface for browsing and curating ARI disease
records. It is organized around a left-to-right workflow:

1. Search diseases, synonyms, and codes from the top bar.
2. Browse the disease catalogue by `Alphabetical` or `Tissue Target`.
3. Select a disease to review its IRI, ARI ID, definition, synonyms, cross-references,
   and other metadata in the detail pane.
4. Open the context panels for curated views such as prevalence, symptoms, environmental
   factors, antibodies, treatments, etiology, genetic associations, biochemical markers,
   and pathophysiology.
5. Create new disease entries, edit existing records, and switch settings or theme.

The current editor UI includes:

- global search across diseases, synonyms, and codes
- alphabetical and tissue-target navigation trees
- disease detail review in the center pane
- a right-side deep-dive panel for disease-specific context
- `New Disease`, `Symptoms`, `Edit`, `Settings`, and theme controls
- a separate cross-reference review surface under `metadata-manager_v2/static/ref-edits/`

## Project Scope

This repository is data-heavy. The editor is backed by the curated ARI catalogue and the
supporting ontology and mapping artifacts used to build it.

- `metadata-manager_v2/` - the FastAPI application, static editor UI, deployment files, and
  data import/build scripts for the live editor
- `data/` - master inputs, generated reports, and repository instructions
- `mappings/` - ARI cross-reference mapping tables
- `notebook/` - grounding and report-generation work
- `ontologies/` - ontology assets used by the project
- `sparql/` - SPARQL helpers, source terms, and query results

## Primary Workflow

1. Maintain the master disease workbook and supporting source data.
2. Rebuild the curated reports and ontology-backed mapping tables.
3. Use the editor to inspect disease records, review cross-references, and apply updates.
4. Publish changes through the metadata manager workflow when the edited record is ready.

## Source Rules

- Use local project data and generated artifacts as the source of truth.
- Do not read `.env` files unless explicitly authorized.
- Keep changes surgical and focused on the affected data or report.

## Related Documentation

- [`metadata-manager_v2/README.md`](metadata-manager_v2/README.md)
- [`metadata-manager_v2/DEPLOY.md`](metadata-manager_v2/DEPLOY.md)
- [`data/README.md`](data/README.md)
- [`data/instructions.md`](data/instructions.md)
- [`notebook/ari-grounding/README.md`](notebook/ari-grounding/README.md)
