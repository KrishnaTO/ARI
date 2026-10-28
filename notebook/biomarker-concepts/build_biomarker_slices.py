"""Write the four external-term slices ontologies/ari_biomarkers.owl imports.

ontologies/ari_biomarkers.owl is where ARI's biomarker classes (ARIB) link to published terms with
skos:exactMatch / closeMatch / broadMatch / narrowMatch / relatedMatch. This script reads those links and
writes one slice per source, so every external match has a label locally:

  ari_pr.owl     Protein Ontology (PR)  term, is_a ancestors, label and id
  ari_chebi.owl  ChEBI                  term, is_a ancestors, label and id
  ari_hgnc.owl   HGNC                   gene: label = symbol, IAO:0000115 = name, and id
  ari_loinc.owl  LOINC                  code: label and id; carries LOINC's licence notice

HPO links are only references (no slice), and any other target is ignored here; the validator reports it.
A source with no linked term gets an empty slice and its release file is not opened. A linked term missing
from its release stops the run, listing each one before anything is written.

Usage: python build_biomarker_slices.py <path to data/2-databases>
The database folder is not tracked in git; it must hold pro_nonreasoned.obo, chebi_lite.obo,
hgnc_complete_set.txt and loinc/LoincTable/Loinc.csv (only those a link needs). Then run
tools/format-owl.sh on the four slices to put them in the canonical layout.
"""
import os, sys
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape, quoteattr

import sources

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ONTOLOGIES = os.path.join(ROOT, "ontologies")
BIOMARKERS = os.path.join(ONTOLOGIES, "ari_biomarkers.owl")

OBO = "http://purl.obolibrary.org/obo/"
RDF = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
OWL = "{http://www.w3.org/2002/07/owl#}"
SKOS = "{http://www.w3.org/2004/02/skos/core#}"
MATCHES = [SKOS + m for m in ("exactMatch", "closeMatch", "broadMatch", "narrowMatch", "relatedMatch")]
ARIB = "http://www.aurint.org/ontologies/ari-biomarkers#ARIB_"

# source -> (IRI prefix, id prefix): IRI = IRI prefix + the id without its id prefix
FORMS = {
    "pr": (OBO + "PR_", "PR:"),
    "chebi": (OBO + "CHEBI_", "CHEBI:"),
    "hgnc": ("http://identifiers.org/hgnc/", "HGNC:"),
    "loinc": ("https://loinc.org/", ""),
}
# source -> release file under <data/2-databases>, and its reader
RELEASES = {
    "pr": ("pro_nonreasoned.obo", sources.read_pr),
    "chebi": ("chebi_lite.obo", sources.read_chebi),
    "hgnc": ("hgnc_complete_set.txt", sources.read_hgnc),
    "loinc": (os.path.join("loinc", "LoincTable", "Loinc.csv"), sources.read_loinc),
}
ANCESTORS = {"pr", "chebi"}  # sources whose slice also holds the is_a ancestors
NAMES = {"pr": "Protein Ontology (PR)", "chebi": "ChEBI", "hgnc": "HGNC", "loinc": "LOINC"}

LOINC_NOTICE = (
    "This material contains content from LOINC (http://loinc.org). LOINC is copyright © Regenstrief "
    "Institute, Inc. and the Logical Observation Identifiers Names and Codes (LOINC) Committee and is "
    "available at no cost under the license at http://loinc.org/license. LOINC® is a registered "
    "United States trademark of Regenstrief Institute, Inc."
)


def slice_iri(source):
    return f"http://www.aurint.org/ontologies/ari_{source}"


def to_iri(source, term_id):
    iri_prefix, id_prefix = FORMS[source]
    return iri_prefix + term_id.removeprefix(id_prefix)


def to_id(source, iri):
    iri_prefix, id_prefix = FORMS[source]
    return id_prefix + iri.removeprefix(iri_prefix)


def referenced_terms(biomarkers_text):
    """source -> external IRIs that any ARIB class names with a skos:*Match. Other targets are ignored."""
    found = {source: set() for source in FORMS}
    for cls in ET.fromstring(biomarkers_text).findall(OWL + "Class"):
        if not cls.get(RDF + "about", "").startswith(ARIB):
            continue
        for tag in MATCHES:
            for match in cls.findall(tag):
                iri = match.get(RDF + "resource", "")
                for source, (iri_prefix, _) in FORMS.items():
                    if iri.startswith(iri_prefix):
                        found[source].add(iri)
    return found


def missing_iris(source, iris, terms):
    """The referenced IRIs whose term is not in the release, sorted."""
    return sorted(iri for iri in iris if to_id(source, iri) not in terms)


def needed_ids(source, iris, terms):
    """The ids of the referenced terms, and for PR and ChEBI all their is_a ancestors in the release."""
    needed, stack = set(), [to_id(source, iri) for iri in iris]
    while stack:
        term_id = stack.pop()
        if term_id in needed:
            continue
        needed.add(term_id)
        if source in ANCESTORS:
            stack.extend(p for p in terms[term_id].parents if p in terms)
    return needed


def literal(tag, text):
    return f"    <{tag}>{escape(text)}</{tag}>\n"


def resource(tag, iri):
    return f"    <{tag} rdf:resource={quoteattr(iri)}/>\n"


def write_slice(source, iris, terms, out_path):
    """Write the slice for one source: a class per referenced term (and ancestor), with label and id."""
    absent = missing_iris(source, iris, terms)
    if absent:
        raise SystemExit(f"{NAMES[source]} terms linked from {os.path.relpath(BIOMARKERS, ROOT)} are not in "
                         "the release:\n  " + "\n  ".join(absent))
    needed = sorted(needed_ids(source, iris, terms))

    comment = f"{NAMES[source]} terms ARI biomarker classes link to"
    comment += ", with their is_a ancestors" if source in ANCESTORS else ""
    comment += ". Generated by notebook/biomarker-concepts/build_biomarker_slices.py; do not edit by hand."
    if source in ANCESTORS:
        releases = sorted({terms[i].release for i in needed if terms[i].release})
        if releases:
            comment += f" Release {', '.join(releases)}."

    out = [
        '<?xml version="1.0"?>\n'
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n'
        '         xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"\n'
        '         xmlns:owl="http://www.w3.org/2002/07/owl#"\n'
        '         xmlns:obo="http://purl.obolibrary.org/obo/"\n'
        '         xmlns:oboInOwl="http://www.geneontology.org/formats/oboInOwl#"\n'
        f'         xml:base="{slice_iri(source)}">\n\n'
        f'<owl:Ontology rdf:about="{slice_iri(source)}">\n'
        + literal("rdfs:comment", comment)
        + (literal("rdfs:comment", LOINC_NOTICE) if source == "loinc" else "")
        + "</owl:Ontology>\n\n"
        '<owl:AnnotationProperty rdf:about="http://www.geneontology.org/formats/oboInOwl#id"/>\n'
    ]
    if source == "hgnc":
        out.append(f'<owl:AnnotationProperty rdf:about="{OBO}IAO_0000115"/>\n')
    out.append("\n")
    for term_id in needed:
        term = terms[term_id]
        out.append(f"<owl:Class rdf:about={quoteattr(to_iri(source, term_id))}>\n")
        if source == "hgnc":
            out.append(literal("rdfs:label", term.symbol))
            out.append(literal("obo:IAO_0000115", term.name))
        else:
            out.append(literal("rdfs:label", term.label))
        out.append(literal("oboInOwl:id", term_id))
        if source in ANCESTORS:
            out.extend(resource("rdfs:subClassOf", to_iri(source, p)) for p in term.parents if p in terms)
        out.append("</owl:Class>\n\n")
    out.append("</rdf:RDF>\n")
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("".join(out))
    return len(needed)


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    with open(BIOMARKERS, encoding="utf-8") as f:
        referenced = referenced_terms(f.read())
    releases, problems = {}, []
    for source, iris in referenced.items():
        if not iris:
            releases[source] = {}
            continue
        name, reader = RELEASES[source]
        releases[source] = reader(os.path.join(sys.argv[1], name))
        problems += missing_iris(source, iris, releases[source])
    if problems:
        raise SystemExit(f"{os.path.relpath(BIOMARKERS, ROOT)} links to terms that are not in their release:\n  "
                         + "\n  ".join(problems))
    for source, iris in referenced.items():
        out_path = os.path.join(ONTOLOGIES, f"ari_{source}.owl")
        count = write_slice(source, iris, releases[source], out_path)
        print(f"{source}: {len(iris)} linked terms; {count} terms in {os.path.relpath(out_path, ROOT)}")


if __name__ == "__main__":
    main()
