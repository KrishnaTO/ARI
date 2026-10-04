"""The ARI diseases to ground, with their current names, read from the ontology.

`ontologies/ari_t1d.owl` is where curators maintain names and synonyms; a synonym
withdrawn there (`ARI_SynonymWithdrawn`) has already left `ARI_Synonym`. Retired
diseases (`ARI_Obsolete` true) are skipped. Parsing reuses the mapping validator's
reader so both see the same entities.
"""
import sys
from pathlib import Path
from xml.etree import ElementTree

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / ".github" / "scripts"))
from validate_mappings import ONTOLOGY_PATH, parse_ontology  # noqa: E402

RDF_RESOURCE = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource"
DISEASE_IRI = "https://diseases.autoimmuneregistry.org/disease/ARI_"


def load():
    """[(ari_id, preferred name, [synonyms], [SNOMED codes])], ordered by ARI id."""
    text = (REPO / ONTOLOGY_PATH).read_text(encoding="utf-8")
    out = []
    for ari_id, d in sorted(parse_ontology(text).items()):
        values = lambda prop: [v for v, _ in d.annotations.get(prop, []) if v]
        if "true" in values("ARI_Obsolete"):
            continue
        snomed = [c.strip() for v in values("ARI_SNOMED") for c in v.split(",") if c.strip()]
        out.append((ari_id, d.label, values("ARI_Synonym"), snomed))
    return out


def parents():
    """{ari_id: {parent ari_id}} from each disease's `hasParentDisease` links."""
    root = ElementTree.parse(REPO / ONTOLOGY_PATH).getroot()
    out = {}
    for entity in root:
        children = {}
        for child in entity:
            children.setdefault(child.tag.rsplit("}", 1)[-1], []).append(child)
        ids = children.get("ARI_ID")
        links = children.get("hasParentDisease")
        if not ids or not links:
            continue
        found = set()
        for link in links:
            iri = link.get(RDF_RESOURCE)
            if not iri.startswith(DISEASE_IRI):
                raise ValueError("%s hasParentDisease %r is not an ARI disease IRI" % (ids[0].text, iri))
            found.add("ARI:" + iri[len(DISEASE_IRI):])
        out[ids[0].text] = found
    return out
