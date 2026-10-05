# Disease hierarchy

`build_disease_hierarchy.py` finds parent/child relations between the ARI core diseases
(report 1) and writes `data/4-reports/10_Disease_Hierarchy.xlsx` plus `disease_hierarchy.csv`.

```
python build_disease_hierarchy.py <path to data/2-databases>
```

The database folder is not tracked in git, so pass the path of a checkout that has it.

Evidence, all local: master list `Diseases`/`Subtypes` sheets, `hasParentDisease` in
`ontologies/ari_t1d.owl`, SNOMED is-a from `snomed/CONCEPT_ANCESTOR.csv`, and DOID is_a from
`doid.owl` over the report 6 DOID matches (`notebook/ari-grounding/doid_matches_all.csv`).
See `data/4-reports/README.md` section 10 for the link types and review flag.
