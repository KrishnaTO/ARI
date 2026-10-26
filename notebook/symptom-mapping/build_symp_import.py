"""Write the SYMP import slice ontologies/ari_symp.owl.

ontologies/ari_symptoms.owl is where ARI's symptom classes (ARIS) link to the Symptom Ontology
(SYMP) and the Human Phenotype Ontology (HPO): rdfs:subClassOf or skos:exactMatch / skos:broadMatch.
This script reads those links and writes the SYMP slice: every SYMP term an ARIS class names and
all its is_a ancestors, with SYMP's label, id and is_a parents. It writes nothing else; the links
themselves are curated in ari_symptoms.owl. HPO terms are only checked against the release, since
the OWL references them by IRI.

A linked SYMP term missing from symp.owl, or HPO term missing from hp.obo (both without their
obsolete terms), stops the run, listing each one.

Usage: python build_symp_import.py <path to data/2-databases>
The database folder is not tracked in git, so pass the path of a checkout holding symp.owl
(http://purl.obolibrary.org/obo/symp.owl) and hp.obo (http://purl.obolibrary.org/obo/hp.obo).
Then run tools/format-owl.sh ontologies/ari_symp.owl to put the slice in the canonical layout.
"""
import os, sys
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape, quoteattr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SYMPTOMS = os.path.join(ROOT, "ontologies", "ari_symptoms.owl")
OUT = os.path.join(ROOT, "ontologies", "ari_symp.owl")

SLICE_IRI = "http://www.aurint.org/ontologies/ari_symp"
OBO = "http://purl.obolibrary.org/obo/"
RDF = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
OWL = "{http://www.w3.org/2002/07/owl#}"
RDFS = "{http://www.w3.org/2000/01/rdf-schema#}"
SKOS = "{http://www.w3.org/2004/02/skos/core#}"
OBOINOWL = "{http://www.geneontology.org/formats/oboInOwl#}"
LINKS = [RDFS + "subClassOf", SKOS + "exactMatch", SKOS + "broadMatch"]


def obo_iri(curie):
    return OBO + curie.replace(":", "_")


def read_symp(path):
    """SYMP CURIE -> (label, [parent CURIEs]) for every non-obsolete term, and the release IRI."""
    root = ET.parse(path).getroot()
    version = root.find(OWL + "Ontology").find(OWL + "versionIRI").get(RDF + "resource")
    terms = {}
    for c in root.findall(OWL + "Class"):
        iri = c.get(RDF + "about", "")
        if not iri.startswith(OBO + "SYMP_") or c.find(OWL + "deprecated") is not None:
            continue
        parents = [p.get(RDF + "resource") for p in c.findall(RDFS + "subClassOf") if p.get(RDF + "resource")]
        terms[c.findtext(OBOINOWL + "id")] = (
            c.findtext(RDFS + "label"),
            [p[len(OBO):].replace("_", ":") for p in parents if p.startswith(OBO + "SYMP_")],
        )
    return terms, version


def read_hp(path):
    """HPO CURIE -> label for every non-obsolete term, and the release IRI."""
    terms, version, term = {}, None, None
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith("data-version: "):
            version = f"{OBO}{line[len('data-version: '):]}/hp.owl"
        elif line.startswith("["):
            term = {} if line == "[Term]" else None
        elif term is not None and line.startswith("id: "):
            term["id"] = line[4:]
        elif term is not None and line.startswith("name: "):
            terms[term["id"]] = line[6:]
        elif term is not None and line == "is_obsolete: true":
            del terms[term["id"]]
    return terms, version


def linked_terms(symptoms_root):
    """(SYMP CURIEs, HP CURIEs) that any class names by rdfs:subClassOf, skos:exactMatch or skos:broadMatch."""
    symp, hp = set(), set()
    for cls in symptoms_root.findall(OWL + "Class"):
        for tag in LINKS:
            for link in cls.findall(tag):
                iri = link.get(RDF + "resource", "")
                for prefix, found in ((OBO + "SYMP_", symp), (OBO + "HP_", hp)):
                    if iri.startswith(prefix):
                        found.add(iri[len(OBO):].replace("_", ":"))
    return symp, hp


def literal(tag, text):
    return f"    <{tag}>{escape(text)}</{tag}>\n"


def resource(tag, iri):
    return f"    <{tag} rdf:resource={quoteattr(iri)}/>\n"


def write_symp_slice(curies, symp, version):
    """A class per given SYMP term and each of its ancestors, with label, id and SYMP parents."""
    needed, stack = set(), list(curies)
    while stack:
        curie = stack.pop()
        if curie not in needed:
            needed.add(curie)
            stack.extend(symp[curie][1])

    out = [
        '<?xml version="1.0"?>\n'
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n'
        '         xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"\n'
        '         xmlns:owl="http://www.w3.org/2002/07/owl#"\n'
        '         xmlns:oboInOwl="http://www.geneontology.org/formats/oboInOwl#"\n'
        '         xmlns:dc="http://purl.org/dc/elements/1.1/"\n'
        f'         xml:base="{SLICE_IRI}">\n\n'
        f'<owl:Ontology rdf:about="{SLICE_IRI}">\n'
        "    <rdfs:comment>SYMP terms ARI symptom classes link to, with their is_a ancestors. "
        "Generated by notebook/symptom-mapping/build_symp_import.py; do not edit by hand.</rdfs:comment>\n"
        + resource("dc:source", version)
        + "</owl:Ontology>\n\n"
        '<owl:AnnotationProperty rdf:about="http://purl.org/dc/elements/1.1/source"/>\n'
        '<owl:AnnotationProperty rdf:about="http://www.geneontology.org/formats/oboInOwl#id"/>\n\n'
    ]
    for curie in sorted(needed):
        out.append(f"<owl:Class rdf:about={quoteattr(obo_iri(curie))}>\n")
        out.append(literal("rdfs:label", symp[curie][0]))
        out.append(literal("oboInOwl:id", curie))
        out.extend(resource("rdfs:subClassOf", obo_iri(p)) for p in symp[curie][1])
        out.append("</owl:Class>\n\n")
    out.append("</rdf:RDF>\n")
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("".join(out))
    return len(needed)


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    symp, symp_version = read_symp(os.path.join(sys.argv[1], "symp.owl"))
    hp, _ = read_hp(os.path.join(sys.argv[1], "hp.obo"))
    symp_linked, hp_linked = linked_terms(ET.parse(SYMPTOMS).getroot())
    problems = [f"{c}: not an active SYMP term" for c in sorted(symp_linked - symp.keys())]
    problems += [f"{c}: not an active HPO term" for c in sorted(hp_linked - hp.keys())]
    if problems:
        raise SystemExit(f"{os.path.relpath(SYMPTOMS, ROOT)} links to terms that cannot be sliced:\n  "
                         + "\n  ".join(problems))
    count = write_symp_slice(symp_linked, symp, symp_version)
    print(f"{len(symp_linked)} linked SYMP terms, {len(hp_linked)} linked HPO terms; "
          f"{count} terms in {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
