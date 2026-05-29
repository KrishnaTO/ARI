#!/usr/bin/env python3
"""
Extract all descendant concepts of SNOMED CT 414029004 |Disorder of immune
function (disorder)| from an RF2 Snapshot release, with full detail, and emit a
Protege-loadable OWL 2 ontology of the subtree.

Outputs (in OUT_DIR):
  - immune_disorder_descendants.csv   : tabular detail, one row per concept
  - immune_disorder_descendants.xlsx  : same data + Summary sheet
  - immune_disorder_subtree.ofn       : OWL 2 Functional Syntax ontology

Tabular columns include: FSN, Preferred Term, all synonyms, text definition,
defining attribute relationships (grouped + labelled), definition status,
direct parents.

Method (RF2 Snapshot, active components only):
  1. Build parent->children from active "Is a" (116680003) relationships.
  2. Transitive closure below the root -> descendants.
  3. Join descriptions (FSN/synonyms), text definitions, language refset (PT),
     and inferred attribute relationships.
  4. Collect the stored OWL axioms (OWL Expression refset) for the subtree and
     assemble a self-contained functional-syntax ontology with declarations and
     rdfs:label annotations for every referenced concept and property.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict, deque
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_ROOT = "414029004"  # Disorder of immune function (disorder)
DEFAULT_PREFIX = "immune_disorder"

# SNOMED CT metadata concept IDs
IS_A = "116680003"
FSN_TYPE = "900000000000003001"
SYNONYM_TYPE = "900000000000013009"
TEXTDEF_TYPE = "900000000000550004"
PREFERRED = "900000000000548007"
US_LANG_REFSET = "900000000000509007"
GB_LANG_REFSET = "900000000000508004"
PRIMITIVE = "900000000000074008"
FULLY_DEFINED = "900000000000073002"

BASE = Path(
    "F:/1Projects/7Projects-Aurint/ARI/data/databases/snomed/"
    "SnomedCT_InternationalRF2_PRODUCTION_20260501T120000Z/"
    "SnomedCT_InternationalRF2_PRODUCTION_20260501T120000Z/Snapshot"
)
TERM = BASE / "Terminology"
REL_FILE = TERM / "sct2_Relationship_Snapshot_INT_20260501.txt"
DESC_FILE = TERM / "sct2_Description_Snapshot-en_INT_20260501.txt"
CONCEPT_FILE = TERM / "sct2_Concept_Snapshot_INT_20260501.txt"
TEXTDEF_FILE = TERM / "sct2_TextDefinition_Snapshot-en_INT_20260501.txt"
OWL_FILE = TERM / "sct2_sRefset_OWLExpressionSnapshot_INT_20260501.txt"
LANG_FILE = (
    BASE / "Refset/Language/der2_cRefset_LanguageSnapshot-en_INT_20260501.txt"
)

OUT_DIR = Path(
    "F:/1Projects/7Projects-Aurint/ARI/data/databases/snomed/immune-extractor"
)

SCT_IRI = "http://snomed.info/id/"

ID_RE = re.compile(r":(\d+)")


def read_rows(path: Path):
    """Yield dict rows from a tab-delimited RF2 file.

    RF2 files are tab-delimited with NO quoting; terms may contain literal
    double-quote characters, so quote processing must be disabled.
    """
    with open(path, "r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
        for row in reader:
            yield row


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract a SNOMED CT subtree to spreadsheet + OWL."
    )
    parser.add_argument(
        "--root",
        default=DEFAULT_ROOT,
        help="Root concept ID whose descendants are extracted "
        f"(default {DEFAULT_ROOT} = Disorder of immune function).",
    )
    parser.add_argument(
        "--prefix",
        default=DEFAULT_PREFIX,
        help=f"Output filename prefix (default {DEFAULT_PREFIX}).",
    )
    args = parser.parse_args()
    root = args.root
    prefix = args.prefix
    ontology_iri = f"http://snomed.info/sct/subtree-{root}"

    # --- 1. Concept status / definition status -----------------------------
    print("Reading concepts...", file=sys.stderr)
    concept_active: dict[str, str] = {}
    concept_defstatus: dict[str, str] = {}
    for row in read_rows(CONCEPT_FILE):
        concept_active[row["id"]] = row["active"]
        concept_defstatus[row["id"]] = row["definitionStatusId"]

    # --- 2. Build parent -> children from active Is-a relationships --------
    print("Reading relationships (pass 1: active Is-a)...", file=sys.stderr)
    children: dict[str, set[str]] = defaultdict(set)
    parents: dict[str, set[str]] = defaultdict(set)
    for row in read_rows(REL_FILE):
        if row["active"] != "1" or row["typeId"] != IS_A:
            continue
        children[row["destinationId"]].add(row["sourceId"])
        parents[row["sourceId"]].add(row["destinationId"])

    # --- 3. Transitive closure of descendants ------------------------------
    print(f"Computing descendants of {root}...", file=sys.stderr)
    descendants: set[str] = set()
    queue = deque(children.get(root, set()))
    while queue:
        c = queue.popleft()
        if c in descendants:
            continue
        descendants.add(c)
        queue.extend(children.get(c, set()))
    print(f"  {len(descendants)} descendant concepts found.", file=sys.stderr)
    direct_children = children.get(root, set())
    subtree = descendants | {root}

    # --- 4. Defining attribute relationships (pass 2: non-Is-a) ------------
    print("Reading relationships (pass 2: attributes)...", file=sys.stderr)
    # source -> group -> list[(typeId, destId)]
    attrs: dict[str, dict[str, list[tuple[str, str]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    rel_label_ids: set[str] = set()
    for row in read_rows(REL_FILE):
        if row["active"] != "1" or row["typeId"] == IS_A:
            continue
        src = row["sourceId"]
        if src not in descendants:
            continue
        attrs[src][row["relationshipGroup"]].append(
            (row["typeId"], row["destinationId"])
        )
        rel_label_ids.add(row["typeId"])
        rel_label_ids.add(row["destinationId"])

    # --- 5. OWL axioms for the subtree -------------------------------------
    print("Reading OWL expression refset...", file=sys.stderr)
    # class axioms (subject in subtree) and the object/data property hierarchy
    class_axioms: list[str] = []
    obj_prop_parent: dict[str, str] = {}  # prop -> superproperty
    data_props: set[str] = set()
    for row in read_rows(OWL_FILE):
        if row["active"] != "1":
            continue
        expr = row["owlExpression"]
        if expr.startswith("SubObjectPropertyOf("):
            ids = ID_RE.findall(expr)
            if len(ids) >= 2:
                obj_prop_parent[ids[0]] = ids[1]
            elif ids:
                obj_prop_parent.setdefault(ids[0], "")
            continue
        if expr.startswith("SubDataPropertyOf("):
            ids = ID_RE.findall(expr)
            if ids:
                data_props.add(ids[0])
            continue
        if expr.startswith(("SubClassOf(", "EquivalentClasses(")):
            if row["referencedComponentId"] in subtree:
                class_axioms.append(expr)

    # Concepts referenced anywhere in the kept class axioms
    referenced: set[str] = set(subtree)
    for ax in class_axioms:
        referenced.update(ID_RE.findall(ax))

    # Partition referenced concepts into properties vs classes.
    object_props: set[str] = {c for c in referenced if c in obj_prop_parent}
    used_data_props: set[str] = {c for c in referenced if c in data_props}
    # Close object-property hierarchy upward so SubObjectPropertyOf targets
    # are themselves declared.
    pq = deque(object_props)
    while pq:
        p = pq.popleft()
        sup = obj_prop_parent.get(p)
        if sup and sup not in object_props:
            object_props.add(sup)
            referenced.add(sup)
            pq.append(sup)

    # Labels are also needed for the (possibly out-of-subtree) direct parents
    # of every descendant so the parentTerms column is fully readable.
    parent_label_ids: set[str] = set()
    for c in descendants:
        parent_label_ids |= parents.get(c, set())
    label_ids = referenced | rel_label_ids | parent_label_ids

    # --- 6. Descriptions: FSN (labels), synonyms (descendants) -------------
    print("Reading descriptions...", file=sys.stderr)
    fsn_label: dict[str, str] = {}
    synonyms: dict[str, dict[str, str]] = defaultdict(dict)
    desc_concept: dict[str, str] = {}
    for row in read_rows(DESC_FILE):
        if row["active"] != "1":
            continue
        cid = row["conceptId"]
        typ = row["typeId"]
        if typ == FSN_TYPE and cid in label_ids:
            fsn_label[cid] = row["term"]
        if cid in descendants and typ == SYNONYM_TYPE:
            synonyms[cid][row["id"]] = row["term"]
            desc_concept[row["id"]] = cid

    # --- 7. Text definitions for descendants -------------------------------
    print("Reading text definitions...", file=sys.stderr)
    text_def: dict[str, list[str]] = defaultdict(list)
    for row in read_rows(TEXTDEF_FILE):
        if row["active"] != "1" or row["typeId"] != TEXTDEF_TYPE:
            continue
        if row["conceptId"] in descendants:
            text_def[row["conceptId"]].append(row["term"])

    # --- 8. Preferred Term via language refset -----------------------------
    print("Reading language refset for preferred terms...", file=sys.stderr)
    pt_us: dict[str, str] = {}
    pt_gb: dict[str, str] = {}
    for row in read_rows(LANG_FILE):
        if row["active"] != "1" or row["acceptabilityId"] != PREFERRED:
            continue
        cid = desc_concept.get(row["referencedComponentId"])
        if cid is None:
            continue
        term = synonyms[cid].get(row["referencedComponentId"])
        if term is None:
            continue
        if row["refsetId"] == US_LANG_REFSET:
            pt_us[cid] = term
        elif row["refsetId"] == GB_LANG_REFSET:
            pt_gb[cid] = term

    # --- 9. Assemble tabular output ----------------------------------------
    print("Assembling spreadsheet...", file=sys.stderr)

    def label(cid: str) -> str:
        return fsn_label.get(cid, cid)

    def semantic_tag(term: str | None) -> str:
        if term and term.endswith(")") and "(" in term:
            return term[term.rfind("(") + 1 : -1]
        return ""

    def render_relationships(cid: str) -> str:
        groups = attrs.get(cid)
        if not groups:
            return ""
        parts: list[str] = []
        # ungrouped (group "0") attributes first, then numbered role groups
        for grp in sorted(groups, key=lambda g: (g != "0", int(g))):
            items = "; ".join(
                f"{label(t)} = {label(d)} ({d})" for t, d in groups[grp]
            )
            parts.append(items if grp == "0" else "{ " + items + " }")
        return " ".join(parts)

    records = []
    for cid in sorted(descendants):
        fsn_term = fsn_label.get(cid, "")
        syn_terms = sorted(set(synonyms.get(cid, {}).values()))
        defst = concept_defstatus.get(cid, "")
        parent_ids = sorted(parents.get(cid, set()))
        records.append(
            {
                "conceptId": cid,
                "fsn": fsn_term,
                "preferredTerm": pt_us.get(cid) or pt_gb.get(cid) or "",
                "semanticTag": semantic_tag(fsn_term),
                "synonyms": " | ".join(syn_terms),
                "textDefinition": " ".join(text_def.get(cid, [])),
                "definingRelationships": render_relationships(cid),
                "conceptActive": concept_active.get(cid, ""),
                "definitionStatus": (
                    "Fully defined"
                    if defst == FULLY_DEFINED
                    else "Primitive"
                    if defst == PRIMITIVE
                    else defst
                ),
                "isDirectChildOfRoot": "Y" if cid in direct_children else "N",
                "numParents": len(parent_ids),
                "parentConceptIds": "|".join(parent_ids),
                "parentTerms": " | ".join(label(p) for p in parent_ids),
            }
        )

    df = pd.DataFrame.from_records(records)
    df = df.sort_values(["semanticTag", "fsn"]).reset_index(drop=True)

    root_fsn = fsn_label.get(root, root)
    csv_path = OUT_DIR / f"{prefix}_descendants.csv"
    xlsx_path = OUT_DIR / f"{prefix}_descendants.xlsx"
    df.to_csv(csv_path, index=False, encoding="utf-8")
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Descendants")
        summary = pd.DataFrame(
            {
                "metric": [
                    "Root concept",
                    "Total descendant concepts",
                    "Direct children of root",
                    "Active concepts",
                    "Fully defined",
                    "Primitive",
                    "With text definition",
                    "With >=1 synonym",
                ],
                "value": [
                    f"{root} |{root_fsn}|",
                    len(df),
                    int((df["isDirectChildOfRoot"] == "Y").sum()),
                    int((df["conceptActive"] == "1").sum()),
                    int((df["definitionStatus"] == "Fully defined").sum()),
                    int((df["definitionStatus"] == "Primitive").sum()),
                    int((df["textDefinition"].fillna("") != "").sum()),
                    int((df["synonyms"].fillna("") != "").sum()),
                ],
            }
        )
        summary.to_excel(writer, index=False, sheet_name="Summary")
    print(f"Wrote {csv_path}", file=sys.stderr)
    print(f"Wrote {xlsx_path}", file=sys.stderr)

    # --- 10. OWL 2 Functional Syntax ontology ------------------------------
    print("Writing OWL ontology...", file=sys.stderr)

    def esc(text: str) -> str:
        return text.replace("\\", "\\\\").replace('"', '\\"')

    ofn_path = OUT_DIR / f"{prefix}_subtree.ofn"
    comment = (
        f"SNOMED CT International Edition 20260501 - subtree of {root} "
        f"|{root_fsn}|. Generated from the RF2 OWL Expression refset."
    )
    classes = sorted(referenced - object_props - used_data_props, key=int)
    with open(ofn_path, "w", encoding="utf-8") as out:
        out.write("Prefix(:=<%s>)\n" % SCT_IRI)
        out.write("Prefix(owl:=<http://www.w3.org/2002/07/owl#>)\n")
        out.write("Prefix(rdf:=<http://www.w3.org/1999/02/22-rdf-syntax-ns#>)\n")
        out.write("Prefix(xsd:=<http://www.w3.org/2001/XMLSchema#>)\n")
        out.write("Prefix(rdfs:=<http://www.w3.org/2000/01/rdf-schema#>)\n\n")
        out.write("Ontology(<%s>\n" % ontology_iri)
        out.write(f'  Annotation(rdfs:comment "{esc(comment)}")\n\n')

        out.write("  # ----- Object property declarations -----\n")
        for p in sorted(object_props, key=int):
            out.write(f"  Declaration(ObjectProperty(:{p}))\n")
            if p in fsn_label:
                out.write(
                    f'  AnnotationAssertion(rdfs:label :{p} "{esc(fsn_label[p])}")\n'
                )
            sup = obj_prop_parent.get(p)
            if sup:
                out.write(f"  SubObjectPropertyOf(:{p} :{sup})\n")
        if used_data_props:
            out.write("\n  # ----- Data property declarations -----\n")
            for p in sorted(used_data_props, key=int):
                out.write(f"  Declaration(DataProperty(:{p}))\n")
                if p in fsn_label:
                    out.write(
                        f'  AnnotationAssertion(rdfs:label :{p} "{esc(fsn_label[p])}")\n'
                    )

        out.write("\n  # ----- Class declarations + labels -----\n")
        for c in classes:
            out.write(f"  Declaration(Class(:{c}))\n")
            if c in fsn_label:
                out.write(
                    f'  AnnotationAssertion(rdfs:label :{c} "{esc(fsn_label[c])}")\n'
                )

        out.write("\n  # ----- Logical axioms (from OWL Expression refset) -----\n")
        for ax in class_axioms:
            out.write(f"  {ax}\n")

        out.write(")\n")

    print(f"Wrote {ofn_path}", file=sys.stderr)

    # --- 11. RDF/XML serialization (universally Protege-loadable .owl) ------
    print("Writing OWL RDF/XML ontology...", file=sys.stderr)
    owl_path = OUT_DIR / f"{prefix}_subtree.owl"
    write_rdfxml(
        owl_path,
        ontology_iri=ontology_iri,
        comment=comment,
        class_axioms=class_axioms,
        classes=classes,
        object_props=object_props,
        obj_prop_parent=obj_prop_parent,
        fsn_label=fsn_label,
    )
    print(f"Wrote {owl_path}", file=sys.stderr)
    print(
        f"  classes={len(classes)} object_properties={len(object_props)} "
        f"axioms={len(class_axioms)}",
        file=sys.stderr,
    )
    print(f"Rows: {len(df)}", file=sys.stderr)


# ---------------------------------------------------------------------------
# OWL 2 Functional Syntax -> RDF/XML (only the constructs SNOMED uses here:
# named classes, ObjectIntersectionOf, ObjectSomeValuesFrom, SubClassOf,
# EquivalentClasses).
# ---------------------------------------------------------------------------
def write_rdfxml(
    path: Path,
    *,
    ontology_iri: str,
    comment: str,
    class_axioms: list[str],
    classes: list[str],
    object_props: set[str],
    obj_prop_parent: dict[str, str],
    fsn_label: dict[str, str],
) -> None:
    from rdflib import RDF, RDFS, OWL, BNode, Graph, Literal, Namespace, URIRef
    from rdflib.collection import Collection

    SCT = Namespace(SCT_IRI)
    g = Graph()
    g.bind("", SCT)
    g.bind("owl", OWL)
    g.bind("rdfs", RDFS)
    g.namespace_manager.bind("sct", SCT)

    onto = URIRef(ontology_iri)
    g.add((onto, RDF.type, OWL.Ontology))
    g.add((onto, RDFS.comment, Literal(comment)))

    def iri(cid: str) -> URIRef:
        return URIRef(SCT_IRI + cid)

    # Declarations + labels
    for p in sorted(object_props, key=int):
        g.add((iri(p), RDF.type, OWL.ObjectProperty))
        if p in fsn_label:
            g.add((iri(p), RDFS.label, Literal(fsn_label[p])))
        sup = obj_prop_parent.get(p)
        if sup:
            g.add((iri(p), RDFS.subPropertyOf, iri(sup)))
    for c in classes:
        g.add((iri(c), RDF.type, OWL.Class))
        if c in fsn_label:
            g.add((iri(c), RDFS.label, Literal(fsn_label[c])))

    # --- functional-syntax expression parser ---------------------------
    def parse_expr(s: str, i: int):
        while i < len(s) and s[i] == " ":
            i += 1
        if s[i] == ":":
            j = i + 1
            while j < len(s) and s[j].isdigit():
                j += 1
            return iri(s[i + 1 : j]), j
        # keyword(
        k = s.index("(", i)
        kw = s[i:k]
        i = k + 1
        if kw == "ObjectSomeValuesFrom":
            prop, i = parse_expr(s, i)
            filler, i = parse_expr(s, i)
            while s[i] == " ":
                i += 1
            assert s[i] == ")", s[i:]
            node = BNode()
            g.add((node, RDF.type, OWL.Restriction))
            g.add((node, OWL.onProperty, prop))
            g.add((node, OWL.someValuesFrom, filler))
            return node, i + 1
        if kw == "ObjectIntersectionOf":
            members = []
            while True:
                while s[i] == " ":
                    i += 1
                if s[i] == ")":
                    i += 1
                    break
                m, i = parse_expr(s, i)
                members.append(m)
            node = BNode()
            g.add((node, RDF.type, OWL.Class))
            lst = BNode()
            Collection(g, lst, members)
            g.add((node, OWL.intersectionOf, lst))
            return node, i
        raise ValueError(f"Unsupported construct {kw!r}")

    def parse_top(axiom: str):
        k = axiom.index("(")
        head = axiom[:k]
        i = k + 1
        a, i = parse_expr(axiom, i)
        b, i = parse_expr(axiom, i)
        return head, a, b

    for ax in class_axioms:
        head, a, b = parse_top(ax)
        if head == "SubClassOf":
            g.add((a, RDFS.subClassOf, b))
        elif head == "EquivalentClasses":
            g.add((a, OWL.equivalentClass, b))

    # Use the plain "xml" serializer: "pretty-xml" silently drops triples on
    # nested/shared blank nodes and RDF lists.
    g.serialize(destination=str(path), format="xml")


if __name__ == "__main__":
    main()
