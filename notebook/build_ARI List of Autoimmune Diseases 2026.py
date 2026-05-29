# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pandas",
#     "pyobo[gilda-slim]>=0.12.0",
# ]
# ///

import pandas as pd
import pyobo

data_url = "ARI List of Autoimmune Diseases 2026.csv"
df = pd.read_csv(data_url, names=["Category","Evidence","Quality","autoimmune","Parent","Disease","Syn","SNOMED","ConceptID","Profile","pubmed","Citation","prevtype","Prevalence_Description","prevnotes","min_rate","max_rate","denom","us_cases_min","us_cases_max","us_cases_mean","rateper100k","Antibodies","Rose_Mackay Citation","Pubmed Evidence (incomplete)"])
#df = df[["species", "strain", "organ"]]


mondo_grounder = pyobo.get_grounder("mondo")
uberon_grounder = pyobo.get_grounder("uberon")
cl_grounder = pyobo.get_grounder("cl")
doid_grounder = pyobo.get_grounder("doid")

for col in ["Category","Evidence","Parent","Disease"]:
    # for the Bioregistry-standardized CURIEs
    mondo_grounder.ground_df(df, col, target_column=f"{col}_curie")
    uberon_grounder.ground_df(df, col, target_column=f"{col}_uberon_curie")
    cl_grounder.ground_df(df, col, target_column=f"{col}_cl_curie")
    doid_grounder.ground_df(df, col, target_column=f"{col}_doid_curie")

    # for Bioregistry-standardized references (e.g., pre-parsed prefix, identifier, and name)
    mondo_grounder.ground_df(
        df, col, target_column=f"{col}_mondo_reference", target_type="reference"
    )
    uberon_grounder.ground_df(
        df, col, target_column=f"{col}_uberon_reference", target_type="reference"
    )
    cl_grounder.ground_df(
        df, col, target_column=f"{col}_cl_reference", target_type="reference"
    )
    doid_grounder.ground_df(
        df, col, target_column=f"{col}_doid_reference", target_type="reference"
    )

#TODO for SNOMED id, get the name from the SNOMED CT ontology and ground that instead of the raw SNOMED id


# # this adds a new column `organ_curie` that has strings
# # for the Bioregistry-standardized CURIEs
# mondo_grounder.ground_df(df, "term", target_column="term_curie")
# uberon_grounder.ground_df(df, "term", target_column="uberon_curie")
# cl_grounder.ground_df(df, "term", target_column="cl_curie")
# doid_grounder.ground_df(df, "term", target_column="doid_curie")

# # this adds a new column `organ_reference` that has reference objects
# # for Bioregistry-standardized references (e.g., pre-parsed prefix, identifier, and name)
# mondo_grounder.ground_df(
#     df, "term", target_column="mondo_reference", target_type="reference"
# )
# uberon_grounder.ground_df(
#     df, "term", target_column="uberon_reference", target_type="reference"
# )
# cl_grounder.ground_df(
#     df, "term", target_column="cl_reference", target_type="reference"
# )
# doid_grounder.ground_df(
#     df, "term", target_column="doid_reference", target_type="reference"
# )

# # print the final dataframe to show below
# print(df.to_markdown(tablefmt="rst", index=False))
df.to_csv("ARI List of Autoimmune Diseases 2026-grounded.csv", index=False, columns=[
    "Category", "Category_curie", [f"Category_{col}_curie" for col in ["mondo", "uberon", "cl", "doid"]],
    "Evidence", "Evidence_curie", [f"Evidence_{col}_curie" for col in ["mondo", "uberon", "cl", "doid"]],
    "Quality","autoimmune",
    "Parent", "Parent_curie", [f"Parent_{col}_curie" for col in ["mondo", "uberon", "cl", "doid"]],
    "Disease", "Disease_curie", [f"Disease_{col}_curie" for col in ["mondo", "uberon", "cl", "doid"]],
    "Syn","SNOMED","ConceptID"]
    )