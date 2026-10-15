"""Apply symptom_mapping.tsv to report 4 and write ari_symptoms.owl (ARI#132).

symptom_mapping.tsv is hand-curated: one row per symptom string found in the Symptoms sheet of
data/4-reports/4_Additional_Info_Index.xlsx or on a Symptom individual in ontologies/ari_t1d.owl.
Each string is one of:
  exact          - same meaning as its SYMP term
  broader        - its SYMP term is the nearest broader Symptom Ontology term
  merged         - another string with the same meaning (Merged Into) carries the mapping
  not a symptom  - a heading, note or test result picked up with the symptoms
Parent Symptom, when set, is the broader ARI symptom it groups under (e.g. Blisters on eyes -> Blisters).
Without one, the parent comes from SYMP: the SYMP term for a broader mapping, the SYMP term's own
parents for an exact one.

Writes:
  - Symptoms sheet of report 4: mapping and parent columns after the existing ones
  - Symptom Mapping sheet of report 4: one row per symptom string
  - ari_symptoms.owl next to this script: a class per mapped symptom under the referenced SYMP terms

Usage: python build_symptom_mapping.py <path to data/2-databases>
The database folder is not tracked in git, so pass the path of a checkout holding symp.owl
(http://purl.obolibrary.org/obo/symp.owl).
"""
import collections, csv, os, sys
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape, quoteattr

import openpyxl
from openpyxl.styles import Font, PatternFill

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ONTOLOGY = os.path.join(ROOT, "ontologies/ari_t1d.owl")
REPORT = os.path.join(ROOT, "data/4-reports/4_Additional_Info_Index.xlsx")
MAPPING = os.path.join(HERE, "symptom_mapping.tsv")
OUT = os.path.join(HERE, "ari_symptoms.owl")

BASE = "http://www.aurint.org/ontologies/ari-symptoms"
ARI_BASE = "http://www.aurint.org/ontologies/ari-disease"
OBO = "http://purl.obolibrary.org/obo/"
MAPPED = {"exact", "broader"}
MAPPINGS = MAPPED | {"merged", "not a symptom"}
RDF = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
OWL = "{http://www.w3.org/2002/07/owl#}"
RDFS = "{http://www.w3.org/2000/01/rdf-schema#}"
OBOINOWL = "{http://www.geneontology.org/formats/oboInOwl#}"

HEADER_FILL = PatternFill("solid", fgColor="1F3864")
HEADER_FONT = Font(bold=True, color="FFFFFF")
LINK_FONT = Font(color="0563C1", underline="single")
SYMPTOM_COLUMNS = [("Symptom ID", 14), ("SYMP ID", 14), ("SYMP Label", 30), ("SYMP Mapping", 14),
                   ("Parent Symptom", 30), ("Parent ID", 16), ("Merged Into", 30)]


def symp_iri(curie):
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


def read_ontology_symptoms():
    """Symptom individual IRI -> label, and label -> ARI IDs of the diseases that list it.

    Individuals are written either as owl:NamedIndividual with rdf:type #Symptom or as a typed
    <Symptom> element, so both forms are read.
    """
    root = ET.parse(ONTOLOGY).getroot()
    labels = {}
    for ind in root:
        typed = ind.tag == "{%s#}Symptom" % ARI_BASE
        if typed or any(t.get(RDF + "resource") == "#Symptom" for t in ind.findall(RDF + "type")):
            labels[ind.get(RDF + "about")] = ind.findtext(RDFS + "label").strip()
    diseases = collections.defaultdict(set)
    for ind in root:
        ari_id = ind.findtext("{*}ARI_ID")
        for ref in ind.findall("{*}hasSymptom"):
            diseases[labels[ref.get(RDF + "resource")]].add(ari_id)
    return labels, diseases


def read_mapping(symp):
    rows = list(csv.DictReader(open(MAPPING, encoding="utf-8", newline=""), delimiter="\t"))
    by_name = {}
    for r in rows:
        name = r["Symptom"]
        if name in by_name:
            raise SystemExit(f"{name!r} appears twice in symptom_mapping.tsv")
        if r["Mapping"] not in MAPPINGS:
            raise SystemExit(f"{name!r}: unknown Mapping {r['Mapping']!r}")
        if (r["Mapping"] in MAPPED) != bool(r["Symptom ID"] and r["SYMP ID"]):
            raise SystemExit(f"{name!r}: exact and broader rows need a Symptom ID and SYMP ID, other rows neither")
        if r["SYMP ID"] and symp.get(r["SYMP ID"], (None,))[0] != r["SYMP Label"]:
            raise SystemExit(f"{name!r}: {r['SYMP ID']} is not an active SYMP term labelled {r['SYMP Label']!r}")
        if (r["Mapping"] == "merged") != bool(r["Merged Into"]):
            raise SystemExit(f"{name!r}: Merged Into is set exactly when Mapping is merged")
        by_name[name] = r
    for r in rows:
        for key in ("Parent Symptom", "Merged Into"):
            target = r[key]
            if target and by_name.get(target, {}).get("Mapping") not in MAPPED:
                raise SystemExit(f"{r['Symptom']!r}: {key} {target!r} is not an exact or broader row")
    ids = [r["Symptom ID"] for r in rows if r["Symptom ID"]]
    if len(ids) != len(set(ids)):
        raise SystemExit("Symptom IDs in symptom_mapping.tsv are not unique")
    for name in by_name:
        seen = set()
        while name:
            if name in seen:
                raise SystemExit(f"Parent Symptom loop through {name!r}")
            seen.add(name)
            name = by_name[name]["Parent Symptom"]
    return rows, by_name


def parents_of(row, by_name, symp):
    """[(label, id)] parents of an exact or broader row."""
    if row["Parent Symptom"]:
        parent = by_name[row["Parent Symptom"]]
        return [(parent["Symptom"], parent["Symptom ID"])]
    if row["Mapping"] == "broader":
        return [(row["SYMP Label"], row["SYMP ID"])]
    return [(symp[p][0], p) for p in symp[row["SYMP ID"]][1]]


def header(ws, col, text, width):
    cell = ws.cell(row=1, column=col, value=text)
    cell.fill, cell.font = HEADER_FILL, HEADER_FONT
    ws.column_dimensions[cell.column_letter].width = width


def link(cell, curie):
    if curie.startswith("SYMP:"):
        cell.hyperlink, cell.font = symp_iri(curie), LINK_FONT


def write_report(by_name, symp, ontology_diseases):
    wb = openpyxl.load_workbook(REPORT)
    ws = wb["Symptoms"]
    first = 8  # after ARI ID, seq, disease, symptom, latin, col4, col5
    if [c.value for c in ws[1]][: first - 1][3] != "symptom":
        raise SystemExit("Symptoms sheet layout changed: column D is no longer 'symptom'")
    for i, (text, width) in enumerate(SYMPTOM_COLUMNS):
        header(ws, first + i, text, width)
    ws.auto_filter.ref = f"A1:{ws.cell(row=1, column=first + len(SYMPTOM_COLUMNS) - 1).column_letter}1"
    report_diseases = collections.defaultdict(set)
    for row in ws.iter_rows(min_row=2):
        name, kind = row[3].value, row[4].value
        for i in range(len(SYMPTOM_COLUMNS)):
            ws.cell(row=row[0].row, column=first + i, value=None).hyperlink = None
        if not name or kind == "cat":  # cat rows name a body system, not a symptom
            continue
        name = name.strip()
        report_diseases[name].add(row[0].value)
        r = by_name[name]
        target = by_name[r["Merged Into"]] if r["Merged Into"] else r
        values = [""] * len(SYMPTOM_COLUMNS)
        if target["Mapping"] in MAPPED:
            parents = parents_of(target, by_name, symp)
            values = [target["Symptom ID"], target["SYMP ID"], target["SYMP Label"], target["Mapping"],
                      "; ".join(p[0] for p in parents), "; ".join(p[1] for p in parents), r["Merged Into"]]
        else:
            values[3] = r["Mapping"]
        for i, v in enumerate(values):
            cell = ws.cell(row=row[0].row, column=first + i, value=v or None)
            if SYMPTOM_COLUMNS[i][0] in ("SYMP ID", "Parent ID"):
                link(cell, v)

    if "Symptom Mapping" in wb.sheetnames:
        del wb["Symptom Mapping"]
    sm = wb.create_sheet("Symptom Mapping", wb.sheetnames.index("Symptoms") + 1)
    columns = [("Symptom", 50), ("Symptom ID", 14), ("Mapping", 14), ("SYMP ID", 14), ("SYMP Label", 30),
               ("Parent Symptom", 30), ("Parent ID", 16), ("Merged Into", 30),
               ("Diseases (Symptoms sheet)", 14), ("Diseases (ontology)", 14)]
    for i, (text, width) in enumerate(columns, 1):
        header(sm, i, text, width)
    sm.freeze_panes, sm.auto_filter.ref = "A2", f"A1:J{len(by_name) + 1}"
    for n, (name, r) in enumerate(sorted(by_name.items(), key=lambda kv: kv[0].casefold()), 2):
        parents = parents_of(r, by_name, symp) if r["Mapping"] in MAPPED else []
        values = [name, r["Symptom ID"], r["Mapping"], r["SYMP ID"], r["SYMP Label"],
                  "; ".join(p[0] for p in parents), "; ".join(p[1] for p in parents), r["Merged Into"],
                  len(report_diseases[name]), len(ontology_diseases[name])]
        for i, v in enumerate(values, 1):
            cell = sm.cell(row=n, column=i, value=v if v != "" else None)
            if columns[i - 1][0] in ("SYMP ID", "Parent ID"):
                link(cell, v)
    wb.save(REPORT)
    return report_diseases


def literal(tag, text):
    return f"    <{tag}>{escape(text)}</{tag}>\n"


def resource(tag, iri):
    return f"    <{tag} rdf:resource={quoteattr(iri)}/>\n"


def write_owl(rows, by_name, symp, version, individuals):
    """A class per exact or broader row, under its parent; SYMP terms it references, with their ancestors."""
    def iri(row_id):
        return symp_iri(row_id) if row_id.startswith("SYMP:") else f"{BASE}#{row_id.replace(':', '_')}"

    concepts = [r for r in rows if r["Mapping"] in MAPPED]
    alt_labels = collections.defaultdict(list)
    for r in rows:
        if r["Merged Into"]:
            alt_labels[r["Merged Into"]].append(r["Symptom"])
    ind_by_label = collections.defaultdict(list)
    for ind, label in individuals.items():
        r = by_name[label]
        ind_by_label[r["Merged Into"] or label].append(ARI_BASE + ind)

    needed, stack = set(), [r["SYMP ID"] for r in concepts]
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
        '         xmlns:skos="http://www.w3.org/2004/02/skos/core#"\n'
        '         xmlns:oboInOwl="http://www.geneontology.org/formats/oboInOwl#"\n'
        '         xmlns:dc="http://purl.org/dc/elements/1.1/"\n'
        f'         xml:base="{BASE}"\n'
        f'         xmlns="{BASE}#">\n\n'
        f'<owl:Ontology rdf:about="{BASE}">\n'
        "    <rdfs:comment>ARI symptoms grouped into a hierarchy and mapped to the Symptom Ontology (SYMP) "
        "for ARI#132, generated from notebook/symptom-mapping/symptom_mapping.tsv. skos:exactMatch names a "
        "SYMP term with the same meaning, skos:broadMatch the nearest broader one. Strings merged into a "
        "symptom are skos:altLabel. ariSymptomIndividual links the Symptom individuals in "
        "ontologies/ari_t1d.owl that carry the symptom. SYMP classes are copied with their labels and "
        "is_a parents only.</rdfs:comment>\n"
        f'    <dc:source rdf:resource="{version}"/>\n'
        "</owl:Ontology>\n\n"
        '<owl:AnnotationProperty rdf:about="http://www.w3.org/2004/02/skos/core#exactMatch"/>\n'
        '<owl:AnnotationProperty rdf:about="http://www.w3.org/2004/02/skos/core#broadMatch"/>\n'
        '<owl:AnnotationProperty rdf:about="http://www.w3.org/2004/02/skos/core#altLabel"/>\n'
        '<owl:AnnotationProperty rdf:about="http://www.geneontology.org/formats/oboInOwl#id"/>\n'
        '<owl:AnnotationProperty rdf:about="#ariSymptomIndividual">\n'
        "    <rdfs:label>ARI symptom individual</rdfs:label>\n"
        "</owl:AnnotationProperty>\n\n"
    ]
    for curie in sorted(needed):
        out.append(f"<owl:Class rdf:about={quoteattr(symp_iri(curie))}>\n")
        out.append(literal("rdfs:label", symp[curie][0]))
        out.append(literal("oboInOwl:id", curie))
        out.extend(resource("rdfs:subClassOf", symp_iri(p)) for p in symp[curie][1])
        out.append("</owl:Class>\n\n")
    for r in concepts:
        out.append(f"<owl:Class rdf:about={quoteattr(iri(r['Symptom ID']))}>\n")
        out.append(literal("rdfs:label", r["Symptom"]))
        out.append(literal("oboInOwl:id", r["Symptom ID"]))
        out.append(resource("skos:exactMatch" if r["Mapping"] == "exact" else "skos:broadMatch", symp_iri(r["SYMP ID"])))
        out.extend(literal("skos:altLabel", a) for a in sorted(alt_labels[r["Symptom"]]))
        out.extend(resource("ariSymptomIndividual", i) for i in sorted(ind_by_label[r["Symptom"]]))
        out.extend(resource("rdfs:subClassOf", iri(p[1])) for p in parents_of(r, by_name, symp))
        out.append("</owl:Class>\n\n")
    out.append("</rdf:RDF>\n")
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("".join(out))
    return len(concepts), len(needed)


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    symp, version = read_symp(os.path.join(sys.argv[1], "symp.owl"))
    rows, by_name = read_mapping(symp)
    individuals, ontology_diseases = read_ontology_symptoms()

    wb = openpyxl.load_workbook(REPORT, read_only=True)
    report_names = {r[3].strip() for r in wb["Symptoms"].iter_rows(min_row=2, values_only=True)
                    if r[3] and r[4] != "cat"}
    missing = sorted((report_names | set(individuals.values())) - set(by_name))
    if missing:
        raise SystemExit(f"{len(missing)} symptoms have no row in symptom_mapping.tsv: {missing}")

    write_report(by_name, symp, ontology_diseases)
    classes, symp_classes = write_owl(rows, by_name, symp, version, individuals)
    counts = collections.Counter(r["Mapping"] for r in rows)
    print(f"{len(rows)} symptom strings: " + ", ".join(f"{n} {k}" for k, n in sorted(counts.items())))
    print(f"{sum(1 for r in rows if r['Parent Symptom'])} grouped under an ARI parent symptom")
    print(f"{classes} ARI symptom classes, {symp_classes} SYMP classes -> {OUT}")


if __name__ == "__main__":
    main()
