"""Propose a body-system group for each top-level symptom, and check the groups against UBERON.

The top-level ARIS classes in ontologies/ari_symptoms.owl sit directly under ari-disease#Symptom,
each with one SYMP term as its other parent. SYMP files every term under one of its top-level
categories ("skin and integumentary tissue symptom", "nervous system symptom", ...), so the category
above a symptom's SYMP parent, read from the ari_symp.owl slice, is the group proposed for it.

SYMP carries no UBERON links, so ANCHORS names by hand the UBERON terms each category covers. ARI's
anatomy classes (ontologies/ari_anatomy.owl) are UBERON terms too, and one fits a group when its
UBERON term is one of the group's terms or sits under one by is_a or part_of. A fit through a body
region (abdomen, chest, craniocervical region) gives way to a fit through a body system, and a class
with no fit of its own takes its ARI parent's.

Writes two review tables to notebook/symptom-mapping/review/:
  - body_systems.tsv: one row per top-level symptom, ordered by proposed group. A symptom whose SYMP
    parent is SYMP's root has no group to propose.
  - body_system_groups.tsv: one row per group, with its UBERON terms, how many symptoms it is
    proposed for, and the ARI anatomy classes that fit it. The last row, "(no group)", holds the
    symptoms and ARI classes that fit none.

decision and note are the review columns: a rebuild keeps the values a row already has, and stops
rather than drop a row that has them. The files are tab-separated, UTF-8 with no byte-order mark and
LF line ends, written and read with the csv module's excel-tab dialect, so a reviewer can fill
`decision` in a spreadsheet and save it as tab-delimited text. Nothing here changes the OWL.

Usage: python propose_body_systems.py <path to data/2-databases>
The database folder is not tracked in git, so pass the path of a checkout holding uberon-basic.obo.
"""
import collections, csv, os, sys
import xml.etree.ElementTree as ET

from build_symptom_report import (ARI, ARI_BASE, ARIS, DISEASE, OBO, OBOINOWL, OWL, RDF, RDFS, ROOT,
                                  SYMP_SLICE, SYMPTOMS, curie)

sys.path.insert(0, os.path.join(ROOT, "notebook", "uberon-mapping"))
from build_uberon_import import ANATOMY, read_uberon

REVIEW_DIR = os.path.join(ROOT, "notebook", "symptom-mapping", "review")
SYMPTOM_COLUMNS = ["symptom_id", "symptom", "diseases", "children", "symp_parent", "proposed_group", "decision", "note"]
GROUP_COLUMNS = ["group", "symp_id", "uberon", "symptoms", "ari_anatomy", "decision", "note"]
SYMP_ROOT = OBO + "SYMP_0000462"
SYMPTOM = ARI_BASE + "Symptom"
NO_GROUP = "(no group)"

# SYMP top-level category -> the UBERON terms it covers.
ANCHORS = {
    "SYMP:0000461": ["UBERON:0000916"],                    # abdominal symptom: abdomen
    "SYMP:0000528": ["UBERON:0004535"],                    # cardiovascular system
    "SYMP:0000459": ["UBERON:0001007"],                    # digestive system
    # head and neck: craniocervical region, and eye. SYMP files eye symptoms under head symptom, but
    # ARI's Eye is UBERON's general eye term, which UBERON places only in the visual system.
    "SYMP:0000597": ["UBERON:0007811", "UBERON:0000970"],
    # hemic and immune system: UBERON's hemolymphoid system (hematopoietic and lymphoid) does not hold
    # its immune system, so both are named.
    "SYMP:0017795": ["UBERON:0002193", "UBERON:0002405"],
    "SYMP:0000891": ["UBERON:0002204"],                    # musculoskeletal system
    "SYMP:0000480": ["UBERON:0001016"],                    # nervous system
    "SYMP:0000196": ["UBERON:0000990"],                    # reproductive system
    "SYMP:0000514": ["UBERON:0001004", "UBERON:0001443"],  # respiratory system and chest
    "SYMP:0000488": ["UBERON:0002416"],                    # skin and integumentary tissue: integumental system
    "SYMP:0000486": ["UBERON:0001008"],                    # urinary system: renal system
    # Three categories name no anatomy. ARI's Systemic and Metabolic System have no UBERON term
    # either (ARI_NoConcept "no term"), and NO_TERM pairs them with the matching category.
    "SYMP:0000567": [],                                     # general symptom
    "SYMP:0000410": [],                                     # neurological and physiological symptom
    "SYMP:0000473": [],                                     # nutrition, metabolism, and development symptom
}
NO_TERM = {"Systemic": "SYMP:0000567", "Metabolic System": "SYMP:0000473"}
# SYMP has no endocrine category, and ARI's anatomy holds the endocrine system and its glands.
ADDED = {"endocrine system symptom": ["UBERON:0000949"]}
REGIONS = {"UBERON:0000916", "UBERON:0001443", "UBERON:0007811"}


def read_symp():
    """SYMP IRI -> (label, parent IRIs), from the ari_symp.owl slice."""
    root = ET.parse(SYMP_SLICE).getroot()
    return {c.get(RDF + "about"): (c.findtext(RDFS + "label"),
                                   [p.get(RDF + "resource") for p in c.findall(RDFS + "subClassOf")])
            for c in root.findall(OWL + "Class")}


def categories(symp, iri):
    """The SYMP top-level categories above a SYMP term: the ancestors whose parent is SYMP's root."""
    if iri == SYMP_ROOT:
        return set()
    if SYMP_ROOT in symp[iri][1]:
        return {iri}
    return set().union(*(categories(symp, p) for p in symp[iri][1]))


def disease_counts():
    """ARIS class IRI -> number of diseases that list a Symptom individual linked to it."""
    root = ET.parse(DISEASE).getroot()
    concept = {ind.get(RDF + "about"): ind.find(ARI + "sharedConcept").get(RDF + "resource")
               for ind in root.findall(OWL + "NamedIndividual") if ind.find(ARI + "sharedConcept") is not None}
    diseases = collections.defaultdict(set)
    for el in root:
        for ref in el.findall(ARI + "hasSymptom"):
            target = concept.get(ref.get(RDF + "resource"))
            if target:
                diseases[target].add(el.findtext(ARI + "ARI_ID"))
    return {iri: len(ids) for iri, ids in diseases.items()}


def above(uid, uberon):
    """A UBERON term and every term above it by is_a or part_of."""
    out, todo = {uid}, [uid]
    while todo:
        term = uberon[todo.pop()]
        for parent in term["is_a"] + term["part_of"]:
            if parent not in out:
                out.add(parent)
                todo.append(parent)
    return out


def anatomy_fits(uberon, anchors):
    """ARI anatomy class label -> (the groups it fits, how): by its UBERON term, by NO_TERM, or by its ARI parent."""
    root = ET.parse(ANATOMY).getroot()
    classes = {}
    for c in root.findall(OWL + "Class"):
        parents = [p.get(RDF + "resource") for p in c.findall(RDFS + "subClassOf")]
        classes[c.get(RDF + "about")] = (c.findtext(RDFS + "label"), c.findtext(ARI + "ARI_ID"),
                                         [p for p in parents if p.startswith(ARI_BASE)])
    fits = {}

    def fit(iri):
        label, uid, parents = classes[iri]
        if label in fits:
            return fits[label]
        groups, how = [], ""
        if uid:
            terms = above(uid, uberon)
            hits = {g: [a for a in ids if a in terms] for g, ids in anchors.items()}
            groups = [g for g, hit in hits.items() if hit]
            systems = [g for g in groups if any(a not in REGIONS for a in hits[g])]
            groups, how = systems or groups, uid
        elif label in NO_TERM:
            groups, how = [NO_TERM[label]], "no UBERON term"
        if not groups:
            for parent in parents:
                if parent in classes:
                    groups, _ = fit(parent)
                    if groups:
                        how = f"via {classes[parent][0]}"
                        break
        fits[label] = (groups, how or "no UBERON term")
        return fits[label]

    for iri in classes:
        fit(iri)
    return fits


def read_review(path, columns):
    """Key (first column) -> the review columns of the table as it stands, or {} before the first build."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        lines = list(csv.reader(f, dialect="excel-tab"))
    if not lines or lines[0] != columns:
        raise SystemExit(f"{path}: the header is not {columns}")
    return {v[0]: v[-2:] for v in lines[1:]}


def write_review(path, columns, rows):
    """Write rows (dicts) after carrying over the decision and note a row already has."""
    review = read_review(path, columns)
    for row in rows:
        row["decision"], row["note"] = review.pop(row[columns[0]], ["", ""])
    dropped = [key for key, values in review.items() if any(values)]
    if dropped:
        raise SystemExit(f"{os.path.relpath(path, ROOT)}: reviewed rows no longer proposed: {dropped}")
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, dialect="excel-tab", lineterminator="\n")
        writer.writerow(columns)
        for row in rows:
            values = [row[c] for c in columns]
            for column, value in zip(columns, values):
                if any(c in value for c in "\t\r\n"):
                    raise SystemExit(f"{row[columns[0]]}: {column} has a tab or a line break")
            writer.writerow(values)


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    uberon, _ = read_uberon(os.path.join(sys.argv[1], "uberon-basic.obo"))
    symp = read_symp()
    top = {curie(i): label for i, (label, parents) in symp.items() if SYMP_ROOT in parents}
    if set(top) != set(ANCHORS):
        raise SystemExit(f"SYMP's top-level categories changed: {sorted(set(top) ^ set(ANCHORS))}")
    for uid in [a for ids in list(ANCHORS.values()) + list(ADDED.values()) for a in ids]:
        if uid not in uberon or uberon[uid]["obsolete"]:
            raise SystemExit(f"{uid} is missing or obsolete in uberon-basic.obo")

    counts = disease_counts()
    classes = [c for c in ET.parse(SYMPTOMS).getroot().findall(OWL + "Class")
               if c.get(RDF + "about").startswith(ARIS)]
    children = collections.Counter(p.get(RDF + "resource") for c in classes for p in c.findall(RDFS + "subClassOf"))
    symptoms = []
    for cls in classes:
        parents = [p.get(RDF + "resource") for p in cls.findall(RDFS + "subClassOf")]
        if SYMPTOM not in parents:
            continue
        symp_parents = [p for p in parents if p.startswith(OBO + "SYMP_")]
        if len(symp_parents) != 1:
            raise SystemExit(f"{cls.get(RDF + 'about')} has {len(symp_parents)} SYMP parents, expected one")
        groups = categories(symp, symp_parents[0])
        symptoms.append(dict(symptom_id=cls.findtext(OBOINOWL + "id"), symptom=cls.findtext(RDFS + "label").strip(),
                             diseases=str(counts.get(cls.get(RDF + "about"), 0)),
                             children=str(children[cls.get(RDF + "about")]),
                             symp_parent=f"{curie(symp_parents[0])} {symp[symp_parents[0]][0]}",
                             proposed_group="; ".join(sorted(symp[g][0] for g in groups))))
    symptoms.sort(key=lambda r: (r["proposed_group"] == "", r["proposed_group"], r["symptom"].casefold()))

    anchors = dict(ANCHORS, **ADDED)
    label = dict(top, **{g: g for g in ADDED})
    fits = anatomy_fits(uberon, anchors)
    members = collections.defaultdict(list)
    for name, (groups, how) in sorted(fits.items()):
        for g in groups or [NO_GROUP]:
            members[g].append(f"{name} ({how})")
    proposed = collections.Counter(r["proposed_group"] or NO_GROUP for r in symptoms)
    groups = [dict(group=label[g], symp_id="" if g in ADDED else g,
                   uberon="; ".join(f"{a} {uberon[a]['name']}" for a in anchors[g]),
                   symptoms=str(proposed[label[g]]), ari_anatomy="; ".join(members[g]))
              for g in sorted(anchors, key=lambda g: label[g])]
    groups.append(dict(group=NO_GROUP, symp_id="", uberon="", symptoms=str(proposed[NO_GROUP]),
                       ari_anatomy="; ".join(members[NO_GROUP])))

    os.makedirs(REVIEW_DIR, exist_ok=True)
    write_review(os.path.join(REVIEW_DIR, "body_systems.tsv"), SYMPTOM_COLUMNS, symptoms)
    write_review(os.path.join(REVIEW_DIR, "body_system_groups.tsv"), GROUP_COLUMNS, groups)
    print(f"{len(symptoms)} top-level symptoms in {len(groups)} groups -> {os.path.relpath(REVIEW_DIR, ROOT)}")
    for g in groups:
        print(f"  {g['symptoms']:>4} {g['group']}: {g['ari_anatomy'] or '-'}")


if __name__ == "__main__":
    main()
