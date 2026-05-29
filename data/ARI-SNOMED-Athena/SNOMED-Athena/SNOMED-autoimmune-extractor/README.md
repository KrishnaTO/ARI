# SNOMED CT Autoimmune Disease Extractor

Extraction of the SNOMED CT subtree under **`85828009` |Autoimmune disease
(disorder)|** from the International Edition, with full concept detail, a
derived term/parent workbook, and a Protege-loadable OWL ontology.

The extraction script is generic (any root concept via `--root`); the
immune-disorder run that produced this folder and all intermediate CSVs have
been moved to `Archive/`.

## Files in this folder

| File | Description |
|------|-------------|
| `extract_immune_disorders.py` | The extraction script — RF2 reader, descendant (transitive `Is a`) finder, and OWL emitter. Parameterized by `--root` / `--prefix`. |
| `autoimmune_disease_subtree.owl` | OWL 2 ontology of the subtree in **RDF/XML** — double-click to open in Protege. |
| `autoimmune_disease_subtree.ofn` | The same ontology in **OWL 2 Functional Syntax** (SNOMED's native axiom form). |
| `autoimmune_disease_combined_terms.xlsx` | Derived workbook with two sheets (see below). |
| `README.md` | This file. |
| `METHODS.md` | Detailed methodology, metadata IDs, and caveats. |

> `Archive/` holds the original immune-disorder outputs (`414029004`), the
> `autoimmune_disease_descendants.*` source tables, and the intermediate
> exploded/parent CSVs. It is not required to use the files above.

## Subtree summary

- **Root concept:** `85828009` |Autoimmune disease (disorder)|
- **Descendant concepts:** 801 (all active, all `(disorder)`); 77 are direct children.
- **OWL ontology:** 1,357 class declarations, 15 object properties, 810 logical axioms.

## The workbook: `autoimmune_disease_combined_terms.xlsx`

**Sheet `SNOMED-AutoimmuneDisease`** — 1,749 rows, one per distinct concept +
term. The FSN (with its ` (disorder)` tag removed), preferred term, and synonyms
are unioned into a single `term` column and deduplicated.

| Column | Meaning |
|--------|---------|
| `conceptId` | SNOMED CT concept identifier. |
| `term` | A name for the concept (FSN-without-tag / preferred term / synonym, deduplicated). |
| `termType` | `Preferred term` or `Synonym`. |
| `semanticTag` | Tag parsed from the FSN (`disorder`). |
| `textDefinition` | Active text definition, where present. |
| `definingRelationships` | Defining attribute relationships (inferred), grouped in `{ ... }` as `Attribute = Target (targetId)`. |
| `conceptActive` | `1` = active. |
| `definitionStatus` | `Primitive` or `Fully defined`. |
| `isDirectChildOfRoot` | `Y` if an immediate `Is a` child of `85828009`. |
| `numParents` | Count of active direct `Is a` parents. |

**Sheet `Parents`** — 2,064 rows, the concept→parent `Is a` links.

| Column | Meaning |
|--------|---------|
| `conceptId` | The child concept. |
| `conceptPreferredTerm` | Preferred term name of the child concept. |
| `parentId` | Direct `Is a` parent concept ID. |
| `parentTerm` | Parent's FSN. |

Join the two sheets on `conceptId`.

## Source data

- **Release:** SNOMED CT International Edition, RF2 **PRODUCTION**, effectiveTime **20260501** (1 May 2026).
- **View used:** `Snapshot` (current state of every component at the release date).
- **Path:** `data/databases/snomed/SnomedCT_InternationalRF2_PRODUCTION_20260501T120000Z/.../Snapshot`

## Opening the ontology in Protege

- **`autoimmune_disease_subtree.owl`** (RDF/XML): `File > Open`, or double-click.
  Most broadly compatible form.
- **`autoimmune_disease_subtree.ofn`** (Functional Syntax): also opens directly
  (the OWL API parses functional syntax natively).

Both were validated by loading with an OWL API-equivalent parser (`owlready2`):
all classes, object properties, labels, and the nested `EquivalentClasses` /
`SubClassOf` axioms parse correctly.

### Seeing the inferred view of Autoimmune disease

The `.owl`/`.ofn` files carry SNOMED's **stated** axioms. To see the **inferred**
class hierarchy (what a reasoner computes from those definitions):

1. **Open** `autoimmune_disease_subtree.owl` in Protege.
2. **Choose a reasoner:** menu `Reasoner > ELK <version>`. SNOMED CT is an OWL 2
   **EL** ontology, so ELK is the correct reasoner. If ELK is not listed, install
   it via `File > Check for plugins…`, tick **ELK Reasoner**, restart Protege,
   then select it under `Reasoner`.
3. **Run it:** `Reasoner > Start reasoner`. Wait for "classified" in the status
   bar (the subtree classifies in seconds).
4. **Switch to the inferred hierarchy:** open the **Entities** tab (or
   `Window > Tabs > Entities`). In the **Class hierarchy** panel use the
   **Asserted / Inferred** toggle at the top and pick **Inferred** — or open the
   dedicated **Class hierarchy (inferred)** panel
   (`Window > Views > Class views > Class hierarchy (inferred)`). Inferred
   parents/children are shown highlighted (pale yellow).
5. **Navigate to the concept:** in the search box (`Ctrl+F` / the search icon)
   type `Autoimmune disease`, select `Autoimmune disease (disorder)`
   (`85828009`), and expand it to read the reasoner-computed subclasses.

Notes on what you will see:

- Concepts defined with **`EquivalentClasses`** (fully defined) are classified by
  the reasoner from their attributes; concepts with only **`SubClassOf`**
  (primitive) sit where their stated `Is a` places them. The inferred tree may
  differ from the stated one where definitions imply additional subsumptions.
- This is a **subtree extract**: referenced target classes outside the subtree
  (body structures, morphologies, primitive parents such as
  *Chronic disease of skin*) are declared with labels but **without their own
  definitions**, so the reasoner classifies the autoimmune-disorder concepts
  against the axioms present here only — not against the full SNOMED CT graph.

## How to re-run / regenerate

```bash
cd data/databases/snomed/immune-extractor

# Autoimmune disease subtree (what this folder is built around)
python extract_immune_disorders.py --root 85828009 --prefix autoimmune_disease

# Default root: 414029004 Disorder of immune function
python extract_immune_disorders.py
```

`--root` selects the concept whose descendants are extracted; `--prefix` sets the
output filename prefix. The script writes `<prefix>_descendants.{csv,xlsx}`,
`<prefix>_subtree.ofn`, and `<prefix>_subtree.owl`. The derived
`autoimmune_disease_combined_terms.xlsx` (term union + Parents sheet) is built
on top of `<prefix>_descendants` and is not produced by the script directly.

Requires Python 3 with `pandas`, `openpyxl`, and `rdflib`. (Close the target
`.xlsx` in Excel first, or the workbook write will fail with a lock error.)

See [METHODS.md](METHODS.md) for the full methodology and caveats.

---
SNOMED CT® © 2002-2026 International Health Terminology Standards Development
Organisation (SNOMED International). Use is subject to the SNOMED CT Affiliate
License.
