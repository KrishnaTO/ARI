## Instructions
### Reorganize disease in Master list
#### Core ARI disease
Provided a table of diseases in 1-master/ARI Master List V 2.1 - 2026-06-04.xlsx, use the table to create a list of diseases from the parent diseases column, but using the preferred name of the disease to create a unique disease profile. 
Per disease:
Attach a unique ARI ID in the format "ARI:0001XXX". The IRI domain will be https://diseases.autoimmuneregistry.org/disease/ARI_0001XXX. 
1 or more synonyms.
1 or more of each SNOMED code, OMOP Code (conceptID in table) and Concept code (DXCode in table) linked to https://athena.ohdsi.org/ database. Not yet populated by each disease will have linked codes (with linkouts) to Disease Ontology, which should be searched by matching name or synonym to file data\2-databases\doid.owl. In addition, some of the codes will be obselete, and will have to marked at independently later.
1 definition, with 1 or more sources. 
tissue region, used to categorize where disease generally presents.
Evidence level, used to identify the type of evidence.
Modifier for if disease if confirmed or unconfirmed to be autoimmune.
Version information from release, currently listed in file.
This will formulate the core annotations for the diseases. Create in a new table. 

#### Proposed diseases
Based on Other sheets in file containing proposed diseases, 1-master/ARI Master List V 2.1 - 2026-06-04.xlsx, create a similar table in a new report. 

#### Proposed changes
Based on sheet "Leon Mapped", create a new report adding the proposed changes to the ARI diseases listed.

#### Additional info per disease
Review other data in sheets to build a linked reports, linked per disease ARI ID. Colour code info from where info was sourced in an index page. 

## Archived info
| File | Source | Target | Significance |
| --- | --- | --- | --- |
| ARI-SNOMED-Athena/ARI_SNOMED_Lookup.xlsx | ARI | SNOMED | Contains original SNOMED codes from ARI, and sourced up-to-date data from SNOMED per SNOMED_ID |
| ARI-SNOMED-Athena/ARI_Athena_Matches.xlsx | ARI | SNOMED, Athena | Contains ARI lookup to Athena database for matches by SNOMED codes or Disease name |
| ARI-MESH_Synonyms/ARI-MESHsynonyms-DOID.xlsx | ARI | MESH, DOID | Contains Synonyms, sourced by Leon/Rodrigo, lookup to DOID |
| ARI-doid/ARI-doid.xlsx | ARI | DOID | Contains DOID lookup by name |
| DOID_autoimmune_diseases/DOID-all.xlsx | DOID | | Contains all children of "autoimmune diseases" within DOID, including all associated synonyms, defintions, and DBxrefs |
| SNOMED-Athena/SNOMED_Athena_Matches-all_autoimmune_disease.xlsx | SNOMED | Athena | Contains all "autoimmune diseases" within SNOMED, with matches to Athena |
| ARI-Linked-Database/ARI-Linked-Disease-Database.xlsx | ARI, DOID, SNOMED, MESH, Athena/OMOP | (integrated) | Fully-linked relational database that unions all of the above sources, deduplicated by shared SNOMED conceptId / DOID CURIE, with a generated ARI_ID foreign key joining disease names, synonyms, definitions, cross-references, SNOMED details and OMOP mappings. See ARI-Linked-Database/README.md. |

## 4-reports (2026-06-14) — disease reorganization per instructions.md

Built by grouping `1-master/ARI Master List V 2.1 - 2026-06-04.xlsx` on the **Parent** column (case-insensitive — casing-only duplicates such as "Multiple sclerosis"/"Multiple Sclerosis", "Eosinophilic Esophagitis", "Inclusion Body Myositis", "Rheumatic Chorea" are merged), using the preferred (`syn = "N"`) name per group. The generic group entry "Autoimmune disease" (master `syn = "G"`, Category "All") is excluded as too broad. All reports source only from the master file; the only external data is the local `2-databases/doid.owl` (Human Disease Ontology, release 2026-04-30, CC0) and the local `2-databases/snomed/` OMOP/Athena export. ARI IDs assigned sequentially in alphabetical order of preferred name, format `ARI:0001XXX`, IRI `https://diseases.autoimmuneregistry.org/disease/ARI_0001XXX`. **210 core diseases.**

| File | Rows | Built from | Contents |
| --- | --- | --- | --- |
| 1_Core_ARI_Diseases.xlsx | 210 diseases | `Diseases` sheet | Core annotations: ARI ID + IRI, preferred name, synonyms, subtypes, SNOMED / OMOP ConceptID / Concept (DXCODE) codes, obsolete-SNOMED flag (`syn = "U"`), Code Status, definition + sources, tissue region, evidence level, autoimmune modifier, version. Codes deduplicated, decimal-suffixed duplicates truncated; SNOMED/OMOP/IRI hyperlinked to Athena. "Confirmed No Code"/"No code" in Code Status only when no numeric code. |
| 2_Proposed_Diseases.xlsx | 52 proposed | `Leon Main` sheet | Proposed diseases with incidence/prevalence, unit, comments, autoimmune justification. Colour-coded **Status**: Already in core (coded / no-code-yet) vs New (not yet added). |
| 3_Proposed_Changes.xlsx | 28 changes | `Leon Mapped` sheet | OMOP/SNOMED mappings proposed for ARI diseases; rows with invalid_reason (U/D; 11) highlighted with proposed-change guidance. |
| 4_Additional_Info_Index.xlsx | 210 + detail | Profiledata, Profilemaster, Symptoms, ageonset, JCIdata, Surveycodes, Subtypes | Index keyed by ARI ID with per-source presence matrix, colour-coded by source (see Legend). One detail sheet per source, joined to ARI ID. |
| 5_DOID_Mapping.xlsx | 11 no-code diseases | `Diseases` + local doid.owl | DOID match for no-code diseases via Gilda lexical grounding. 1 hit (COPA syndrome -> DOID:0081242); other 10 not in DOID. |
| 6_DOID_Matches_All.xlsx | 210 diseases | `Diseases` + local doid.owl | DOID match for all diseases via Gilda. Sheet 1: ARI ID, name, DOID (PURL link), label, score, match type, matched-via, SNOMED xref, obsolete (129/210 matched). Sheet 2 "Matched Disease Details": full DOID annotation per matched disease - definition, synonyms, all xrefs grouped by source (SNOMED, MESH, NCI, UMLS, ICD, other). |
| 7_SNOMED_Matches_All.xlsx | 210 diseases | `Diseases` + local snomed/CONCEPT.csv | SNOMED match for all diseases via Gilda over standard SNOMED Condition concepts. Matched code (Athena search link), name, score, OMOP ConceptID (Athena term link), existing master code, and "Agrees w/ Existing" QA flag (green=agrees, amber=differs). 188/210 matched; 183 agree with existing master codes. |

Matching method (reports 5-7): Gilda lexical grounding (same method as `notebook/build_autoimmune-single.py`'s pyobo grounders), built from local ontology data only - no online sources. Programming work in `notebook/ari-grounding/`.

Sources: master list only, plus local `data/2-databases/doid.owl` and `data/2-databases/snomed/`. No online sources used.
