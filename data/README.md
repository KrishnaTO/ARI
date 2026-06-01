| File | Source | Target | Significance |
| --- | --- | --- | --- |
| ARI-SNOMED-Athena/ARI_SNOMED_Lookup.xlsx | ARI | SNOMED | Contains original SNOMED codes from ARI, and sourced up-to-date data from SNOMED per SNOMED_ID |
| ARI-SNOMED-Athena/ARI_Athena_Matches.xlsx | ARI | SNOMED, Athena | Contains ARI lookup to Athena database for matches by SNOMED codes or Disease name |
| ARI-MESH_Synonyms/ARI-MESHsynonyms-DOID.xlsx | ARI | MESH, DOID | Contains Synonyms, sourced by Leon/Rodrigo, lookup to DOID |
| ARI-doid/ARI-doid.xlsx | ARI | DOID | Contains DOID lookup by name |
| DOID_autoimmune_diseases/DOID-all.xlsx | DOID | | Contains all children of "autoimmune diseases" within DOID, including all associated synonyms, defintions, and DBxrefs |
| SNOMED-Athena/SNOMED_Athena_Matches-all_autoimmune_disease.xlsx | SNOMED | Athena | Contains all "autoimmune diseases" within SNOMED, with matches to Athena |
| ARI-Linked-Database/ARI-Linked-Disease-Database.xlsx | ARI, DOID, SNOMED, MESH, Athena/OMOP | (integrated) | Fully-linked relational database that unions all of the above sources, deduplicated by shared SNOMED conceptId / DOID CURIE, with a generated ARI_ID foreign key joining disease names, synonyms, definitions, cross-references, SNOMED details and OMOP mappings. See ARI-Linked-Database/README.md. |
