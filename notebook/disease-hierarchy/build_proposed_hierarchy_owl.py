"""Write proposed_parents.tsv as an OWL class hierarchy for viewing (e.g. in Protege).

Every active disease in ontologies/ari_disease.owl becomes a class, using the same disease IRI.
Rows of proposed_parents.tsv become axioms, each annotated with its relation, confidence and reason:
  is_a, manifestation_of, duplicate_of - subClassOf the parent
  component_of                         - subClassOf "Combination disease" (ARI#138) and
                                         subClassOf (hasComponent some <parent>)
  reject                               - left out
Diseases with no parent sit directly under "ARI disease".

Usage: python build_proposed_hierarchy_owl.py
Writes proposed_hierarchy.owl next to this script.
"""
import csv, os
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape, quoteattr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ONTOLOGY = os.path.join(ROOT, "ontologies/ari_disease.owl")
PROPOSED = os.path.join(HERE, "proposed_parents.tsv")
OUT = os.path.join(HERE, "proposed_hierarchy.owl")

BASE = "http://www.aurint.org/ontologies/ari-disease-proposed-hierarchy"
DISEASE = "https://diseases.autoimmuneregistry.org/disease/"
ROOT_CLASS = BASE + "#ARIDisease"
COMBINATION = BASE + "#CombinationDisease"
HAS_COMPONENT = BASE + "#hasComponent"
SUBCLASS_RELATIONS = {"is_a", "manifestation_of", "duplicate_of"}
RDF = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"


def disease_iri(ari_id):
    return DISEASE + ari_id.replace(":", "_")


def read_diseases():
    """ARI ID -> label for every non-obsolete disease individual in the ontology."""
    diseases = {}
    for ind in ET.parse(ONTOLOGY).getroot():
        if "/disease/ARI_" not in ind.get(RDF + "about", ""):
            continue
        fields = {e.tag.split("}")[-1]: e.text for e in ind}
        if fields.get("ARI_Obsolete") == "true":
            continue
        diseases[fields["ARI_ID"]] = fields["label"]
    return diseases


def literal(tag, text):
    return f"    <{tag}>{escape(text)}</{tag}>\n"


def axiom(source, target_xml, row):
    """An owl:Axiom annotating source subClassOf target with the row's relation, confidence and reason."""
    return (
        "<owl:Axiom>\n"
        f"    <owl:annotatedSource rdf:resource={quoteattr(source)}/>\n"
        '    <owl:annotatedProperty rdf:resource="http://www.w3.org/2000/01/rdf-schema#subClassOf"/>\n'
        f"    {target_xml}\n"
        + literal("relation", row["Relation"])
        + literal("confidence", row["Confidence"])
        + literal("reason", row["Reason"])
        + "</owl:Axiom>\n\n"
    )


def main():
    diseases = read_diseases()
    rows = [r for r in csv.DictReader(open(PROPOSED, encoding="utf-8"), delimiter="\t") if r["Relation"] != "reject"]
    for r in rows:
        for key in ("Child ARI ID", "Parent ARI ID"):
            if r[key] not in diseases:
                raise SystemExit(f"{r[key]} in proposed_parents.tsv is not an active disease in the ontology")

    parents = {}       # child -> [(parent IRI, row)]
    components = {}    # child -> [row]
    for r in rows:
        child = r["Child ARI ID"]
        if r["Relation"] in SUBCLASS_RELATIONS:
            parents.setdefault(child, []).append((disease_iri(r["Parent ARI ID"]), r))
        elif r["Relation"] == "component_of":
            components.setdefault(child, []).append(r)
        else:
            raise SystemExit(f"Unknown relation {r['Relation']!r}")

    out = [
        '<?xml version="1.0"?>\n'
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n'
        '         xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"\n'
        '         xmlns:owl="http://www.w3.org/2002/07/owl#"\n'
        f'         xml:base="{BASE}"\n'
        f'         xmlns="{BASE}#">\n\n'
        f'<owl:Ontology rdf:about="{BASE}">\n'
        "    <rdfs:comment>Proposed parent links between ARI diseases for ARI#137 and ARI#138, "
        "generated from notebook/disease-hierarchy/proposed_parents.tsv for viewing. Not the record: "
        "ontologies/ari_disease.owl is.</rdfs:comment>\n"
        "</owl:Ontology>\n\n"
    ]
    for name in ("ariId", "relation", "confidence", "reason"):
        out.append(f'<owl:AnnotationProperty rdf:about="#{name}"/>\n')
    out.append(
        '<owl:ObjectProperty rdf:about="#hasComponent">\n'
        "    <rdfs:label>has component</rdfs:label>\n"
        "</owl:ObjectProperty>\n\n"
        f'<owl:Class rdf:about="{ROOT_CLASS}">\n    <rdfs:label>ARI disease</rdfs:label>\n</owl:Class>\n\n'
        f'<owl:Class rdf:about="{COMBINATION}">\n'
        "    <rdfs:label>Combination disease</rdfs:label>\n"
        f'    <rdfs:subClassOf rdf:resource="{ROOT_CLASS}"/>\n'
        "    <rdfs:comment>Diseases defined by two or more listed diseases occurring together (ARI#138).</rdfs:comment>\n"
        "</owl:Class>\n\n"
    )

    axioms = []
    for ari_id in sorted(diseases):
        iri = disease_iri(ari_id)
        out.append(f"<owl:Class rdf:about={quoteattr(iri)}>\n")
        out.append(literal("rdfs:label", diseases[ari_id]))
        out.append(literal("ariId", ari_id))
        for parent, row in parents.get(ari_id, []):
            out.append(f"    <rdfs:subClassOf rdf:resource={quoteattr(parent)}/>\n")
            axioms.append(axiom(iri, f"<owl:annotatedTarget rdf:resource={quoteattr(parent)}/>", row))
        if ari_id in components:
            out.append(f'    <rdfs:subClassOf rdf:resource="{COMBINATION}"/>\n')
        for row in components.get(ari_id, []):
            node = f"c_{ari_id[4:]}_{row['Parent ARI ID'][4:]}"
            out.append(f'    <rdfs:subClassOf rdf:nodeID="{node}"/>\n')
            axioms.append(axiom(iri, f'<owl:annotatedTarget rdf:nodeID="{node}"/>', row))
            axioms.append(
                f'<owl:Restriction rdf:nodeID="{node}">\n'
                f'    <owl:onProperty rdf:resource="{HAS_COMPONENT}"/>\n'
                f"    <owl:someValuesFrom rdf:resource={quoteattr(disease_iri(row['Parent ARI ID']))}/>\n"
                "</owl:Restriction>\n\n"
            )
        if ari_id not in parents and ari_id not in components:
            out.append(f'    <rdfs:subClassOf rdf:resource="{ROOT_CLASS}"/>\n')
        out.append("</owl:Class>\n\n")
    out.extend(axioms)
    out.append("</rdf:RDF>\n")

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("".join(out))
    print(f"{len(diseases)} diseases, {sum(map(len, parents.values()))} subclass links, "
          f"{sum(map(len, components.values()))} component links -> {OUT}")


if __name__ == "__main__":
    main()
