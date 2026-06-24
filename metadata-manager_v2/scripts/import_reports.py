#!/usr/bin/env python3
"""Import the ARI disease reports into the metadata-manager v2 ontology.

Reads the curated report spreadsheets under ``data/4-reports/`` and folds every
disease (and its symptoms, age-of-onset, prevalence, clinical subtypes, external
references, authorship and DOID/SNOMED/UMLS/ICD/MeSH/NCI/OMOP cross-references)
into ``ontologies/ari_t1d.owl``.

Reports ``2_*`` (Proposed Diseases) and ``3_*`` (Proposed Changes) are
intentionally skipped -- only the confirmed catalogue is imported.

The import is additive and idempotent: a disease already present in the ontology
(matched by ARI ID, or by a name token-set so the curated "Type 1 diabetes
mellitus" absorbs the report's "Diabetes mellitus type 1") is enriched in place
rather than duplicated, and re-running does not create copies.

Usage:
    python scripts/import_reports.py [--reports DIR] [--output ari_t1d.owl] [--rebuild]

Dependencies: owlready2, openpyxl
"""
import argparse
import re
import sys
import types
from datetime import datetime, date
from pathlib import Path

import openpyxl
from owlready2 import (
    World, AnnotationProperty, DataProperty, ObjectProperty,
    label, comment, seeAlso,
)

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent                       # metadata-manager_v2
REPO_ROOT = PROJECT_ROOT.parent                  # ARI
DEFAULT_REPORTS = REPO_ROOT / "data" / "4-reports"
DEFAULT_ONTO = PROJECT_ROOT / "ontologies" / "ari_t1d.owl"

# Report file names (the 2_* / 3_* proposals are deliberately excluded).
F_CORE = "1_Core_ARI_Diseases.xlsx"
F_INFO = "4_Additional_Info_Index.xlsx"
F_DOID_MAP = "5_DOID_Mapping.xlsx"
F_DOID_ALL = "6_DOID_Matches_All.xlsx"
F_SNOMED = "7_SNOMED_Matches_All.xlsx"

TODAY = datetime.now().strftime("%Y-%m-%d %H:%M")

# A handful of tissue regions need a friendlier OWL class name than the raw label.
REGION_CLASS_OVERRIDE = {"All": "AllTissues"}
STOPWORDS = {"the", "of", "and", "a", "an", "to", "in", "with"}


# --------------------------------------------------------------------------- #
# Spreadsheet helpers
# --------------------------------------------------------------------------- #
def load_rows(path: Path, sheet: str) -> list:
    """Return each non-empty data row of *sheet* as a dict keyed by header."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[sheet]
    it = ws.iter_rows(values_only=True)
    headers = [str(h).strip() if h is not None else "" for h in next(it)]
    rows = []
    for r in it:
        if all(c is None for c in r):
            continue
        rows.append(dict(zip(headers, r)))
    wb.close()
    return rows


def s(val) -> str:
    return "" if val is None else str(val).strip()


def strip_prefix(val: str) -> str:
    """Drop a leading ``PREFIX:`` ontology qualifier (UMLS_CUI:, ICD10CM:, ...)."""
    return re.sub(r"^[A-Za-z0-9_]+:", "", s(val)).strip()


def split_ids(val, keep_prefix=False) -> list:
    """Split a comma/semicolon list of identifiers, stripping namespace prefixes."""
    if val is None:
        return []
    out = []
    for part in re.split(r"[;,]", str(val)):
        part = part.strip()
        if not part:
            continue
        out.append(part if keep_prefix else strip_prefix(part))
    # de-dupe, preserve order
    seen, uniq = set(), []
    for x in out:
        if x and x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def name_tokens(text: str) -> frozenset:
    return frozenset(re.findall(r"[a-z0-9]+", (text or "").lower())) - STOPWORDS


def camel(text: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", text or "")
    return "".join(p[:1].upper() + p[1:] for p in parts) or "Unknown"


def local_from_ari(ari_id: str) -> str:
    """'ARI:0001001' -> 'ARI_0001001'."""
    digits = re.sub(r"[^0-9]", "", ari_id) or ari_id
    return "ARI_" + digits


# --------------------------------------------------------------------------- #
# Build per-ARI-ID lookup tables from the reports
# --------------------------------------------------------------------------- #
def build_tables(reports: Path) -> dict:
    core = {}
    name_to_ari = {}
    for r in load_rows(reports / F_CORE, "Core ARI Diseases"):
        ari = s(r.get("ARI ID"))
        if not ari:
            continue
        core[ari] = r
        name_to_ari[s(r.get("Preferred Name")).lower()] = ari

    def ari_of(row):
        ari = s(row.get("ARI ID"))
        if ari:
            return ari
        return name_to_ari.get(s(row.get("Disease")).lower()) or \
            name_to_ari.get(s(row.get("disease")).lower())

    # ---- DOID (full matches report, then the flagged mapping report) ----
    doid = {}
    for r in load_rows(reports / F_DOID_ALL, "DOID Matches (All)"):
        ari, code = s(r.get("ARI ID")), strip_prefix(r.get("DOID"))
        if ari and code:
            doid.setdefault(ari, code)
    umls, icd, mesh, nci = {}, {}, {}, {}
    for r in load_rows(reports / F_DOID_ALL, "Matched Disease Details"):
        ari = s(r.get("ARI ID"))
        if not ari:
            continue
        if not doid.get(ari):
            c = strip_prefix(r.get("DOID"))
            if c:
                doid[ari] = c
        umls.setdefault(ari, split_ids(r.get("UMLS xrefs")))
        icd.setdefault(ari, split_ids(r.get("ICD xrefs")))
        mesh.setdefault(ari, split_ids(r.get("MESH xrefs")))
        nci.setdefault(ari, split_ids(r.get("NCI xrefs")))

    # ---- SNOMED fallback ----
    snomed_fallback = {}
    for r in load_rows(reports / F_SNOMED, "SNOMED Matches (All)"):
        ari, code = s(r.get("ARI ID")), s(r.get("SNOMED Code"))
        if ari and code:
            snomed_fallback.setdefault(ari, code)

    # ---- Symptoms (skip body-region category headers and ':'-terminated sub-heads) ----
    symptoms = {}
    for r in load_rows(reports / F_INFO, "Symptoms"):
        ari = s(r.get("ARI ID"))
        text = s(r.get("symptom"))
        if not ari or not text:
            continue
        if s(r.get("latin")).lower() == "cat":
            continue
        if text.endswith(":"):
            continue
        symptoms.setdefault(ari, []).append((int(r.get("seq") or 0), text))

    # ---- Age of onset (prefer the 'General' row) ----
    onset = {}
    for r in load_rows(reports / F_INFO, "Age of Onset"):
        ari = s(r.get("ARI ID"))
        if not ari:
            continue
        onset.setdefault(ari, []).append(r)

    def as_int(v):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return None

    def age_range(ari):
        rows = onset.get(ari, [])
        if not rows:
            return ""
        row = next((x for x in rows if s(x.get("datatype")) == "General"), rows[0])
        dt = s(row.get("datatype"))
        lo, hi = as_int(row.get("minage")), as_int(row.get("maxage"))
        if lo is not None and hi is not None:
            base = f"{lo}-{hi} years"
            if dt and dt not in ("General",):
                base = f"{dt}: {base}"
            return base
        # descriptive datatype (e.g. "Can occur at any age.")
        if dt and dt.lower() not in ("no data.", "general"):
            return dt
        return ""

    # ---- Prevalence (JCI) ----
    prev = {}
    for r in load_rows(reports / F_INFO, "Prevalence (JCI)"):
        ari = ari_of(r)
        if not ari:
            continue
        prev.setdefault(ari, r)

    # ---- Reference links (external web links only) ----
    reflinks = {}
    for r in load_rows(reports / F_INFO, "Reference Links"):
        ari = s(r.get("ARI ID"))
        url = s(r.get("url"))
        text = s(r.get("data")) or s(r.get("datatype"))
        if not ari or not url.lower().startswith("http"):
            continue
        reflinks.setdefault(ari, []).append(f"{text} | {url}")

    # ---- Authorship / byline ----
    authors = {}
    for r in load_rows(reports / F_INFO, "Authorship-Byline"):
        ari = s(r.get("ARI ID"))
        if not ari:
            continue
        byline = s(r.get("byline"))
        link = s(r.get("bylink"))
        d = r.get("bydate")
        when = d.strftime("%Y-%m") if isinstance(d, (datetime, date)) else s(d)
        authors[ari] = {
            "byline": (f"{byline} | {link}" if link else byline),
            "date": when,
        }

    # ---- Clinical subtypes ----
    subtypes = {}
    for r in load_rows(reports / F_INFO, "Subtypes"):
        ari = ari_of(r)
        name = s(r.get("subtype"))
        if not ari or not name:
            continue
        descr = s(r.get("descr"))
        subtypes.setdefault(ari, []).append(f"{name} - {descr}" if descr else name)

    # ---- Survey codes ----
    survey = {}
    for r in load_rows(reports / F_INFO, "Survey Codes"):
        ari = ari_of(r)
        code = s(r.get("code"))
        if ari and code:
            survey.setdefault(ari, code)

    return {
        "core": core, "doid": doid, "umls": umls, "icd": icd, "mesh": mesh,
        "nci": nci, "snomed_fallback": snomed_fallback, "symptoms": symptoms,
        "age_range": age_range, "prev": prev, "reflinks": reflinks,
        "authors": authors, "subtypes": subtypes, "survey": survey,
    }


# --------------------------------------------------------------------------- #
# Ontology import
# --------------------------------------------------------------------------- #
def import_into(onto_path: Path, reports: Path) -> dict:
    world = World()
    placeholder = world.get_ontology("http://ari.local/ontology")
    with open(onto_path, "rb") as f:
        onto = placeholder.load(fileobj=f)
    base = onto.base_iri

    def P(name):
        return world[base + name]

    # Ensure the report-specific properties exist (created once, in the onto NS).
    def ensure(name, kind):
        p = world[base + name]
        if p is None:
            with onto:
                p = types.new_class(name, (kind,))
        return p

    ensure("ARI_OMOP", AnnotationProperty)
    ensure("ARI_DXCODE", AnnotationProperty)
    ensure("ARI_MESH", AnnotationProperty)
    ensure("ARI_NCI", AnnotationProperty)
    ensure("ARI_RefLink", AnnotationProperty)
    ensure("ARI_Author", AnnotationProperty)
    ensure("ARI_AuthorDate", AnnotationProperty)
    ensure("ARI_ClinicalSubtype", AnnotationProperty)
    ensure("ARI_SurveyCode", AnnotationProperty)

    Disease = onto.AutoimmuneDisease
    Symptom = onto.Symptom
    root_tissue = onto.MulticellularAnatomicalStructure

    def get_label(ent):
        v = label[ent]
        return str(v[0]) if v else ent.name

    # Index existing diseases (for idempotent enrich-in-place).
    existing = list(Disease.instances(world=world))
    by_ari = {}
    by_tokens = {}
    for ind in existing:
        for a in P("ARI_ID")[ind]:
            by_ari[str(a)] = ind
        by_tokens.setdefault(name_tokens(get_label(ind)), ind)

    # Diseases are created under the registry namespace from the report's IRI
    # column (https://diseases.autoimmuneregistry.org/disease/...) rather than the
    # ontology's own aurint.org namespace.
    ns_cache = {}

    def get_ns(base_iri):
        if base_iri not in ns_cache:
            ns_cache[base_iri] = onto.get_namespace(base_iri)
        return ns_cache[base_iri]

    def split_iri(iri):
        """Split a full IRI into (namespace_base, local_name)."""
        if "#" in iri:
            b, _, n = iri.rpartition("#")
            return b + "#", n
        b, _, n = iri.rpartition("/")
        return b + "/", n

    tissue_cache = {}

    def tissue_individual(region):
        if region in tissue_cache:
            return tissue_cache[region]
        cname = REGION_CLASS_OVERRIDE.get(region, camel(region))
        cls = world[base + cname]
        if cls is None:
            with onto:
                cls = types.new_class(cname, (root_tissue,))
            label[cls] = [region]
        iname = "Tissue_" + cname
        ind = world[base + iname]
        if ind is None:
            with onto:
                ind = cls(iname)
            label[ind] = [region]
        tissue_cache[region] = ind
        return ind

    def set_if_empty(prop, ent, values):
        if prop is not None and values and not prop[ent]:
            prop[ent] = list(values)

    def set_always(prop, ent, values):
        if prop is not None:
            prop[ent] = list(values)

    def merge_into(prop, ent, values):
        if prop is None or not values:
            return
        cur = [str(x) for x in prop[ent]]
        for v in values:
            if v and v not in cur:
                cur.append(v)
        prop[ent] = cur

    tables = build_tables(reports)
    core = tables["core"]
    age_range = tables["age_range"]

    created, enriched, sym_added = 0, 0, 0

    for ari, rec in core.items():
        pref = s(rec.get("Preferred Name"))
        report_iri = s(rec.get("IRI"))
        # locate or create the disease individual
        ind = by_ari.get(ari) or by_tokens.get(name_tokens(pref))
        is_new = ind is None
        if is_new:
            ind = world[report_iri] if report_iri else world[base + local_from_ari(ari)]
            if ind is None:
                if report_iri:
                    iri_base, iri_name = split_iri(report_iri)
                    with onto:
                        ind = Disease(iri_name, namespace=get_ns(iri_base))
                else:
                    with onto:
                        ind = Disease(local_from_ari(ari))
                label[ind] = [pref]
            P("ARI_Obsolete")[ind] = ["false"]
            created += 1
        else:
            # curated disease being merged (e.g. T1D): adopt the registry IRI
            if report_iri and ind.iri != report_iri:
                ind.iri = report_iri
            enriched += 1

        # ----- identifiers -----
        set_always(P("ARI_ID"), ind, [ari])
        snomed = split_ids(rec.get("SNOMED Code(s)")) or \
            split_ids(tables["snomed_fallback"].get(ari))
        set_if_empty(P("ARI_SNOMED"), ind, snomed)
        set_if_empty(P("ARI_DOID"), ind, [tables["doid"][ari]] if tables["doid"].get(ari) else [])
        set_if_empty(P("ARI_UMLS"), ind, tables["umls"].get(ari, []))
        set_if_empty(P("ARI_ICD10"), ind, tables["icd"].get(ari, []))
        set_if_empty(P("ARI_MESH"), ind, tables["mesh"].get(ari, []))
        set_if_empty(P("ARI_NCI"), ind, tables["nci"].get(ari, []))
        if s(rec.get("OMOP ConceptID")):
            set_if_empty(P("ARI_OMOP"), ind, [s(rec.get("OMOP ConceptID"))])
        if s(rec.get("Concept Code (DXCODE)")):
            set_if_empty(P("ARI_DXCODE"), ind, [s(rec.get("Concept Code (DXCODE)"))])

        # ----- core descriptive fields -----
        if s(rec.get("Definition")):
            if not comment[ind]:
                comment[ind] = [s(rec.get("Definition"))]
        merge_into(P("ARI_Synonym"), ind, split_ids(rec.get("Synonyms")))
        # definition source: keep the full citation, pull out any PubMed links
        defsrc = s(rec.get("Definition Source(s)"))
        if defsrc:
            set_if_empty(P("ARI_DefSource"), ind, [defsrc])
            pmids = [u for u in re.findall(r"https?://[^\s;]+", defsrc) if "pubmed" in u.lower()]
            set_if_empty(P("ARI_Pubmed"), ind, pmids)
        set_if_empty(P("evidenceQuality"), ind, [s(rec.get("Evidence Level"))] if s(rec.get("Evidence Level")) else [])
        set_if_empty(P("diseaseCategory"), ind, [s(rec.get("Autoimmune Modifier"))] if s(rec.get("Autoimmune Modifier")) else [])
        if s(rec.get("Version")):
            set_if_empty(P("ARI_Version"), ind, [s(rec.get("Version"))])

        # ----- target tissue (new diseases only; keep curated targets) -----
        if is_new and s(rec.get("Tissue Region")):
            P("targetsTissue")[ind].append(tissue_individual(s(rec.get("Tissue Region"))))

        # ----- prevalence -----
        pr = tables["prev"].get(ari)
        if pr:
            def num(v):
                try:
                    f = float(v)
                    return f if f > 0 else None
                except (TypeError, ValueError):
                    return None
            us = num(pr.get("usprev"))
            if us is not None and not P("prevalencePer100k")[ind]:
                P("prevalencePer100k")[ind] = [us]
            bits = []
            for lbl, key in (("Female", "femaleprev"), ("Male", "maleprev")):
                v = num(pr.get(key))
                if v is not None:
                    bits.append(f"{lbl} {v:g}/100k")
            ratio = num(pr.get("fmratio"))
            if ratio is not None:
                bits.append(f"F:M ratio {ratio:g}")
            if bits:
                set_if_empty(P("ARI_PrevalenceDesc"), ind, ["; ".join(bits)])

        # ----- age of onset -----
        ar = age_range(ari)
        if ar:
            set_if_empty(P("ageRange"), ind, [ar])

        # ----- report-sourced extras -----
        set_always(P("ARI_RefLink"), ind, tables["reflinks"].get(ari, []))
        set_always(P("ARI_ClinicalSubtype"), ind, tables["subtypes"].get(ari, []))
        if tables["authors"].get(ari):
            set_always(P("ARI_Author"), ind, [tables["authors"][ari]["byline"]])
            set_always(P("ARI_AuthorDate"), ind, [tables["authors"][ari]["date"]])
        if tables["survey"].get(ari):
            set_always(P("ARI_SurveyCode"), ind, [tables["survey"][ari]])

        # ----- symptoms (only when the disease has none yet) -----
        if not P("hasSymptom")[ind]:
            for seq, text in sorted(tables["symptoms"].get(ari, [])):
                sym_local = f"Sym_{re.sub(r'[^0-9]', '', ari)}_{seq}"
                with onto:
                    sym = Symptom(sym_local)
                label[sym] = [text]
                P("ARI_Obsolete")[sym] = ["false"]
                P("hasSymptom")[ind].append(sym)
                sym_added += 1

        # ----- changelog -----
        clog = P("ARI_ChangeLog")
        if clog is not None:
            verb = "Imported from ARI core reports" if is_new else "Enriched from ARI core reports"
            clog[ind] = list(clog[ind]) + [f"{TODAY} | Importer | {verb}"]

    onto.save(file=str(onto_path), format="rdfxml")
    return {
        "created": created, "enriched": enriched, "symptoms": sym_added,
        "total_diseases": len(list(Disease.instances(world=world))),
        "classes": len(list(onto.classes())),
        "individuals": len(list(onto.individuals())),
    }


def main():
    ap = argparse.ArgumentParser(description="Import ARI reports into the v2 ontology")
    ap.add_argument("--reports", default=str(DEFAULT_REPORTS), help="data/4-reports directory")
    ap.add_argument("--output", default=str(DEFAULT_ONTO), help="ontology .owl file to import into")
    ap.add_argument("--rebuild", action="store_true",
                    help="regenerate the curated T1D base ontology first")
    args = ap.parse_args()

    reports = Path(args.reports)
    out = Path(args.output)

    if args.rebuild or not out.exists():
        sys.path.insert(0, str(HERE))
        import build_t1d_ontology
        out.parent.mkdir(parents=True, exist_ok=True)
        build_t1d_ontology.build_ontology(str(out))
        print(f"Rebuilt curated base: {out}")

    if not reports.exists():
        sys.exit(f"Reports directory not found: {reports}")

    stats = import_into(out, reports)
    print("OK Import complete:")
    print(f"  Output:          {out}")
    print(f"  Diseases created: {stats['created']}")
    print(f"  Diseases enriched:{stats['enriched']}")
    print(f"  Symptoms added:   {stats['symptoms']}")
    print(f"  Total diseases:   {stats['total_diseases']}")
    print(f"  Classes:          {stats['classes']}")
    print(f"  Individuals:      {stats['individuals']}")


if __name__ == "__main__":
    main()
