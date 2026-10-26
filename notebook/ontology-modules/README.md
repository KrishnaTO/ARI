# Ontology modules

The ARI ontology is split into one file per domain, so a curator can bring in terms from a
published ontology (UBERON, SYMP/HPO, later the Cell Ontology, Protein Ontology or LOINC) where
they belong, without wading through the disease records. The design and the decisions behind it are
in `docs/superpowers/specs/2026-10-18-ontology-modules-design.md`.

## The files

All in `ontologies/`. `ari_<domain>.owl` is ARI-owned and edited in place; `ari_<source>.owl` named
after a published ontology is a generated import slice, never edited by hand.

| File | Holds | Imports |
| --- | --- | --- |
| `ari_core.owl` | Three umbrella classes (`Disease`, `Anatomical entity`, `Biomarker`) over the key classes (`AutoimmuneDisease`, `Symptom`, `MulticellularAnatomicalStructure`, `AffectedCellTissueOrOrgan`, `Autoantibody`, `Antigen`, `ClinicalBiomarker`), and **every property declaration** | nothing |
| `ari_disease.owl` | The diseases and their per-disease entries; each points at its shared concept with `sharedConcept` | core, symptoms, anatomy, biomarkers |
| `ari_symptoms.owl` | 765 `ARIS_…` symptom classes, linked to SYMP and HPO | core, `ari_symp` |
| `ari_anatomy.owl` | 25 tissue and system classes and the 23 `Tissue_*` individuals, linked to UBERON | core, `ari_uberon` |
| `ari_biomarkers.owl` | Biomarker concepts (empty for now) | core |
| `ari_symp.owl` | The SYMP terms the symptom classes name, with their ancestors (generated slice) | nothing |
| `ari_uberon.owl` | The UBERON terms the tissue classes name, with their ancestors (generated slice) | nothing |
| `catalog-v001.xml` | Maps each imported ontology IRI to its file | |

Every entity keeps its IRI. The disease file is never imported: it is the file you open.

## Opening in Protégé

Open **`ontologies/ari_disease.owl`** from the `ontologies/` folder. Protégé reads
`catalog-v001.xml` beside it and resolves every import locally; the imported IRIs
(`http://www.aurint.org/ontologies/ari_core`, …) do not resolve on the web. Any other ARI-owned
file also opens on its own, with its own imports.

## Loading in owlready2

```python
from owlready2 import onto_path, get_ontology
onto_path.append("ontologies")
onto = get_ontology("ontologies/ari_disease.owl").load()   # on Windows, load from a file object
```

`onto_path` is how owlready2 finds the imported files; without it the imports are not found.

## Who writes what

| File | Written by |
| --- | --- |
| `ari_disease.owl` | The editor app (pull requests under each curator's identity); Protégé |
| `ari_symptoms.owl`, `ari_anatomy.owl`, `ari_biomarkers.owl`, `ari_core.owl` | Protégé. To map a symptom or link a tissue, see `notebook/symptom-mapping/README.md` and `notebook/uberon-mapping/README.md` |
| `ari_symp.owl` | `notebook/symptom-mapping/build_symp_import.py`, from `ari_symptoms.owl` and `symp.owl` / `hp.obo` |
| `ari_uberon.owl` | `notebook/uberon-mapping/build_uberon_import.py`, from `ari_anatomy.owl` and `uberon-basic.obo` |
| `catalog-v001.xml` | By hand, when an import is added |

`notebook/ontology-modules/split_ontology.py` made the split from the single `ari_t1d.owl`. It ran
once and is kept for the record.

After any write, run `tools/format-owl.sh` (it reads the catalog, so imports resolve) or commit
through `.githooks/pre-commit`. The `OWL format` workflow rejects a file that is not in the canonical
layout. `.github/scripts/validate_mappings.py` reads all the modules and also checks that a property
is declared only in `ari_core.owl`, that an entity is in one module only, and that every
`sharedConcept` points at a class a module declares.
