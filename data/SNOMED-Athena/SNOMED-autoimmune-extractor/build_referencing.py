#!/usr/bin/env python3
"""
Augment the Autoimmune disease outputs with the concepts that *reference* each
autoimmune concept through an attribute relationship (incoming, non-Is-a).

Example: "Dementia due to celiac disease (disorder)" has a `Due to (attribute)`
relationship pointing at "Celiac disease (disorder)", so it is a referencing
concept of celiac disease.

Outputs:
  * A new sheet `ReferencingConcepts` in autoimmune_disease_combined_terms.xlsx:
    one row per autoimmune concept that is referenced, one column per attribute
    type, each cell listing the referencing concepts as `id | term`.
  * Regenerated autoimmune_disease_subtree.owl / .ofn that additionally include
    the referencing concepts and their stored axioms, with the ` (attribute)`
    tag stripped from every object-property label.
"""

from __future__ import annotations

import re
from collections import defaultdict

import pandas as pd

from extract_immune_disorders import (
    DESC_FILE,
    FSN_TYPE,
    IS_A,
    ID_RE,
    OUT_DIR,
    OWL_FILE,
    REL_FILE,
    SCT_IRI,
    read_rows,
    write_rdfxml,
)

ROOT = "85828009"  # Autoimmune disease (disorder)
XLSX = OUT_DIR / "autoimmune_disease_combined_terms.xlsx"
MAIN_SHEET = "SNOMED-AutoimmuneDisease"
OWL_PATH = OUT_DIR / "autoimmune_disease_subtree.owl"
OFN_PATH = OUT_DIR / "autoimmune_disease_subtree.ofn"
ONTOLOGY_IRI = "http://snomed.info/sct/autoimmune-disease-85828009-with-referencing"
ATTR_TAG = re.compile(r"\s*\(attribute\)\s*$")


def main() -> None:
    # --- target concepts (the autoimmune subtree, from the workbook) -------
    sheets = pd.read_excel(XLSX, sheet_name=None, dtype=str)
    main_df = sheets[MAIN_SHEET].fillna("")
    targets = set(main_df["conceptId"].unique())
    pt = dict(
        zip(
            main_df.loc[main_df.termType == "Preferred term", "conceptId"],
            main_df.loc[main_df.termType == "Preferred term", "term"],
        )
    )
    print(f"target concepts: {len(targets)}")

    # --- incoming attribute references -------------------------------------
    # target -> attrTypeId -> set(sourceConceptId)
    refs: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    referencing: set[str] = set()
    attr_types: set[str] = set()
    print("Scanning relationships for incoming attribute references...")
    for row in read_rows(REL_FILE):
        if row["active"] != "1" or row["typeId"] == IS_A:
            continue
        dest = row["destinationId"]
        if dest not in targets:
            continue
        src = row["sourceId"]
        refs[dest][row["typeId"]].add(src)
        referencing.add(src)
        attr_types.add(row["typeId"])
    print(
        f"  concepts referenced: {len(refs)} | "
        f"referencing concepts: {len(referencing)} | "
        f"attribute types: {len(attr_types)}"
    )

    # --- OWL axioms for the expanded set -----------------------------------
    expanded = targets | referencing | {ROOT}
    print(f"expanded concept set (targets + referencing + root): {len(expanded)}")
    class_axioms: list[str] = []
    obj_prop_parent: dict[str, str] = {}
    data_props: set[str] = set()
    print("Scanning OWL expression refset...")
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
        elif expr.startswith("SubDataPropertyOf("):
            ids = ID_RE.findall(expr)
            if ids:
                data_props.add(ids[0])
        elif expr.startswith(("SubClassOf(", "EquivalentClasses(")):
            if row["referencedComponentId"] in expanded:
                class_axioms.append(expr)

    referenced: set[str] = set(expanded)
    for ax in class_axioms:
        referenced.update(ID_RE.findall(ax))

    object_props = {c for c in referenced if c in obj_prop_parent}
    used_data_props = {c for c in referenced if c in data_props}
    from collections import deque

    pq = deque(object_props)
    while pq:
        p = pq.popleft()
        sup = obj_prop_parent.get(p)
        if sup and sup not in object_props:
            object_props.add(sup)
            referenced.add(sup)
            pq.append(sup)

    # --- FSN labels for everything we name ---------------------------------
    label_ids = referenced | attr_types | referencing
    print("Reading descriptions for labels...")
    fsn_label: dict[str, str] = {}
    for row in read_rows(DESC_FILE):
        if row["active"] != "1" or row["typeId"] != FSN_TYPE:
            continue
        if row["conceptId"] in label_ids:
            fsn_label[row["conceptId"]] = row["term"]

    def lbl(cid: str) -> str:
        return fsn_label.get(cid, cid)

    # --- new sheet: referencing concepts, attribute per column -------------
    # column order: attributes by descending number of (target,source) refs
    attr_count = {
        a: sum(1 for t in refs for s in refs[t].get(a, ())) for a in attr_types
    }
    ordered_attrs = sorted(attr_types, key=lambda a: (-attr_count[a], lbl(a)))
    attr_header = {a: ATTR_TAG.sub("", lbl(a)) for a in ordered_attrs}

    records = []
    for cid in main_df["conceptId"].drop_duplicates():
        if cid not in refs:
            continue
        rec = {"conceptId": cid, "conceptPreferredTerm": pt.get(cid, lbl(cid))}
        for a in ordered_attrs:
            srcs = refs[cid].get(a)
            rec[attr_header[a]] = (
                " ; ".join(f"{s} | {lbl(s)}" for s in sorted(srcs, key=int))
                if srcs
                else ""
            )
        records.append(rec)
    ref_df = pd.DataFrame.from_records(
        records,
        columns=["conceptId", "conceptPreferredTerm"]
        + [attr_header[a] for a in ordered_attrs],
    )
    # drop attribute columns that ended up entirely empty
    ref_df = ref_df.loc[:, (ref_df != "").any(axis=0)]
    print(f"ReferencingConcepts rows: {len(ref_df)} | columns: {list(ref_df.columns)}")

    # --- strip " (attribute)" from ALL labels (only attributes carry it) ---
    clean_label = {cid: ATTR_TAG.sub("", t) for cid, t in fsn_label.items()}

    # --- regenerate OWL (RDF/XML) ------------------------------------------
    classes = sorted(referenced - object_props - used_data_props, key=int)
    comment = (
        "SNOMED CT International Edition 20260501 - Autoimmune disease "
        "(85828009) subtree plus all concepts referencing those concepts via "
        "attribute relationships. Object-property labels have the (attribute) "
        "tag removed. Generated from the RF2 OWL Expression refset."
    )
    print("Writing OWL RDF/XML...")
    write_rdfxml(
        OWL_PATH,
        ontology_iri=ONTOLOGY_IRI,
        comment=comment,
        class_axioms=class_axioms,
        classes=classes,
        object_props=object_props,
        obj_prop_parent=obj_prop_parent,
        fsn_label=clean_label,
    )
    print(f"Wrote {OWL_PATH}")

    # --- regenerate OWL (Functional Syntax) --------------------------------
    def esc(text: str) -> str:
        return text.replace("\\", "\\\\").replace('"', '\\"')

    print("Writing OWL Functional Syntax...")
    with open(OFN_PATH, "w", encoding="utf-8") as out:
        out.write("Prefix(:=<%s>)\n" % SCT_IRI)
        out.write("Prefix(owl:=<http://www.w3.org/2002/07/owl#>)\n")
        out.write("Prefix(rdf:=<http://www.w3.org/1999/02/22-rdf-syntax-ns#>)\n")
        out.write("Prefix(xsd:=<http://www.w3.org/2001/XMLSchema#>)\n")
        out.write("Prefix(rdfs:=<http://www.w3.org/2000/01/rdf-schema#>)\n\n")
        out.write("Ontology(<%s>\n" % ONTOLOGY_IRI)
        out.write(f'  Annotation(rdfs:comment "{esc(comment)}")\n\n')

        out.write("  # ----- Object property declarations -----\n")
        for p in sorted(object_props, key=int):
            out.write(f"  Declaration(ObjectProperty(:{p}))\n")
            if p in clean_label:
                out.write(
                    f'  AnnotationAssertion(rdfs:label :{p} "{esc(clean_label[p])}")\n'
                )
            sup = obj_prop_parent.get(p)
            if sup:
                out.write(f"  SubObjectPropertyOf(:{p} :{sup})\n")
        if used_data_props:
            out.write("\n  # ----- Data property declarations -----\n")
            for p in sorted(used_data_props, key=int):
                out.write(f"  Declaration(DataProperty(:{p}))\n")
                if p in clean_label:
                    out.write(
                        f'  AnnotationAssertion(rdfs:label :{p} "{esc(clean_label[p])}")\n'
                    )

        out.write("\n  # ----- Class declarations + labels -----\n")
        for c in classes:
            out.write(f"  Declaration(Class(:{c}))\n")
            if c in clean_label:
                out.write(
                    f'  AnnotationAssertion(rdfs:label :{c} "{esc(clean_label[c])}")\n'
                )

        out.write("\n  # ----- Logical axioms (from OWL Expression refset) -----\n")
        for ax in class_axioms:
            out.write(f"  {ax}\n")
        out.write(")\n")
    print(f"Wrote {OFN_PATH}")
    print(
        f"  classes={len(classes)} object_properties={len(object_props)} "
        f"axioms={len(class_axioms)}"
    )

    # --- write workbook (preserve existing sheets, add/replace new one) ----
    # Done last so the OWL files are produced even if the .xlsx is locked open
    # in Excel; falls back to a standalone workbook on PermissionError.
    def write_book(path):
        with pd.ExcelWriter(path, engine="openpyxl") as w:
            for name, d in sheets.items():
                if name == "ReferencingConcepts":
                    continue
                d.to_excel(w, index=False, sheet_name=name)
            ref_df.to_excel(w, index=False, sheet_name="ReferencingConcepts")

    try:
        write_book(XLSX)
        print(f"Updated {XLSX}")
    except PermissionError:
        fallback = OUT_DIR / "autoimmune_disease_referencing.xlsx"
        with pd.ExcelWriter(fallback, engine="openpyxl") as w:
            ref_df.to_excel(w, index=False, sheet_name="ReferencingConcepts")
        print(
            f"!! {XLSX.name} is open/locked in Excel - wrote the new sheet to "
            f"{fallback.name} instead. Close Excel and re-run to merge it back."
        )


if __name__ == "__main__":
    main()
