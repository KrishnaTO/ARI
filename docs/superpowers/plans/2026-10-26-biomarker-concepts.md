# Biomarker concepts (ontology modules, Project 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fill `ari_biomarkers.owl` with reviewed ARIB concepts for every autoantibody, antigen and
clinical biomarker, linked to HPO / Protein Ontology / HGNC / ChEBI / LOINC and to each other, with
every per-disease entry pointing at its concept, and show each marker's relatives in the editor.

**Architecture:** Scripts in `notebook/biomarker-concepts/` read the modules and local releases and
turn proposals into rows of a review table. One writer turns rows into OWL, both for the PR
preview and, once reviewers have decided every row, for the final commit. The validator
gains biomarker checks. The app links new entries by label lookup across the biomarker module and
serves a per-entry concept view that the disease page expands in place.

**Tech Stack:**
- Python 3.12, stdlib `xml.etree` / expat for the data repo (the validator stays stdlib-only).
- pytest for the new data-repo scripts and validator checks (run locally; no new CI job).
- ROBOT 1.9.11 via `tools/format-owl.sh` (Java in WSL here).
- App: owlready2 0.51, FastAPI, pytest, `node --test`.

**Spec:** `docs/superpowers/specs/2026-10-26-biomarker-concepts-design.md`. It refines the
"Project 2" section of `docs/superpowers/specs/2026-10-18-ontology-modules-design.md`.

## Global Constraints

- **Concept IRIs:** `http://www.aurint.org/ontologies/ari-biomarkers#ARIB_nnnnnnn`, seven digits,
  allocated in sequence after the highest id present, never reused. Each class has
  `oboInOwl:id` `ARIB:nnnnnnn`, as ARIS classes do.
- **Each ARIB class is a subclass of exactly one of these, or of an ARIB class of the same kind:**
  - `http://www.aurint.org/ontologies/ari-disease#Autoantibody`
  - `…ari-disease#Antigen`
  - `…ari-disease#ClinicalBiomarker`
- **New properties go only in `ari_core.owl`, in the `ari-disease#` namespace** (the Project 1
  rule). Each is an annotation property:

  | Property | Label |
  | --- | --- |
  | `ari-disease#targetsAntigen` | "targets antigen" |
  | `ari-disease#expressedIn` | "expressed in" |
  | `ari-disease#associatedSymptom` | "associated symptom" |
  | `http://www.w3.org/2004/02/skos/core#relatedMatch` | — |

- **`ARI_NoConcept` values:** exactly `not a symptom`, `no term`, `not linked`, `not a biomarker`.
- **External IRIs:**

  | Source | IRI form | Example |
  | --- | --- | --- |
  | HPO | `http://purl.obolibrary.org/obo/HP_nnnnnnn` | — |
  | Protein Ontology | `http://purl.obolibrary.org/obo/PR_<id>` | `PR_Q05329` |
  | ChEBI | `http://purl.obolibrary.org/obo/CHEBI_<n>` | — |
  | HGNC | `http://identifiers.org/hgnc/<n>` | — |
  | LOINC | `https://loinc.org/<code>` | `https://loinc.org/4548-4` |

- **Slices and imports:**
  - Generated slices: `ari_pr.owl`, `ari_chebi.owl`, `ari_hgnc.owl` and `ari_loinc.owl`, with
    ontology IRIs `http://www.aurint.org/ontologies/ari_pr` (and so on).
  - `ari_biomarkers.owl` imports core and the four slices, and the catalog lists them.
  - HPO terms are referenced with no slice.
- **Label lookup is the Project 1 rule:** the entry's `rdfs:label`, whitespace-stripped and
  case kept, equals a concept's `rdfs:label` or `skos:altLabel`. For biomarkers, it is done
  **within one kind**: an antibody entry looks up only Autoantibody concepts.
- **Category, kind and core class.** The app category names the kind, and the scripts use the
  same kind names:

  | App category | Kind | Core class | Disease link |
  | --- | --- | --- | --- |
  | `antibodies` | `antibodies` | `Autoantibody` | `hasAntibody` |
  | `antigens` | `antigens` | `Antigen` | `involvesAntigen` |
  | `biomarkers` | `tests` | `ClinicalBiomarker` | `hasBiomarker` |

- **Live entries:** entries with `ARI_Obsolete` `true` are never proposed or changed.
- **OWL handling:**
  - Read and write OWL as XML, never by line.
  - Run `MSYS_NO_PATHCONV=1 wsl -e tools/format-owl.sh <files>` after every write.
  - Never hand-edit a slice.
- **Local sources only.** No network call at build time. Every script takes the
  `data/2-databases` path as an argument. That folder is the primary checkout's, untracked:
  `F:/1Projects/7Projects-Aurint/ARI/data/2-databases`.
- **Re-runs never overwrite Protégé work.** `propose.py` never rewrites an existing ARIB class. It
  proposes only for live entries with neither `sharedConcept` nor `ARI_NoConcept`, and adds
  `altLabel`s, matches and targets only to concepts it creates in the same run.
- **Nothing reaches `main` unreviewed.** The apply script refuses a table with any blank or
  unknown `decision`.
- **Nothing on the live server or staging is touched without the user confirming that step at
  the time.**
- **Branches:**
  - Data repo: `biomarker-concepts` (foundations), then `biomarker-concepts/antibodies`,
    `/antigens` and `/tests` (review PRs), each cut from `origin/main` once the one before is
    merged.
  - App: `biomarker-concepts-linking` and `biomarker-concepts-view`, in worktrees under
    `ARI-metadata-manager/.claude/worktrees/` cut from `origin/main`.
- Every PR gets an entry under `## <branch>` in its repo's changelog (what and why).

## Decisions taken here that the spec left open (confirm when reviewing)

1. **One writer, two uses.** `propose.py` writes the review table **and** the OWL with every row
   applied, so the PR diff previews the result. `apply_review.py` restores the two module files
   from the base commit and re-runs the same writer on the accepted and corrected rows only.
2. **Review table columns:**

   | Column | Holds |
   | --- | --- |
   | `row` | the row's id |
   | `group` | `judgement` or `confident` |
   | `action` | what the row does (next table) |
   | `concept` | the concept key: an existing ARIB IRI, or `new:<preferred label>` |
   | `value` | the action's value |
   | `value_label` | a readable label for the value |
   | `diseases` | the diseases involved |
   | `entries` | the per-disease entries involved |
   | `evidence` | why the row is proposed |
   | `depends` | row ids this row needs, comma-separated |
   | `decision` | `accept`, `reject` or `correct` |
   | `correction` | the corrected value, for `correct` |
   | `note` | free text |

   `action` is one of these:

   | Action | Value |
   | --- | --- |
   | `concept` | the core kind or a parent concept key |
   | `altLabel` | — |
   | `exactMatch`, `broadMatch`, `closeMatch`, `relatedMatch` | the external IRI |
   | `no_term` | — |
   | `target` | the antigen concept key |
   | `link` | the concept key; one entry per row |
   | `not_a_biomarker` | — |
   | `label_fix` | the clean label |

   `correct` replaces `value` with `correction`. A row whose `depends` row was rejected is
   skipped and listed in the apply summary.
3. **IEDB source:** the IEDB B-cell assay export `bcell_full_v3` (CSV), downloaded into
   `data/2-databases/iedb/`. Its antigen name and UniProt IRI per assay are enough to propose
   targets; the SQL dump would need a database server.
4. **App version:** none to bump. `APP_VERSION` is derived from git.
5. **Tests for the data-repo scripts** live in `notebook/biomarker-concepts/tests/`, and for the
   validator in `.github/scripts/test_validate_mappings.py`. Both run with
   `python -m pytest -q <path>` and use tiny inline fixtures, not the real files.

## Review Focus

1. **A curator renames an antibody entry to a string that is an antigen concept's label.** The
   entry must not link the antigen. Lookup is per kind (Task 9 test).
2. **A curator edits a biomarker entry's frequency or source without renaming it.** Its
   `sharedConcept` values, including a bundle's several, and any `ARI_NoConcept` must survive
   the save (Task 9 test).
3. **`propose.py` is re-run after a curator edited an ARIB class in Protégé.** The class must be
   byte-for-byte unchanged in the output (Task 6 test).
4. **A reviewer rejects a `concept` row.** Its dependent `altLabel`, match, `target` and `link`
   rows must not be written, rather than linking to a class that does not exist (Task 7 test).
5. **The editor expands an entry with no concept, or a concept with no relatives.** It must
   render "no shared concept yet" or "none recorded", not an empty box or a script error
   (Task 11 test).

---

## Part A — Foundations (data repo, branch `biomarker-concepts`)

**Set up.** Run `git worktree list` and check that no other worktree is working on this area.
Then cut the branch in a new worktree:
- if the design PR (branch `biomarker-concepts-design`, holding the spec and this plan) is
  merged, use
  `git worktree add .claude/worktrees/biomarker-concepts -b biomarker-concepts origin/main`;
- otherwise cut it from `origin/biomarker-concepts-design` instead.

### Task 1: Core declarations and the new `ARI_NoConcept` value

**Files:**
- Modify: `ontologies/ari_core.owl`
- Modify: `.github/scripts/validate_mappings.py:187` (`NO_CONCEPT_VALUES`)
- Test: `.github/scripts/test_validate_mappings.py` (create)

**Interfaces:**
- Produces: the four properties in Global Constraints, declared in core; `NO_CONCEPT_VALUES`
  including `"not a biomarker"`.

- [ ] **Step 1: Write the failing test** `test_not_a_biomarker_is_a_valid_decision`.
  - Build `texts` for `check_no_concept_values` from a minimal module text per `ARI_OWNED` path.
    One entity carries `ARI_NoConcept "not a biomarker"`.
  - Assert no `no-concept-value` finding.
  - Add `test_a_misspelt_decision_is_an_error`, with `"not biomarker"` giving one finding.
- [ ] **Step 2: Run** `python -m pytest -q .github/scripts/test_validate_mappings.py`. Expected:
  the first test FAILs.
- [ ] **Step 3: Implement.**
  - Add `"not a biomarker"` to `NO_CONCEPT_VALUES`.
  - Declare the four annotation properties in `ari_core.owl` by XML edit:
    - `rdfs:label` per Global Constraints;
    - an `rdfs:comment` giving domain and range in words, e.g. "From an ARIB antibody class to
      the ARIB antigen class it binds.";
    - for `relatedMatch`, the standard SKOS IRI with no label.
  - Format the file.
- [ ] **Step 4: Verify.** Run pytest (PASS) and `python .github/scripts/validate_mappings.py`.
  Expected: no new error codes against `main`'s output, and `property-outside-core` absent.
- [ ] **Step 5: Commit** `Declare the biomarker relations in core; accept ARI_NoConcept "not a biomarker"`.

### Task 2: Local source readers

**Files:**
- Create: `notebook/biomarker-concepts/sources.py`
- Create: `notebook/biomarker-concepts/tests/test_sources.py` (with tiny inline sample files
  written to `tmp_path`)

**Interfaces:**
- Produces (all pure readers; each skips obsolete terms and raises `FileNotFoundError` naming the
  expected file when it is absent):
  - `read_hp(path) -> dict[str, Term]`, from `hp.obo`.
  - `read_pr(path) -> dict[str, Term]`, from PR's OBO release (`pro_nonreasoned.obo`). Keep only
    terms with `only_in_taxon NCBITaxon:9606`, their `is_a` ancestors, and non-human terms whose
    id is a UniProt accession.
  - `read_chebi(path) -> dict[str, Term]`, from `chebi_lite.obo`.
  - `read_hgnc(path) -> dict[str, Gene]`, from `hgnc_complete_set.txt`.
  - `read_loinc(path) -> dict[str, Term]`, from `LoincTable/Loinc.csv`. Synonyms come from
    `SHORTNAME`, `COMPONENT` and `RELATEDNAMES2`, split on `;`. Only `STATUS` `ACTIVE`.
  - `read_iedb_bcell(path) -> list[Assay]`, from `bcell_full_v3.csv`.
- Data shapes, in `sources.py`:
  - `Term(id: str, label: str, synonyms: list[str], parents: list[str], release: str)`;
  - `Gene(hgnc_id: str, symbol: str, name: str, aliases: list[str], uniprot: list[str])`;
  - `Assay(antigen_name: str, antigen_iri: str, organism: str, disease: str)`.

- [ ] **Step 1: Download.** Into `data/2-databases/`: PR (`pro_nonreasoned.obo`), HGNC
  (`hgnc_complete_set.txt`), ChEBI (`chebi_lite.obo`) and IEDB (`iedb/bcell_full_v3.csv`, from
  the zip). **LOINC needs a loinc.org login: ask the user to download the LOINC table zip and
  unpack it to `data/2-databases/loinc/`.** Wait for it, and do not attempt it yourself.
  Record each release's version and date in the README (Task 8).
- [ ] **Step 2: Write the failing tests**, one per reader. For example,
  `test_read_hgnc_maps_symbol_to_uniprot` asserts that `read_hgnc(sample)["HGNC:4093"]` has
  symbol `GAD2` and `uniprot == ["Q05329"]`. `test_obsolete_terms_are_skipped` covers each OBO
  reader.
- [ ] **Step 3: Run** `python -m pytest -q notebook/biomarker-concepts/tests/test_sources.py`.
  Expected: FAIL (module missing).
- [ ] **Step 4: Implement the readers** (streaming line parse for OBO and TSV, `csv` for CSV).
- [ ] **Step 5: Run the tests** (PASS). Load each real file once and print term counts, as a
  sanity check that is not committed.
- [ ] **Step 6: Commit** `Add readers for the biomarker source releases`.

### Task 3: The biomarker slice extractor

**Files:**
- Create: `notebook/biomarker-concepts/build_biomarker_slices.py`
- Create (generated): `ontologies/ari_pr.owl`, `ari_chebi.owl`, `ari_hgnc.owl`, `ari_loinc.owl`
- Modify: `ontologies/ari_biomarkers.owl` (imports), `ontologies/catalog-v001.xml`
- Test: `notebook/biomarker-concepts/tests/test_slices.py`

**Interfaces:**
- Consumes: the Task 2 readers.
- Produces:
  - `referenced_terms(biomarkers_text: str) -> dict[str, set[str]]`, mapping source (`pr`,
    `chebi`, `hgnc`, `loinc`) to external IRIs. It reads every `skos:*Match` target on an ARIB
    class.
  - `write_slice(source: str, iris: set[str], terms, out_path) -> None`.
  - CLI `python build_biomarker_slices.py <data/2-databases>`.

**Behaviour:**
- Each slice holds each referenced term with its `rdfs:label` and `oboInOwl:id`, plus `is_a`
  ancestors for PR and ChEBI.
- The HGNC and LOINC slices hold label only (the HGNC label is the symbol, with the name as
  `IAO:0000115`).
- `ari_loinc.owl` carries LOINC's licence notice as an `rdfs:comment` on the ontology.
- A referenced IRI missing from its release stops the run, listing every missing one, as
  `build_symp_import.py` does.
- An empty set still writes the slice (an empty ontology), so the import graph is fixed from now
  on.

- [ ] **Step 1: Write the failing tests:**
  - `test_referenced_terms_reads_every_match`: a three-class ARIB text gives PR, HGNC and LOINC
    sets.
  - `test_a_missing_term_stops_the_run`: `SystemExit`, with the IRI in the message.
  - `test_pr_slice_includes_ancestors`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement it.** Follow `notebook/symptom-mapping/build_symp_import.py`'s
  structure and output header. Add the four `owl:imports` to `ari_biomarkers.owl` and the four
  `uri` entries to the catalog.
- [ ] **Step 4: Run it** on today's (empty) `ari_biomarkers.owl`, then format all six touched
  files. Then run
  `python -c "import owlready2 …"` (or the app's loader), loading `ontologies/ari_disease.owl`
  from the folder.
  Expected: loads with all imports. Validator: no new findings.
- [ ] **Step 5: Commit** `Add the PR, ChEBI, HGNC and LOINC slices for ari_biomarkers.owl`.

### Task 4: Validator biomarker checks

**Files:**
- Modify: `.github/scripts/validate_mappings.py`
- Test: `.github/scripts/test_validate_mappings.py`

**Interfaces:**
- Produces:
  - `biomarker_kinds(text: str) -> dict[str, str]`: ARIB class IRI → kind (`antibodies` /
    `antigens` / `tests`), found by walking `rdfs:subClassOf` to a core class.
  - `biomarker_labels(text, report) -> dict[str, dict[str, str]]`: kind → {label: class IRI}.
    It reports `concept-label-ambiguous` within a kind only, and `concept-id-repeated` for an
    `oboInOwl:id` on two ARIB classes, reusing the codes `concept_labels` emits.
  - `check_biomarker_concepts(texts, report)`, called from `check_modules`.

**Finding codes:**

| Code | Level | When |
| --- | --- | --- |
| `biomarker-concept-kind` | error | an ARIB class reaches no core kind, or two |
| `biomarker-link-wrong-kind` | error | an entry's `sharedConcept` is an ARIB class of another kind |
| `biomarker-concept-mismatch` | error | a single-link entry's link differs from its lookup; on both the label line and the link line |
| `biomarker-concept-missing` | warning | the label names a concept but the entry has no link |
| `biomarker-unmapped` | warning | a live entry with no link and no `ARI_NoConcept` whose label names no concept |
| `biomarker-decided-and-linked` | error | an entry has both a link and `ARI_NoConcept` |
| `biomarker-relation-target` | error | `targetsAntigen` not to an antigen ARIB class; `expressedIn` not to an `ari_anatomy.owl` class or an `ari_uberon.owl` term; `associatedSymptom` not to an ARIS class |
| `biomarker-external-missing` | error | a match IRI absent from its slice |
| `biomarker-concept-unlinked` | warning | an ARIB class with no `skos:exact/broad/closeMatch`, no `ARI_NoConcept`, and no ancestor ARIB class that has a match |

An entry with more than one `sharedConcept` (a bundle) gets only the kind and existence checks.
Obsolete entries are skipped. Add every code except `biomarker-relation-target` and
`biomarker-external-missing` to a new `is_biomarker_link_finding`. In `filter_to_changes`, keep
those findings unscoped when `BIOMARKERS_PATH` differs from `ref`, as for symptoms.

- [ ] **Step 1: Write the failing tests**, one per code, on inline module texts. The key cases
  are:
  - `test_lookup_is_per_kind`: an antibody entry labelled with an antigen concept's label →
    `biomarker-unmapped`, not a link to the antigen.
  - `test_a_bundle_is_not_checked_against_its_label`: two links, no finding.
  - `test_a_child_of_a_matched_parent_is_decided`: no `biomarker-concept-unlinked`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement** in the existing style (`read_entities`, `Report`, one docstring per
  check saying where its findings sit and why).
- [ ] **Step 4: Run** pytest (PASS). Then run the validator on the repo. Expected: one
  `biomarker-unmapped` warning per live biomarker entry (about 700), and nothing else new.
- [ ] **Step 5: Commit** `Validate biomarker concepts, links and relations`.

### Task 5: Reading biomarker names

**Files:**
- Create: `notebook/biomarker-concepts/names.py`
- Test: `notebook/biomarker-concepts/tests/test_names.py`

**Interfaces:**
- Produces:
  - `normalise(label: str) -> str`, the grouping key: lower-case, collapsed whitespace,
    punctuation and hyphens dropped, and the "anti-"/"antibodies"/"autoantibodies"/"antibody"
    words removed for antibodies only (`normalise(label, kind)`).
  - `parse_antibody(label: str) -> Antibody(stem: str, qualifier: str | None)`: `qualifier` is
    an isotype or functional phrase from `QUALIFIERS = ("IgG4", "IgG", "IgA", "IgM", "IgE",
    "neutralizing", "blocking", "stimulating")`, matched case-insensitively as a whole word.
  - `split_bundle(label: str) -> list[str]`: the marker names in a bundle, or `[label]`. It
    splits on `,`, ` and `, ` / ` and ` & `, but only when every part looks like a marker name
    on its own.
  - `parse_family(label: str) -> Family(name: str, members: list[str]) | None`: "X antigens
    (A, B, C)" → `name="X antigens"`, `members=["A","B","C"]`.
  - `noisy(label: str) -> str | None`: the clean label when a stray number, percentage or
    frequency fragment sits inside the name ("Anti-GAD65  25" → "Anti-GAD65"), else None.
  - `sentence_like(label: str) -> bool`: more than 8 words, or a verb phrase such as "is", "are",
    "may", "seen in" or "associated with".

- [ ] **Step 1: Write the failing tests** with the spec's own examples:
  - `normalise("Type VII Colagen", "antigens") != normalise("Type VII collagen", "antigens")`.
    The spelling slip is caught by fuzzy grouping in Task 6, not by normalise; assert this so
    nobody widens normalise.
  - `normalise("Anti-GAD65 autoantibodies", "antibodies") == normalise("Anti-GAD65", "antibodies")`
  - `parse_antibody("Anti-CNTN1 IgG4") == Antibody("CNTN1", "IgG4")`
  - `parse_antibody("Anti-ADAMTS13 neutralizing IgG").qualifier == "neutralizing IgG"`
  - `split_bundle("ANA, anti-dsDNA and anti-Sm") == ["ANA", "anti-dsDNA", "anti-Sm"]`
  - `parse_family("Sperm surface antigens (SP-10, YLP-12, Izumo1)").members == ["SP-10", "YLP-12", "Izumo1"]`
  - `noisy("Anti-GAD65  25") == "Anti-GAD65"`
  - `noisy("Anti-ACSL5 (…)  <50%")` is not None
  - `noisy("Anti-IA-2")` is None
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run them over the real labels.** Print every label the functions change, read the
  list, and add a test case for any wrong parse you fix. Expected: PASS.
- [ ] **Step 5: Commit** `Parse biomarker names: antibody targets, isotypes, bundles, families`.

### Task 6: The proposal script and the shared writer

**Files:**
- Create: `notebook/biomarker-concepts/model.py` (read entries and concepts; write rows into the
  OWL)
- Create: `notebook/biomarker-concepts/review_table.py` (read and write the TSV)
- Create: `notebook/biomarker-concepts/propose.py`
- Test: `notebook/biomarker-concepts/tests/test_propose.py`, `test_model.py`

**Interfaces:**
- Consumes: Tasks 2 and 5.
- Produces:
  - `Entry(iri, kind, label, diseases: list[tuple[str, str]], obsolete: bool,
    shared: list[str], no_concept: str | None)`
  - `Concept(iri, kind, label, alt_labels, parents, matches: dict[str, list[str]],
    targets: list[str], no_concept)`
  - `read_entries(disease_text: str) -> list[Entry]`
  - `read_concepts(biomarkers_text: str) -> list[Concept]`
  - `Row`: a dataclass whose fields are the review table columns in Decision 2.
  - `write_rows(rows: list[Row], biomarkers_path, disease_path) -> dict[str, str]`
    - Applies the rows to the two files with ElementTree.
    - Returns concept key → ARIB IRI.
    - Allocates ids per Global Constraints.
    - `link` sets `sharedConcept` (several `link` rows on one entry make a bundle).
    - `label_fix` replaces the entry's `rdfs:label`.
    - `not_a_biomarker` and `no_term` set `ARI_NoConcept` on the entry or the class.
    - `target` sets `targetsAntigen`.
    - Leaves layout to ROBOT.
  - `review_table.write(path, rows)` and `review_table.read(path) -> list[Row]`
  - `propose(kind, disease_text, biomarkers_text, sources) -> list[Row]`
  - CLI `python propose.py --kind {antibodies,antigens,tests} <data/2-databases> [--out DIR]`:
    writes `notebook/biomarker-concepts/review/<kind>.tsv` and applies every row to the OWL in
    place. With `--out`, it writes the TSV and copies of the two OWL files into `DIR` instead.

**What `propose` does (judgement rows first in the output, then confident ones; ids in that
order):**
1. **Takes the live entries of `kind`** with no `sharedConcept` and no `ARI_NoConcept`.
   - Sentence-like labels → `not_a_biomarker` (judgement).
   - Noisy labels → `label_fix` (judgement); later steps use the clean label.
   - Bundles → one `link` per part (judgement).
2. **Groups labels** by `normalise`, then merges groups whose keys are within edit distance 2 and
   share a first token (judgement; the "Colagen" case). It looks up existing concepts first: a
   label already held by a concept of the kind gets a `link` to it (confident).
3. **Per new group:**
   - a `concept` row, named by the most frequent label, with ties broken by the shortest;
   - an `altLabel` row for every other label;
   - a `link` row per entry.
4. **Nesting** (antibodies): a qualified antibody's `concept` row has the unqualified concept as
   its parent, which is created if no entry names it. A family's members become child concepts
   of the family concept.
5. **External match:**
   - **Antibodies** match an HPO term whose label or synonym contains the stem and "antibody".
     Exact stem → `exactMatch` (confident); else `closeMatch` (judgement).
   - **Antigens** resolve the name to an HGNC symbol, alias or name, then to its UniProt
     accession, then to `PR_<acc>` if PR has it. That gives `exactMatch` PR and `relatedMatch`
     HGNC (confident on an exact symbol or name, judgement on an alias).
     - A name that resolves to no protein tries ChEBI label and synonyms.
   - **Tests** match the LOINC long common name, short name or related names (judgement unless
     exact).
   - No match → `no_term` (confident), unless the concept has a parent with a match.
6. **Targets** (`kind == "antigens"` only):
   - For every antibody concept on `main` without `targetsAntigen` on itself or an ancestor
     (children inherit the parent's target, which is stated once), take its parsed stem and
     look it up among antigen concepts by label lookup.
   - If no antigen concept matches, propose a new antigen `concept` row for the stem with its
     external match (decision 8 in the spec), then a `target` row (confident when the name gave
     it).
   - Stems that do not resolve try IEDB: an assay whose antigen name contains the stem gives
     the antigen (judgement, with the assay count as evidence).
7. **Evidence and labels.** Every row fills `diseases`, `entries`, `value_label` and `evidence`,
   so a reviewer never needs another file.

- [ ] **Step 1: Write the failing tests** on a small inline disease and biomarkers text:
  - `test_existing_concepts_are_never_rewritten`: run `propose` and `write_rows` on a text with
    one hand-made ARIB class. That class's XML element is unchanged in the output (Review Focus 3).
  - `test_decided_entries_are_skipped`: entries with a link or `ARI_NoConcept` get no rows.
  - `test_judgement_rows_come_first`.
  - `test_a_qualified_antibody_nests_under_its_unqualified_concept`.
  - `test_a_bundle_gets_one_link_per_marker`.
  - `test_an_antibody_naming_an_unknown_antigen_creates_it` (antigens kind).
  - `test_write_rows_round_trips`: write, re-read with `read_concepts` / `read_entries`, and get
    the same labels, links and matches.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement** `model.py`, `review_table.py` and `propose.py`.
- [ ] **Step 4: Run them** (PASS). Then run a **dry run** on the real files into a scratch copy
  (`--out <scratch dir>`, a flag that writes the TSV and OWL copies there instead of in place),
  for each kind. Read the counts: concepts, judgement rows and `no_term` rows.
  Expected: about 266 antibody and 257 antigen groups before nesting, and 17 tests. Do not
  commit any output.
- [ ] **Step 5: Commit** `Propose biomarker concepts into a review table and the OWL`.

### Task 7: Applying a reviewed table

**Files:**
- Create: `notebook/biomarker-concepts/apply_review.py`
- Test: `notebook/biomarker-concepts/tests/test_apply.py`

**Interfaces:**
- Consumes: `review_table.read`, `model.write_rows`.
- Produces:
  - `decide(rows: list[Row]) -> tuple[list[Row], list[Row]]` returns (rows to write, rows
    skipped).
    - Raises `ValueError` listing every row with a blank or unknown `decision`, or `correct`
      with an empty `correction`.
    - `correct` swaps in the correction.
    - `reject` drops the row, and every row whose `depends` includes a dropped row is skipped.
    - A rejected `label_fix` adds an `altLabel` row: the entry's original (noisy) label, on the
      concept its `link` row names, so lookup still finds it (spec: Per-disease entries).
  - CLI `python apply_review.py review/<kind>.tsv --base <ref>`:
    1. restores `ontologies/ari_biomarkers.owl` and `ari_disease.owl` from `<ref>`
       (`git show`);
    2. calls `write_rows` on the decided rows;
    3. deletes the TSV;
    4. prints counts and the skipped rows.

    The user then runs the slice build and the formatter.

- [ ] **Step 1: Write the failing tests:**
  - `test_a_blank_decision_refuses_to_apply`.
  - `test_rejecting_a_concept_skips_its_dependents` (Review Focus 4).
  - `test_correct_replaces_the_value`.
  - `test_a_rejected_label_fix_keeps_the_noisy_label_as_an_alt_label`.
  - `test_accept_all_writes_what_propose_wrote`: `write_rows` from a fully accepted table
    produces the same files as `propose.py`'s preview.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run them.** Expected: PASS.
- [ ] **Step 5: Commit** `Apply a reviewed biomarker table to the OWL`.

### Task 8: Docs, changelog and the foundations PR

**Files:**
- Create: `notebook/biomarker-concepts/README.md`
- Modify: `README.md` (ontologies list), `CLAUDE.md` (table row: name the new slices),
  `changelog.md`

- [ ] **Step 1: Write the README.**
  - **Contents:**
    - sources, with release dates;
    - the review flow: propose → PR → table → apply → slices → format → validate;
    - the table columns and actions (Decision 2);
    - how to add `targetsAntigen` / `expressedIn` / `associatedSymptom` in Protégé
      (Annotations pane, value is a class IRI).
  - **Allowed targets for each relation.**
  - **A SPARQL example**, as `notebook/symptom-mapping/README.md` has: the diseases whose
    antibody entries link a given ARIB concept.
- [ ] **Step 2:** Add a `## biomarker-concepts` changelog entry, then run the validator and
  every pytest. Check that `git status` shows no stray outputs.
- [ ] **Step 3: Commit, push and open the PR** against `main`. Its body says that it adds no
  concepts yet, and that the first review PR follows once the app linking PR (Task 9) is merged.
  **Ask the user before merging.**

---

## Part B — App linking (app repo, branch `biomarker-concepts-linking`)

Must be merged and deployed **before** the first review PR merges, so no curator save drops a
new link (spec: Delivery step 1).

### Task 9: Link biomarker entries by label lookup

**Files:**
- Modify: `app/concepts.py`, `app/ontology_service.py:122,1424-1448` (`_symptom_concept`,
  `_set_symptom_concept`, `add_item`, `update_item`)
- Modify: `tests/fixtures/ontologies/ari_biomarkers.owl`, `ari_core.owl` (the Task 1
  declarations), plus the four empty slices and the catalog entries
- Test: `tests/test_ontology_service.py`

**Interfaces:**
- Produces:
  - `concepts.BIOMARKERS_ONTOLOGY = "http://www.aurint.org/ontologies/ari_biomarkers"`
  - `concepts.KIND_CLASSES = {"antibodies": "…ari-disease#Autoantibody", "antigens":
    "…#Antigen", "biomarkers": "…#ClinicalBiomarker"}`
  - `concept_index(world, ontology_iri, under: str | None = None)`. With `under`, it indexes
    only classes that are subclasses (transitively) of that class IRI.
  - `OntologyService._concept_indexes: dict[str, dict[str, str]]`, keyed by category
    (`symptoms` plus the three above), built in `_load`.
  - `_concept_for(category, values) -> str | None` and `_set_shared_concept(e, concept)`
    replace `_symptom_concept` / `_set_symptom_concept`. Same body, any category in
    `_concept_indexes`.

**Behaviour:**
- **Add:** an entry is linked by lookup in its own category's index.
- **Rename:** an entry is relinked only when the stripped label changes, as today. A renamed
  bundle relinks to its lookup, or to nothing.
- **Any other save** leaves `sharedConcept` and `ARI_NoConcept` alone.

- [ ] **Step 1: Write the failing tests.**
  - **Fixture:** add to `ari_biomarkers.owl` one antibody class "Anti-GAD65 antibody"
    (altLabel "GADA") and one antigen class "GAD65".
  - **Tests:**
    - `test_an_antibody_links_the_concept_its_label_names`: `add_item(..., "antibodies",
      {"name": "GADA"})` gives a `sharedConcept` equal to the antibody class.
    - `test_lookup_stays_within_the_kind`: an antibody named "GAD65" gets no link
      (Review Focus 1).
    - `test_a_save_without_rename_keeps_every_link`: an antibody entry with two
      `sharedConcept` triples, updated with only `{"frequency": "40%"}`, still has both
      (Review Focus 2).
    - `test_a_clinical_biomarker_links_by_label`.
- [ ] **Step 2: Run** `python -m pytest -q tests/test_ontology_service.py -k "concept or links"`.
  Expected: FAIL.
- [ ] **Step 3: Implement.** Grep for `_symptom_concept` / `_set_symptom_concept` and rename
  every caller.
- [ ] **Step 4: Run** `python -m pytest -q`, `ruff check .` and
  `node --test tests/*.test.js`. Expected: all pass.
- [ ] **Step 5: Changelog, commit, push, open the PR.** Cross-link it with the foundations PR.
  **Ask the user before merging or deploying.**

---

## Part C — The review PRs (data repo)

Each kind is its own branch and PR, in order: antibodies, antigens, tests. Each starts once the
previous one has merged. These tasks are run with the user, not by a subagent alone: the user
reviews the table.

### Task 10: Review PR — one kind (repeat for `antibodies`, `antigens`, `tests`)

- [ ] **Step 1:** Cut `biomarker-concepts/<kind>` from `origin/main` in a new worktree. Run
  `python notebook/biomarker-concepts/propose.py --kind <kind> <data/2-databases>`, then
  `build_biomarker_slices.py`, then the formatter on every changed `ontologies/*.owl`.
- [ ] **Step 2: Verify.**
  - Run the validator: no errors.
  - Check the `biomarker-unmapped` count for this kind: it equals the entries the table leaves
    undecided, which should be 0.
  - Load the disease file in owlready2 with imports.
- [ ] **Step 3: Open the PR.**
  - **Body:** row counts by group and action, and the review instructions (fill `decision` on
    every row; `correct` with a `correction`; filling `accept` down the confident block in one
    action is fine).
  - Changelog entry under `## biomarker-concepts/<kind>`.
  - **Stop and hand the table to the user.**
- [ ] **Step 4: Apply.** When the user says the table is filled (on the branch, or a file they
  hand back):
  1. run `apply_review.py review/<kind>.tsv --base origin/main`;
  2. rebuild the slices;
  3. format;
  4. validate.

  Commit `Apply the <kind> review` and push. Report the skipped rows.
- [ ] **Step 5:** The user merges. Do not merge it yourself.

---

## Part D — Editor view (app repo, branch `biomarker-concepts-view`)

Can be built while Part C is in review. The fixtures carry the concepts it needs.

### Task 11: The concept view and expand-in-place rows

**Files:**
- Create: `app/biomarker_concepts.py`
- Modify: `app/routes/ontology.py` (one route)
- Create: `static/js/biomarker-detail.js`, using the `review-model.js` pattern: a global plus
  `module.exports`
- Modify: `static/js/panels.js` (`renderAntibodies`, `renderBiomarkers`, `renderImmuneList` for
  `antigens`), `static/index.html` (script tag before `panels.js`), and the CSS file that styles
  `.data-table`
- Modify: `tests/fixtures/ontologies/ari_biomarkers.owl`, `ari_disease.owl`. Use a second
  disease whose antibody also links "Anti-GAD65 antibody" and a second antibody concept, so the
  "Also in" and "Appears with" sections have content. Also add a `targetsAntigen` and one
  `expressedIn`.
- Modify: `.github/workflows/*` (the `node --test` line gets the new test)
- Test: `tests/test_biomarker_concepts.py`, `tests/biomarker-detail.test.js`

**Interfaces:**
- `concept_detail(svc: OntologyService, entry_iri: str) -> dict`
- `GET /api/v2/biomarker-concept/{iri:path}`: it raises `NotFound` for an IRI that is not a
  biomarker entry. The response:

  ```
  {"entry": str, "status": "linked" | "bundle" | "no_concept" | "unlinked",
   "reason": str | None,                       # the ARI_NoConcept value
   "concepts": [{
      "iri", "id", "label", "kind", "alt_labels": [str],
      "external": [{"predicate", "iri", "curie", "label"}],   # label from the slice; HPO: curie only
      "parents": [Ref], "children": [Ref],
      "targets": [Ref & {"external": [...]}],    # antibody → antigen, with PR/HGNC links
      "targeted_by": [Ref], "same_target": [Ref],
      "appears_with": [Ref & {"shared": int}],   # top 10, by shared diseases desc, then label
      "also_in": [{"iri", "label"}],             # diseases, excluding the entry's own
      "body_parts": [Ref], "symptoms": [Ref]}]}
  # Ref = {"iri": str, "label": str}
  ```

- **Indirect relatives.** "Appears with" counts the concepts linked by entries of every disease
  that has an entry linked to this concept. It counts distinct diseases shared, across all three
  kinds, and excludes the concept itself.
- `conceptDetailHtml(detail, esc) -> string` in `biomarker-detail.js`. It takes `esc`, the HTML
  escaper `panels.js` uses (passed in, not a global).

**Behaviour:**
- **Rows:** in each of the three panels, clicking a row toggles a following
  `<tr class="concept-detail"><td colspan=N>`. It is fetched on first open and cached per entry.
  This replaces the antibody panel's `#ab-detail` card; its sources and IRI move into the
  expanded row.
- **Disease names** in "Also in" call `selectDisease(iri)`.
- **Empty states:**
  - `unlinked` → "No shared concept yet."
  - `no_concept` → "No shared concept: <reason>."
  - An empty section → "none recorded".

- [ ] **Step 1: Write the failing Python tests:**
  - `test_detail_lists_target_and_gene`
  - `test_appears_with_counts_shared_diseases`
  - `test_also_in_excludes_the_entrys_disease`
  - `test_an_unlinked_entry_reports_unlinked`
  - `test_a_bundle_returns_each_concept`
  - `test_a_non_biomarker_iri_is_not_found`
- [ ] **Step 2: Write the failing node tests:**
  - `unlinked renders "No shared concept yet."`
  - `a concept with no relatives renders "none recorded" in each empty section`
    (Review Focus 5)
  - `labels are escaped`
- [ ] **Step 3: Run** `python -m pytest -q tests/test_biomarker_concepts.py` and
  `node --test tests/biomarker-detail.test.js`. Expected: FAIL.
- [ ] **Step 4: Implement** the service, route, JS module and the three panels.
- [ ] **Step 5: Run** the full suite, `ruff check .` and all node tests. Expected: PASS.
- [ ] **Step 6: Check in a browser.** Start the app locally against the fixtures, open the
  fixture disease, expand an antibody row, and check each section and a disease link. Screenshot
  it for the PR.
- [ ] **Step 7: Changelog, commit, push and open the PR.** **Ask the user before merging or
  deploying.**

---

## Part E — Live

### Task 12: Deploy and check "done"

- [ ] **Step 1:** With the user, step by step: deploy the linking app PR before the first review
  PR merges, and the view PR whenever it is approved. Nothing on the server is touched without
  their go-ahead at that step (DEPLOY.md's update flow).
- [ ] **Step 2:** After the three review PRs merge, run the validator on `main`.
  Expected: zero `biomarker-unmapped` and `biomarker-concept-unlinked` warnings, or each one
  explained by a row the reviewers rejected.
- [ ] **Step 3:** On the live editor, the user expands one antibody, one antigen and one clinical
  biomarker row. Report what they see against the spec's "Done".
