# ARI Linked Disease Database

`ARI-Linked-Disease-Database.xlsx` — a fully-linked relational database that
unifies the ARI autoimmune-disease data spread across DOID, SNOMED CT, MESH and
OMOP/Athena into a single workbook keyed by a generated `ARI_ID`.

## Original data sources

This file is **derived** (no new external data was fetched). It was built by
integrating the following sibling folders under `data/`:

| Source tag | Source file | Contributes |
| --- | --- | --- |
| ARI-doid | `ARI-doid/ARI-doid.xlsx` | ARI curated disease list, names + ARI synonym flags, SNOMED codes, OMOP ConceptID, DOID name-lookup, Category/Parent |
| ARI-MESH | `ARI-MESH_Synonyms/ARI-MESHsynonyms-DOID.xlsx` | MESH-sourced synonyms, DOID name-lookup |
| ARI-SNOMED-Lookup | `ARI-SNOMED-Athena/ARI_SNOMED_Lookup.xlsx` | Up-to-date SNOMED CT metadata per ARI SNOMED code (FSN, preferred term, synonyms, text definition) |
| ARI-Athena | `ARI-SNOMED-Athena/ARI_Athena_Matches.xlsx` | ARI → Athena/OMOP matches |
| DOID-all | `DOID_autoimmune_diseases/DOID-all.xlsx` | All DOID children of "autoimmune disease": labels, definitions, exact/related synonyms, `db_xref` cross-references |
| SNOMED-all | `SNOMED-Athena/SNOMED_Athena_Matches-all_autoimmune_disease.xlsx` | All SNOMED autoimmune concepts + Athena/OMOP matches |

## What was built / updated

* **Scope:** union of every concept across all six inputs (ARI curated list +
  full DOID and SNOMED autoimmune subsets), de-duplicated.
* **Concept identity (conservative):** records merge when they share the same
  SNOMED conceptId, or the same DOID CURIE. SNOMED↔DOID are merged **only** for
  reciprocal 1:1 matches (34 merges). All other SNOMED↔DOID links are kept in the
  `Crosswalk_SNOMED_DOID` sheet rather than collapsed, because ARI's DOID column
  and DOID `db_xref` are many-to-many name/xref lookups (forcing merges there
  produced incorrect mega-clusters).
* **`ARI_ID`:** generated surrogate primary key (`ARI-#####`) — the foreign key
  that joins every sheet.
* **DOID normalization:** all CURIEs canonicalised to 7-digit form
  (e.g. `doid:4313` → `DOID:0004313`).
* **IDs generated where missing:** concepts lacking a native ID still receive an
  `ARI_ID`; SNOMED-only and DOID-only concepts keep their native code.

## What's in the file (sheets)

| Sheet | Grain | Key columns |
| --- | --- | --- |
| README | — | overview, identity model, source map |
| Diseases | one row per concept (**PK = ARI_ID**) | Primary_Name, Category, In_ARI, SNOMED_ID, DOID_CURIE, OMOP_ConceptIDs, Definition |
| Master_Wide | one row per concept (denormalized) | synonyms + each cross-ref vocabulary collapsed into delimited cells |
| Synonyms | one row per synonym | ARI_ID, Synonym, Synonym_Type, Source |
| Definitions | one row per definition | ARI_ID, Definition, Def_System (DOID/SNOMED), Source_File |
| CrossReferences | one row per external xref | ARI_ID, DOID_CURIE, Xref_System (MESH/ICD10CM/ICD9CM/NCI/UMLS_CUI/ORDO/GARD/MIM/EFO/KEGG), Xref_ID |
| Crosswalk_SNOMED_DOID | one row per candidate SNOMED↔DOID link | SNOMED_ID, DOID_CURIE, Link_Basis, Merged_1to1, resolved ARI_IDs + names |
| SNOMED_Details | one row per SNOMED concept | FSN, PreferredTerm, SemanticTag, DefinitionStatus, ConceptActive, In_Release, TextDefinition, ModuleId, EffectiveTime |
| Athena_OMOP | one row per SNOMED→OMOP match | OMOP_ConceptID, AthenaName, vocabularyId, domainId, conceptClassId, standardConcept, validity, matchStatus |

## Row counts

Diseases 1,136 (246 in the ARI curated list) · Synonyms 1,499 · Definitions 179
· CrossReferences 386 · Crosswalk_SNOMED_DOID 347 · SNOMED_Details 943 ·
Athena_OMOP 809.

## Integrity

All foreign keys validated: 0 orphan `ARI_ID`s, 0 null keys in child sheets,
unique primary key, `Master_Wide` 1:1 with `Diseases`. (A handful of crosswalk
SNOMED/DOID codes intentionally resolve to no master row — they are external
`db_xref` targets outside the autoimmune union.)

## Rebuild

Generated from `build_db.py` (concept resolution → `_resolved.json` /
`_crosswalk.json`) and `build_xlsx.py` (workbook assembly).
