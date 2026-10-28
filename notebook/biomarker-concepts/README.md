# Biomarker concepts

Tooling that ties every autoantibody, antigen and clinical biomarker entry of
`ontologies/ari_disease.owl` to one shared concept, an `ARIB_…` class in
**`ontologies/ari_biomarkers.owl`**, and each concept to published terms (HPO, Protein Ontology,
HGNC, ChEBI, LOINC). The design is in
[`docs/superpowers/specs/2026-10-26-biomarker-concepts-design.md`](../../docs/superpowers/specs/2026-10-26-biomarker-concepts-design.md).

**This tooling adds no concepts yet.** `ari_biomarkers.owl` is still empty. The concepts arrive in
three review PRs, one per kind, in this order: `antibodies`, then `antigens`, then `tests`. The
`antigens` PR also proposes the antibody → antigen `targetsAntigen` links. Until they land, the
validator reports every unlinked entry as a `biomarker-unmapped` warning (702 today: 357 antibodies,
327 antigens, 18 tests).

## How the OWL holds it

| In `ari_biomarkers.owl` | Meaning |
|--------|---------|
| An `ARIB_…` class | One shared concept. Its `rdfs:label` is the preferred name |
| `rdfs:subClassOf` | Its parent: an `Autoantibody`, `Antigen` or `ClinicalBiomarker` core class, or another ARIB class of that kind (an isotype under its antibody, a family member under its family) |
| `skos:altLabel` | A label merged into it: same meaning, so it links this class |
| `skos:exactMatch` / `closeMatch` / `broadMatch` / `narrowMatch` / `relatedMatch` | Its external term. An ARIB class is *decided* when it, or an ARIB class above it, has an exact, close or broad match, or `ARI_NoConcept "no term"` |
| `targetsAntigen`, `expressedIn`, `associatedSymptom` | Relations to other classes (see below) |

A per-disease entry (an `Ab_…`, antigen or biomarker individual in `ari_disease.owl`) is one marker
*in one disease*. It points at the one shared class with `sharedConcept`, found by **label lookup**:
its `rdfs:label`, stripped of surrounding whitespace and with case kept, equals the `rdfs:label` or a
`skos:altLabel` of a class of its kind. An entry that is not a biomarker (a sentence, a heading) takes
`ARI_NoConcept "not a biomarker"` instead.

## Sources

All six sources are read from `data/2-databases/` (untracked; see `CLAUDE.md`). `propose.py` and
`build_biomarker_slices.py` take that folder as their argument; `apply_review.py` reads no source.

| Source | File read (under `data/2-databases/`) | Release used | Used for |
|--------|------|------|------|
| HPO | `hp.obo` | hp/releases/2026-02-16 | antibody terms |
| Protein Ontology (PR) | `pro_nonreasoned.obo` | 73.1, 2026-09-15 | antigen terms; `ari_pr.owl` |
| ChEBI | `chebi_lite.obo` | chebi/256, 2026-10-06 | antigen terms; `ari_chebi.owl` |
| HGNC | `hgnc_complete_set.txt` | downloaded 2026-10-27 (the file has no version) | gene symbols and names; `ari_hgnc.owl` |
| LOINC | `loinc/LoincTable/Loinc.csv` (unpack the LOINC download into `loinc/`) | **not yet downloaded** | test terms; `ari_loinc.owl` |
| IEDB | `iedb/bcell_full_v3.csv` (extract it from `bcell_full_v3.zip`, the B-cell assay export, into `iedb/`) | **not yet downloaded** | the antigen each antibody binds |

LOINC needs a loinc.org login and the IEDB export comes from iedb.org's database export, so the
user downloads both. **Until those files arrive, the LOINC reader and the IEDB column names have
been tested only on small inline samples**, not on the real files. Expect to fix a column name or
two on the first real run of `--kind tests` or `--kind antigens`.

The four slices (`ari_pr.owl`, `ari_chebi.owl`, `ari_hgnc.owl`, `ari_loinc.owl`) are generated and
never edited by hand. `ari_loinc.owl` carries LOINC's licence notice.

## Scripts

| Script | What it does |
|--------|--------------|
| `propose.py --kind {antibodies,antigens,tests} <data/2-databases> [--out DIR]` | Reads the live entries of that kind that have neither `sharedConcept` nor `ARI_NoConcept`, groups their labels, matches each new concept to its source, and writes the review table **and** the OWL with every row applied, so the PR diff previews the result. With `--out` it writes the table and copies of the two OWL files into `DIR` instead. |
| `apply_review.py <review/kind.tsv> --base <ref>` | Restores `ari_biomarkers.owl` and `ari_disease.owl` from `<ref>`, writes only the decided rows, prints a summary and deletes the table. Paths are relative to the repository root. |
| `build_biomarker_slices.py <data/2-databases>` | Reads the matches in `ari_biomarkers.owl` and writes the four slices. A linked term missing from its release stops the run, listing each one. A source with no linked term gets an empty slice. |
| `names.py`, `sources.py`, `model.py`, `review_table.py` | Libraries: label parsing, the source readers, the OWL reader and the one writer (`model.write_rows`), and the table's TSV format. |

Tests: `python -m pytest -q notebook/biomarker-concepts/tests/`. They use small inline fixtures,
not the real releases.

## The review flow

Run every command from the repository root. Java for the formatter is in WSL (see `CLAUDE.md`).

1. **Propose.** `python notebook/biomarker-concepts/propose.py --kind <kind> <data/2-databases>`
   writes `notebook/biomarker-concepts/review/<kind>.tsv` and the two OWL files in place.
2. **Build the slices.** `python notebook/biomarker-concepts/build_biomarker_slices.py <data/2-databases>`
3. **Format.** `MSYS_NO_PATHCONV=1 wsl -e tools/format-owl.sh <each changed ontologies/*.owl>`
4. **Validate.** `python .github/scripts/validate_mappings.py`
5. **Open the PR.** Its diff shows the table and the OWL as it would be with every row accepted.
6. **Review.** Reviewers fill `decision` on **every** row (see below). A blank decision is refused,
   and filling `accept` down the whole confident block in one action is fine. To use a spreadsheet,
   open the TSV in it, fill `decision` (and `correction`), and save it back as tab-delimited text
   (UTF-8) under the same name; the byte-order mark and the quoting a spreadsheet adds are read back
   as they were.
7. **Apply.** `python notebook/biomarker-concepts/apply_review.py notebook/biomarker-concepts/review/<kind>.tsv --base origin/main`
   restores the two module files from the base, writes only the decided rows and deletes the table.
   Every check on the table runs first: if a decision is blank or unknown, a correction is empty, a
   `link` is corrected, a correction names a `new:` key that no written `concept` row creates, or a
   `depends` row is missing, the run lists every problem and nothing is touched. One kind of error
   comes later, from the writer, after the two module files were restored: a value that is not in
   the files (an IRI that is no ARIB class, an entry that is not there). The table is kept then; fix
   it and run again.
8. **Rebuild and check.** Build the slices, run the formatter and run the validator again.
9. **Merge.**

### The review table

`review/<kind>.tsv` is tab-separated, one row per proposed change, judgement rows first.

| Column | Holds |
|--------|-------|
| `row` | the row's id |
| `group` | `judgement` (a call a reviewer should check) or `confident` (the rest, for example an entry whose label an existing concept already holds) |
| `action` | what the row does (next table) |
| `concept` | the concept key: an existing ARIB IRI, or `new:<preferred label>` |
| `value` | the action's value |
| `value_label` | a readable label for the value |
| `diseases` | the diseases involved |
| `entries` | the per-disease entries involved |
| `evidence` | why the row is proposed |
| `depends` | row ids this row needs, separated by `;` (as `132;134`) |
| `decision` | `accept`, `reject` or `correct` (filled by the reviewer) |
| `correction` | the corrected value, for `correct` |
| `note` | free text |

| Action | Value | Effect |
|--------|-------|--------|
| `concept` | the parent: a core class IRI, or a parent concept key | creates the class under that parent |
| `altLabel` | none | adds a label to the concept, so lookup links entries holding it |
| `exactMatch`, `broadMatch`, `closeMatch`, `relatedMatch` | the external IRI | links the concept to a published term |
| `no_term` | none | sets `ARI_NoConcept "no term"` on the concept |
| `target` | the antigen concept key | adds `targetsAntigen` from the antibody concept |
| `link` | the concept key; one entry per row | sets `sharedConcept` on the entry |
| `not_a_biomarker` | none | sets `ARI_NoConcept "not a biomarker"` on the entry |
| `label_fix` | the clean label | replaces the entry's label with the clean one, for a stray trailing value (a number or percentage) |

`correct` replaces `value` with `correction`. A `concept` row's value is its parent, written in full:
one of the three core class IRIs

- `http://www.aurint.org/ontologies/ari-disease#Autoantibody`
- `http://www.aurint.org/ontologies/ari-disease#Antigen`
- `http://www.aurint.org/ontologies/ari-disease#ClinicalBiomarker`

or a parent concept key (`new:<label>` or an existing `ARIB_…` IRI). To un-nest a concept from a
family you reject, correct its `concept` row to the core class, for example
`http://www.aurint.org/ontologies/ari-disease#Autoantibody` for an antibody: a corrected `concept`
row depends only on its corrected parent, so the rejected family no longer skips it, its matches or
its links. A correction to a `new:` key must name a concept whose `concept` row is written.

Some rows cannot be corrected, or bring a row with them:

- **A `link` cannot be corrected**; apply refuses it. Reject the link, and the `altLabel` row that
  carries the entry's label if there is one, then fix the entry's concept in Protégé after the merge.
- **A corrected `label_fix`** writes the corrected label on the entry and adds it as an `altLabel`
  on the concept the entry's `link` row names, so the entry still resolves. If that link row was
  rejected or skipped, no altLabel is added and the summary says so.

Two rules a reviewer must know:

- **Rejecting a row also skips every row that depends on it**, however deep (a rejected `concept`
  skips its `altLabel`, match and `link` rows). The apply summary lists each skipped row and why.
  A rejected `label_fix` keeps the entry's original label as an `altLabel` on the concept its
  `link` row names, so the entry still resolves.
- **A new concept's preferred label cannot be renamed in the table.** To rename one, a curator
  edits it in Protégé after the merge and keeps the old spelling as a `skos:altLabel`, so lookup
  still matches the entries.

The apply summary also lists new concepts left with no deciding match and no `no_term`; the
validator warns on each (`biomarker-concept-unlinked`).

## Adding relations in Protégé

Three relations are authored by hand, as annotations on the ARIB class. Open `ari_disease.owl`, so
the ARIS, anatomy and UBERON classes are loaded to pick from. Protégé writes a new axiom into the
*active* ontology, so before adding anything make `ari_biomarkers` the active ontology (the
ontology selector at the top of the window). Then select the ARIB class, add the property in the
**Annotations** pane with a value that is a class IRI, and save. An annotation written into
`ari_disease.owl` instead is a `subject-in-two-modules` error, and the relation checks never see it.
The validator's `biomarker-relation-target` error enforces the targets.

| Relation | From | To |
|----------|------|----|
| `targetsAntigen` | an ARIB antibody class | an ARIB antigen class |
| `expressedIn` | any ARIB class | a class in `ari_anatomy.owl`, or a term in `ari_uberon.owl` |
| `associatedSymptom` | any ARIB class | an ARIS class in `ari_symptoms.owl` |

## What the validator checks

`python .github/scripts/validate_mappings.py` reports these for biomarkers (a concept's own findings sit
on its line in `ari_biomarkers.owl`; an entry's on its line in `ari_disease.owl`):

| Code | Level | What to do |
|------|-------|------------|
| `biomarker-concept-kind` | error | An ARIB class is under no kind or two, or has a parent other than its core class or an ARIB class of its kind (a PR term, say). Make it a subclass of exactly one of `Autoantibody`, `Antigen`, `ClinicalBiomarker`, or of ARIB classes of that kind; an external term goes in a skos match |
| `biomarker-link-wrong-kind` | error | An entry links a concept of another kind. Link a concept of the entry's own kind |
| `biomarker-relation-target` | error | `targetsAntigen`, `expressedIn` or `associatedSymptom` points at the wrong target, or `targetsAntigen` sits on a class that is not an antibody (table above). Point it at an allowed class, move it, or remove it |
| `biomarker-external-missing` | error | A match to a PR, ChEBI, HGNC or LOINC term that is not in its slice. Rebuild the slices |
| `biomarker-concept-mismatch` | error | An entry's `sharedConcept` is not the class its label names. Typical after a Protégé rename or a `label_fix`: link the class the label names, or fix the label (or add it as an `skos:altLabel` on the right class) |
| `biomarker-decided-and-linked` | error | An entry has both `ARI_NoConcept` and a `sharedConcept`. Remove whichever is wrong |
| `shared-concept-target-missing` | error | A `sharedConcept` points at a class no concept module declares (shared with symptoms and tissues). Link an existing class, or add this one |
| `concept-label-ambiguous` | error | Two ARIB classes **of one kind** carry the same `rdfs:label` or `skos:altLabel`, so an entry with that label cannot tell which it means. Remove it from all but one, or merge the classes. An antibody and an antigen may share a name |
| `concept-id-repeated` | error | Two ARIB classes (of any kind) carry the same `oboInOwl:id`. Give each its own |
| `biomarker-unmapped` | warning | An entry's label is not a label of any concept of its kind. Add the label as an `skos:altLabel` or create the concept (a review PR), or set `ARI_NoConcept` |
| `biomarker-concept-missing` | warning | An entry's label names a concept but the entry has no `sharedConcept`. Link it |
| `biomarker-concept-unlinked` | warning | A concept has no exact, close or broad match, none on an ARIB class above it, and no `ARI_NoConcept`. Add its external term, or set `ARI_NoConcept "no term"` |

## Querying

The diseases whose antibody entries link a given concept (substitute a real `ARIB_…` id once concepts
exist):

```sparql
PREFIX ari:  <http://www.aurint.org/ontologies/ari-disease#>
PREFIX arib: <http://www.aurint.org/ontologies/ari-biomarkers#>
SELECT ?disease WHERE { ?disease ari:hasAntibody ?a . ?a ari:sharedConcept arib:ARIB_0000001 }
```
