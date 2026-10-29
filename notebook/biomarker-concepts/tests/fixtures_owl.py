"""Tiny disease and biomarker OWL texts shared by test_model.py and test_propose.py."""

ARI = "http://www.aurint.org/ontologies/ari-disease#"
ARIB = "http://www.aurint.org/ontologies/ari-biomarkers#ARIB_"
DISEASE = "https://diseases.autoimmuneregistry.org/disease/"

HEADER = """<?xml version="1.0"?>
<rdf:RDF xmlns="{default}"
     xml:base="{base}"
     xmlns:dc="http://purl.org/dc/elements/1.1/"
     xmlns:obo="http://purl.obolibrary.org/obo/"
     xmlns:owl="http://www.w3.org/2002/07/owl#"
     xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
     xmlns:xml="http://www.w3.org/XML/1998/namespace"
     xmlns:xsd="http://www.w3.org/2001/XMLSchema#"
     xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
     xmlns:skos="http://www.w3.org/2004/02/skos/core#"
     xmlns:oboInOwl="http://www.geneontology.org/formats/oboInOwl#"
     xmlns:ari-disease="http://www.aurint.org/ontologies/ari-disease#">
"""


def entry(local, kind_class, label, extra=""):
    return f"""    <owl:NamedIndividual rdf:about="{ARI}{local}">
        <rdf:type rdf:resource="{ARI}{kind_class}"/>
        {extra}
        <ARI_Obsolete>false</ARI_Obsolete>
        <rdfs:label>{label}</rdfs:label>
    </owl:NamedIndividual>
"""


def disease(ari_id, label, links):
    lines = "\n".join(f'        <{prop} rdf:resource="{ARI}{local}"/>' for prop, local in links)
    return f"""    <owl:NamedIndividual rdf:about="{DISEASE}{ari_id}">
        <rdf:type rdf:resource="{ARI}AutoimmuneDisease"/>
{lines}
        <rdfs:label>{label}</rdfs:label>
    </owl:NamedIndividual>
"""


def disease_text(entries, diseases):
    return (
        HEADER.format(default=ARI, base="http://www.aurint.org/ontologies/ari-disease")
        + '    <owl:Ontology rdf:about="http://www.aurint.org/ontologies/ari-disease"/>\n'
        + "".join(diseases)
        + "".join(entries)
        + "</rdf:RDF>\n"
    )


def biomarkers_text(classes=""):
    return (
        HEADER.format(default="http://www.aurint.org/ontologies/ari_biomarkers#",
                      base="http://www.aurint.org/ontologies/ari_biomarkers")
        + """    <owl:Ontology rdf:about="http://www.aurint.org/ontologies/ari_biomarkers">
        <owl:imports rdf:resource="http://www.aurint.org/ontologies/ari_core"/>
        <rdfs:comment>Shared ARI biomarker concepts.</rdfs:comment>
    </owl:Ontology>
"""
        + classes
        + "</rdf:RDF>\n"
    )


def arib_class(number, parent, label, body=""):
    return f"""    <owl:Class rdf:about="{ARIB}{number:07d}">
        <rdfs:subClassOf rdf:resource="{parent}"/>
        <oboInOwl:id>ARIB:{number:07d}</oboInOwl:id>
        <rdfs:label>{label}</rdfs:label>
{body}    </owl:Class>
"""


# The antibodies fixture: one hand-made concept (ARIB_0000005 "Anti-Ro antibodies"), entries that are
# decided (linked, ARI_NoConcept, obsolete) and entries that exercise every proposal step.
EXISTING_RO = arib_class(
    5, ARI + "Autoantibody", "Anti-Ro antibodies",
    '        <skos:altLabel>Ro antibody</skos:altLabel>\n'
    '        <skos:exactMatch rdf:resource="http://purl.obolibrary.org/obo/HP_0000005"/>\n',
)

ANTIBODY_ENTRIES = [
    entry("Ab_1", "Autoantibody", "Anti-GAD65 autoantibodies"),
    entry("Ab_2", "Autoantibody", "Anti-GAD65 antibodies"),
    entry("Ab_3", "Autoantibody", "Anti-MOG IgG"),
    entry("Ab_4", "Autoantibody", "ANA, anti-dsDNA and anti-Sm"),
    entry("Ab_5", "Autoantibody", "Anti-Ro antibodies",
          f'<sharedConcept rdf:resource="{ARIB}0000005"/>'),
    entry("Ab_6", "Autoantibody", "Elevated IgG", "<ARI_NoConcept>not a biomarker</ARI_NoConcept>"),
    entry("Ab_7", "Autoantibody", "Anti-old antibodies").replace(
        "<ARI_Obsolete>false</ARI_Obsolete>", "<ARI_Obsolete>true</ARI_Obsolete>"),
    entry("Ab_8", "Autoantibody", "Type VII Colagen"),
    entry("Ab_9", "Autoantibody", "Type VII collagen"),
    entry("Ab_10", "Autoantibody", "Type VII collagen"),
    entry("Ab_11", "Autoantibody", "This antibody is associated with relapse."),
    entry("Ab_12", "Autoantibody", "anti-villin 40"),
    entry("Ab_13", "Autoantibody", "Anti-Ro antibodies"),
    entry("Ab_14", "Autoantibody", "Type VI collagen"),
]
ANTIBODY_DISEASES = [
    disease("ARI_0000001", "Disease one", [("hasAntibody", f"Ab_{n}") for n in (1, 3, 5, 7, 8, 11, 13)]),
    disease("ARI_0000002", "Disease two", [("hasAntibody", f"Ab_{n}") for n in (2, 4, 6, 9, 10, 12, 14)]),
]
