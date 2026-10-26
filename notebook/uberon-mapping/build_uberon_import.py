"""Write the UBERON import slice ontologies/ari_uberon.owl.

ontologies/ari_anatomy.owl is where ARI's tissue and system classes link to UBERON, by
rdfs:subClassOf (and skos:exactMatch / skos:broadMatch / skos:closeMatch where a class uses them).
This script reads those links and writes the slice: every linked UBERON term and all its is_a
ancestors, with UBERON's label, definition and is_a parents (a MIREOT-style slice of the given
release). It writes nothing else; the links themselves are curated in ari_anatomy.owl.

A linked term that is missing or obsolete in the release stops the run, listing each one.

Usage: python build_uberon_import.py <path to data/2-databases>
The database folder is not tracked in git, so pass the path of a checkout holding
uberon-basic.obo (http://purl.obolibrary.org/obo/uberon/basic.obo). Then run
tools/format-owl.sh ontologies/ari_uberon.owl to put the slice in the canonical layout.
"""
import os, re, sys
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ANATOMY = os.path.join(ROOT, "ontologies", "ari_anatomy.owl")
SLICE = os.path.join(ROOT, "ontologies", "ari_uberon.owl")

SLICE_IRI = "http://www.aurint.org/ontologies/ari_uberon"
OBO = "http://purl.obolibrary.org/obo/"
UBERON_IRI = OBO + "UBERON_"
XSD_STRING = "http://www.w3.org/2001/XMLSchema#string"
RDF = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
RDFS = "{http://www.w3.org/2000/01/rdf-schema#}"
OWL = "{http://www.w3.org/2002/07/owl#}"
SKOS = "{http://www.w3.org/2004/02/skos/core#}"
LINKS = [RDFS + "subClassOf", SKOS + "exactMatch", SKOS + "broadMatch", SKOS + "closeMatch"]


def obo_iri(curie):
    return OBO + curie.replace(":", "_")


def read_uberon(path):
    """UBERON terms by id: name, definition, is_a parents, obsolete flag; plus the release."""
    terms, cur, version = {}, None, None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("data-version: "):
                version = line.split(": ", 1)[1]
            if line == "[Term]":
                cur = {"is_a": [], "obsolete": False, "definition": ""}
                continue
            if line.startswith("["):
                cur = None
                continue
            if cur is None or ": " not in line:
                continue
            key, value = line.split(": ", 1)
            if key == "id":
                terms[value] = cur
            elif key == "name":
                cur["name"] = value
            elif key == "def":
                cur["definition"] = re.match(r'"((?:[^"\\]|\\.)*)"', value).group(1).replace('\\"', '"')
            elif key == "is_a":
                cur["is_a"].append(value.split(" ")[0])
            elif key == "is_obsolete" and value == "true":
                cur["obsolete"] = True
    if not version:
        sys.exit(f"{path} has no data-version line")
    return terms, version


def linked_uberon(anatomy_root):
    """UBERON CURIEs that any class names by rdfs:subClassOf, skos:exactMatch, skos:broadMatch or skos:closeMatch."""
    curies = set()
    for cls in anatomy_root.findall(OWL + "Class"):
        for tag in LINKS:
            for link in cls.findall(tag):
                iri = link.get(RDF + "resource")
                if iri and iri.startswith(UBERON_IRI):
                    curies.add(iri[len(OBO):].replace("_", ":"))
    return curies


def ancestors(uid, terms):
    out, todo = set(), [uid]
    while todo:
        for parent in terms[todo.pop()]["is_a"]:
            if parent not in out:
                out.add(parent)
                todo.append(parent)
    return out


def write_slice(curies, terms, version):
    ids = set()
    for curie in curies:
        ids |= {curie} | ancestors(curie, terms)
    out = [
        '<?xml version="1.0"?>',
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"',
        '         xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"',
        '         xmlns:owl="http://www.w3.org/2002/07/owl#"',
        f'         xmlns:obo="{OBO}"',
        f'         xml:base="{SLICE_IRI}">',
        "",
        f'<owl:Ontology rdf:about="{SLICE_IRI}">',
        f'  <rdfs:comment rdf:datatype="{XSD_STRING}">UBERON terms ARI tissue and system classes link to, '
        f"with their is_a ancestors. Built by notebook/uberon-mapping/build_uberon_import.py from "
        f"{escape(version)}; do not edit by hand.</rdfs:comment>",
        f'  <owl:versionInfo rdf:datatype="{XSD_STRING}">{escape(version)}</owl:versionInfo>',
        "</owl:Ontology>",
        "",
        f'<owl:AnnotationProperty rdf:about="{OBO}IAO_0000115">',
        f'  <rdfs:label rdf:datatype="{XSD_STRING}">definition</rdfs:label>',
        "</owl:AnnotationProperty>",
        "",
    ]
    for uid in sorted(ids):
        term = terms[uid]
        out.append(f'<owl:Class rdf:about="{obo_iri(uid)}">')
        for parent in sorted(term["is_a"]):
            out.append(f'  <rdfs:subClassOf rdf:resource="{obo_iri(parent)}"/>')
        out.append(f'  <rdfs:label rdf:datatype="{XSD_STRING}">{escape(term["name"])}</rdfs:label>')
        if term["definition"]:
            out.append(f'  <obo:IAO_0000115 rdf:datatype="{XSD_STRING}">'
                       f'{escape(term["definition"])}</obo:IAO_0000115>')
        out += ["</owl:Class>", ""]
    out.append("</rdf:RDF>")
    with open(SLICE, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    return len(ids)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    terms, version = read_uberon(os.path.join(sys.argv[1], "uberon-basic.obo"))
    curies = linked_uberon(ET.parse(ANATOMY).getroot())
    problems = [f"{c}: " + ("is obsolete in UBERON" if c in terms else "is not in UBERON")
                for c in sorted(curies) if c not in terms or terms[c]["obsolete"]]
    if problems:
        sys.exit(f"{os.path.relpath(ANATOMY, ROOT)} links to UBERON terms that cannot be sliced:\n  "
                 + "\n  ".join(problems))
    count = write_slice(curies, terms, version)
    print(f"{len(curies)} linked UBERON terms ({version}); {count} terms in {os.path.relpath(SLICE, ROOT)}")


if __name__ == "__main__":
    main()
