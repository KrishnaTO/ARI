"""Robustly parse local doid.owl into records (label, synonyms, xrefs, deprecated).
Uses ElementTree (handles nested anonymous owl:Class correctly, unlike regex)."""
import xml.etree.ElementTree as ET, json, os

DOID = "/sessions/zen-keen-curie/mnt/ARI/data/2-databases/doid.owl"
OUT = "/sessions/zen-keen-curie/mnt/ARI/notebook/ari-grounding/doid_records.json"

NS = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "obo": "http://purl.obolibrary.org/obo/",
    "oboInOwl": "http://www.geneontology.org/formats/oboInOwl#",
}
ABOUT = f"{{{NS['rdf']}}}about"
RES = f"{{{NS['rdf']}}}resource"

def tag(p, t): return f"{{{NS[p]}}}{t}"

tree = ET.parse(DOID)
root = tree.getroot()
records = {}
for cls in root.findall(tag("owl", "Class")):
    about = cls.get(ABOUT, "")
    if "/DOID_" not in about:
        continue
    doid_id = "DOID:" + about.rsplit("DOID_", 1)[1]
    label_el = cls.find(tag("rdfs", "label"))
    label = label_el.text if label_el is not None and label_el.text else ""
    exact = [e.text for e in cls.findall(tag("oboInOwl", "hasExactSynonym")) if e.text]
    related = [e.text for e in cls.findall(tag("oboInOwl", "hasRelatedSynonym")) if e.text]
    narrow = [e.text for e in cls.findall(tag("oboInOwl", "hasNarrowSynonym")) if e.text]
    broad = [e.text for e in cls.findall(tag("oboInOwl", "hasBroadSynonym")) if e.text]
    dep_el = cls.find(tag("owl", "deprecated"))
    deprecated = dep_el is not None and (dep_el.text or "").strip().lower() == "true"
    xrefs = [e.text for e in cls.findall(tag("oboInOwl", "hasDbXref")) if e.text]
    snomed = [x.split(":")[-1] for x in xrefs if x.startswith("SNOMED")]
    defn_el = cls.find(tag("obo", "IAO_0000115"))
    records[doid_id] = {
        "doid": doid_id, "label": label,
        "exact_syn": exact, "related_syn": related, "narrow_syn": narrow + broad,
        "deprecated": deprecated, "snomed": snomed, "xrefs": xrefs,
        "definition": defn_el.text if defn_el is not None and defn_el.text else "",
    }

json.dump(records, open(OUT, "w"))
print("classes parsed:", len(records))
print("with label:", sum(1 for r in records.values() if r["label"]))
print("deprecated:", sum(1 for r in records.values() if r["deprecated"]))
# sanity
for probe in ["alopecia areata", "ankylosing spondylitis", "acquired hemophilia"]:
    hit = [k for k,r in records.items() if r["label"].lower()==probe]
    print(f"  probe {probe!r}:", hit[:2])
