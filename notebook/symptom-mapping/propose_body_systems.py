"""Propose a body-system group for each top-level symptom: notebook/symptom-mapping/review/body_systems.tsv.

The top-level ARIS classes in ontologies/ari_symptoms.owl sit directly under ari-disease#Symptom,
each with one SYMP term as its other parent. SYMP files every term under one of its top-level
categories ("skin and integumentary tissue symptom", "nervous system symptom", ...), so the category
above a symptom's SYMP parent, read from the ari_symp.owl slice, is the group proposed for it. A
symptom whose SYMP parent is SYMP's root has no group to propose; one whose parent reaches several
categories gets them all, for the reviewer to choose.

One row per top-level symptom, ordered by proposed group. decision and note are the review columns:
a rebuild keeps the values a row already has, and stops rather than drop a row that has them. The
file is tab-separated, UTF-8 with no byte-order mark and LF line ends, written and read with the csv
module's excel-tab dialect, so a reviewer can fill `decision` in a spreadsheet and save it as
tab-delimited text. Nothing here changes the OWL.

Usage: python propose_body_systems.py
"""
import collections, csv, os
import xml.etree.ElementTree as ET

from build_symptom_report import (ARI, ARI_BASE, ARIS, DISEASE, OBO, OBOINOWL, OWL, RDF, RDFS, ROOT,
                                  SYMP_SLICE, SYMPTOMS, curie)

REVIEW = os.path.join(ROOT, "notebook", "symptom-mapping", "review", "body_systems.tsv")
COLUMNS = ["symptom_id", "symptom", "diseases", "children", "symp_parent", "proposed_group", "decision", "note"]
REVIEW_COLUMNS = COLUMNS[-2:]
SYMP_ROOT = OBO + "SYMP_0000462"
SYMPTOM = ARI_BASE + "Symptom"


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


def read_review():
    """symptom_id -> the review columns of the table as it stands, or {} before the first build."""
    if not os.path.exists(REVIEW):
        return {}
    with open(REVIEW, encoding="utf-8-sig", newline="") as f:
        lines = list(csv.reader(f, dialect="excel-tab"))
    if not lines or lines[0] != COLUMNS:
        raise SystemExit(f"{REVIEW}: the header is not {COLUMNS}")
    return {v[0]: v[-len(REVIEW_COLUMNS):] for v in lines[1:]}


def main():
    symp = read_symp()
    counts = disease_counts()
    classes = [c for c in ET.parse(SYMPTOMS).getroot().findall(OWL + "Class")
               if c.get(RDF + "about").startswith(ARIS)]
    children = collections.Counter(p.get(RDF + "resource") for c in classes for p in c.findall(RDFS + "subClassOf"))
    rows = []
    for cls in classes:
        parents = [p.get(RDF + "resource") for p in cls.findall(RDFS + "subClassOf")]
        if SYMPTOM not in parents:
            continue
        symp_parents = [p for p in parents if p.startswith(OBO + "SYMP_")]
        if len(symp_parents) != 1:
            raise SystemExit(f"{cls.get(RDF + 'about')} has {len(symp_parents)} SYMP parents, expected one")
        groups = categories(symp, symp_parents[0])
        rows.append(dict(symptom_id=cls.findtext(OBOINOWL + "id"), symptom=cls.findtext(RDFS + "label").strip(),
                         diseases=str(counts.get(cls.get(RDF + "about"), 0)),
                         children=str(children[cls.get(RDF + "about")]),
                         symp_parent=f"{curie(symp_parents[0])} {symp[symp_parents[0]][0]}",
                         proposed_group="; ".join(sorted(symp[g][0] for g in groups))))

    review = read_review()
    for row in rows:
        row.update(zip(REVIEW_COLUMNS, review.pop(row["symptom_id"], [""] * len(REVIEW_COLUMNS))))
    dropped = [key for key, values in review.items() if any(values)]
    if dropped:
        raise SystemExit(f"Reviewed rows no longer top-level symptoms: {dropped}")

    rows.sort(key=lambda r: (r["proposed_group"] == "", r["proposed_group"], r["symptom"].casefold()))
    os.makedirs(os.path.dirname(REVIEW), exist_ok=True)
    with open(REVIEW, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, dialect="excel-tab", lineterminator="\n")
        writer.writerow(COLUMNS)
        for row in rows:
            values = [row[c] for c in COLUMNS]
            for column, value in zip(COLUMNS, values):
                if any(c in value for c in "\t\r\n"):
                    raise SystemExit(f"{row['symptom_id']}: {column} has a tab or a line break")
            writer.writerow(values)
    by_group = collections.Counter(r["proposed_group"] or "(none)" for r in rows)
    print(f"{len(rows)} top-level symptoms in {len(by_group)} groups -> {os.path.relpath(REVIEW, ROOT)}")
    for group, n in by_group.most_common():
        print(f"  {n:4d} {group}")


if __name__ == "__main__":
    main()
