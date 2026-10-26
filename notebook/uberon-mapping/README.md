# Tissue and system mapping to UBERON

ARI's tissue and system classes (the classes under *Multicellular anatomical structure*, which the
`targetsTissue` individuals are typed by) live in **`ontologies/ari_anatomy.owl`**, linked to the
[UBERON](http://purl.obolibrary.org/obo/uberon/basic.obo) anatomy ontology, release 2026-10-01. The
links were hand-curated; the OWL is now the record, and there is no mapping table.

| In `ari_anatomy.owl` | Meaning |
|--------|---------|
| `rdfs:subClassOf` an UBERON term | `exact`: the UBERON term has the same meaning. The class also carries `ARI_ID` set to the UBERON CURIE |
| `ARI_NoConcept "no term"` | UBERON has none, so it stays an ARI class |
| `ARI_NoConcept "not linked"` | Left unlinked on purpose; the `rdfs:comment` says why |
| `rdfs:comment` | Why a term was chosen over a near neighbour, or why a class is not linked |

Counts: 21 exact. 3 with no term: Systemic, Metabolic System, All. 2 not linked: the root
(it also holds the three classes with no term) and Pancreatic beta cell (a cell type, so it
belongs to the Cell Ontology; its individual carries CL:0000169). The root,
*Multicellular anatomical structure*, is declared in `ari_core.owl`, so its note and
`not linked` are on the class there.

## Linking a tissue class

In Protégé, give the class an `rdfs:subClassOf` to its UBERON term and set `ARI_ID` on the class
to that term's CURIE (e.g. `UBERON:0001264`); the editor's tissue tree shows `ARI_ID`, and nothing
generates it. Or set `ARI_NoConcept` (`no term` or `not linked`, with an `rdfs:comment`). A class
with neither is a validator warning (`tissue-unlinked`). Then rebuild the slice.

## Build

```
python notebook/uberon-mapping/build_uberon_import.py <path to data/2-databases>
wsl -e tools/format-owl.sh ontologies/ari_uberon.owl
```

Run both lines from the repository root; Java for the formatter is in WSL (see `CLAUDE.md`).
The database folder holds `uberon-basic.obo`. The script reads the UBERON links in
`ontologies/ari_anatomy.owl` and writes **only** `ontologies/ari_uberon.owl`, the import slice:
each linked UBERON term and all its is_a ancestors (61 terms), with UBERON's label, definition and
parents. It stops, listing each, if a linked term is missing or obsolete in the release. The slice
is generated, never edited by hand, and `ari_anatomy.owl` imports it.

**Why subClassOf and not equivalentClass.** ARI's class tree uses subClassOf for "part of":
Pancreas sits under Endocrine system, Islet under Pancreas and Beta cell under Islet. It also
puts Blood and every system directly under multicellular anatomical structure. UBERON disagrees
in nine places; for example, blood is a fluid there, not a multicellular structure. An equivalence
would turn those ARI placements into claims about the UBERON terms themselves. With subClassOf,
the ARI classes and their individuals gain the UBERON types and nothing is said about UBERON.

**Loading.** The import IRI `http://www.aurint.org/ontologies/ari_uberon` does not resolve on the
web, so a reader has to find `ari_uberon.owl` locally. In owlready2 that means
`onto_path.append("<repo>/ontologies")` before loading; in Protégé, open from the `ontologies/`
folder and the catalog resolves it. See
[`notebook/ontology-modules/README.md`](../ontology-modules/README.md).

`notebook/category-uberon.csv` is an older automated match list for the same categories and is
superseded by this mapping. Skin is the one real difference: it had *zone of skin*, a region, where
this mapping uses *skin of body*.
