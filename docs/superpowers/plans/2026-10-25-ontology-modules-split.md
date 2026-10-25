# Ontology modules, Project 1 (the split) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split `ontologies/ari_t1d.owl` into the core, disease, symptoms, anatomy and biomarkers modules. The OWL files become the only record and the two curated TSVs retire. The editor keeps working across the switch.

**Architecture:** A one-off script moves every top-level element of today's two files into the module the spec assigns it. IRIs stay the same, and `ROBOT` (via `tools/format-owl.sh`) writes all of them in the canonical layout. Everything that read the TSVs reads the OWL instead:
- the validator
- the two slice extractors
- the report 4 builder
- the app, which finds a symptom's concept by label lookup in the loaded `ari_symptoms.owl`

The work is two PRs, merged together at a confirmed cutover: one to `KrishnaTO/ARI` and one to `KrishnaTO/ARI-metadata-manager`.

**Tech Stack:**
- Python 3 with `xml.etree` / expat. The validator stays stdlib-only.
- openpyxl for report 4.
- owlready2 0.51 in the app and for load checks.
- ROBOT 1.9.11 (Java 21 in WSL here; Java 17 in CI).
- pytest for the app.

**Spec:** `docs/superpowers/specs/2026-10-18-ontology-modules-design.md`, section "Project 1 — the split" and everything it references.

## Global Constraints

- Every existing entity IRI is unchanged. Moved entities keep `http://www.aurint.org/ontologies/ari-disease#…`, and ARIS classes keep `http://www.aurint.org/ontologies/ari-symptoms#ARIS_nnnnnnn`.
- **Ontology IRIs.** Each one ends in its file stem:

  | File | Ontology IRI |
  | --- | --- |
  | `ari_core.owl` | `http://www.aurint.org/ontologies/ari_core` |
  | `ari_symptoms.owl` | `http://www.aurint.org/ontologies/ari_symptoms` |
  | `ari_anatomy.owl` | `http://www.aurint.org/ontologies/ari_anatomy` |
  | `ari_biomarkers.owl` | `http://www.aurint.org/ontologies/ari_biomarkers` |
  | `ari_symp.owl` | `http://www.aurint.org/ontologies/ari_symp` |
  | `ari_uberon.owl` | `http://www.aurint.org/ontologies/ari_uberon` (unchanged) |
  | `ari_disease.owl` | `http://www.aurint.org/ontologies/ari-disease` (unchanged; this file is loaded directly, never imported) |

- **Imports:**

  | File | Imports |
  | --- | --- |
  | disease | core, symptoms, anatomy, biomarkers |
  | symptoms | core, `ari_symp` |
  | anatomy | core, `ari_uberon` |
  | biomarkers | core |
  | core | nothing |
  | slices | nothing |

- **New classes:** `http://www.aurint.org/ontologies/ari-core#Disease`, `#AnatomicalEntity` and `#Biomarker`, labelled `Disease`, `Anatomical entity` and `Biomarker`.
- **New properties keep the `ari-disease#` namespace** that every existing property has (the spec gives `ari-disease#sharedConcept`):
  - `ari-disease#sharedConcept`
  - `ari-disease#ARI_NoConcept`
  - `ari-disease#ARI_EnrichmentSource`
- `ARI_NoConcept` values are exactly `not a symptom`, `no term` and `not linked`.
- **No ARI-owned file except `ari_core.owl` declares a property.** The generated slices (`ari_uberon.owl`, `ari_symp.owl`) may declare the standard annotation properties they copy (`obo:IAO_0000115`, `oboInOwl:id`), as their sources do.
- Every `ontologies/*.owl` is in ROBOT's canonical layout. Run `wsl -e tools/format-owl.sh <files>` after any write; `catalog-v001.xml` must resolve every import.
- **Read and write OWL as XML/RDF, never by line.**
- **Nothing on the live server or staging is touched without the user confirming that step at the time** (Task 12).
- Data repo branch: `ontology-modules-split` (rename this worktree's branch). App branch: `ontology-modules-split`, in a new worktree `ARI-metadata-manager/.claude/worktrees/ontology-modules-split` cut from `origin/main`.
- Release dumps live in `F:/1Projects/7Projects-Aurint/ARI/data/2-databases`: `symp.owl`, `hp.obo` and `uberon-basic.obo`. Call it `$DB` below.

## Decisions taken here that the spec left open (confirm when reviewing)

1. **Namespace.** `ARI_NoConcept` and `ARI_EnrichmentSource` use `ari-disease#`, like every other property, so the app's `self.base + suffix` lookup keeps one rule.
2. **Core declares a little more than the spec lists**, because ARI-owned files use these:
   - `oboInOwl:id`
   - `dc:source`
   - `ARI_EnrichmentSource` (the app writes it today without any declaration)
3. **The generated slices keep their own declarations of `IAO_0000115` / `oboInOwl:id`.** The "only in core" rule is checked on ARI-owned files.
4. **The `MulticellularAnatomicalStructure` root moves to core**, so its UBERON note (`rdfs:comment`) and `ARI_NoConcept "not linked"` go on the class in core.
5. **Live counts differ from the spec:**
   - 2,248 `symptomConcept` links to rename, not 2,102.
   - 46 obsolete Symptom individuals get `ARI_NoConcept "not a symptom"`.
   - Label lookup over `rdfs:label` and `skos:altLabel` reproduces all 2,248 links exactly (checked 2026-10-25).
6. **HPO labels.** Report 4 needs them and the OWL carries only HPO IRIs, so the report builder reads `hp.obo`, as the build script does today.
7. **The app reloads the shared ontology when any `ontologies/*.owl` changes**, not only the disease file. Otherwise a Protégé edit to a concept module would not show until a restart.
8. **The app never declares a property any more.** It currently can, in two places:
   - `OntologyService._ensure_annotation_property` creates a missing property.
   - `merge_service._ensure_property` copies a declaration into the publish.

   After the split both would write a declaration into the disease file. Both become fail-fast lookups.

## Review Focus

1. **Renaming a symptom that carries `ARI_NoConcept`** drops that decision. It takes `sharedConcept` from the new label, or no link and a validator warning. A non-name edit keeps it. *(Task 8 test)*
2. **A publish never puts a property declaration, or a triple about a core/anatomy/symptoms entity, into `ari_disease.owl`.** *(Task 10 test, and Task 2's `subject-in-two-modules` / `property-outside-core` checks)*
3. **A module changed on its own** (a Protégé edit to `ari_anatomy.owl` merged to `main`) is fetched by the server and shows in the app without the disease file changing. *(Task 9 test, Task 11 script)*
4. **A module formatted while its imports don't resolve.** If `catalog-v001.xml` misses an entry, ROBOT could guess property types and re-declare them. The check: format every file through the catalog, and `property-outside-core` reports nothing. *(Task 1 Step 6, Task 2)*
5. **Whitespace and case in a symptom label.** Lookup matches today's table: surrounding whitespace is stripped, and case matters. `" Polyuria "` links, `"polyuria"` does not. *(Task 8 test)*

---

# Part A: data PR (`KrishnaTO/ARI`, this worktree)

### Task 1: Split the ontology into modules

**Files:**
- Create: `notebook/ontology-modules/split_ontology.py`, run once and kept for the record.
- Rename: `ontologies/ari_t1d.owl` → `ontologies/ari_disease.owl`, using `git mv` before running the script.
- Move: `notebook/symptom-mapping/ari_symptoms.owl` → `ontologies/ari_symptoms.owl` (`git mv`).
- Create:
  - `ontologies/ari_core.owl`
  - `ontologies/ari_anatomy.owl`
  - `ontologies/ari_biomarkers.owl`
  - `ontologies/ari_symp.owl`
- Modify: `ontologies/catalog-v001.xml`

**Interfaces:**
- Consumes: today's `ari_t1d.owl`, `notebook/symptom-mapping/ari_symptoms.owl`, `symptom_mapping.tsv` (only to pick the 46 "not a symptom" individuals) and `uberon_mapping.tsv` (Notes and no-term rows).
- Produces: the six files above and the catalog. Every later task relies on the IRIs and paths in Global Constraints.

- [ ] **Step 1: Branch and move files**

```bash
git branch -m ontology-modules-split
git mv ontologies/ari_t1d.owl ontologies/ari_disease.owl
git mv notebook/symptom-mapping/ari_symptoms.owl ontologies/ari_symptoms.owl
git commit -m "Rename ari_t1d.owl to ari_disease.owl and move ari_symptoms.owl into ontologies/"
```

A rename-only commit lets git follow both files' history through the rewrite.

- [ ] **Step 2: Write `split_ontology.py`**

`main()` takes no arguments; the paths are repo-relative constants. Each element is parsed with ElementTree, and IRIs are resolved against `xml:base` as `resolve()` in `build_uberon_import.py` does. Routing:

| From | Element | Goes to |
| --- | --- | --- |
| disease | every `owl:AnnotationProperty` / `ObjectProperty` / `DatatypeProperty` except `symptomConcept` | core |
| disease | classes `AutoimmuneDisease`, `Symptom`, `MulticellularAnatomicalStructure`, `AffectedCellTissueOrOrgan`, `Autoantibody`, `Antigen`, `ClinicalBiomarker` | core. Replace each one's `rdfs:subClassOf owl:Thing` with its umbrella: `AutoimmuneDisease` → `Disease`; `MulticellularAnatomicalStructure` and `AffectedCellTissueOrOrgan` → `AnatomicalEntity`; `Autoantibody`, `Antigen` and `ClinicalBiomarker` → `Biomarker`. `Symptom` stays under `owl:Thing`. |
| disease | every other class whose superclass chain reaches `MulticellularAnatomicalStructure` (25 classes), and every individual typed by one of them (23 `Tissue_*`) | anatomy |
| disease | everything else | stays in disease |
| symptoms | `owl:Class` with an `http://purl.obolibrary.org/obo/SYMP_` IRI (309) | `ari_symp.owl` |
| symptoms | its four property declarations | dropped (they are in core) |
| symptoms | ARIS classes | stay |

Additions:
- **Core:**
  - the three new classes;
  - declarations of `sharedConcept`, `ARI_NoConcept`, `ARI_EnrichmentSource`, `skos:exactMatch`, `skos:broadMatch`, `skos:closeMatch`, `skos:altLabel`, `obo:IAO_0000115`, `oboInOwl:id` and `dc:source`.
- **On each tissue class with a non-empty `uberon_mapping.tsv` Note:**
  - `rdfs:comment` holding the Note;
  - `ARI_NoConcept` set to the row's Mapping when that is `no term` or `not linked`.
  - Both go on the `MulticellularAnatomicalStructure` row too, in core.
- **Disease file:**
  - every `symptomConcept` element is renamed to `sharedConcept`, keeping its `rdf:resource`;
  - each Symptom individual whose label's TSV row is `not a symptom` gets `<ARI_NoConcept>not a symptom</ARI_NoConcept>`.
- **Symptoms file:** each ARIS class none of whose `rdfs:subClassOf` targets is an ARIS class gets `rdfs:subClassOf ari-disease#Symptom`.
- **Headers:**
  - each new file gets its ontology IRI, its `owl:imports` and an `rdfs:comment` saying what it holds;
  - the disease header loses its direct `ari_uberon` import and gains the four module imports;
  - the symptoms header gets its new IRI, the imports, and a comment that no longer mentions the TSV, keeping its two `dc:source`;
  - `ari_symp.owl` gets the `dc:source` of the SYMP release and a comment saying it is generated by `build_symp_import.py`.
- **`catalog-v001.xml`:** one `<uri>` per imported ontology IRI (core, symptoms, anatomy, biomarkers, `ari_uberon`, `ari_symp`).

The script refuses (raises `SystemExit`) if any of these counts differ:
- 7 core classes found
- 25 anatomy classes
- 23 `Tissue_*` individuals
- 2,248 renamed links
- 46 `not a symptom` individuals
- 309 SYMP classes

Its last line prints them all.

- [ ] **Step 3: Run it**

Run: `python notebook/ontology-modules/split_ontology.py`
Expected: `core: 7 key classes + 3 new, 103 properties; anatomy: 25 classes, 23 individuals; disease: 2248 sharedConcept, 46 ARI_NoConcept; symptoms: 766 classes, N under Symptom; ari_symp: 309 classes`. The 103 properties are today's 94 less `symptomConcept`, plus the 10 that core adds.

- [ ] **Step 4: Format everything**

Run: `wsl -e tools/format-owl.sh ontologies/*.owl`, then `wsl -e tools/format-owl.sh --check ontologies/*.owl`
Expected: the check exits 0.

- [ ] **Step 5: Check that it loads in owlready2 and the content is the same**

Run (loading by file object, as the app does, because owlready2's `file://` handling breaks on Windows paths): `python -c "from owlready2 import *; onto_path.append('ontologies'); w=World(); o=w.get_ontology('http://ari.local/x').load(fileobj=open('ontologies/ari_disease.owl','rb')); print(len(list(w.individuals())), sorted(i.base_iri for i in o.imported_ontologies))"`
Expected:
- 6,832 individuals in all (6,809 disease + 23 tissue);
- four imports: core, symptoms, anatomy, biomarkers.

Run ROBOT to compare the whole old content with the whole new content:

```bash
wsl -e bash -c 'J=.cache/robot/robot-1.9.11.jar; C=ontologies/catalog-v001.xml; mkdir -p /tmp/old;
git show main:ontologies/ari_t1d.owl > /tmp/old/ari_t1d.owl; git show main:notebook/symptom-mapping/ari_symptoms.owl > /tmp/old/ari_symptoms.owl;
git show main:ontologies/ari_uberon.owl > /tmp/old/ari_uberon.owl; git show main:ontologies/catalog-v001.xml > /tmp/old/catalog-v001.xml;
java -jar $J merge --catalog /tmp/old/catalog-v001.xml --input /tmp/old/ari_t1d.owl --input /tmp/old/ari_symptoms.owl --output /tmp/old.owl;
java -jar $J merge --catalog $C --input ontologies/ari_disease.owl --output /tmp/new.owl;
java -jar $J diff --left /tmp/old.owl --right /tmp/new.owl --output /tmp/split.diff; grep -c "^- " /tmp/split.diff; grep -c "^+ " /tmp/split.diff'
```

Expected: every line of `/tmp/split.diff` is one of the following, and nothing else.

Removed:
- the `symptomConcept` declaration and its 2,248 assertions
- 6 `SubClassOf(X owl:Thing)` lines for the re-parented key classes
- the old symptoms ontology's annotations

Added:
- the `sharedConcept` declaration and its 2,248 assertions
- the 3 new classes and their labels
- 6 umbrella `SubClassOf` lines
- the ARIS-root `SubClassOf Symptom` lines
- 46 + 5 `ARI_NoConcept` assertions
- the tissue `rdfs:comment`s
- the new property declarations

- [ ] **Step 6: Open in Protégé**

Open `ontologies/ari_disease.owl` from the folder. All four imports load with no "missing import" dialog, and the class tree under `owl:Thing` shows `Disease`, `Symptom`, `AnatomicalEntity` and `Biomarker`. This step is manual.

- [ ] **Step 7: Commit**

```bash
git add notebook/ontology-modules/split_ontology.py ontologies/
git commit -m "Split the ontology into core, disease, symptoms, anatomy and biomarkers modules"
```

### Task 2: The validator reads the modules

**Files:**
- Modify: `.github/scripts/validate_mappings.py`, `.github/workflows/mappings-validate.yml`

**Interfaces:**
- Consumes: the module paths and IRIs from Task 1.
- Produces: finding codes:
  - errors: `property-outside-core`, `subject-in-two-modules`, `shared-concept-target-missing`, `concept-label-ambiguous`, `concept-id-repeated`, `symptom-concept-mismatch`, `symptom-concept-repeated`, `symptom-decided-and-linked`
  - warnings: `symptom-concept-missing`, `symptom-unmapped`, `tissue-unlinked`

- [ ] **Step 1: Point the validator at the modules**

`ONTOLOGY_PATH = "ontologies/ari_disease.owl"`. Add:
- `CORE_PATH`, `SYMPTOMS_PATH`, `ANATOMY_PATH`, `BIOMARKERS_PATH`
- `ARI_OWNED = (CORE_PATH, ONTOLOGY_PATH, SYMPTOMS_PATH, ANATOMY_PATH, BIOMARKERS_PATH)`
- `SHARED_CONCEPT = ARI_DISEASE_BASE + "sharedConcept"`
- `NO_CONCEPT = ARI_DISEASE_BASE + "ARI_NoConcept"`
- `SKOS_ALT_LABEL`, `OBOINOWL_ID`
- `UBERON = "http://purl.obolibrary.org/obo/UBERON_"`

Delete `SYMPTOM_MAPPING_PATH`, `SYMPTOM_MAPPING_COLUMNS`, `expected_symptom_concepts` and `SYMPTOM_CONCEPT`, and update the module docstring.

- [ ] **Step 2: Add the checks**

Each takes `report: Report`. Findings sit on the line of the offending statement.

- `concept_labels(path: str, text: str, report) -> dict[str, str]`
  - Maps every ARIS class's `rdfs:label` and `skos:altLabel` (stripped) to the class IRI.
  - The same string on two classes → `concept-label-ambiguous`.
  - The same `oboInOwl:id` on two classes → `concept-id-repeated`.
- `check_symptom_concepts(disease_text: str, labels: dict[str, str], report)`. Per Symptom individual:
  - more than one `sharedConcept` → `symptom-concept-repeated`
  - `ARI_NoConcept` and a `sharedConcept` → `symptom-decided-and-linked`
  - `ARI_NoConcept` alone → fine
  - link equals `labels.get(label)` → fine
  - no link, label found → `symptom-concept-missing`
  - label not found → `symptom-unmapped`; the message names any leftover link
  - otherwise → `symptom-concept-mismatch`
  - Messages tell the curator to add the label or an `skos:altLabel` in `ontologies/ari_symptoms.owl`, or to set `ARI_NoConcept`.
- `check_shared_concept_targets(disease_text: str, concept_iris: set[str], report)`
  - Every `sharedConcept` value must be an `owl:Class` declared in symptoms, anatomy or biomarkers.
- `check_property_declarations(texts: dict[str, str], report)`
  - In each `ARI_OWNED` path except `CORE_PATH`, any entity typed `owl:AnnotationProperty`, `owl:ObjectProperty` or `owl:DatatypeProperty` → `property-outside-core`.
- `check_module_subjects(texts: dict[str, str], report)`
  - Any IRI that is the subject of an entity in more than one `ARI_OWNED` file → `subject-in-two-modules`. It is reported in each file but the first.
- `check_tissue_links(texts: dict[str, str], report)`
  - Each class in `ANATOMY_PATH` with neither an `rdfs:subClassOf` to a `UBERON` IRI nor `ARI_NoConcept` → `tissue-unlinked`.

`filter_to_changes` scopes by statement for every path ending in `.owl`, not only `ONTOLOGY_PATH`. `main()` reads the five ARI-owned texts with `read_text` and runs the new checks after the existing ontology checks.

- [ ] **Step 3: Workflow triggers**

In `mappings-validate.yml`, drop the `notebook/symptom-mapping/symptom_mapping.tsv` path. `ontologies/**` already covers the modules.

- [ ] **Step 4: The clean tree passes**

Run: `python .github/scripts/validate_mappings.py`
Expected: `0 error(s), 5 warning(s)`. These are today's 5 `dxcode-without-snomed` warnings, with no symptom or tissue findings.

- [ ] **Step 5: Each check catches its fault**

Make each edit with a short Python ElementTree snippet, run the validator, then `git restore <file>`.

| Edit | Expected finding |
| --- | --- |
| Add `<owl:AnnotationProperty rdf:about="…ari-disease#ARI_Synonym"/>` to `ari_anatomy.owl` | `error property-outside-core` |
| Add `<rdfs:label>x</rdfs:label>` about `…ari-disease#Tissue_Pancreas` to `ari_disease.owl` | `error subject-in-two-modules` |
| Point one `sharedConcept` at `…ari-symptoms#ARIS_9999999` | `shared-concept-target-missing` and `symptom-concept-mismatch` |
| Add an `skos:altLabel` "Fatigue" to a second ARIS class | `error concept-label-ambiguous` |
| Remove `ARI_NoConcept` from one tissue class | `warning tissue-unlinked` |

- [ ] **Step 6: Commit**

```bash
git add .github/
git commit -m "Validate the ontology modules: symptom links by label lookup, properties only in core, one module per subject"
```

### Task 3: The slice extractors write only the slices

**Files:**
- Modify: `notebook/uberon-mapping/build_uberon_import.py`
- Rename and modify: `notebook/symptom-mapping/build_symptom_mapping.py` → `notebook/symptom-mapping/build_symp_import.py` (`git mv`). The report half moves to Task 4.

**Interfaces:**
- Consumes: `ontologies/ari_anatomy.owl`, `ontologies/ari_symptoms.owl`, `$DB`.
- Produces: `ontologies/ari_uberon.owl` and `ontologies/ari_symp.owl`, and nothing else.

- [ ] **Step 1: `build_uberon_import.py <db>`**

- `linked_uberon(anatomy_root) -> set[str]`: UBERON CURIEs named by `rdfs:subClassOf`, `skos:exactMatch`, `skos:broadMatch` or `skos:closeMatch` on any class.
- Exit with an error listing any CURIE that is missing or obsolete in `uberon-basic.obo`.
- `write_slice` is unchanged.
- Delete `read_mapping`, `tissue_classes`, `link_ontology` and the `ari_t1d.owl` write.
- Rewrite the docstring.

- [ ] **Step 2: `build_symp_import.py <db>`**

- `linked_terms(symptoms_root) -> tuple[set[str], set[str]]`: SYMP and HP CURIEs named by `rdfs:subClassOf` / `skos:exactMatch` / `skos:broadMatch` on ARIS classes.
- Exit with an error on any SYMP CURIE missing from `read_symp` or any HP CURIE missing from `read_hp`. Both are obsolete-filtered, as today.
- `write_symp_slice(curies, symp, version) -> int`: writes `ontologies/ari_symp.owl`.
  - Each needed term and every SYMP ancestor gets `rdfs:label`, `oboInOwl:id` and SYMP parents.
  - Header: IRI `ari_symp`, a comment, the `dc:source` release IRI.
  - It declares `oboInOwl:id`.
- Delete everything that read the TSV or wrote report 4, `ari_symptoms.owl` or the disease file.

- [ ] **Step 3: Both reproduce the Task 1 slices byte for byte**

```bash
python notebook/uberon-mapping/build_uberon_import.py "$DB"
python notebook/symptom-mapping/build_symp_import.py "$DB"
wsl -e tools/format-owl.sh ontologies/ari_uberon.owl ontologies/ari_symp.owl
git status --short ontologies/
```

Expected:
- the scripts print `61 terms` and `309 terms`;
- `git status` shows no changes, because the slices match the split's output.

If `ari_symp.owl` differs only in its header comment or `dc:source`, fix the split's header to match and re-run Task 1 Steps 3–4.

- [ ] **Step 4: Commit**

```bash
git add notebook/uberon-mapping/build_uberon_import.py notebook/symptom-mapping/
git commit -m "Make the UBERON and SYMP builders slice extractors that read the ARI-owned modules"
```

### Task 4: Report 4's symptom sheets come from the OWL

**Files:**
- Create: `notebook/symptom-mapping/build_symptom_report.py`. It reuses `read_hp` and `SYMPTOM_COLUMNS` from today's script; move them, don't share them.
- Modify: `data/4-reports/4_Additional_Info_Index.xlsx`, by running the script.

**Interfaces:**
- Consumes:
  - `ontologies/ari_symptoms.owl` and `ari_symp.owl` (SYMP labels)
  - `ontologies/ari_disease.owl` (Symptom labels, `ARI_NoConcept`, diseases)
  - `$DB/hp.obo` (HPO labels)
- Produces: the Symptoms and Symptom Mapping sheets, with the same columns as today.

- [ ] **Step 1: Write it**

- `concepts(symptoms_root, symp_labels, hp_labels) -> dict[str, dict]` maps each label and `altLabel` string to the row values that `write_report` builds today:
  - Symptom ID
  - SYMP ID / Label / Mapping (`exact` from `skos:exactMatch` to SYMP, otherwise `broader`)
  - HPO ID / Label / Mapping (`no term` when there is no HP match)
  - Parent Symptom and Parent ID, from `rdfs:subClassOf` targets other than `ari-disease#Symptom`
  - Merged Into: the class label when the string is an `altLabel`
- **Symptoms sheet.** Per row:
  - string found → write its values;
  - string is the label of a Symptom individual with `ARI_NoConcept "not a symptom"` → write only SYMP Mapping = `not a symptom`;
  - otherwise (one of the 33 sheet-only strings) → leave the row's cells untouched.
- **Symptom Mapping sheet.** Rewritten in place, one row per string in the union of:
  - concept labels and `altLabel`s
  - Symptom individual labels
  - Symptoms-sheet strings

  Its Mapping column holds `exact`, `broader`, `merged` or `not a symptom`. A string with no OWL information copies its mapping columns from the sheet's existing row. Both disease counts are recomputed.

- [ ] **Step 2: Same cells as today**

Run `python notebook/symptom-mapping/build_symptom_report.py "$DB"`. Then compare both sheets, cell by cell, with `git show main:data/4-reports/4_Additional_Info_Index.xlsx`: a short openpyxl loop over `ws.iter_rows(values_only=True)` for each sheet.
Expected: `0 differing cells` in Symptoms and in Symptom Mapping. Hyperlinks are as before.

- [ ] **Step 3: Commit**

```bash
git add notebook/symptom-mapping/build_symptom_report.py data/4-reports/4_Additional_Info_Index.xlsx
git commit -m "Build report 4's symptom sheets from ari_symptoms.owl and ari_disease.owl"
```

### Task 5: Retire the TSVs and repoint every script

**Files:**
- Delete: `notebook/symptom-mapping/symptom_mapping.tsv`, `notebook/uberon-mapping/uberon_mapping.tsv`
- Modify the path in:
  - `notebook/disease-hierarchy/build_disease_hierarchy.py`
  - `notebook/disease-hierarchy/build_proposed_hierarchy_owl.py`
  - `notebook/research-gaps/build_research_gaps.py`, which also changes the line 476 prose to "`ari_core.owl` declares"
  - `notebook/master-list-comparison/compare.py`
  - `import_columns.py`, `import_gaps.py`, `import_prevalence.py` (usage docstrings only)
  - `notebook/ari-grounding/ari_diseases.py`
  - `notebook/synonym-review/gather.py`
- `compare.py` also reads `ari_anatomy.owl`.

- [ ] **Step 1: Before/after outputs for the two scripts that follow tissue links**

On `main`, in a scratch clone at `C:/Users/krish/AppData/Local/Temp/claude/.../scratchpad/main-clone`, run:
- `compare.py` (master list, `ari_t1d.owl`, `out_before.xlsx`)
- `build_research_gaps.py`, with `OUT` pointed at the scratchpad

- [ ] **Step 2: Make the edits**

- `compare.py` builds `nodes` from both `OWL_PATH` and `os.path.join(os.path.dirname(OWL_PATH), "ari_anatomy.owl")`. `linked(e, 'targetsTissue')` dereferences the `Tissue_*` individuals that now live there.
- Every other script only changes the path string.
- Delete the TSVs with `git rm`.

- [ ] **Step 3: Same reports**

Run both scripts on the branch into the scratchpad, then compare cell values with the before files, ignoring the one "Generated <date>" cell.
Expected: no other differences.

Then run `git grep -n -e ari_t1d -e symptom_mapping.tsv -e uberon_mapping.tsv -e symptomConcept -- ':!changelog.md' ':!docs/superpowers'`.
Expected: no output. (The README hits are fixed in Task 6; run this after Task 6 if any remain.)

- [ ] **Step 4: Commit**

```bash
git add -A notebook/
git commit -m "Retire symptom_mapping.tsv and uberon_mapping.tsv; point every script at the modules"
```

### Task 6: Docs, changelog and the data PR

**Files:**
- Modify:
  - `README.md` (ontology section and formatter example)
  - `CLAUDE.md` (the table row becomes `ontologies/*.owl`, with `ari_disease.owl` as the disease record; the formatter note)
  - `data/README.md`
  - `data/4-reports/README.md` (symptom sections)
  - `notebook/symptom-mapping/README.md`, rewritten: concepts live in `ontologies/ari_symptoms.owl`; to map a new string, add a label or `altLabel`, or set `ARI_NoConcept`; the builders and report script
  - `notebook/uberon-mapping/README.md`, rewritten the same way
  - `changelog.md`
- Create: `notebook/ontology-modules/README.md`, covering:
  - the file table
  - opening in Protégé through the catalog
  - loading in owlready2: `onto_path.append("ontologies")`
  - which tool writes which file

- [ ] **Step 1: Write the docs and a `## ontology-modules-split` changelog entry** saying what changed and why, in the style of the existing entries.

- [ ] **Step 2: Full checks**

```bash
python .github/scripts/validate_mappings.py --since main
wsl -e tools/format-owl.sh --check ontologies/*.owl
```

Expected:
- the validator reports 0 errors; its warnings are the 5 `dxcode-without-snomed` ones, now reported against the renamed file;
- the format check exits 0.

- [ ] **Step 3: Commit, push, open the PR** against `main`. Its body:
  - links the spec and the app PR;
  - states "merge only together with the app PR, at the cutover in Task 12";
  - ends with the Claude Code line.

Do not merge it.

---

# Part B: app PR (`KrishnaTO/ARI-metadata-manager`, new worktree)

### Task 7: Fixtures and paths

**Files:**
- Create in `tests/fixtures/ontologies/`:
  - `ari_disease.owl` (`git mv` from `ari_t1d.owl`, then transformed)
  - `ari_core.owl`, `ari_anatomy.owl`, `ari_biomarkers.owl`, `ari_uberon.owl`, `ari_symp.owl` and `catalog-v001.xml`, copied from the data branch
  - `ari_symptoms.owl`, hand-written
- Modify:
  - `tests/conftest.py`: `BASE_OWL` and `_copy_service` dest → `ari_disease.owl`
  - `app/config.py`: both defaults → `ontologies/ari_disease.owl`
  - `run.py` default
  - `app/pr_review/github.py`: delete `ONTOLOGY_PATH` and use `config.GH_ONTOLOGY_PATH` in `pr_review/compare.py`
  - `.env.example`
  - `scripts/backfill_id_authors.py` and `scripts/report_synonyms.py` defaults

**Interfaces:**
- Produces: a fixture set that loads through `onto_path` exactly as the server's `ontologies/` does. The fixture symptoms module holds:
  - `ARIS_0000390` "Polyuria"
  - `ARIS_0000034` "Bloating", with `skos:altLabel` "Abdominal bloating"

  Both are under `ari-disease#Symptom`. It imports core and `ari_symp`.

- [ ] **Step 1: Transform the fixture disease file once**

In a short Python snippet (not committed):
1. Delete every top-level element of the fixture whose `rdf:about` IRI is declared in the copied `ari_core.owl` or `ari_anatomy.owl`. That covers all property declarations, the key classes, tissue classes and `Tissue_*` individuals.
2. Set the header's `owl:imports` to core, symptoms, anatomy and biomarkers.
3. Format the result with the data repo's `tools/format-owl.sh` and the fixture catalog.

- [ ] **Step 2: Run the suite**

Run: `python -m pytest -q`
Expected: all pass. The old symptom test still passes: the TSV fixture stays until Task 8, and `_ensure_annotation_property` still creates `symptomConcept`. Any failure is a fixture problem: fix it here.

- [ ] **Step 3: Commit** (`git add` named files only; never `git checkout -- .`)

```bash
git commit -m "Load the split ontology modules: fixtures, config and publish paths name ari_disease.owl"
```

### Task 8: Symptom concepts by label lookup, and no property is ever created

**Files:**
- Create: `app/concepts.py`
- Delete: `app/symptom_mapping.py`, `tests/fixtures/mappings/symptom_mapping.tsv`
- Modify: `app/ontology_service.py`
  - `_symptom_concept`, `_set_symptom_concept`, imports
  - rename `_ensure_annotation_property` → `_annotation_property` at all 13 call sites
  - update the `runtime_mappings` docstring in `tests/conftest.py`
- Test: `tests/test_ontology_service.py`

**Interfaces:**
- `app/concepts.py` provides:
  - `ARIS_BASE = "http://www.aurint.org/ontologies/ari-symptoms#"`
  - `concept_index(world, namespace: str) -> dict[str, str]`: stripped `rdfs:label` and `skos:altLabel` → class IRI, for classes whose IRI starts with `namespace`. Raises `ValueError` naming the string when one string names two classes.
- `OntologyService._annotation_property(suffix: str)` returns `self.world[self.base + suffix]`. If that is `None` it raises `RuntimeError(f"{suffix} is not declared in ari_core.owl")`. It never creates a property.
- `OntologyService` gains `self._symptom_concepts`, built in `_load` from `concept_index(self.world, ARIS_BASE)`.
- `_symptom_concept(category, values) -> str | None` looks up `values["name"].strip()` in `self._symptom_concepts`.
- `_set_symptom_concept(e, concept)` writes `sharedConcept` and removes any `ARI_NoConcept`. It is only called when the name changes (`update_item`'s existing `"name" in changes` guard), so a non-name edit keeps the decision.

- [ ] **Step 1: Rewrite the failing test and add three more**

```python
ARIS = "http://www.aurint.org/ontologies/ari-symptoms#"

def test_a_symptom_links_the_shared_symptom_its_label_names(service):
    # tests/fixtures/ontologies/ari_symptoms.owl: Polyuria is ARIS_0000390;
    # Bloating is ARIS_0000034, with altLabel "Abdominal bloating".
    iri = service.get_diseases_list()[0]["iri"]
    service.add_item(iri, "symptoms", {"name": " Polyuria "}, editor="t")
    item = next(s["iri"] for s in service.get_disease_detail(iri)["symptoms"] if s["name"] == " Polyuria ")
    # links(svc): the item's sharedConcept lines in the saved file, as in the old test
    assert links(service) == [f'<sharedConcept rdf:resource="{ARIS}ARIS_0000390"/>']
    for name, want in [("Abdominal bloating", "ARIS_0000034"),
                       ("Absence of orthostatic hypotension", None),
                       ("Bloating", "ARIS_0000034"),
                       ("polyuria", None),
                       ("Polyuria", "ARIS_0000390")]:
        svc = OntologyService(str(service.path))
        svc.update_item(item, "symptoms", {"name": name}, disease_iri=iri, editor="t")
        assert links(svc) == ([f'<sharedConcept rdf:resource="{ARIS}{want}"/>'] if want else []), name
    svc = OntologyService(str(service.path))
    svc.update_item(item, "symptoms", {"likelihood": "Rare"}, disease_iri=iri, editor="t")
    assert links(svc) == [f'<sharedConcept rdf:resource="{ARIS}ARIS_0000390"/>']


def test_renaming_a_symptom_drops_its_no_concept_decision(service):
    iri = service.get_diseases_list()[0]["iri"]
    service.add_item(iri, "symptoms", {"name": "Rare:"}, editor="t")
    item = next(s["iri"] for s in service.get_disease_detail(iri)["symptoms"] if s["name"] == "Rare:")
    no_concept = service.world[service.base + "ARI_NoConcept"]
    no_concept[service._entity(item)] = ["not a symptom"]
    service._save()
    svc = OntologyService(str(service.path))
    svc.update_item(item, "symptoms", {"likelihood": "Rare"}, disease_iri=iri, editor="t")
    assert svc._get_annotation(svc._entity(item), svc.base + "ARI_NoConcept") == ["not a symptom"]
    svc.update_item(item, "symptoms", {"name": "Polyuria"}, disease_iri=iri, editor="t")
    svc = OntologyService(str(service.path))
    assert svc._get_annotation(svc._entity(item), svc.base + "ARI_NoConcept") == []
    assert svc._get_annotation(svc._entity(item), svc.base + "sharedConcept") == [ARIS + "ARIS_0000390"]


def test_a_string_naming_two_concepts_is_refused():
    from owlready2 import Thing, World
    from app.concepts import ARIS_BASE, concept_index
    onto = World().get_ontology(ARIS_BASE)
    with onto:
        type("ARIS_1", (Thing,), {}).label = ["Fatigue"]
        type("ARIS_2", (Thing,), {}).label = ["Fatigue"]
    with pytest.raises(ValueError, match="Fatigue"):
        concept_index(onto.world, ARIS_BASE)
```

- [ ] **Step 2: Run them**

Run: `python -m pytest -q tests/test_ontology_service.py -k "symptom or concept"`
Expected: FAIL. `app.concepts` doesn't exist yet, and links are still written as `symptomConcept`.

- [ ] **Step 3: Implement `app/concepts.py`, `_annotation_property` and the two symptom methods**

Delete `app/symptom_mapping.py` and the TSV fixture. The triple-level write in `_set_symptom_concept` stays, with `sharedConcept` in place of `symptomConcept`. It also removes `ARI_NoConcept` with `_del_data_triple_spod`. Fix its docstring: ARIS classes are now loaded entities, but the raw-triple write is still how an IRI value is stored.

- [ ] **Step 4: Run the whole suite**

Run: `python -m pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git commit -m "Link symptoms to their shared concept by label lookup in ari_symptoms.owl; never create a property"
```

### Task 9: Read across the imported modules

**Files:**
- Modify:
  - `app/ontology_service.py`: `get_tissues`, `get_tissue_hierarchy`, `search`
  - `app/workspace.py`: the reload key
- Test: `tests/test_ontology_service.py`, `tests/test_working_copy_sync.py` (or wherever `workspace.base()` is tested today; grep `def test.*base`)

**Interfaces:**
- `workspace._base_key() -> tuple[str, int]` returns `(config.ONTOLOGY_FILE, newest st_mtime_ns over Path(config.ONTOLOGY_FILE).parent.glob("*.owl"))`. Both `_BASE_KEY` and `base()` use it.

- [ ] **Step 1: Tests**

```python
def test_tissues_are_read_from_the_anatomy_module(ro_service):
    names = {t["local_name"] for t in ro_service.get_tissues()}
    assert len(names) == 23 and {"Tissue_Pancreas", "Tissue_Systemic"} <= names


def test_tissue_hierarchy_holds_every_tissue_class(ro_service):
    seen = set()
    def walk(n):
        seen.add(n["local_name"])
        for c in n["children"]:
            walk(c)
    walk(ro_service.get_tissue_hierarchy()[0])
    assert len(seen) == 26 and {"Pancreas", "IsletOfLangerhans", "BetaCell"} <= seen


def test_search_finds_a_tissue(ro_service):
    assert any(r["local_name"] == "Tissue_Pancreas" for r in ro_service.search("pancreas"))


def test_the_base_reloads_when_a_module_changes(tmp_path, monkeypatch, base_owl):
    from app import config, workspace
    monkeypatch.setattr(workspace, "BASE", workspace.BASE)         # restored afterwards
    monkeypatch.setattr(workspace, "_BASE_KEY", workspace._BASE_KEY)
    for f in base_owl.parent.iterdir():
        shutil.copy2(f, tmp_path / f.name)
    monkeypatch.setattr(config, "ONTOLOGY_FILE", str(tmp_path / "ari_disease.owl"))
    first = workspace.base()
    anatomy = tmp_path / "ari_anatomy.owl"
    st = anatomy.stat()
    os.utime(anatomy, ns=(st.st_atime_ns, st.st_mtime_ns + 10**9))
    assert workspace.base() is not first
```

- [ ] **Step 2: Run them**

Expected: the tissue, hierarchy and search tests fail, because `onto.individuals()` no longer holds the `Tissue_*` individuals. The reload test fails because only the disease file's mtime counts.

- [ ] **Step 3: Implement**

- **`get_tissues`** collects individuals with `cls.instances(world=self.world)` for each tissue class, de-duplicated by IRI and sorted as now.
- **`get_tissue_hierarchy`** replaces `sub.namespace == self.onto` with `sub.iri.startswith(self.base)`. The children are the ARI classes, wherever they are declared.
- **`search`** iterates `self.world.individuals()` for the non-disease pass.
- **`workspace`** uses `_base_key()`.
- `overview` and `create_release` still count the disease module only. Leave them.

- [ ] **Step 4: Run the whole suite.** Expected: all pass. **Step 5: Commit**

```bash
git commit -m "Read tissues and search across the imported modules; reload when any module file changes"
```

### Task 10: A publish writes only disease-module statements

**Files:**
- Modify: `app/merge_service.py`, deleting `_ensure_property` and its call in `_write`
- Test: `tests/test_publish_rebase.py`

**Interfaces:**
- `merge_service._write` raises `ValueError(f"{p_iri} is not declared in ari_core.owl")` when `p_iri.startswith(dst.base)` and `dst.world._abbreviate(p_iri, False) is None`. It never copies a declaration.

- [ ] **Step 1: Test.** This pins Review Focus 2 on the real publish path: graft, then `_save`, then ROBOT, the same steps as `test_a_publish_diffs_only_on_the_curators_change`. A re-declared property would show as a top-level element about a core IRI, so one subject check covers both cases.

```python
def _subjects(root):
    return {e.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about") for e in root} - {None}


def test_a_publish_writes_only_disease_module_statements(pair):
    import xml.etree.ElementTree as ET
    from pathlib import Path

    from app import config
    from app.owl_format import format_owl
    working, branch = pair
    mine = _iris(working, 1)[0]
    working.update_disease(mine, {"synonyms": "only-change"}, editor="ada")
    working.add_item(mine, "symptoms", {"name": "Polyuria"}, editor="ada")
    merge_service.graft_diseases(working, branch, {mine})
    branch._save()
    published = _subjects(ET.fromstring(format_owl(branch.path.read_bytes())))
    fixtures = Path(config.ONTOLOGY_FILE).parent
    elsewhere = set().union(*(_subjects(ET.parse(fixtures / f).getroot())
                              for f in ("ari_core.owl", "ari_anatomy.owl", "ari_symptoms.owl")))
    assert published and not published & elsewhere
```

- [ ] **Step 2: Run it.** `python -m pytest -q tests/test_publish_rebase.py`. Expected: PASS. Core already declares everything, so `_ensure_property` finds each property known. Keep the test as the guard.

- [ ] **Step 3: Delete `_ensure_property`, and add the fail-fast check in `_write`.** Run: `python -m pytest -q`. Expected: all pass. **Step 4: Commit**

```bash
git commit -m "Grafting never copies a property declaration: the core module declares every one"
```

### Task 11: Deploy scripts, docs and the app PR

**Files:**
- Modify:
  - `deploy/update-ontology.sh`
  - `deploy/update-mappings.sh`
  - `README.md`, `DEPLOY.md`, `STAGING.md`
  - `changelog.md`

- [ ] **Step 1: `update-ontology.sh` fetches every file in the ontology's folder**

- List the folder with the contents API: `GET /repos/{owner}/{repo}/contents/{dir}?ref={branch}`, keeping entries ending in `.owl` or `.xml`.
- Fetch each one to a temp file.
- Install the changed ones with `install_if_changed`. Every file except `GITHUB_ONTOLOGY_PATH`'s goes first; the disease file goes last, so an import is never missing when it reloads.
- Remove the hard-coded slice and catalog logic.

- [ ] **Step 2: `update-mappings.sh`** drops the `symptom_mapping.tsv` line and its comment.

- [ ] **Step 3: Check the script by hand against the data branch**

```bash
GITHUB_BASE_BRANCH=ontology-modules-split ARI_ONTOLOGY_FILE=$PWD/tmp-onto/ari_disease.owl GITHUB_ONTOLOGY_PATH=ontologies/ari_disease.owl bash deploy/update-ontology.sh
```

Run it from a scratch dir with a venv path the script expects, or run the embedded Python by hand.
Expected: `Updated …` for the eight files, disease last. A second run prints `Already up to date` eight times.

- [ ] **Step 4: Docs and changelog**

- Every path rename.
- DEPLOY.md's refresh section: the folder fetch, and no symptom TSV.
- STAGING.md's file list.
- A `## ontology-modules-split` changelog entry.

- [ ] **Step 5: Run `python -m pytest -q` and `ruff check`. Commit, push and open the PR**, cross-linked with the data PR: "merge only together, at the cutover". Do not merge it.

---

# Part C: rehearsal and cutover (live; every step confirmed with the user at the time)

### Task 12: Staging rehearsal, then the live switch

Nothing here is run without the user's go-ahead for that step. Each ask names what the step does and its most likely failure.

- [ ] **Step 1: Staging rehearsal** (STAGING.md, "Testing another branch")
  1. Push the data branch to `KrishnaTO/ARI-staging`.
  2. Set staging's `.env`: `GITHUB_BASE_BRANCH=ontology-modules-split`, `GITHUB_ONTOLOGY_PATH=ontologies/ari_disease.owl` and `APP_REPO_BRANCH=ontology-modules-split`. Remove any `ARI_ONTOLOGY_FILE` pin.
  3. Run `update.sh`.

  Check:
  - `/healthz` shows the branch commit
  - the tissue picker lists 23 tissues
  - the tissue tree is full
  - adding the symptom "Fatigue" links `sharedConcept`
  - one publish opens a PR in `ARI-staging` whose only file is `ontologies/ari_disease.owl`, and that PR passes `OWL format` and `Validate mappings`
  - ROBOT stays under staging's 384 MB heap (`journalctl -u ari-mm-staging`)

- [ ] **Step 2: Drain the curators**

Announce, then confirm both are zero:
- open `edit/*` PRs: `gh pr list --repo KrishnaTO/ARI --search "head:edit/"`
- working copies with unpublished changes in `/opt/ari/ari-metadata-manager/.user-data/`

- [ ] **Step 3: Pause the three timers**

`sudo systemctl stop ari-mm-update.timer ari-mm-ontology-update.timer ari-mm-mapping-update.timer`

- [ ] **Step 4: Merge the data PR, then the app PR.**

- [ ] **Step 5: Server config**

In `/opt/ari/ari-metadata-manager/.env`, set `GITHUB_ONTOLOGY_PATH=ontologies/ari_disease.owl` and remove any `ARI_ONTOLOGY_FILE` that names `ari_t1d.owl`.

- [ ] **Step 6: Clear pre-split state**

- Archive the remaining working copies into `USER_ARCHIVE_DIR` (the mechanism `workspace` uses for idle copies).
- Clear `.user-data/baselines/`. Its cached files are pre-split shas of the old single file.

- [ ] **Step 7: Refresh by hand**

Run `deploy/update.sh`, `deploy/update-ontology.sh` and `deploy/update-mappings.sh`, then restart `ari-mm`.
Check: `/healthz`, a disease page, the tissue picker and the symptom search.

- [ ] **Step 8: Resume the timers, then one test publish**

The publish should be a 2–3 line diff to `ari_disease.owl` only, with both checks green.

- [ ] **Step 9: Remove the stale files**

Delete the server's leftover `ontologies/ari_t1d.owl` and `ari-mappings/symptom_mapping.tsv`.
