"""Write data/4-reports/13_Non_Symptom_Review.tsv: every entry judged "not a symptom", for review.

Two places hold such entries:
  - ontologies/ari_disease.owl: Symptom individuals with ARI_NoConcept "not a symptom". A disease
    that lists one with hasSymptom names it; an unlisted one names its disease in its IRI,
    Sym_<ARI ID digits>_<n>.
  - the Symptoms sheet of data/4-reports/4_Additional_Info_Index.xlsx: rows whose SYMP Mapping is
    "not a symptom" (written by build_symptom_report.py, or kept from the sheet for a string the
    ontology does not hold). Most of these are headings such as "Early stages:".

Headings that name a subtype of the disease (SUBTYPE_HEADINGS, from park_subtype_symptoms.py) are
left out: a subtype is neither a symptom nor a non-symptom entry. They stay in report 4, where they
head the entries of that subtype.

One row per disease and entry. `before` is the entry above it in the Symptoms sheet. `after` is,
for a heading (an entry ending in a colon), every entry it heads, up to the next heading or
body-system row; for any other entry, the entry below it.

kind, proposed, decision and note are the review columns. A rebuild keeps the values a row already
has, so the table can be rebuilt while the review is open, and a reviewed row whose entry is no
longer judged "not a symptom" (apply_non_symptom_review.py restored it) stays as it was, as do the
rows review_listed_symptoms.py adds for listed symptoms that are not one symptom. The file is tab-separated, UTF-8 with
no byte-order mark and LF line ends, written and read with the csv module's excel-tab dialect, so a
reviewer can fill `decision` in a spreadsheet and save it as tab-delimited text.

Usage: python build_non_symptom_review.py
"""
import collections, csv, os, re
import xml.etree.ElementTree as ET

import openpyxl

from build_symptom_report import ARI, ARI_BASE, DISEASE, NOT_A_SYMPTOM, OWL, RDF, RDFS, REPORT, ROOT
from park_subtype_symptoms import SUBTYPE_HEADINGS

REVIEW = os.path.join(ROOT, "data", "4-reports", "13_Non_Symptom_Review.tsv")
COLUMNS = ["ari_id", "disease", "entry", "individual", "report_4_seq", "likelihood", "before", "after",
           "kind", "proposed", "decision", "note"]
REVIEW_COLUMNS = COLUMNS[-4:]
IRI_DISEASE = re.compile(r"#Sym_(\d{7})_\d+$")


def read_ontology():
    """(ARI ID -> disease label, [(ARI ID, label, individual id, likelihood)] of "not a symptom" individuals)."""
    root = ET.parse(DISEASE).getroot()
    names, listed_by = {}, collections.defaultdict(list)
    for el in root:
        ari_id = el.findtext(ARI + "ARI_ID")
        if ari_id:
            names[ari_id] = el.findtext(RDFS + "label").strip()
            for ref in el.findall(ARI + "hasSymptom"):
                listed_by[ref.get(RDF + "resource")].append(ari_id)
    entries = []
    for ind in root.findall(OWL + "NamedIndividual"):
        iri = ind.get(RDF + "about")
        if ind.findtext(ARI + "ARI_NoConcept") != NOT_A_SYMPTOM:
            continue
        diseases = listed_by[iri]
        if not diseases:
            m = IRI_DISEASE.search(iri)
            if not m:
                raise SystemExit(f"{iri} is listed by no disease and its IRI names none")
            diseases = [f"ARI:{m.group(1)}"]
        for ari_id in diseases:
            if ari_id not in names:
                raise SystemExit(f"{iri} names {ari_id}, which is not a disease in the ontology")
            entries.append((ari_id, ind.findtext(RDFS + "label").strip(), iri[len(ARI_BASE):],
                            ind.findtext(ARI + "likelihood") or ""))
    return names, entries


def read_sheet():
    """[(ARI ID, entry, seq, before, after)] for each "not a symptom" row of the Symptoms sheet."""
    ws = openpyxl.load_workbook(REPORT, read_only=True)["Symptoms"]
    rows = ws.iter_rows(values_only=True)
    header = list(next(rows))
    col = {name: header.index(name) for name in ("ARI ID", "seq", "symptom", "latin", "SYMP Mapping")}
    by_disease = collections.defaultdict(list)
    for r in rows:
        if r[col["symptom"]]:
            by_disease[r[col["ARI ID"]]].append((r[col["symptom"]].strip(), r[col["seq"]],
                                                 r[col["latin"]] == "cat", r[col["SYMP Mapping"]]))

    def is_heading(item):
        return item[3] == NOT_A_SYMPTOM and item[0].endswith(":")

    found = []
    for ari_id, items in by_disease.items():
        for i, item in enumerate(items):
            if item[3] != NOT_A_SYMPTOM:
                continue
            before = items[i - 1][0] if i else ""
            if is_heading(item):
                headed = []
                for later in items[i + 1:]:
                    if later[2] or is_heading(later):  # a body-system row or the next heading
                        break
                    headed.append(later[0])
                after = "; ".join(headed)
            else:
                after = items[i + 1][0] if i + 1 < len(items) else ""
            found.append((ari_id, item[0], str(item[1]), before, after))
    return found


def read_review():
    """(ARI ID, entry) -> the row of the table as it stands (as a list), or {} before the first build."""
    if not os.path.exists(REVIEW):
        return {}
    with open(REVIEW, encoding="utf-8-sig", newline="") as f:
        lines = list(csv.reader(f, dialect="excel-tab"))
    if not lines or lines[0] != COLUMNS:
        raise SystemExit(f"{REVIEW}: the header is not {COLUMNS}")
    return {(v[0], v[2]): v for v in lines[1:]}


def main():
    names, individuals = read_ontology()
    rows = {}
    sheet = read_sheet()
    stale = set(SUBTYPE_HEADINGS) - {(ari_id, entry) for ari_id, entry, *_ in sheet}
    if stale:
        raise SystemExit(f"Subtype headings no longer in the Symptoms sheet: {sorted(stale)}")
    for ari_id, entry, seq, before, after in sheet:
        if (ari_id, entry) in SUBTYPE_HEADINGS:
            continue
        if (ari_id, entry) in rows:
            raise SystemExit(f"{ari_id} lists {entry!r} twice in the Symptoms sheet")
        rows[ari_id, entry] = dict(ari_id=ari_id, disease=names[ari_id], entry=entry, individual="",
                                   report_4_seq=seq, likelihood="", before=before, after=after)
    for ari_id, entry, individual, likelihood in individuals:
        row = rows.setdefault((ari_id, entry), dict(ari_id=ari_id, disease=names[ari_id], entry=entry,
                                                    report_4_seq="", before="", after=""))
        if row.get("individual"):
            raise SystemExit(f"{ari_id} has two {NOT_A_SYMPTOM!r} individuals labelled {entry!r}")
        row.update(individual=individual, likelihood=likelihood)

    review = read_review()
    for key in SUBTYPE_HEADINGS:
        review.pop(key, None)
    for key, row in rows.items():
        row.update(zip(REVIEW_COLUMNS, review.pop(key, [""] * len(COLUMNS))[-len(REVIEW_COLUMNS):]))
    # A reviewed entry no longer judged not a symptom (one restored as a symptom) keeps its row as it
    # was: the row is the record of the decision.
    for key, values in review.items():
        if any(values[-len(REVIEW_COLUMNS):]):
            rows[key] = dict(zip(COLUMNS, values))

    ordered = sorted(rows.values(), key=lambda r: (r["ari_id"], int(r["report_4_seq"] or 0), r["individual"]))
    with open(REVIEW, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, dialect="excel-tab", lineterminator="\n")
        writer.writerow(COLUMNS)
        for row in ordered:
            values = [row[c] for c in COLUMNS]
            for column, value in zip(COLUMNS, values):
                if any(c in value for c in "\t\r\n"):
                    raise SystemExit(f"{row['ari_id']} {row['entry']!r}: {column} has a tab or a line break")
            writer.writerow(values)
    in_ontology = sum(1 for r in ordered if r["individual"])
    print(f"{len(ordered)} entries: {in_ontology} Symptom individuals, "
          f"{len(ordered) - in_ontology} only in the Symptoms sheet -> {os.path.relpath(REVIEW, ROOT)}")


if __name__ == "__main__":
    main()
