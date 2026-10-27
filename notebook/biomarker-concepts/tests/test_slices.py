import xml.etree.ElementTree as ET

import pytest

import build_biomarker_slices as slices
import sources

ARIB = "http://www.aurint.org/ontologies/ari-biomarkers#ARIB_"

BIOMARKERS = f"""<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:owl="http://www.w3.org/2002/07/owl#"
         xmlns:skos="http://www.w3.org/2004/02/skos/core#">
  <owl:Class rdf:about="{ARIB}0000001">
    <skos:exactMatch rdf:resource="http://purl.obolibrary.org/obo/PR_Q05329"/>
    <skos:closeMatch rdf:resource="http://purl.obolibrary.org/obo/HP_0000001"/>
  </owl:Class>
  <owl:Class rdf:about="{ARIB}0000002">
    <skos:broadMatch rdf:resource="http://identifiers.org/hgnc/4093"/>
    <skos:narrowMatch rdf:resource="http://purl.obolibrary.org/obo/CHEBI_15377"/>
  </owl:Class>
  <owl:Class rdf:about="{ARIB}0000003">
    <skos:relatedMatch rdf:resource="https://loinc.org/4548-4"/>
    <skos:exactMatch rdf:resource="http://example.org/other"/>
  </owl:Class>
  <owl:Class rdf:about="http://example.org/NotArib">
    <skos:exactMatch rdf:resource="http://purl.obolibrary.org/obo/PR_P00000"/>
  </owl:Class>
</rdf:RDF>
"""

RDF = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
RDFS = "{http://www.w3.org/2000/01/rdf-schema#}"
OBOINOWL = "{http://www.geneontology.org/formats/oboInOwl#}"
OWL = "{http://www.w3.org/2002/07/owl#}"
IAO = "{http://purl.obolibrary.org/obo/}IAO_0000115"


def term(id, label, parents=()):
    return sources.Term(id, label, [], list(parents), "73.1")


def classes(path):
    root = ET.parse(path).getroot()
    return {c.get(RDF + "about"): c for c in root.findall(OWL + "Class")}


def test_referenced_terms_reads_every_match():
    assert slices.referenced_terms(BIOMARKERS) == {
        "pr": {"http://purl.obolibrary.org/obo/PR_Q05329"},
        "chebi": {"http://purl.obolibrary.org/obo/CHEBI_15377"},
        "hgnc": {"http://identifiers.org/hgnc/4093"},
        "loinc": {"https://loinc.org/4548-4"},
    }


def test_a_missing_term_stops_the_run(tmp_path):
    with pytest.raises(SystemExit) as stop:
        slices.write_slice(
            "pr",
            {"http://purl.obolibrary.org/obo/PR_Q05329", "http://purl.obolibrary.org/obo/PR_Q99999"},
            {"PR:Q05329": term("PR:Q05329", "protein")},
            tmp_path / "ari_pr.owl",
        )
    assert "http://purl.obolibrary.org/obo/PR_Q99999" in str(stop.value)
    assert "PR_Q05329" not in str(stop.value)
    assert not (tmp_path / "ari_pr.owl").exists()


def test_pr_slice_includes_ancestors(tmp_path):
    release = {
        "PR:000000001": term("PR:000000001", "protein"),
        "PR:000000002": term("PR:000000002", "family", ["PR:000000001"]),
        "PR:Q05329": term("PR:Q05329", "GAD2", ["PR:000000002", "PR:000099999"]),  # last parent not in release
        "PR:Q00001": term("PR:Q00001", "unrelated", ["PR:000000001"]),
    }
    out = tmp_path / "ari_pr.owl"
    slices.write_slice("pr", {"http://purl.obolibrary.org/obo/PR_Q05329"}, release, out)
    found = classes(out)
    base = "http://purl.obolibrary.org/obo/"
    assert set(found) == {base + "PR_Q05329", base + "PR_000000002", base + "PR_000000001"}
    gad = found[base + "PR_Q05329"]
    assert gad.findtext(RDFS + "label") == "GAD2"
    assert gad.findtext(OBOINOWL + "id") == "PR:Q05329"
    assert [p.get(RDF + "resource") for p in gad.findall(RDFS + "subClassOf")] == [base + "PR_000000002"]


def test_hgnc_slice_holds_symbol_name_and_id(tmp_path):
    genes = {"HGNC:4093": sources.Gene("HGNC:4093", "GAD2", "glutamate decarboxylase 2", [], [])}
    out = tmp_path / "ari_hgnc.owl"
    slices.write_slice("hgnc", {"http://identifiers.org/hgnc/4093"}, genes, out)
    cls = classes(out)["http://identifiers.org/hgnc/4093"]
    assert cls.findtext(RDFS + "label") == "GAD2"
    assert cls.findtext(IAO) == "glutamate decarboxylase 2"
    assert cls.findtext(OBOINOWL + "id") == "HGNC:4093"


def test_loinc_slice_carries_the_licence_notice(tmp_path):
    out = tmp_path / "ari_loinc.owl"
    slices.write_slice("loinc", {"https://loinc.org/4548-4"}, {"4548-4": term("4548-4", "Hemoglobin A1c")}, out)
    assert classes(out)["https://loinc.org/4548-4"].findtext(OBOINOWL + "id") == "4548-4"
    comments = [c.text for c in ET.parse(out).getroot().find(OWL + "Ontology").findall(RDFS + "comment")]
    assert any("LOINC is copyright © Regenstrief Institute" in c for c in comments)


def test_an_empty_set_writes_an_empty_ontology(tmp_path):
    out = tmp_path / "ari_chebi.owl"
    slices.write_slice("chebi", set(), {}, out)
    root = ET.parse(out).getroot()
    assert root.find(OWL + "Ontology").get(RDF + "about") == "http://www.aurint.org/ontologies/ari_chebi"
    assert root.findall(OWL + "Class") == []
