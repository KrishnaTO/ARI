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


# --------------------------------------------------------------------------
# Biomarker concepts
# --------------------------------------------------------------------------

ARIB = "http://www.aurint.org/ontologies/ari-biomarkers#ARIB_"
ANTIBODY = ARI_DISEASE + "Autoantibody"
ANTIGEN = ARI_DISEASE + "Antigen"
OBO = "http://purl.obolibrary.org/obo/"


def module(*nodes):
    return (
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
        'xmlns:owl="http://www.w3.org/2002/07/owl#" '
        'xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#" '
        'xmlns:skos="http://www.w3.org/2004/02/skos/core#" '
        'xmlns:oboInOwl="http://www.geneontology.org/formats/oboInOwl#" '
        f'xmlns:ari-disease="{ARI_DISEASE}">\n' + "\n".join(nodes) + "\n</rdf:RDF>"
    )


def node(tag, iri, *children):
    return f'<{tag} rdf:about="{iri}">\n' + "\n".join(children) + f"\n</{tag}>"


def res(prop, iri):
    return f'<{prop} rdf:resource="{iri}"/>'


def lit(prop, text):
    return f"<{prop}>{text}</{prop}>"


def concept(n, parent, label, *more, decided=True):
    """An ARIB class; `decided` gives it ARI_NoConcept "no term" so it is not unlinked."""
    extra = [lit("ari-disease:ARI_NoConcept", "no term")] if decided else []
    return node("owl:Class", ARIB + n, res("rdfs:subClassOf", parent),
                lit("rdfs:label", label), *more, *extra)


def entry(name, core, label, *more, obsolete="false"):
    return node("owl:NamedIndividual", ARI_DISEASE + name, res("rdf:type", core),
                lit("ari-disease:ARI_Obsolete", obsolete), lit("rdfs:label", label), *more)


def link(n):
    return res("ari-disease:sharedConcept", ARIB + n)


def classes(*iris):
    return module(*(node("owl:Class", iri) for iri in iris))


def biomarker_findings(concepts=(), entries=(), anatomy=(), uberon=(), symptoms=(), pr=()):
    texts = {path: EMPTY_MODULE for path in (*vm.ARI_OWNED, *vm.GENERATED)}
    texts[vm.BIOMARKERS_PATH] = module(*concepts)
    texts[vm.ONTOLOGY_PATH] = module(*entries)
    texts[vm.ANATOMY_PATH] = classes(*anatomy)
    texts[vm.UBERON_PATH] = classes(*uberon)
    texts[vm.SYMPTOMS_PATH] = classes(*symptoms)
    texts["ontologies/ari_pr.owl"] = classes(*pr)
    report = vm.Report()
    vm.check_biomarker_concepts(texts, report)
    return [f.code for f in report.findings]


def test_a_kind_is_found_through_parent_concepts():
    text = module(concept("0000001", ANTIBODY, "Anti-MOG antibody"),
                  concept("0000002", ARIB + "0000001", "Anti-MOG IgG"))
    assert vm.biomarker_kinds(text) == {ARIB + "0000001": "antibodies",
                                        ARIB + "0000002": "antibodies"}


def test_a_concept_with_no_kind_is_an_error():
    assert biomarker_findings([concept("0000001", ARI_DISEASE + "Symptom", "X")]) == [
        "biomarker-concept-kind"]


def test_a_concept_with_two_kinds_is_an_error():
    codes = biomarker_findings([
        concept("0000001", ANTIBODY, "A"),
        concept("0000002", ARIB + "0000001", "B", res("rdfs:subClassOf", ANTIGEN)),
    ])
    assert codes == ["biomarker-concept-kind"] * 2  # on each parent line


def test_a_link_to_another_kind_is_an_error():
    codes = biomarker_findings([concept("0000001", ANTIGEN, "GAD65")],
                               [entry("Ab_1", ANTIBODY, "GAD65", link("0000001"))])
    assert "biomarker-link-wrong-kind" in codes


def test_a_link_its_label_does_not_name_is_a_mismatch_on_both_lines():
    codes = biomarker_findings(
        [concept("0000001", ANTIBODY, "GADA"), concept("0000002", ANTIBODY, "IA-2A")],
        [entry("Ab_1", ANTIBODY, "GADA", link("0000002"))])
    assert codes == ["biomarker-concept-mismatch"] * 2


def test_a_named_concept_not_linked_is_missing():
    codes = biomarker_findings([concept("0000001", ANTIBODY, "GADA")],
                               [entry("Ab_1", ANTIBODY, "GADA")])
    assert codes == ["biomarker-concept-missing"]


def test_a_label_naming_no_concept_is_unmapped():
    assert biomarker_findings([], [entry("Ab_1", ANTIBODY, "GADA")]) == ["biomarker-unmapped"]


def test_an_obsolete_entry_is_skipped():
    assert biomarker_findings([], [entry("Ab_1", ANTIBODY, "GADA", obsolete="true")]) == []


def test_a_decision_and_a_link_together_are_an_error():
    codes = biomarker_findings(
        [concept("0000001", ANTIBODY, "GADA")],
        [entry("Ab_1", ANTIBODY, "GADA", link("0000001"),
               lit("ari-disease:ARI_NoConcept", "not a biomarker"))])
    assert codes == ["biomarker-decided-and-linked"] * 2


def test_lookup_is_per_kind():
    codes = biomarker_findings([concept("0000001", ANTIGEN, "GAD65")],
                               [entry("Ab_1", ANTIBODY, "GAD65")])
    assert codes == ["biomarker-unmapped"]


def test_a_bundle_is_not_checked_against_its_label():
    codes = biomarker_findings(
        [concept("0000001", ANTIBODY, "ANA"), concept("0000002", ANTIBODY, "Anti-dsDNA")],
        [entry("Ab_1", ANTIBODY, "ANA and anti-dsDNA", link("0000001"), link("0000002"))])
    assert codes == []


def test_a_bundle_still_gets_the_kind_check():
    codes = biomarker_findings(
        [concept("0000001", ANTIBODY, "ANA"), concept("0000002", ANTIGEN, "dsDNA")],
        [entry("Ab_1", ANTIBODY, "ANA and dsDNA", link("0000001"), link("0000002"))])
    assert codes == ["biomarker-link-wrong-kind"]


def test_relation_targets():
    anatomy = ARI_DISEASE + "BetaCell"
    uberon = OBO + "UBERON_0000006"
    symptom = "http://www.aurint.org/ontologies/ari-symptoms#ARIS_0000001"
    good = concept("0000001", ANTIBODY, "GADA",
                   res("ari-disease:targetsAntigen", ARIB + "0000002"),
                   res("ari-disease:expressedIn", anatomy),
                   res("ari-disease:expressedIn", uberon),
                   res("ari-disease:associatedSymptom", symptom))
    antigen = concept("0000002", ANTIGEN, "GAD65")
    bad = concept("0000003", ANTIBODY, "IA-2A",
                  res("ari-disease:targetsAntigen", ARIB + "0000001"),
                  res("ari-disease:expressedIn", symptom),
                  res("ari-disease:associatedSymptom", anatomy))
    codes = biomarker_findings([good, antigen, bad], anatomy=[anatomy], uberon=[uberon],
                               symptoms=[symptom])
    assert codes == ["biomarker-relation-target"] * 3


def test_a_match_missing_from_its_slice_is_an_error():
    codes = biomarker_findings(
        [concept("0000001", ANTIGEN, "GAD65", res("skos:exactMatch", OBO + "PR_Q05329"),
                 res("skos:relatedMatch", OBO + "PR_P00001"),
                 res("skos:exactMatch", OBO + "HP_5000011"))],
        pr=[OBO + "PR_Q05329"])
    assert codes == ["biomarker-external-missing"]


def test_a_related_match_alone_leaves_a_concept_unlinked():
    codes = biomarker_findings([concept("0000001", ANTIGEN, "GAD65",
                                        res("skos:relatedMatch", OBO + "PR_Q05329"),
                                        decided=False)],
                               pr=[OBO + "PR_Q05329"])
    assert codes == ["biomarker-concept-unlinked"]


def test_a_child_of_a_matched_parent_is_decided():
    codes = biomarker_findings([
        concept("0000001", ANTIBODY, "Anti-MOG antibody", res("skos:exactMatch", OBO + "HP_1"),
                decided=False),
        concept("0000002", ARIB + "0000001", "Anti-MOG IgG", decided=False),
    ])
    assert codes == []


def test_a_label_on_two_concepts_of_one_kind_is_ambiguous():
    codes = biomarker_findings([concept("0000001", ANTIBODY, "GADA"),
                                concept("0000002", ANTIBODY, "GADA")])
    assert codes == ["concept-label-ambiguous"] * 2


def test_a_label_on_two_kinds_is_not_ambiguous():
    assert biomarker_findings([concept("0000001", ANTIBODY, "GAD65"),
                               concept("0000002", ANTIGEN, "GAD65")]) == []


def test_an_id_on_two_concepts_is_repeated():
    codes = biomarker_findings([
        concept("0000001", ANTIBODY, "A", lit("oboInOwl:id", "ARIB:0000001")),
        concept("0000002", ANTIGEN, "B", lit("oboInOwl:id", "ARIB:0000001")),
    ])
    assert codes == ["concept-id-repeated"] * 2


def test_relation_and_slice_findings_stay_scoped_to_their_lines():
    def finding(code):
        return vm.Finding("error", code, vm.BIOMARKERS_PATH, 1, "")
    assert vm.is_biomarker_link_finding(finding("biomarker-unmapped"))
    assert vm.is_biomarker_link_finding(finding("biomarker-concept-unlinked"))
    assert not vm.is_biomarker_link_finding(finding("biomarker-relation-target"))
    assert not vm.is_biomarker_link_finding(finding("biomarker-external-missing"))
