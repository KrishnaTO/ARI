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