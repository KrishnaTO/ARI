# Synonym vs subtype review (report 9)

These scripts build `data/4-reports/9_Synonym_Review.tsv`. The method and columns are
described under report 9 in `data/4-reports/README.md`.

## Steps

```bash
# 1. Gather names. Reads the ontology, the confirmed SSSOM mappings and data/2-databases;
#    Orphanet/NCIt come from EBI OLS4 and MeSH from the NLM SPARQL endpoint (cached next to OUT).
python -I gather.py <repo> <repo>/data/2-databases <scratch>/gather.json

# 2. Merge names per disease and judge them. The second argument is the current report:
#    its verdicts carry forward for ARI strings that no database names.
python -I classify.py <scratch>/gather.json <repo>/data/4-reports/9_Synonym_Review.tsv <scratch>/candidates.json

# 3. List what still needs a curator verdict. Each new decision goes into decisions.json;
#    then rerun step 2.
python -I worklist.py <scratch>/candidates.json <scratch>/worklist.tsv

# 4. Write the report.
python -I write_report.py <scratch>/candidates.json <repo>/data/4-reports/9_Synonym_Review.tsv <yyyy-mm-dd>
```

The first run of step 1 takes several minutes because it reads the SNOMED export, and it
keeps a `snomed.pkl` cache next to the output.

## Files

- `gather.py` collects, for every ARI disease, its `ARI_Synonym`, `ARI_SynonymWithdrawn` and
  `ARI_ClinicalSubtype` strings. For each confirmed target term it also collects the label,
  synonyms with their scope, parents and descendants.
- `classify.py` normalises names (case, accents, possessives, British spelling, inverted
  "Anemia, Aplastic" forms and plurals) into one key per disease. It applies the
  subtype-wins rule, the variant patterns and the broader/narrower mapped-term corrections,
  then overlays `decisions.json`.
- `decisions.json` holds the hand decisions, keyed `"<ARI id>\t<normalised key>"`, as
  `{verdict, note, name}`.
- `worklist.py` lists conflicts, related-only names, qualified names (for example "juvenile
  X" or "primary X" offered as exact synonyms) and ARI strings whose verdict changed. None of
  these has a decision yet.
- `write_report.py` writes one row per ARI string and one row per database-only name.

`classify.py` adds MONDO:1060002 (ocular myasthenia gravis) by hand, because the local
`mondo.obo` predates it.
