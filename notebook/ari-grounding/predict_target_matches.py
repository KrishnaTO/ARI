"""Predict a target-database match for every (disease, target database) pair.

Two prediction routes, both offline:

1. **Lexical grounding** — the existing Gilda match reports
   (`doid_matches_all.csv`, `snomed_matches_all.csv`) give a candidate DOID,
   SNOMED code and OMOP concept id per disease.
2. **Cross-reference expansion** — Mondo and DOID terms carry equivalence
   cross-references into every other target database. Starting from an anchor
   (a curated `skos:exactMatch`, or a lexical match) the hub term that is or
   cross-references that anchor is located, and its own cross-references become
   predictions for the remaining databases.

A candidate the curators already rejected for that disease and database is
dropped — the rejection is the more recent judgement.

Writes notebook/ari-grounding/target_predictions.json:
  "<ARI ID>|<prefix>": [{"id", "name", "method", "evidence"}, ...]
ordered best-first. Consumed by resolve_target_labels.py (for labels) and
build_disease_target_matrix.py (for the report columns).
"""
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = Path("F:/1Projects/7Projects-Aurint/ARI/data/2-databases")
SSSOM = REPO / "mappings" / "ari.sssom.tsv"
HERE = Path(__file__).resolve().parent
OUT = HERE / "target_predictions.json"

TARGET_PREFIXES = ["SNOMEDCT", "omop", "DOID", "MONDO", "ncit",
                   "icd10cm", "mesh", "umls", "ORPHA", "OMIM"]

# Cross-reference prefixes as written by each hub ontology -> ARI prefix.
MONDO_XREF = {"DOID": "DOID", "Orphanet": "ORPHA", "OMIM": "OMIM", "SCTID": "SNOMEDCT",
              "MESH": "mesh", "NCIT": "ncit", "ICD10CM": "icd10cm", "UMLS": "umls"}
DOID_XREF = {"UMLS_CUI": "umls", "MIM": "OMIM", "NCI": "ncit", "MESH": "mesh",
             "ICD10CM": "icd10cm", "ORDO": "ORPHA"}
# Only equivalence-grade Mondo cross-references are used; MEDGEN, hierarchy and
# obsolete-side qualifiers are not equivalence claims.
MONDO_EQUIV = ("MONDO:equivalentTo", "MONDO:exact")

# --- curated state -----------------------------------------------------------
lines = [l for l in SSSOM.open(encoding="utf-8") if not l.startswith("#")]
mappings = list(csv.DictReader(lines, delimiter="\t"))

confirmed = defaultdict(list)     # ari_id -> [(prefix, local)]
rejected = defaultdict(set)       # (ari_id, prefix) -> {local}
disease_name = {}
for m in mappings:
    disease_name.setdefault(m["subject_id"], m["subject_label"])
    oid = m["object_id"]
    if oid.startswith("sssom:"):
        continue
    prefix, local = oid.split(":", 1)
    if m["predicate_modifier"] == "Not":
        rejected[(m["subject_id"], prefix)].add(local)
    else:
        confirmed[m["subject_id"]].append((prefix, local))

# --- lexical anchors from the existing Gilda reports -------------------------
lexical = defaultdict(dict)       # ari_id -> {prefix: (local, name, score, via)}
for r in csv.DictReader((HERE / "doid_matches_all.csv").open(encoding="utf-8")):
    if r["DOID"]:
        lexical[r["ARI ID"]]["DOID"] = (r["DOID"].split(":", 1)[1], r["DOID Label"],
                                        r["Score"], r["Matched Via"])
for r in csv.DictReader((HERE / "snomed_matches_all.csv").open(encoding="utf-8")):
    if r["SNOMED Code"]:
        lexical[r["ARI ID"]]["SNOMEDCT"] = (r["SNOMED Code"], r["SNOMED Name"],
                                            r["Score"], r["Matched Via"])
    if r["OMOP ConceptID"]:
        lexical[r["ARI ID"]]["omop"] = (r["OMOP ConceptID"], r["SNOMED Name"],
                                        r["Score"], r["Matched Via"])

# --- hub terms: Mondo --------------------------------------------------------
print("scanning mondo.obo", flush=True)
mondo_name = {}
mondo_xrefs = defaultdict(lambda: defaultdict(list))   # mondo id -> prefix -> [local]
xref_to_hub = defaultdict(set)                         # (prefix, local) -> {hub curie}
XREF_RE = re.compile(r"^xref: (\S+)(?:\s+\{(.*)\})?")


def add_mondo(term_id, name, xrefs, obsolete):
    if not term_id or not term_id.startswith("MONDO:") or obsolete:
        return
    mondo_name[term_id] = name
    for raw, qualifier in xrefs:
        if not any(q in qualifier for q in MONDO_EQUIV):
            continue
        if ":" not in raw:
            continue
        src, local = raw.split(":", 1)
        prefix = MONDO_XREF.get(src)
        if not prefix:
            continue
        mondo_xrefs[term_id][prefix].append(local)
        xref_to_hub[(prefix, local)].add(term_id)
    xref_to_hub[("MONDO", term_id.split(":", 1)[1])].add(term_id)


with (DB / "mondo.obo").open(encoding="utf-8") as fh:
    cur_id = cur_name = None
    xrefs, obsolete = [], False
    for line in fh:
        line = line.rstrip("\n")
        if line.startswith("["):
            add_mondo(cur_id, cur_name, xrefs, obsolete)
            cur_id = cur_name = None
            xrefs, obsolete = [], False
        elif line.startswith("id: "):
            cur_id = line[4:].strip()
        elif line.startswith("name: "):
            cur_name = line[6:].strip()
        elif line.startswith("is_obsolete: true"):
            obsolete = True
        elif line.startswith("xref: "):
            m = XREF_RE.match(line)
            if m:
                xrefs.append((m.group(1), m.group(2) or ""))
    add_mondo(cur_id, cur_name, xrefs, obsolete)

# --- hub terms: DOID ---------------------------------------------------------
print("scanning doid.owl", flush=True)
CLS_RE = re.compile(
    r'\n    <owl:Class rdf:about="http://purl\.obolibrary\.org/obo/DOID_(\d+)">(.*?)\n    </owl:Class>',
    re.S)
LABEL_RE = re.compile(r"<rdfs:label[^>]*>(.*?)</rdfs:label>", re.S)
DBXREF_RE = re.compile(r"<oboInOwl:hasDbXref[^>]*>(.*?)</oboInOwl:hasDbXref>", re.S)
DEPRECATED_RE = re.compile(r"<owl:deprecated[^>]*>true</owl:deprecated>")
SNOMED_SRC_RE = re.compile(r"^SNOMEDCT_US(?:_\d{4}_\d{2}_\d{2})?$")

doid_name = {}
doid_xrefs = defaultdict(lambda: defaultdict(list))
doid_text = (DB / "doid.owl").read_text(encoding="utf-8")
for local_id, blob in CLS_RE.findall(doid_text):
    lm = LABEL_RE.search(blob)
    if not lm or DEPRECATED_RE.search(blob):
        continue
    curie = "DOID:" + local_id
    doid_name[curie] = lm.group(1).strip()
    for raw in DBXREF_RE.findall(blob):
        raw = raw.strip()
        if ":" not in raw:
            continue
        src, local = raw.split(":", 1)
        prefix = "SNOMEDCT" if SNOMED_SRC_RE.match(src) else DOID_XREF.get(src)
        if not prefix:
            continue
        doid_xrefs[curie][prefix].append(local)
        xref_to_hub[(prefix, local)].add(curie)
    xref_to_hub[("DOID", local_id)].add(curie)
del doid_text

hub_name = dict(mondo_name)
hub_name.update(doid_name)
hub_xrefs = {}
hub_xrefs.update({k: dict(v) for k, v in mondo_xrefs.items()})
hub_xrefs.update({k: dict(v) for k, v in doid_xrefs.items()})

# --- SNOMED code -> OMOP standard concept id ---------------------------------
# Needed to carry a predicted SNOMED code through to an OMOP concept id.
print("scanning snomed/CONCEPT.csv", flush=True)
wanted_snomed = set()
for ari_id in set(confirmed) | set(lexical):
    for prefix, local in confirmed.get(ari_id, []):
        if prefix == "SNOMEDCT":
            wanted_snomed.add(local)
    if "SNOMEDCT" in lexical.get(ari_id, {}):
        wanted_snomed.add(lexical[ari_id]["SNOMEDCT"][0])
for hub, xr in hub_xrefs.items():
    for local in xr.get("SNOMEDCT", []):
        wanted_snomed.add(local)

snomed_to_omop = {}
snomed_std_name = {}          # only standard, non-invalid SNOMED Condition concepts
with (DB / "snomed" / "CONCEPT.csv").open(encoding="utf-8", newline="") as fh:
    rd = csv.reader(fh, delimiter="	", quoting=csv.QUOTE_NONE)
    header = next(rd)
    i_id, i_vocab, i_code = (header.index("concept_id"), header.index("vocabulary_id"),
                             header.index("concept_code"))
    i_name, i_std = header.index("concept_name"), header.index("standard_concept")
    i_invalid = header.index("invalid_reason")
    for rec in rd:
        if len(rec) <= i_invalid:
            continue
        if (rec[i_vocab] == "SNOMED" and rec[i_code] in wanted_snomed
                and rec[i_std] == "S" and not rec[i_invalid]):
            snomed_to_omop.setdefault(rec[i_code], rec[i_id])
            snomed_std_name.setdefault(rec[i_code], rec[i_name])

# --- predict -----------------------------------------------------------------
# A candidate can be produced by several routes. Each route carries a weight and
# the weights add up, so a candidate corroborated by several hub terms (or by a
# hub and the lexical match) outranks one supported by a single broad xref.
predictions = defaultdict(dict)          # (ari_id, prefix) -> {local: candidate}


def add(ari_id, prefix, local, name, method, evidence, weight):
    if not local or local in rejected.get((ari_id, prefix), ()):
        return
    # A retired or non-standard SNOMED concept is not a usable prediction; the
    # ontologies still carry xrefs to codes SNOMED has since deprecated.
    if prefix == "SNOMEDCT":
        if local not in snomed_std_name:
            return
        name = name or snomed_std_name[local]
    bucket = predictions[(ari_id, prefix)]
    cand = bucket.get(local)
    if cand is None:
        bucket[local] = {"id": local, "name": name or "", "method": method,
                         "evidence": evidence, "support": weight, "routes": 1}
        return
    cand["support"] += weight
    cand["routes"] += 1
    if not cand["name"] and name:
        cand["name"] = name
    if ORDER[method] < ORDER[cand["method"]]:
        cand["method"], cand["evidence"] = method, evidence


ORDER = {"xref via curated anchor": 0, "lexical grounding": 1, "xref via lexical anchor": 2}
ANCHOR_WEIGHT = {"curated": 2, "lexical": 1}

for ari_id in sorted(set(confirmed) | set(lexical)):
    anchors = []                                   # (prefix, local, grade, evidence)
    for prefix, local in confirmed.get(ari_id, []):
        anchors.append((prefix, local, "curated", "curated %s:%s" % (prefix, local)))
    for prefix, (local, _, score, via) in sorted(lexical.get(ari_id, {}).items()):
        anchors.append((prefix, local, "lexical",
                        "lexical match %s:%s (Gilda %s via %s)" % (prefix, local, score, via)))

    # Score each hub term by the anchors that reach it, so a hub corroborated by
    # several of the disease's own identifiers beats one reached from a single
    # broader cross-reference.
    hub_score = defaultdict(int)
    hub_grade = {}
    hub_evidence = {}
    for prefix, local, grade, evidence in anchors:
        for hub in sorted(xref_to_hub.get((prefix, local), ())):
            hub_score[hub] += ANCHOR_WEIGHT[grade]
            if grade == "curated" or hub not in hub_grade:
                if hub_grade.get(hub) != "curated":
                    hub_grade[hub] = grade
                    hub_evidence[hub] = evidence

    # Route 1: direct lexical predictions.
    for prefix, (local, name, score, via) in sorted(lexical.get(ari_id, {}).items()):
        add(ari_id, prefix, local, name, "lexical grounding",
            "Gilda score %s via %s" % (score, via), 2)

    # Route 2: cross-reference expansion through Mondo / DOID hub terms.
    for hub, score in sorted(hub_score.items()):
        grade = hub_grade[hub]
        method = "xref via curated anchor" if grade == "curated" else "xref via lexical anchor"
        evidence = hub_evidence[hub]
        hub_prefix, hub_local = hub.split(":", 1)
        add(ari_id, hub_prefix, hub_local, hub_name.get(hub), method,
            "%s from %s" % (hub, evidence), score)
        for out_prefix, locals_ in sorted(hub_xrefs.get(hub, {}).items()):
            for out_local in locals_:
                add(ari_id, out_prefix, out_local, None, method,
                    "%s xref, %s" % (hub, evidence), score)
                if out_prefix == "SNOMEDCT" and out_local in snomed_to_omop:
                    add(ari_id, "omop", snomed_to_omop[out_local], snomed_std_name[out_local],
                        method, "%s xref SCTID:%s, %s" % (hub, out_local, evidence), score)

out = {}
for (ari_id, prefix), cands in predictions.items():
    if prefix not in TARGET_PREFIXES:
        continue
    ranked = sorted(cands.values(),
                    key=lambda c: (-c["support"], ORDER[c["method"]], c["id"]))
    out["%s|%s" % (ari_id, prefix)] = ranked

OUT.write_text(json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
print("wrote %s (%d disease/database pairs, %d candidates)"
      % (OUT, len(out), sum(len(v) for v in out.values())))
by_prefix = defaultdict(int)
for key in out:
    by_prefix[key.split("|")[1]] += 1
for p in TARGET_PREFIXES:
    print("  %-10s %3d pairs" % (p, by_prefix[p]))
