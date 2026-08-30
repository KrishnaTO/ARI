# `data/2-databases` — local scratch, not version control

Nothing in this directory is tracked except this file. `.gitignore` excludes
`data/2-databases/*`, and it should stay that way: this is where large raw
ontology release dumps land — MONDO, DOID, NCIt, MeSH, Orphanet, SNOMED,
UniProt, NCBI taxonomy and the rest — and together they run to roughly 11 GB.
They are re-downloadable from their publishers, several are licence-restricted
against redistribution, and none of them are a curator's decision.

## The name collides with something in the app repo

[`KrishnaTO/ARI-metadata-manager`](https://github.com/KrishnaTO/ARI-metadata-manager)
has a directory at the same path holding **different** files, and those *are*
committed:

| | Here | In the app repo |
| --- | --- | --- |
| Contents | raw release dumps (`mondo.obo`, `doid.owl`, `taxonomy.rdf`, …) | distilled `*.index.tsv`, `*.details.tsv`, `*.subtypes.tsv` |
| Size | ~11 GB | ~32 MB |
| Tracked | no | yes |
| Built by | downloaded by hand or by the grounding scripts | `scripts/fetch_databases.py` |
| Read by | the notebooks under `notebook/` | `app/predict_service`, `app/concept_service` |

The app's copies are build products: one lean row per ontology term, distilled
from these same public releases with no human judgment in the path, so a code
change regenerates them and they belong with the code that builds them. What is
here is the input to that, kept locally because it is enormous and reproducible.

If you are looking for the compact indexes that back the editor's predicted
cross-references, they are in the app repo, not here.
