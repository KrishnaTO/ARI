import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import validate_mappings as vm

ARI_DISEASE = "http://www.aurint.org/ontologies/ari-disease#"

EMPTY_MODULE = (
    '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
    'xmlns:owl="http://www.w3.org/2002/07/owl#" '
    f'xmlns:ari-disease="{ARI_DISEASE}"></rdf:RDF>'
)


def no_concept_findings(value):
    texts = {path: EMPTY_MODULE for path in vm.ARI_OWNED}
    texts[vm.BIOMARKERS_PATH] = (
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
        'xmlns:owl="http://www.w3.org/2002/07/owl#" '
        f'xmlns:ari-disease="{ARI_DISEASE}">'
        '<owl:Class rdf:about="http://www.aurint.org/ontologies/ari-biomarkers#ARIB_0000001">'
        f"<ari-disease:ARI_NoConcept>{value}</ari-disease:ARI_NoConcept>"
        "</owl:Class></rdf:RDF>"
    )
    report = vm.Report()
    vm.check_no_concept_values(texts, report)
    return [f for f in report.findings if f.code == "no-concept-value"]


def test_not_a_biomarker_is_a_valid_decision():
    assert no_concept_findings("not a biomarker") == []


def test_a_misspelt_decision_is_an_error():
    assert len(no_concept_findings("not biomarker")) == 1
