"""Link ARI's tissue and system classes to UBERON and write the UBERON import slice.

uberon_mapping.tsv is hand-curated: one row per ARI class under MulticellularAnatomicalStructure
in ontologies/ari_t1d.owl (the classes the targetsTissue individuals are typed by). Mapping is:
  exact       - the UBERON term has the same meaning
  no term     - UBERON has no term for it (Systemic, Metabolic System, All); stays an ARI class
  not linked  - deliberately left unlinked; the Note says why

Writes:
  - ontologies/ari_uberon.owl: every mapped UBERON term and all its is_a ancestors, with
    UBERON's label, definition and is_a parents (a MIREOT-style slice of the given release)
  - ontologies/ari_t1d.owl: an owl:imports of the slice, and on each exact class an
    rdfs:subClassOf to its UBERON term plus ARI_ID set to the UBERON CURIE

The link is rdfs:subClassOf, not owl:equivalentClass, because ARI's own class tree uses
subClassOf for "part of" (Pancreas under Endocrine system, Islet under Pancreas) and puts Blood
and the systems under multicellular anatomical structure. An equivalence would push those claims
onto the UBERON terms themselves.

Re-running is safe: links already in place are left alone.

Usage: python build_uberon_import.py <path to data/2-databases>
The database folder is not tracked in git, so pass the path of a checkout holding
uberon-basic.obo (http://purl.obolibrary.org/obo/uberon/basic.obo).
"""
import csv, os, re, sys
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ONTOLOGY = os.path.join(ROOT, "ontologies", "ari_t1d.owl")
SLICE = os.path.join(ROOT, "ontologies", "ari_uberon.owl")
MAPPING = os.path.join(HERE, "uberon_mapping.tsv")

SLICE_IRI = "http://www.aurint.org/ontologies/ari_uberon"
ARI_ONTOLOGY_IRI = "http://www.aurint.org/ontologies/ari-disease"
OBO = "http://purl.obolibrary.org/obo/"
MAPPINGS = {"exact", "no term", "not linked"}
XSD_STRING = "http://www.w3.org/2001/XMLSchema#string"
ARI_BASE = ARI_ONTOLOGY_IRI + "#"
ARI_ID = "{%s}ARI_ID" % ARI_BASE
RDF = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
RDFS = "{http://www.w3.org/2000/01/rdf-schema#}"
OWL = "{http://www.w3.org/2002/07/owl#}"


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


def read_mapping(terms, ontology_classes):
    with open(MAPPING, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    errors = []
    names = [r["ARI Class"] for r in rows]
    for name in set(names):
        if names.count(name) > 1:
            errors.append(f"{name}: more than one row")
    for name in sorted(set(ontology_classes) - set(names)):
        errors.append(f"{name}: tissue class in ari_t1d.owl has no row in uberon_mapping.tsv")
    for r in rows:
        name, mapping, uid = r["ARI Class"], r["Mapping"], r["UBERON ID"]
        if name not in ontology_classes:
            errors.append(f"{name}: not a tissue class in ari_t1d.owl")
        if mapping not in MAPPINGS:
            errors.append(f"{name}: unknown Mapping {mapping!r}")
        if mapping != "exact":
            if uid:
                errors.append(f"{name}: {mapping} row has a UBERON ID")
            continue
        term = terms.get(uid)
        if term is None:
            errors.append(f"{name}: {uid} is not in UBERON")
        elif term["obsolete"]:
            errors.append(f"{name}: {uid} is obsolete in UBERON")
        elif term["name"] != r["UBERON Label"]:
            errors.append(f"{name}: {uid} is {term['name']!r} in UBERON, not {r['UBERON Label']!r}")
    if errors:
        sys.exit("uberon_mapping.tsv:\n  " + "\n  ".join(errors))
    return [r for r in rows if r["Mapping"] == "exact"]


def resolve(ref):
    """Absolute IRI of an rdf:about / rdf:resource, which may be relative to the file's xml:base."""
    return urljoin(ARI_ONTOLOGY_IRI, ref)


def ari_classes(root):
    """ARI class name -> its owl:Class element, for classes in the ari-disease namespace."""
    out = {}
    for cls in root.findall(OWL + "Class"):
        iri = resolve(cls.get(RDF + "about"))
        if iri.startswith(ARI_BASE):
            out[iri[len(ARI_BASE):]] = cls
    return out


def tissue_classes(root):
    """ARI classes under MulticellularAnatomicalStructure, including it."""
    parents = {
        name: [resolve(s.get(RDF + "resource"))[len(ARI_BASE):]
               for s in cls.findall(RDFS + "subClassOf")
               if s.get(RDF + "resource") and resolve(s.get(RDF + "resource")).startswith(ARI_BASE)]
        for name, cls in ari_classes(root).items()
    }

    def under_root(name, seen=()):
        if name == "MulticellularAnatomicalStructure":
            return True
        return any(p not in seen and under_root(p, seen + (name,)) for p in parents.get(name, []))

    return {name for name in parents if under_root(name)}


def ancestors(uid, terms):
    out, todo = set(), [uid]
    while todo:
        for parent in terms[todo.pop()]["is_a"]:
            if parent not in out:
                out.add(parent)
                todo.append(parent)
    return out


def write_slice(rows, terms, version):
    ids = set()
    for r in rows:
        ids |= {r["UBERON ID"]} | ancestors(r["UBERON ID"], terms)
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


def link_ontology(root, rows):
    header = root.find(OWL + "Ontology")
    if not any(i.get(RDF + "resource") == SLICE_IRI for i in header.findall(OWL + "imports")):
        ET.SubElement(header, OWL + "imports", {RDF + "resource": SLICE_IRI})

    classes = ari_classes(root)
    for r in rows:
        name, uid = r["ARI Class"], r["UBERON ID"]
        cls = classes[name]
        existing = [e.text.strip() for e in cls.findall(ARI_ID)]
        if existing not in ([], [uid]):
            sys.exit(f"ari_t1d.owl: {name} already has ARI_ID {existing}, not {uid}")
        if not any(s.get(RDF + "resource") == obo_iri(uid) for s in cls.findall(RDFS + "subClassOf")):
            ET.SubElement(cls, RDFS + "subClassOf", {RDF + "resource": obo_iri(uid)})
        if not existing:
            ET.SubElement(cls, ARI_ID, {RDF + "datatype": XSD_STRING}).text = uid


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    terms, version = read_uberon(os.path.join(sys.argv[1], "uberon-basic.obo"))
    # Prefixes registered so the rewrite keeps them; the pre-commit hook (tools/format-owl.sh)
    # then puts the file back in the canonical layout, so only the new links show in the diff.
    for _, (prefix, uri) in ET.iterparse(ONTOLOGY, events=["start-ns"]):
        ET.register_namespace(prefix, uri)
    tree = ET.parse(ONTOLOGY)
    rows = read_mapping(terms, tissue_classes(tree.getroot()))
    count = write_slice(rows, terms, version)
    link_ontology(tree.getroot(), rows)
    tree.write(ONTOLOGY, encoding="utf-8", xml_declaration=True)
    print(f"{len(rows)} ARI classes linked to UBERON ({version}); {count} terms in {os.path.relpath(SLICE, ROOT)}")


if __name__ == "__main__":
    main()
