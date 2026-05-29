# Get UMLS ID from DOIDs

Given a list of DOIDs, and that most entries for DOIDs have an accompanying annotation_property for 'database_cross_reference', which includes a reference to an UMLS_CUI (ex. UMLS_CUI:C0019069), we should be able to extract a list of UMLS ids. 

Proposed:
1. Assemble list of DOIDs in a csv. 
2. Use ROBOT tool to extract target DOIDs from the full ontology (download doid.owl file).

```sh Sample script {/mnt/f/1Projects/7Projects-Aurint/1Ontologies/Immunology/immuno-test/manual_import/annotate}
id="doid"
docker run -it -v $(pwd):/tools/tmp obolibrary/odkfull \
robot extract --method subset \
    --input tmp/${id}.owl \
    --term-file tmp/${id}_terms.txt \
    --copy-ontology-annotations true \
    -individuals exclude \
    --output tmp/results/${id}_terms.owl
```

3. Use SPARQL query to generate a list of UMLS_CUI with the given DOIDs. 

```sh
docker run -it -v $(pwd):/tools/tmp obolibrary/odkfull \
robot query --input tmp/results/doid_terms.owl --query tmp/umls.sparql tmp/results/doid_terms.csv
```

```SPARQL Target query {/mnt/f/1Projects/7Projects-Aurint/1Ontologies/Immunology/immuno-terms/query/umls.sparql}
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX OBO: <http://www.geneontology.org/formats/oboInOwl#>
PREFIX IAO: <http://purl.obolibrary.org/obo/IAO_>

SELECT DISTINCT ?disease ?dbxref
WHERE {
    ?disease a owl:Class .
    OPTIONAL{?disease OBO:hasDbXref ?dbxref .}
    FILTER (STRSTARTS(STR(?dbxref), STR("UMLS")))
 }
```