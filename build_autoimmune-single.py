# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pandas",
#     "pyobo[gilda-slim]>=0.12.0",
# ]
# ///

import pandas as pd
import pyobo

data_url = "autoimmune-single.csv"
df = pd.read_csv(data_url, names=["term"])
#df = df[["species", "strain", "organ"]]

mondo_grounder = pyobo.get_grounder("mondo")
uberon_grounder = pyobo.get_grounder("uberon")
cl_grounder = pyobo.get_grounder("cl")
doid_grounder = pyobo.get_grounder("doid")

# this adds a new column `organ_curie` that has strings
# for the Bioregistry-standardized CURIEs
mondo_grounder.ground_df(df, "term", target_column="term_curie")
uberon_grounder.ground_df(df, "term", target_column="uberon_curie")
cl_grounder.ground_df(df, "term", target_column="cl_curie")
doid_grounder.ground_df(df, "term", target_column="doid_curie")

# this adds a new column `organ_reference` that has reference objects
# for Bioregistry-standardized references (e.g., pre-parsed prefix, identifier, and name)
mondo_grounder.ground_df(
    df, "term", target_column="mondo_reference", target_type="reference"
)
uberon_grounder.ground_df(
    df, "term", target_column="uberon_reference", target_type="reference"
)
cl_grounder.ground_df(
    df, "term", target_column="cl_reference", target_type="reference"
)
doid_grounder.ground_df(
    df, "term", target_column="doid_reference", target_type="reference"
)

# print the final dataframe to show below
print(df.to_markdown(tablefmt="rst", index=False))
df.to_csv("autoimmune-single-grounded.csv", index=False)