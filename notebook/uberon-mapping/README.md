# Tissue and system mapping to UBERON

`uberon_mapping.tsv` links each ARI tissue and system class (the classes under
*Multicellular anatomical structure* in `ontologies/ari_t1d.owl`, which the `targetsTissue`
individuals are typed by) to the [UBERON](http://purl.obolibrary.org/obo/uberon/basic.obo)
anatomy ontology, release 2026-10-01. It is hand-curated, not script output.

| Column | Meaning |
|--------|---------|
| ARI Class | Local name of the ARI class |
| ARI Label | Its label in ARI |
| Mapping | `exact`: the UBERON term has the same meaning. `no term`: UBERON has none, so it stays an ARI class. `not linked`: left unlinked on purpose; the Note says why |
| UBERON ID / UBERON Label | The UBERON term, label exactly as UBERON has it |
| Note | Why a term was chosen over a near neighbour, or why a class is not linked |

Counts: 21 exact. 3 with no term: Systemic, Metabolic System, All. 2 not linked: the root
(it also holds the three classes with no term) and Pancreatic beta cell (a cell type, so it
belongs to the Cell Ontology; its individual carries CL:0000169).

`build_uberon_import.py <path to data/2-databases>` reads the TSV and `uberon-basic.obo`. It
fails if any ID is missing or obsolete, if a label differs from UBERON, or if a tissue class has
no row. It then writes:

- `ontologies/ari_uberon.owl`, the import slice: each mapped UBERON term and all its is_a
  ancestors (61 terms), with UBERON's label, definition and parents.
- In `ontologies/ari_t1d.owl`: an `owl:imports` of the slice, and on each exact class an
  `rdfs:subClassOf` to its UBERON term plus `ARI_ID` set to the UBERON CURIE.

Re-running leaves links that are already in place alone. Both files are written as plain XML;
commit them through the pre-commit hook (or run `tools/format-owl.sh`) to put them back in the
canonical layout.

**Why subClassOf and not equivalentClass.** ARI's class tree uses subClassOf for "part of":
Pancreas sits under Endocrine system, Islet under Pancreas and Beta cell under Islet. It also
puts Blood and every system directly under multicellular anatomical structure. UBERON disagrees
in nine places; for example, blood is a fluid there, not a multicellular structure. An equivalence
would turn those ARI placements into claims about the UBERON terms themselves. With subClassOf,
the ARI classes and their individuals gain the UBERON types and nothing is said about UBERON.

**Loading.** The import IRI `http://www.aurint.org/ontologies/ari_uberon` does not resolve on the
web, so a reader has to find `ari_uberon.owl` locally. In owlready2 that means
`onto_path.append("<repo>/ontologies")` before loading. In Protégé, open the file from the
`ontologies/` folder, or map the IRI in the catalog.

`notebook/category-uberon.csv` is an older automated match list for the same categories and is
superseded by this TSV. Skin is the one real difference: it had *zone of skin*, a region, where
this mapping uses *skin of body*.
