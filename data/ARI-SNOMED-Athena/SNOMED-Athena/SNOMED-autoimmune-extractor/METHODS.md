# Methods

How the descendants of `414029004` |Disorder of immune function (disorder)|
were identified, described, and serialized as an OWL ontology.

## 1. Source release

- **Package:** `SnomedCT_InternationalRF2_PRODUCTION_20260501T120000Z`
- **Format:** RF2 (Release Format 2), tab-delimited UTF-8 text.
- **effectiveTime:** `20260501`
- **View:** `Snapshot` — for each component, the most recent row up to and
  including the release date. The `Full` view (entire history) was not used.

Files consumed:

| Logical content | File |
|-----------------|------|
| Concepts (status, definition status) | `Terminology/sct2_Concept_Snapshot_INT_20260501.txt` |
| Relationships (IS-A hierarchy + attributes) | `Terminology/sct2_Relationship_Snapshot_INT_20260501.txt` |
| Descriptions (FSN + synonyms) | `Terminology/sct2_Description_Snapshot-en_INT_20260501.txt` |
| Text definitions | `Terminology/sct2_TextDefinition_Snapshot-en_INT_20260501.txt` |
| Stored OWL axioms | `Terminology/sct2_sRefset_OWLExpressionSnapshot_INT_20260501.txt` |
| Language reference set (preferred terms) | `Refset/Language/der2_cRefset_LanguageSnapshot-en_INT_20260501.txt` |

## 2. Metadata concept IDs used

| ID | Meaning |
|----|---------|
| `414029004` | Root: Disorder of immune function (disorder) |
| `116680003` | `Is a` relationship type (subsumption edge) |
| `900000000000003001` | Fully Specified Name description type |
| `900000000000013009` | Synonym description type |
| `900000000000550004` | Text definition description type |
| `900000000000548007` | Acceptability = Preferred |
| `900000000000509007` / `900000000000508004` | US / GB English language reference sets |
| `900000000000074008` / `900000000000073002` | Definition status: Primitive / Fully defined |
| `762705008` | Concept model object attribute (object-property root) |

## 3. Procedure

1. **Concept status.** Read the Concept file into maps of `conceptId → active`
   and `conceptId → definitionStatusId`.

2. **IS-A graph.** Stream the Relationship file keeping rows with `active = 1`
   and `typeId = 116680003`. Each is an edge `sourceId --is-a--> destinationId`
   (source is a child of destination). Build `parent → {children}` and
   `child → {parents}` indexes.

3. **Transitive closure (descendants).** Breadth-first traversal down
   `parent → children` from the root's direct children collects every concept
   reached. The root is excluded (the request is for terms *under* it). Result:
   **2,474** concepts; **55** are immediate children.

4. **Attribute relationships.** A second pass over the Relationship file keeps
   active, non-IS-A rows whose `sourceId` is a descendant, indexed by
   `relationshipGroup`. These are the **inferred** defining attributes
   (e.g. *Finding site*, *Associated morphology*, *Pathological process*,
   *Causative agent*). Rendered per concept as grouped, labelled text:
   role groups in `{ ... }`, each attribute as `Attribute = Target (targetId)`.

5. **OWL axioms.** One pass over the OWL Expression refset:
   - `SubClassOf(...)` / `EquivalentClasses(...)` rows whose
     `referencedComponentId` is in the subtree (root + descendants) are kept as
     the logical axioms (**2,501** rows — some concepts carry more than one,
     including 26 general concept inclusion axioms).
   - `SubObjectPropertyOf(...)` rows give the object-property hierarchy;
     `SubDataPropertyOf(...)` rows identify data properties.

6. **Referenced-entity closure.** Every `:id` token in the kept class axioms is
   collected. An id is treated as an **object property** if it has a
   `SubObjectPropertyOf` axiom, otherwise as a **class**. The object-property
   hierarchy is closed upward so each `SubObjectPropertyOf` target is itself
   declared. Result: **3,819** classes and **15** object properties.

7. **Descriptions, definitions, preferred terms.**
   - The Description file supplies the active FSN (used both as the `fsn` column
     and as the `rdfs:label` for *every* referenced concept) and all active
     synonyms for descendants.
   - The TextDefinition file supplies active text definitions for descendants
     (**299** have one).
   - The Language refset resolves the Preferred Term: the synonym marked
     Preferred (`900000000000548007`) in the **US** refset
     (`900000000000509007`), falling back to **GB** (`900000000000508004`).

8. **Outputs.** Rows sorted by semantic tag then FSN are written to CSV and to
   an Excel workbook (`Descendants` + `Summary`). The ontology is written twice
   (see §4).

## 4. OWL serialization

The same logical content is emitted in two W3C-standard forms:

- **`immune_disorder_subtree.ofn`** — OWL 2 **Functional Syntax**. The kept
  axiom strings are SNOMED's native functional-syntax expressions and are
  written verbatim, preceded by prefix lines, an `Ontology(...)` wrapper,
  `Declaration` axioms for every class/object property, `SubObjectPropertyOf`
  for the property hierarchy, and `AnnotationAssertion(rdfs:label ...)` for
  every entity that has an FSN.

- **`immune_disorder_subtree.owl`** — **RDF/XML**, produced by parsing the
  functional-syntax class expressions (only `ObjectIntersectionOf`,
  `ObjectSomeValuesFrom`, and named classes occur here) into RDF triples per
  the OWL 2 Mapping to RDF Graphs (`owl:Restriction` /
  `owl:someValuesFrom` / `owl:intersectionOf` with RDF lists) and serializing
  with `rdflib`'s plain `xml` writer.

**Validation.** Structural checks confirm balanced parentheses, that every
referenced id is declared, and that every property-position id is declared as
an object property. The RDF/XML was additionally **loaded with `owlready2`**
(an OWL API-equivalent parser): 3,819 classes and 15 object properties load,
labels resolve, and nested axioms reconstruct correctly — e.g. the root's
`EquivalentClasses` round-trips to
`Disease & RoleGroup.some(Pathological process.some(Immunopathological process))`.

## 5. Definitions and design choices

- **"Child terms under"** = the full **descendant** set (transitive IS-A
  closure), not only the 55 immediate children. The `isDirectChildOfRoot`
  column lets you filter to direct children.
- **Active components only.** Inactive relationships, descriptions, language
  rows, and OWL axioms are ignored. Because descendants are reached only through
  active IS-A edges, every output concept is itself active (all 2,474 confirmed).
- **Inferred relationships** are used for the tabular attributes (distribution
  normal form). The **stored OWL axioms** are used for the ontology — these are
  the authoritative author-defined logic definitions. The two are consistent
  but not identical in shape (the inferred form is the classifier output).
- **Labels** in the ontology are the FSN of each concept; SNOMED concept IRIs
  use the `http://snomed.info/id/` namespace.

## 6. Caveats

- Reflects the **20260501** International Edition only; no national extensions
  are included.
- The hierarchy is **poly-hierarchical**: a concept may have several parents and
  appear under more than one branch. Each concept appears **once** in the
  spreadsheet; `parentConceptIds` / `parentTerms` list all direct parents.
- The ontology is a **subtree extract**, not the full SNOMED CT graph. Referenced
  body-structure/morphology/etc. classes are declared and labelled but their own
  defining axioms and IS-A parents are **not** included, so a reasoner will
  classify the immune-disorder concepts against declared targets only.
- A literal double-quote (`"`) can appear in RF2 term text; RF2 has no CSV
  quoting, so the reader uses `QUOTE_NONE`. Do not re-parse the source files
  with a quote-aware CSV reader.
- Counts are specific to this release and will change with future editions.

## 7. Reproducibility

```bash
cd data/databases/snomed/immune-extractor
python extract_immune_disorders.py
```

Dependencies: Python 3, `pandas`, `openpyxl`, `rdflib` (and `owlready2` only if
you want to re-run the load test). Paths in the script are absolute and point at
the 20260501 Snapshot; edit the `BASE` constant to target another release.
