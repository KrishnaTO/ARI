# ARI ontology modules — design

Date: 2026-10-18. Branch: `claude/ontology-file-structure-23209b`.

## Intent

`ontologies/ari_t1d.owl` is one 5 MB file holding everything: 228 diseases, ~2,300 per-disease
symptom entries, 358 autoantibody and 327 antigen entries, 18 clinical biomarkers, 424 affected
cell/tissue/organ entries, the 22 tissue and system classes, and every property. The shared ARIS
symptom classes live apart in `notebook/symptom-mapping/ari_symptoms.owl`, not imported.

The ontology is opened by the editor app and by experienced curators in Protégé. The reason to
split it is **importing from published ontologies**: each domain gets its own file, so a curator
can bring in UBERON, the Cell Ontology, SYMP/HPO, Protein Ontology or LOINC terms where they
belong, without wading through the disease records.

## Decisions made by the user

1. Split into one file per domain: **disease**, **symptoms**, **anatomy** (UBERON body parts and
   tissues), **biomarkers**.
2. The key terms are classes in an **encompassing core ontology**, which all modules import.
3. The **disease** file links to the concepts in all the other files.
4. **One set of properties** shared across all files.
5. Biomarkers include **autoantibodies and antigens** as well as clinical biomarkers.
6. Biomarkers are **shared concepts** (one *Antinuclear antibodies* class), not the per-disease
   entries moved over. The per-disease entries stay with the disease and point at the concept,
   as symptoms already do (ARI#152).
7. **Affected cell, tissue or organ** concepts go in the **anatomy** file.
8. **The OWL files are the record.** Every change, from any source (app, Protégé, script), is made
   to the OWL file. Curated TSVs stop being sources.
9. **Any writer, one layout.** Any tool may write any file. One pinned formatter (ROBOT) rewrites
   every `ontologies/*.owl` into the same canonical layout, so the same content always has the same
   bytes, and CI rejects a file that is not canonical. Lands first, as Project 0.

## Goals

- Five ARI-owned files, each opening cleanly in Protégé and loading in owlready2 with its imports.
- Every property declared once, in the core.
- Each concept module is where a curator imports and links to that domain's published ontologies.
- The editor keeps working, every day, across the change.

## Non-goals

- Changing any entity IRI. Disease, symptom, tissue and every other existing IRI stays exactly as
  it is, so `mappings/*.tsv`, reports and links keep resolving.
- Changing what a disease record holds (fields, values, per-disease entries).
- Reworking the disease category classes or the pathway/etiology/immune-component entries. They
  stay in the disease file.

## Anti-goals (failure even if it technically works)

- A Protégé edit to a concept file silently overwritten by a script re-run.
- The editor broken between the data PR and the app PR merging.
- The same property declared in two files, or a module minting its own variant of a shared one.

## File layout

All in `ontologies/`. Naming rule: `ari_<domain>.owl` is ARI-owned and edited in place;
`ari_<source>.owl` named after a published ontology (`ari_uberon.owl`, `ari_symp.owl`, later
`ari_cl.owl`, `ari_pr.owl`) is a **generated import slice**, never edited by hand.

| File | Ontology IRI | Holds | Imports |
| --- | --- | --- | --- |
| `ari_core.owl` | `http://www.aurint.org/ontologies/ari_core` | key classes, every property | — |
| `ari_disease.owl` (was `ari_t1d.owl`, `git mv`) | `http://www.aurint.org/ontologies/ari-disease` (unchanged) | diseases and all per-disease entries | core, symptoms, anatomy, biomarkers |
| `ari_symptoms.owl` (moved from `notebook/symptom-mapping/`) | `http://www.aurint.org/ontologies/ari_symptoms` | ARIS symptom classes | core, `ari_symp.owl` |
| `ari_anatomy.owl` | `http://www.aurint.org/ontologies/ari_anatomy` | the 25 tissue/system classes and 23 `#Tissue_*` individuals; later the ARIA cell/tissue concepts | core, `ari_uberon.owl` |
| `ari_biomarkers.owl` | `http://www.aurint.org/ontologies/ari_biomarkers` | ARIB biomarker concepts | core |
| `ari_uberon.owl` | unchanged | UBERON slice (generated) | — |
| `ari_symp.owl` | `http://www.aurint.org/ontologies/ari_symp` | SYMP slice, split out of today's `ari_symptoms.owl` (generated) | — |
| `catalog-v001.xml` | — | maps each import IRI to its file, for Protégé | — |

**Ontology IRI ends in the file stem** for every imported file. owlready2 resolves an import by
looking for `<last IRI segment>.owl` on `onto_path`, which is how `ari_uberon` already works.
Today's `ari-symptoms` ontology IRI therefore becomes `ari_symptoms`; its **entity** namespace
`http://www.aurint.org/ontologies/ari-symptoms#ARIS_…` does not change. The disease file is
loaded directly, never imported, so its ontology IRI stays.

Moved entities keep their IRIs. The tissue classes and `#Tissue_*` individuals stay in the
`ari-disease#` namespace while living in `ari_anatomy.owl`; the key classes keep theirs in
`ari_core.owl`. New entities use their module's namespace: `ari-core#`, `ari-biomarkers#ARIB_nnnnnnn`,
`ari-anatomy#ARIA_nnnnnnn` (seven digits, like `ARIS_`).

## The core ontology

**Key classes.** Existing IRIs are moved into the core, two new umbrella classes are added:

```
Disease (new, ari-core#)
  └ AutoimmuneDisease (existing)
Symptom (existing)
AnatomicalEntity (new, ari-core#)
  ├ MulticellularAnatomicalStructure (existing; the tissue/system tree hangs under it in ari_anatomy.owl)
  └ AffectedCellTissueOrOrgan (existing)
Biomarker (new, ari-core#)
  ├ Autoantibody (existing)
  ├ Antigen (existing)
  └ ClinicalBiomarker (existing)
```

Per-disease entries stay individuals of these classes in the disease file, so the app's
category reading (by `rdf:type`) is unchanged. Concept classes in each module are subclasses of
the matching key class: ARIS classes under `Symptom` (alongside their SYMP parents), ARIB classes
under `Autoantibody` / `Antigen` / `ClinicalBiomarker`, ARIA classes under
`AffectedCellTissueOrOrgan`. The Protégé class tree in the core is therefore the map of the whole
registry.

Everything else that is a class today (disease categories, pathway step, etiology, immune
components, epidemiology profile, genetic factors, treatment, environmental factor) stays declared
in the disease file. *My call:* these are disease-internal, and the user named the four domains.

**Properties.** Every object, datatype and annotation property in `ari_t1d.owl` today moves to
the core with its IRI, plus the mapping vocabulary the modules use: `skos:exactMatch`,
`skos:broadMatch`, `skos:closeMatch`, `skos:altLabel`, `IAO:0000115` (definition). No other file
declares a property. The validator enforces this.

**One concept link.** `symptomConcept` is replaced by **`sharedConcept`** (annotation property,
`ari-disease#sharedConcept`), used the same way by every per-disease entry that has a concept:
Symptom → ARIS, Autoantibody/Antigen/ClinicalBiomarker → ARIB, AffectedCellTissueOrOrgan → ARIA.
It stays an annotation property because its value is a class. *My call* on the name and on
keeping it an annotation; typing each entry directly by its concept class was considered and
rejected because the app reads the category from `rdf:type`.

## What "OWL is the record" changes

- `notebook/symptom-mapping/symptom_mapping.tsv` and `notebook/uberon-mapping/uberon_mapping.tsv`
  are retired as sources and deleted. Before deletion, anything they hold that the OWL does not:
  - uberon Notes (why a term was chosen, why a class is unlinked) → `rdfs:comment` on the class.
  - symptom rows: the per-string decision is already in the OWL (exact/broad matches on the ARIS
    class, merged strings as `skos:altLabel`).
  - **Decided-none is recorded, not left blank** (*my call*), so it never looks like "not reviewed
    yet". One annotation property in the core, `ARI_NoConcept`, whose value says why:
    `not a symptom` on each per-disease Symptom individual judged so (live or retired), and
    `no term` / `not linked` on the tissue classes the uberon TSV marked so. The validator treats an
    entry with `ARI_NoConcept` as decided; the report reads it.
  - Report 4 rows for the 33 strings that exist only in the master-list sheet (no OWL entity) keep
    their current cell values; the report build leaves them untouched (*my call*).
- **Label lookup replaces the table.** "Which concept does this entry's label name?" is answered
  by matching it against concept `rdfs:label` and `skos:altLabel` in the concept module. The app,
  the validator and the scripts all use this one rule. A label with no match and no
  `ARI_NoConcept` is a validator warning, as an unmapped label is today.
- Every file is read with an XML/RDF parse, never line by line (Project 0 makes this true for the
  validator and the scripts).
- The two build scripts become **slice extractors only**: read the external IDs referenced in the
  ARI-owned module (`rdfs:subClassOf` / `skos:*Match` targets), write `ari_uberon.owl` /
  `ari_symp.owl` with those terms and their is_a ancestors. They no longer write ARI-owned files.
- The report 4 Symptoms and Symptom Mapping sheets are built from `ari_symptoms.owl` and
  `ari_disease.owl` instead of the TSV. Same columns.

## Who writes and who reads each part

Writers: **App** (curators in the editor), **Protégé** (curators), **Batch** (one-off import
scripts in `notebook/`, e.g. `master-list-comparison/import_*.py`), **Extractor** (the slice
builders). Readers: **App** (disease pages, tissue picker, concept lookup, export, PR review
diff, predicted mappings), **Protégé**, **Validator** (`validate_mappings.py` in CI), **Reports**
(`research-gaps` report 12, `master-list-comparison/compare.py`, report 4 symptom sheets,
`ari-grounding`, `synonym-review`, `disease-hierarchy`).

| File | Part | Written by | Read by |
| --- | --- | --- | --- |
| disease | Disease identity: label, ARI_ID, synonyms, codes (MONDO, SNOMED, DOID, UMLS, ICD10…), definition, obsolete, changelog, author | App, Batch | App, Validator (codes vs `mappings/*.tsv`), Reports (grounding, synonym review, report 12, compare) |
| disease | Disease hierarchy and categories (`hasParentDisease`, `hasParentCategory`, category classes) | App, Batch | App, Reports (disease hierarchy, report 12) |
| disease | Per-disease symptom entries (likelihood, description, source) | App, Batch | App, Validator, Reports (report 4, report 12, compare) |
| disease | Per-disease antibody / antigen / clinical biomarker entries (frequency, diagnostic value, type, sensitivity) | App, Batch | App, Reports (report 12, compare) |
| disease | Per-disease affected cell / tissue / organ entries (relevance) | App, Batch | App, Reports (report 12, compare) |
| disease | Which tissues a disease targets (`targetsTissue`) | App | App, Reports (report 12, compare) |
| disease | `sharedConcept` / `ARI_NoConcept` on each per-disease entry | App (on add/rename, by label lookup), Batch (backfill) | App, Validator, Reports |
| disease | Other per-disease detail: pathway steps, etiology, triggers, genetics, treatments, immune components, epidemiology | App, Batch | App, Reports (report 12, compare) |
| core | Key classes and every property declaration | Protégé | App (field list), Protégé, Validator (properties only declared here) |
| symptoms | Shared symptom classes: label, `altLabel`, hierarchy, SYMP/HPO matches, ARIS ids | Protégé | App (lookup, display), Protégé, Validator (link targets exist, ids unique), Reports (report 4), Extractor (which SYMP terms to copy) |
| biomarkers | Shared antibody / antigen / test classes: label, `altLabel`, PR/LOINC/ChEBI matches, ARIB ids | Protégé | App, Protégé, Validator, Reports, Extractor |
| anatomy | Tissue/system classes and `#Tissue_*` individuals; later ARIA cell/tissue classes; UBERON/CL links; `ARI_NoConcept` on unlinked classes | Protégé | App (tissue tree, picker, lookup), Protégé, Validator, Reports (report 12), Extractor (which UBERON/CL terms to copy) |
| `ari_uberon`, `ari_symp` (later `ari_cl`, `ari_pr`) | Copies of published terms with their parents | Extractor only | App, Protégé (as imports) |

Every written path leads to one PR against `main`; the server pulls `ontologies/` from `main`.
Whichever tool wrote a file, the formatter runs before the commit (Project 0), so the PR diff shows
only the content that changed.

## Delivery: four projects, in order

Each is its own data PR paired with an app PR (`KrishnaTO/ARI-metadata-manager`), merged
together, as ARI#149 with app#239 was.

### Project 0 — canonical layout (branch `ontology-formatter`)

- **Engine.** ROBOT, pinned in `tools/robot.version` (version, jar sha256):
  `robot convert --catalog ontologies/catalog-v001.xml --input F --format owl --output F`.
  Output is OWL API RDF/XML sorted by IRI — what Protégé writes.
- **Where it runs.** `tools/format-owl.sh` (fetches and checks the pinned jar). A pre-commit hook
  in `.githooks/` formats staged `ontologies/*.owl`. The app formats after its graft and save,
  in place of `owl_splice`, before it pushes the PR branch. The `owl-format` workflow runs
  `format-owl.sh --check` on every PR and blocks a file that would change.
- **Layout-free readers.** The validator parses the XML (expat) instead of matching lines, and
  scopes PR findings by `(entity, property, value)` instead of line text. The two notebook writers
  that edit the disease file use ElementTree and leave the layout to the formatter.
- **One reformat commit**, content-free, proved with `robot diff`.
- **App PR:** `app/owl_format.py`, `owl_splice.py` deleted, Java and the pinned jar on the server
  (`deploy/install-robot.sh`), the catalog fetched with the ontology.
- **Cutover:** drain open `edit/*` PRs, install ROBOT on the server, merge the data PR, deploy the
  app, test one publish. Each live step confirmed with the user at the time.

### Project 1 — the split

Mechanical; no new curation.

1. Write `ari_core.owl`; move the key classes and all properties into it.
2. `git mv ontologies/ari_t1d.owl ontologies/ari_disease.owl`; remove what moved; add the imports.
3. Write `ari_anatomy.owl` with the tissue/system classes and `#Tissue_*` individuals (moved),
   uberon Notes as comments, importing core and `ari_uberon.owl`.
4. Move `ari_symptoms.owl` into `ontologies/`, change its ontology IRI, split the SYMP terms into
   generated `ari_symp.owl`, import core and the slice; put ARIS root classes under `Symptom`.
5. Write an empty `ari_biomarkers.owl` (imports core) so the import graph is final from day one.
6. Rename `symptomConcept` → `sharedConcept` on the 2,102 links.
7. `catalog-v001.xml` for Protégé.
8. Convert the two build scripts to slice extractors; move report 4 symptom sheets to read OWL;
   delete the two TSVs.
9. Update every script path (`notebook/**`, `sparql/`), `.github/scripts/validate_mappings.py`
   (paths; symptom-link check by label lookup; new checks: properties only in core, every
   `sharedConcept` target exists), `.github/workflows/*` path triggers, `README.md`,
   `CLAUDE.md`, data READMEs, `changelog.md`.
10. **Check:** the disease file loads in owlready2 with all imports; triple count of the union
    equals today's `ari_t1d.owl` + `ari_symptoms.owl` (less only the renamed property's
    declaration and the deliberate additions); validator passes; opens in Protégé from the folder.

**App PR for project 1:**
- `ONTOLOGY_FILE` / `GITHUB_ONTOLOGY_PATH` → `ontologies/ari_disease.owl` (config, `pr_review/github.py`, `deploy/update-ontology.sh`).
- `deploy/update-ontology.sh` fetches every file in `ontologies/`, not one file plus the slice.
- `symptom_mapping.py` looks the label up in the loaded `ari_symptoms.owl` (label/altLabel)
  instead of reading `symptom_mapping.tsv`; `symptomConcept` → `sharedConcept`.
- Saves and PRs still write only `ari_disease.owl`. **Constraint:** an app write that would land a
  triple about a concept-module entity in the disease file is a bug; the validator flags it.
- `get_tissues` / `get_tissue_hierarchy` read tissue individuals from the disease ontology only;
  they must read across the loaded imports once the tissues move.
- `deploy/update-mappings.sh` stops fetching `symptom_mapping.tsv`.
- Old-format working copies (`.user-data/<login>.owl`, full snapshots of the single file) are
  handled at cutover, below.

**Cutover (live server).** The server's own config may pin `ontologies/ari_t1d.owl`, and app,
ontology and mappings refresh on separate timers. So the switch is a short runbook: curators
publish or discard drafts; pause the three update timers; merge both PRs; update the server
config path; archive any remaining working copies with the existing archive mechanism; resume
the timers. Every live step is confirmed with the user at the time — nothing on the server is
touched without that.

### Project 2 — biomarker concepts

`ari_biomarkers.owl`: one ARIB class per distinct autoantibody (~269 names), antigen (~261) and
clinical test (~17), after grouping names that mean the same thing ("Anti-GAD65 (GADA)" /
"Anti-GAD65 autoantibodies"). Variant names become `skos:altLabel`. Classes link to published
ontologies with `skos:exactMatch`/`broadMatch` (guess: Protein Ontology for antigens and antibody
targets, LOINC for tests, ChEBI for small-molecule analytes) through generated slices. Every
per-disease entry gets `sharedConcept`. App: link new entries automatically by label lookup.
Needs its own short design pass (grouping rules, which external ontologies).

### Project 3 — affected cell, tissue or organ concepts

ARIA classes in `ari_anatomy.owl` for the ~335 distinct names in the 424 entries, linked to
UBERON and the Cell Ontology (new `ari_cl.owl` slice); every entry gets `sharedConcept`. Open for
its own design pass: how ARIA classes sit relative to the existing tissue/system tree.

## Left to the builder

- How the split is scripted (a one-off script in `notebook/ontology-modules/`, run once, kept for
  the record).
- Exact wording of comments and README sections.
