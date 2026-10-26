# Symptom mapping (ARI#132)

The mapping of every symptom string ARI holds to the
[Symptom Ontology](http://purl.obolibrary.org/obo/symp.owl) (SYMP, release 2026-07-30) and the
[Human Phenotype Ontology](http://purl.obolibrary.org/obo/hp.obo) (HPO, release 2026-02-16) lives in
**`ontologies/ari_symptoms.owl`**. It also groups similar-sounding symptoms under a root symptom, so
that "Blisters on eyes", "Blister on lips" and "Genital blisters" sit under **Blisters** instead of
standing as 23 unrelated entries.

It was hand-curated from 903 strings (the Symptoms sheet of
`data/4-reports/4_Additional_Info_Index.xlsx` and the Symptom individuals in the ontology). The OWL
is now the record: there is no mapping table to keep in step with it.

## How the OWL holds it

| In `ari_symptoms.owl` | Meaning |
|--------|---------|
| An `ARIS_…` class | One shared symptom. Its `rdfs:label` is the symptom string |
| `skos:altLabel` | A string merged into it: same meaning, so it links this class |
| `skos:exactMatch` / `skos:broadMatch` | Its SYMP term and its HPO term. `broadMatch`: the term is the nearest broader one. No HPO match means HPO has only narrower terms |
| `rdfs:subClassOf` | Its parent: another ARIS class, or a SYMP term when ARI has no parent for it. The roots sit under `ari-disease#Symptom` |

In `ari_disease.owl`, a Symptom individual is one symptom *in one disease*: it carries that
disease's likelihood, description and source, and the editor deletes it when a curator removes it
from that disease. So "Fatigue" stays 76 individuals, one per disease, and each points at the one
shared **Fatigue** class with `sharedConcept`. To ask which diseases list fatigue:

```sparql
PREFIX ari:  <http://www.aurint.org/ontologies/ari-disease#>
PREFIX aris: <http://www.aurint.org/ontologies/ari-symptoms#>
SELECT ?disease WHERE { ?disease ari:hasSymptom ?s . ?s ari:sharedConcept aris:ARIS_0000190 }
```

An individual links a class by **label lookup**: its `rdfs:label`, with surrounding whitespace
stripped and case kept, equals a class's `rdfs:label` or `skos:altLabel`. Nothing else carries the
link.

## Mapping a new symptom string

A symptom a curator adds or renames in the editor, or a string from a new master list, has no link
until one of these is done:

- add it as the `rdfs:label` of a new `ARIS_…` class in `ontologies/ari_symptoms.owl` (Protégé),
  with its SYMP and HPO matches and its parent;
- or add it as a `skos:altLabel` on the existing class with the same meaning;
- or, when it is not a symptom (a heading, a note on course or onset, a test result, a
  cross-reference), set `ARI_NoConcept "not a symptom"` on the Symptom individual in
  `ari_disease.owl`.

The editor links a new or renamed symptom by the same lookup. `.github/scripts/validate_mappings.py`
checks the result. A symptom with neither a link nor `ARI_NoConcept`, or a label no class holds, is a
warning: it appears when a curator adds a symptom the OWL does not know yet. A wrong link, a label
held by two classes, or an individual both linked and marked `ARI_NoConcept` is an error.

## Build

The database folder is not tracked in git, so pass the path of a checkout that has `symp.owl` and
`hp.obo` (from <http://purl.obolibrary.org/obo/symp.owl> and <http://purl.obolibrary.org/obo/hp.obo>).

```
python notebook/symptom-mapping/build_symp_import.py <path to data/2-databases>
wsl -e tools/format-owl.sh ontologies/ari_symp.owl
python notebook/symptom-mapping/build_symptom_report.py <path to data/2-databases>
```

Run every line from the repository root; Java for the formatter is in WSL (see `CLAUDE.md`).

- **`build_symp_import.py`** writes `ontologies/ari_symp.owl` and nothing else: every SYMP term an
  ARIS class names and its is_a ancestors up to *symptom*, with SYMP's label, id and parents. It
  stops if a linked SYMP term, or a linked HPO term, is missing or obsolete in the release. HPO
  terms are only checked; the OWL references them by IRI. The slice is generated, never edited by
  hand, and `ari_symptoms.owl` imports it. Run it after adding SYMP terms to a class.
- **`build_symptom_report.py`** rebuilds two sheets of Report 4 from the OWL and changes no OWL file.
  HPO labels come from `hp.obo`, since the OWL holds HPO IRIs only.
  - *Symptoms sheet*: Symptom ID, SYMP ID, SYMP Label, SYMP Mapping, HPO ID, HPO Label, HPO Mapping,
    Parent Symptom, Parent ID and Merged Into for every row. A merged row shows the values of the
    symptom it merges into. Body-system category rows (`cat`) are left blank.
  - *Symptom Mapping sheet*: one row per symptom string, with how many diseases list it in the
    Symptoms sheet and in the ontology.

## Counts

196 exact, 569 broader, 63 merged, 75 not a symptom. 452 symptoms group under one of 148 ARI parent
symptoms. A symptom without an ARI parent takes its parent from SYMP: the SYMP term for a broader
mapping, or the SYMP term's own parent for an exact one (Blisters → *skin and integumentary tissue
symptom*).

SYMP is small (895 active terms) and has no term for many patient-worded symptoms, so a broader
mapping is often the body-system term, e.g. "Brittle fingernails" → *skin and integumentary tissue
symptom*. HPO is much larger and has layperson synonyms, so it matches more closely. Of the 765
mapped symptoms, 310 match an HPO term exactly ("Brittle fingernails" → *Fragile nails*), against
196 for SYMP, and 452 map to a broader HPO term. Three have no HPO term at all: Dizziness, Stiffness
and Swelling. HPO has only narrower terms for these, such as *Vertigo*, *Joint stiffness* and *Edema*.
The parent hierarchy is unchanged: parents come from ARI or SYMP, never from HPO.
