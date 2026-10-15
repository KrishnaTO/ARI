# Symptom mapping (ARI#132)

`symptom_mapping.tsv` maps every symptom string ARI holds to the
[Symptom Ontology](http://purl.obolibrary.org/obo/symp.owl) (SYMP, release 2026-07-30) and groups
similar-sounding symptoms under a root symptom, so that "Blisters on eyes", "Blister on lips" and
"Genital blisters" sit under **Blisters** instead of standing as 20 unrelated entries.

It is hand-curated, not script output. The strings come from two places, 703 in all:

- the Symptoms sheet of `data/4-reports/4_Additional_Info_Index.xlsx` (master list V2.1)
- the Symptom individuals in `ontologies/ari_t1d.owl`

69 strings are only in the ontology and 33 only in the sheet.

| Column | Meaning |
|--------|---------|
| Symptom ID | `ARIS:` id of the symptom, for exact and broader rows |
| Symptom | The string exactly as ARI stores it |
| Mapping | `exact`: same meaning as the SYMP term. `broader`: the SYMP term is the nearest broader one. `merged`: same meaning as the row in Merged Into, which carries the mapping. `not a symptom`: a heading ("Rare:"), a note on course or onset, a lab or imaging result, or a cross-reference |
| SYMP ID / SYMP Label | The Symptom Ontology term |
| Parent Symptom | The broader ARI symptom this one groups under, when ARI has one |
| Merged Into | For `merged` rows, the symptom with the same meaning |

Counts: 191 exact, 405 broader, 51 merged, 56 not a symptom. 339 symptoms group under one of 111
ARI parent symptoms. A symptom without a Parent Symptom takes its parent from SYMP: the SYMP term
for a broader mapping, or the SYMP term's own parent for an exact one (Blisters → *skin and
integumentary tissue symptom*).

SYMP is small (895 active terms) and has no term for many patient-worded symptoms, so a broader
mapping is often the body-system term, e.g. "Brittle fingernails" → *skin and integumentary tissue
symptom*.

## Build

```
python build_symptom_mapping.py <path to data/2-databases>
```

The database folder is not tracked in git, so pass the path of a checkout that has `symp.owl`
(download it from <http://purl.obolibrary.org/obo/symp.owl>). The script checks the TSV first and
stops if a string from either source has no row, a SYMP id is obsolete or relabelled, or a parent
or merge target is not an exact or broader row. It then writes:

- **Report 4, Symptoms sheet**: Symptom ID, SYMP ID, SYMP Label, SYMP Mapping, Parent Symptom,
  Parent ID and Merged Into for every row. A merged row shows the values of the symptom it merges
  into. Body-system category rows (`cat`) are left blank.
- **Report 4, Symptom Mapping sheet**: one row per symptom string, with how many diseases list it
  in the Symptoms sheet and in the ontology.
- **`ari_symptoms.owl`**: a class per exact or broader symptom (`ARIS_…`) under its parent. Each class has:
  - `skos:exactMatch` or `skos:broadMatch` to its SYMP term
  - its merged strings as `skos:altLabel`
  - `ariSymptomIndividual` links to the Symptom individuals in `ari_t1d.owl` that carry it

  The SYMP terms it references are copied in with their labels and is_a parents, up to *symptom*,
  so the file opens in Protégé without importing SYMP.

The OWL file shows the proposal for review. `ontologies/ari_t1d.owl` is still the record, and it
is not changed here.
