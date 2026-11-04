"""Take the symptoms of a disease's subtypes off the disease, keeping them for the subtype.

The registry site lists, under some diseases, the symptoms of a subtype beneath a heading that names
it ("Inflammatory EBA:", "Lofgren's syndrome:"). Report 4's Symptoms sheet keeps that layout. A
disease lists (hasSymptom) only the symptoms of the disease itself, so for each heading in
SUBTYPE_HEADINGS, every symptom it heads in the sheet (up to the next heading or body-system row):

  - is no longer listed by the disease;
  - keeps its Symptom individual, whose IRI (Sym_<ARI ID digits>_<n>) still names the disease;
  - carries symptomOfSubtype, the subtype's name, so the subtype can list it if it is added as a
    disease of its own.

An entry the sheet marks "not a symptom" is left as it is: report 13 reviews those. A rerun finds
the symptoms already moved and changes nothing. Run tools/format-owl.sh on ontologies/ari_disease.owl
afterwards, then build_symptom_report.py.

Usage: python park_subtype_symptoms.py
"""
import collections, os, re, sys
import xml.etree.ElementTree as ET

import openpyxl

from build_symptom_report import ARI, ARI_BASE, DISEASE, NOT_A_SYMPTOM, OWL, RDF, RDFS, REPORT, ROOT

sys.path.insert(0, os.path.join(ROOT, "notebook", "biomarker-concepts"))
from model import _declared_namespaces, _serialise  # noqa: E402

# (ARI ID, Symptoms-sheet heading) -> the name of the subtype it heads.
SUBTYPE_HEADINGS = {
    ("ARI:0001001", "Non-inflammatory EBA:"): "Non-inflammatory EBA",
    ("ARI:0001001", "Inflammatory EBA:"): "Inflammatory EBA",
    ("ARI:0001001", "Mucous membrane EBA:"): "Mucous membrane EBA",
    ("ARI:0001065", "Symptoms caused by the bacterium borrelia mayonii:"): "Borrelia mayonii infection",
    ("ARI:0001154", "Pemphigus vulgaris:"): "Pemphigus vulgaris",
    ("ARI:0001154", "Pemphigus foliaceus:"): "Pemphigus foliaceus",
    ("ARI:0001186", "Lofgren's syndrome:"): "Lofgren's syndrome",
}
SUBTYPE = ARI + "symptomOfSubtype"
SYMPTOM_IRI = re.compile(r"#Sym_(\d{7})_\d+$")


def subtype_entries():
    """[(ARI ID, subtype name, entry)] for each symptom the sheet lists under a subtype heading."""
    ws = openpyxl.load_workbook(REPORT, read_only=True)["Symptoms"]
    rows = ws.iter_rows(values_only=True)
    header = list(next(rows))
    col = {name: header.index(name) for name in ("ARI ID", "symptom", "latin", "SYMP Mapping")}
    by_disease = collections.defaultdict(list)
    for r in rows:
        r = list(r) + [None] * (len(header) - len(r))
        if r[col["symptom"]]:
            by_disease[r[col["ARI ID"]]].append((r[col["symptom"]].strip(), r[col["latin"]] == "cat",
                                                 r[col["SYMP Mapping"]] == NOT_A_SYMPTOM))
    found, seen = [], set()
    for ari_id, items in by_disease.items():
        subtype = None
        for entry, is_body_system, not_a_symptom in items:
            if (ari_id, entry) in SUBTYPE_HEADINGS:
                subtype = SUBTYPE_HEADINGS[ari_id, entry]
                seen.add((ari_id, entry))
            elif is_body_system or (not_a_symptom and entry.endswith(":")):
                subtype = None
            elif subtype and not not_a_symptom:
                found.append((ari_id, subtype, entry))
    missing = set(SUBTYPE_HEADINGS) - seen
    if missing:
        raise SystemExit(f"Subtype headings not in the Symptoms sheet: {sorted(missing)}")
    return found


def main():
    entries = subtype_entries()
    declared = _declared_namespaces(DISEASE)
    root = ET.parse(DISEASE).getroot()
    diseases = {el.findtext(ARI + "ARI_ID"): el for el in root if el.findtext(ARI + "ARI_ID")}
    symptoms = collections.defaultdict(list)  # (ARI ID, casefolded label) -> [Symptom individual]
    for ind in root.findall(OWL + "NamedIndividual"):
        m = SYMPTOM_IRI.search(ind.get(RDF + "about"))
        if m and ind.findtext(RDFS + "label"):
            symptoms[f"ARI:{m.group(1)}", ind.findtext(RDFS + "label").strip().casefold()].append(ind)
    listed_by = collections.defaultdict(set)
    for el in root:
        for ref in el.findall(ARI + "hasSymptom"):
            listed_by[ref.get(RDF + "resource")].add(el.findtext(ARI + "ARI_ID"))

    moved = 0
    for ari_id, subtype, entry in entries:
        found = symptoms[ari_id, entry.casefold()]
        if len(found) != 1:
            raise SystemExit(f"{ari_id} {entry!r}: {len(found)} Symptom individuals carry this label")
        ind = found[0]
        iri = ind.get(RDF + "about")
        if listed_by[iri] - {ari_id}:
            raise SystemExit(f"{iri} is also listed by {sorted(listed_by[iri] - {ari_id})}")
        names = [el.text for el in ind.findall(SUBTYPE)]
        if names not in ([], [subtype]):
            raise SystemExit(f"{iri} already names subtype {names}, not {subtype!r}")
        refs = [ref for ref in diseases[ari_id].findall(ARI + "hasSymptom") if ref.get(RDF + "resource") == iri]
        for ref in refs:
            diseases[ari_id].remove(ref)
        if not names:
            ET.SubElement(ind, SUBTYPE).text = subtype
        if refs or not names:
            moved += 1
            print(f"  {ari_id} {subtype}: {entry} ({iri[len(ARI_BASE):]})")
    with open(DISEASE, "w", encoding="utf-8", newline="\n") as f:
        f.write(_serialise(root, declared))
    print(f"{len(entries)} subtype symptoms, {moved} moved off their disease -> {os.path.relpath(DISEASE, ROOT)}")


if __name__ == "__main__":
    main()
