"""Build SSSOM + biomappings-style equivalency files from confirmed cross-references.

When a curator marks a disease's database cross-reference as correct in the
reference-review page, those become exact-match mappings (ARI disease -> external
id). When they flag one as "needs change", that is recorded as a *negative*
mapping (exactMatch with a "Not" predicate modifier, biomappings-style). This
module renders/accumulates an SSSOM TSV and a simpler equivalencies TSV, and can
read them back so the review page can pre-highlight already-judged cells.
"""
import datetime

# database key -> bioregistry-style prefix for the object/target
PREFIX = {
    "snomed": "SNOMEDCT", "omop": "omop", "doid": "DOID", "umls": "umls",
    "mondo": "MONDO", "icd10": "icd10cm", "mesh": "mesh", "nci": "ncit",
    "dxcode": "SNOMEDCT",
}

CURIE_MAP = {
    "ARI": "https://diseases.autoimmuneregistry.org/disease/ARI_",
    "DOID": "http://purl.obolibrary.org/obo/DOID_",
    "MONDO": "http://purl.obolibrary.org/obo/MONDO_",
    "SNOMEDCT": "http://snomed.info/id/",
    "ncit": "http://purl.obolibrary.org/obo/NCIT_",
    "mesh": "http://id.nlm.nih.gov/mesh/",
    "umls": "https://uts.nlm.nih.gov/uts/umls/concept/",
    "icd10cm": "http://purl.bioontology.org/ontology/ICD10CM/",
    "omop": "https://athena.ohdsi.org/search-terms/terms/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "semapv": "https://w3id.org/semapv/vocab/",
    "orcid": "https://orcid.org/",
}

SSSOM_COLS = ["subject_id", "subject_label", "predicate_id", "predicate_modifier",
              "object_id", "mapping_justification", "author_id", "mapping_date"]
EQUIV_COLS = ["source_prefix", "source_id", "source_name", "relation",
              "target_prefix", "target_id", "type", "source"]

# prefix (as written in the object curie) -> review-page database key(s). One
# prefix can back more than one column (SNOMED is used for both snomed + dxcode),
# so the loader emits a judgment for every candidate key.
PREFIX_TO_DBS: dict[str, list[str]] = {}
for _db, _prefix in PREFIX.items():
    PREFIX_TO_DBS.setdefault(_prefix, []).append(_db)


def _object_curie(db, ident):
    return f"{PREFIX.get(db, db)}:{ident}"


def _sssom_header():
    lines = ["# curie_map:"]
    for k, v in CURIE_MAP.items():
        lines.append(f"#   {k}: {v}")
    lines += [
        "# mapping_set_id: https://diseases.autoimmuneregistry.org/mappings/ari.sssom.tsv",
        "# mapping_provider: https://www.autoimmuneregistry.org",
        "# mapping_set_title: ARI disease cross-reference mappings",
        "# license: https://creativecommons.org/publicdomain/zero/1.0/",
    ]
    return "\n".join(lines)


def _merge_tsv(existing, cols, new_rows, key_idx, header_block=""):
    existing_data = []
    if existing:
        for line in existing.splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("\t")
            if parts == cols:
                continue
            existing_data.append(parts)
    keys = set(tuple(r[i] for i in key_idx if i < len(r)) for r in existing_data)
    merged = list(existing_data)
    added = 0
    for r in new_rows:
        k = tuple(str(r[i]) for i in key_idx)
        if k in keys:
            continue
        keys.add(k); merged.append(r); added += 1
    out = []
    if header_block:
        out.append(header_block.rstrip("\n"))
    out.append("\t".join(cols))
    for r in merged:
        out.append("\t".join(str(x) for x in r))
    return "\n".join(out) + "\n", added


def build(confirmed, author, existing_sssom="", existing_equiv="", flagged=None):
    """Accumulate confirmed (positive) and flagged (negative) cross-references.

    ``confirmed`` and ``flagged`` are lists of ``{ari_id, name, db, ids}``.
    Negatives are written with a ``Not`` predicate modifier (SSSOM) and a
    ``skos:exactMatch`` relation tagged ``negative`` in the ``type`` column
    (equivalencies), matching the biomappings convention for incorrect mappings.
    """
    today = datetime.date.today().isoformat()
    sssom_rows, equiv_rows = [], []
    for items, modifier, eq_type in ((confirmed or [], "", "manual"),
                                     (flagged or [], "Not", "manual-negative")):
        for c in items:
            subj = c.get("ari_id") or ""
            name = c.get("name", "")
            for ident in c.get("ids", []):
                obj = _object_curie(c["db"], ident)
                sssom_rows.append([subj, name, "skos:exactMatch", modifier, obj,
                                   "semapv:ManualMappingCuration", author, today])
                equiv_rows.append(["ARI", (subj.split(":")[-1] if subj else ""), name,
                                   "skos:exactMatch", PREFIX.get(c["db"], c["db"]), str(ident),
                                   eq_type, author])
    # Dedup on (subject, predicate, modifier, object) so a positive and a later
    # negative for the same triple don't silently collapse into one another.
    sssom, n1 = _merge_tsv(existing_sssom, SSSOM_COLS, sssom_rows, (0, 2, 3, 4), _sssom_header())
    equiv, n2 = _merge_tsv(existing_equiv, EQUIV_COLS, equiv_rows, (0, 1, 4, 5, 6))
    return {"sssom": sssom, "equiv": equiv, "added": max(n1, n2)}


def load_judgments(sssom_text="", equiv_text=""):
    """Parse stored mapping files into per-cell judgments for pre-highlighting.

    Returns a list of ``{ari_id, prefix, dbs, id, judgment}`` where ``judgment``
    is ``"positive"`` or ``"negative"`` and ``dbs`` lists the review-page column
    keys the prefix maps to. SSSOM is canonical; the equivalencies file is used
    only as a fallback when no SSSOM is present.
    """
    out, seen = [], set()

    def _add(ari_id, prefix, ident, judgment):
        key = (ari_id, prefix, ident)
        if not prefix or not ident or key in seen:
            return
        seen.add(key)
        out.append({"ari_id": ari_id, "prefix": prefix, "id": ident,
                    "dbs": PREFIX_TO_DBS.get(prefix, []), "judgment": judgment})

    if sssom_text and sssom_text.strip():
        cols = None
        for line in sssom_text.splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("\t")
            if cols is None:
                cols = parts
                continue
            row = dict(zip(cols, parts))
            obj = row.get("object_id", "")
            prefix, _, ident = obj.partition(":")
            judgment = "negative" if (row.get("predicate_modifier", "").strip().lower() == "not") else "positive"
            _add(row.get("subject_id", ""), prefix, ident, judgment)
        return out

    if equiv_text and equiv_text.strip():
        cols = None
        for line in equiv_text.splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("\t")
            if cols is None:
                cols = parts
                continue
            row = dict(zip(cols, parts))
            judgment = "negative" if "negative" in row.get("type", "").lower() else "positive"
            ari = row.get("source_id", "")
            _add(("ARI:" + ari) if ari and not ari.startswith("ARI:") else ari,
                 row.get("target_prefix", ""), row.get("target_id", ""), judgment)
    return out
