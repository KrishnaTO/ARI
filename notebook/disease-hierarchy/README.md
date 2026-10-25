# Disease hierarchy

`build_disease_hierarchy.py` finds parent/child relations between the ARI core diseases
(report 1) and writes `data/4-reports/11_Disease_Hierarchy.xlsx` plus `disease_hierarchy.csv`.

```
python build_disease_hierarchy.py <path to data/2-databases>
```

The database folder is not tracked in git, so pass the path of a checkout that has it.

Evidence, all local: master list `Diseases`/`Subtypes` sheets, `hasParentDisease` in
`ontologies/ari_disease.owl`, SNOMED is-a from `snomed/CONCEPT_ANCESTOR.csv`, and DOID is_a from
`doid.owl` over the report 6 DOID matches (`notebook/ari-grounding/doid_matches_all.csv`).
See `data/4-reports/README.md` section 11 for the link types and review flag.

## Proposed parents (ARI#137, ARI#138)

`proposed_parents.tsv` is a hand-curated proposal, not script output: parents for listed diseases
taken from other listed diseases, each with a reason and a confidence. It confirms, refines or
rejects report 11's links and adds new ones. The `Report 11` column shows the matching report 11
link, or `new`.

| Relation | Meaning |
|----------|---------|
| `is_a` | The child is a subtype of the parent (#137) |
| `manifestation_of` | The child is an organ manifestation or complication of the parent; group it under the parent (#137) |
| `component_of` | The child is a combination disease and the parent is one of its listed components (#138) |
| `duplicate_of` | The two entries are the same disease; merge the child into the parent rather than nesting it |
| `reject` | Report 11's link should not become a parent link; the reason says what to do instead |

To browse the proposal as a tree, open `proposed_hierarchy.owl` in Protégé (Entities → Class
hierarchy). It is generated from the TSV and the ontology's disease labels:

```
python build_proposed_hierarchy_owl.py
```

Every active disease is a class under *ARI disease*. `is_a`, `manifestation_of` and `duplicate_of`
rows are subclass links; combination diseases sit under *Combination disease* with a
`hasComponent some <component>` restriction per component; `reject` rows are left out. Each link
carries its relation, confidence and reason as axiom annotations (select the class, then the
annotation icon on the SubClass Of entry). Rerun the script after editing the TSV.

The `is_a` and `manifestation_of` rows are applied to the ontology as `hasParentDisease`.
`component_of` rows wait for a component property (#138); `duplicate_of` rows are merges, and
`reject` rows are not applied.
