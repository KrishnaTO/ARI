# ARI Disease Metadata Manager v2

A standalone web application for browsing and managing autoimmune disease data stored in a Protégé-compatible OWL ontology file. Built as an evolution of `Metadata-manager/` with a richer, disease-focused UI.

## Features

- **Hierarchical disease views** (top tabs)
  - **Alphabetical** — diseases grouped under their **parent disease**; expand a parent to reveal child subtypes (e.g. T1D → LADA, Fulminant T1D)
  - **Tissue Target** — the *multicellular anatomical structure* (`UBERON:0010000`) hierarchy, with each disease attached as an expandable item under every tissue it targets
  - **Symptoms** — flat list of all symptoms in the dataset (the only symptom context with enough data)
- **Ontology detail panel** — IRI, ARI local id, label, definition, synonyms, definition source, and **database cross-references that link out** to the source databases (ICD-10, SNOMED, DOID, UMLS, MONDO). Obsolete entries render faded with an `(obsolete)` marker.
- **Editing** — Click **Edit** to enter editing mode:
  - **Disease fields** — label, definition, synonyms, identifiers, prevalence, demographics, sources, obsolete flag.
  - **Data items** — add / edit / delete the individual items inside every category (symptoms, environmental factors, antibodies, genetics, treatments, etiology, biomarkers, pathway steps, and all immune/molecular components) via schema-driven forms. Each category's deep-dive panel also has an **✎ Edit items** button, so items can be managed directly from any view without toggling global edit mode (use **← Back to details** to return).
  - Every change writes the OWL file and appends a timestamped **per-disease changelog** entry.
- **Version release pipeline** — The **Admin** dialog cuts a versioned release: it snapshots the OWL into `releases/`, bumps the version on every disease, and records the release in each disease's changelog and a `releases.json` manifest.
- **Disease story** — the data categories are arranged as a narrative timeline: ① triggers & onset → ② etiology → ③ pathophysiology → ④ biomarkers & treatments → ⑤ prevalence. Within each step the boxes are grouped under their **aspect category** (Clinical profile, Etiology, Genetics, Innate immune component, Adaptive immunity, Signaling & molecular, …), derived from the [Immunological Data Model v3](../data_model/Immuno-data-model-v3.xlsx). Clicking a box opens its deep-dive on the right, where the concept's **description** (also from the data model) is shown under the panel title.
- **Rich right-panel deep dives** (the panel squashes the list + detail to the left half and opens on the right with a Close button):
  - 📊 **Prevalence** — Chart.js chart, stat cards, **table view**, and sources
  - 🤒 **Symptoms** — likelihood-badged table with HPO/PubMed links + D3 word cloud
  - 🌍 **Environmental factors** — only shown when triggers exist; cards with likelihood + sources
  - 🧬 **Autoantibodies** — the pathophysiology map with the autoantibody step highlighted, plus a selectable antibody panel
  - 💊 **Treatments** — cards with type, description, FDA status, sources
  - 🔬 **Etiology** — origins classified as **Genetic / External / Idiopathic**, with study excerpts and sources
  - 🧬 **Genetic associations** — table with gene/HLA, locus, product, effect, odds ratio
  - 🩸 **Biochemical markers** — diagnostic markers with uses and sources
  - 🗺️ **Pathophysiology** — an interactive **force-directed pathograph graph** (D3): a numbered spine of cascade steps (genetic → trigger → tolerance → presentation → autoantibodies → insulitis → beta-cell death → hyperglycemia) with the associated genetic, antigen, antibody, T-cell, cytokine, complement, inflammasome and NETosis mediators branching off each step; drag nodes, click a step for sources
  - **Immune / molecular components** — Cytokines, T-Cells, APCs, transcription factors, innate immunity, complement, receptors, **NETosis, inflammasome, acute phase reactants, antigens**
  - 📋 **Change log** — per-disease edit and release history
- **Search** — Live full-text search across all individuals
- **Protégé-compatible** — The `.owl` file is standard RDF/XML; open and edit it in Protégé, restart to reflect external changes
- **Curated dataset** — Type 1 Diabetes (T1D) plus two child subtypes (LADA, Fulminant T1D) as a comprehensive demonstration

## Requirements

- Python 3.10+
- owlready2, fastapi, uvicorn

## Setup

```bash
pip install -r requirements.txt
```

## Running

```bash
python run.py
```

This starts the server at http://127.0.0.1:8001 and opens your browser automatically.

To use a custom port or ontology file:

```bash
python run.py --port 8002 --file path/to/your.owl
```

## Project Structure

```
metadata-manager_v2/
├── README.md
├── requirements.txt
├── run.py                    # Launcher (uvicorn + browser)
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI REST API (routes only)
│   ├── ontology_service.py   # owlready2 service layer (reads, edits, releases)
│   └── schema.py             # Editable disease-data item field schema
├── scripts/
│   └── build_t1d_ontology.py # T1D ontology generator
├── ontologies/
│   └── ari_t1d.owl           # Generated OWL file (T1D data)
├── releases/                 # Versioned release snapshots
└── static/
    ├── index.html            # Page skeleton
    ├── css/
    │   └── styles.css        # All styles
    └── js/                   # Browser app, classic scripts loaded in order
        ├── core.js           #   state, constants, helpers, API client
        ├── trees.js          #   tree views, tabs, search
        ├── detail.js         #   disease detail + narrative story
        ├── panels.js         #   category deep-dive read views
        ├── graph.js          #   D3 pathophysiology graph
        ├── editor.js         #   field/item editing + admin releases
        └── main.js           #   bootstrap (init)
```

## Data Model

The ontology follows the [Immunological Data Model](https://github.com/KrishnaTO/ARI/blob/main/data_model/immunological_data_model.owl) schema, with:

- **AutoimmuneDisease** class for disease individuals (parent/child diseases linked by `hasParentDisease`)
- **22 object properties** connecting diseases to their associations (symptoms, antibodies, genetics, treatments, etiology, biomarkers, pathway steps, immune components, antigens, NETosis, inflammasome, acute phase reactants, …)
- **32 data properties** for structured attributes
- **13 annotation properties** for metadata, identifiers, changelog, and the `ARI_Obsolete` flag
- **Tissue hierarchy** (UBERON-style): MulticellularAnatomicalStructure (`UBERON:0010000`) → AnatomicalSystem → EndocrineSystem → Pancreas → IsletOfLangerhans → BetaCell

## REST API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v2/overview` | Counts + current version |
| GET | `/api/v2/tree/alphabetical` | Parent→child disease tree |
| GET | `/api/v2/tree/tissue` | UBERON tissue tree with diseases attached |
| GET | `/api/v2/symptoms` | Flat symptom index |
| GET | `/api/v2/schema` | Field schema for every editable data-item category |
| GET | `/api/v2/disease/{iri}` | Full disease detail |
| PUT | `/api/v2/disease/{iri}` | Edit disease fields `{ "changes": {...}, "editor": "name" }` (appends changelog) |
| POST | `/api/v2/disease/{iri}/item` | Add a data item `{ category, values, editor }` |
| PUT | `/api/v2/item/{iri}` | Edit a data item `{ category, changes, disease, editor }` |
| DELETE | `/api/v2/item/{iri}` | Delete a data item `{ category, disease, editor }` |
| GET | `/api/v2/releases` | Current version + release history |
| POST | `/api/v2/releases` | Cut a release `{ "notes": "...", "version": "" }` |
| GET | `/api/v2/search?q=` | Full-text search |

## Regenerating the Ontology

```bash
python scripts/build_t1d_ontology.py
```

## Working with Protégé

The generated `.owl` file is standard RDF/XML. Open it in Protégé to edit or extend. Restart the app server after making external changes.