"""Build a human-readable summary of what changed between the current ontology
and a baseline (the source branch), for inclusion in a pull-request body.
"""

# field key -> display label (covers the editable + key display fields)
FIELDS = [
    ("name", "Label"), ("definition", "Definition"), ("synonyms", "Synonyms"),
    ("clinical_subtypes", "Clinical subtypes"),
    ("snomed", "SNOMED"), ("omop", "OMOP"), ("dxcode", "Concept code (DXCODE)"),
    ("doid", "DOID"), ("umls", "UMLS"), ("mondo", "MONDO"), ("icd10", "ICD-10"),
    ("mesh", "MeSH"), ("nci", "NCI"),
    ("def_source", "Definition source"), ("obsolete", "Obsolete"), ("version", "Version"),
    ("disease_category", "Category"), ("evidence_quality", "Evidence quality"),
    ("prevalence_per_100k", "Prevalence /100k"), ("prevalence_value", "Estimated cases"),
    ("incidence_rate", "Incidence rate"), ("demographic_bias", "Demographic bias"),
    ("age_range", "Age range"), ("prevalence_desc", "Prevalence description"),
]


def _fmt(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, (list, tuple)):
        return ", ".join(str(x) for x in v)
    return str(v)


def _cell(v):
    s = _fmt(v).replace("|", "\\|").replace("\n", " ")
    return (s[:300] + "…") if len(s) > 300 else (s or "_(empty)_")


def _rows(service):
    out = {}
    for it in service.get_diseases_list():
        d = service.get_disease_detail(it["iri"])
        key = (d.get("ari_id") or [None])[0] or d.get("iri")
        out[key] = d
    return out


def build_change_summary(current_service, baseline_service) -> str:
    cur = _rows(current_service)
    base = _rows(baseline_service)
    blocks = []

    for key, d in sorted(cur.items(), key=lambda kv: _fmt(kv[1].get("name"))):
        name = _fmt(d.get("name")) or key
        if key not in base:
            blocks.append(f"### {name} ({key}) — **new disease**")
            continue
        b = base[key]
        diffs = []
        for fkey, label in FIELDS:
            ov, nv = _fmt(b.get(fkey)), _fmt(d.get(fkey))
            if ov != nv:
                diffs.append((label, b.get(fkey), d.get(fkey)))
        if diffs:
            tbl = ["### " + name + " (" + key + ")", "",
                   "| Field | Previous | New |", "| --- | --- | --- |"]
            for label, ov, nv in diffs:
                tbl.append(f"| {label} | {_cell(ov)} | {_cell(nv)} |")
            blocks.append("\n".join(tbl))

    for key, b in sorted(base.items(), key=lambda kv: _fmt(kv[1].get("name"))):
        if key not in cur:
            blocks.append(f"### {_fmt(b.get('name')) or key} ({key}) — **removed**")

    if not blocks:
        return "_No field-level differences detected versus the source branch._"
    return "\n\n".join(blocks)
