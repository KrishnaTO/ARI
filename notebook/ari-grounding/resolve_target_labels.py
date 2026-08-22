"""Resolve a label for every mapped and predicted target id.

Covers every object_id in mappings/ari.sssom.tsv and every candidate in
notebook/ari-grounding/target_predictions.json, so run predict_target_matches.py
first.

Local vocabulary/ontology copies under data/2-databases are used wherever they
cover the vocabulary. ORPHA and NCIT have no usable local copy (the local OMOP
NCIt export only carries AJCC staging chapters), so those two are resolved via
the EBI OLS4 API. UMLS has no downloadable label source here; CUIs are labelled
from the DOID/MONDO term that cross-references them, which is the same route
sparql/get_UMLS_id.md already uses for CUI extraction.

Writes notebook/ari-grounding/target_labels.json: curie -> [label, source].
"""
import csv, json, re, sys, urllib.parse, urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = Path("F:/1Projects/7Projects-Aurint/ARI/data/2-databases")
SSSOM = REPO / "mappings" / "ari.sssom.tsv"
PREDICTIONS = REPO / "notebook" / "ari-grounding" / "target_predictions.json"
OUT = REPO / "notebook" / "ari-grounding" / "target_labels.json"

lines = [l for l in SSSOM.open(encoding="utf-8") if not l.startswith("#")]
rows = list(csv.DictReader(lines, delimiter="\t"))

wanted = {}
for r in rows:
    oid = r["object_id"]
    if oid.startswith("sssom:"):
        continue
    prefix, local = oid.split(":", 1)
    wanted.setdefault(prefix, set()).add(local)

for key, cands in json.loads(PREDICTIONS.read_text(encoding="utf-8")).items():
    prefix = key.split("|", 1)[1]
    for c in cands:
        wanted.setdefault(prefix, set()).add(c["id"])

g = lambda p: wanted.get(p, set())

labels = {}

# --- OMOP-format vocabulary exports (SNOMED, OMOP concept ids, ICD10CM, MeSH)
def omop_pass(path):
    src = path.parent.name + "/CONCEPT.csv"
    snomed, omop, icd, mesh = g("SNOMEDCT"), g("omop"), g("icd10cm"), g("mesh")
    with path.open(encoding="utf-8", newline="") as fh:
        rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
        header = next(rd)
        i_id, i_name = header.index("concept_id"), header.index("concept_name")
        i_vocab, i_code = header.index("vocabulary_id"), header.index("concept_code")
        for rec in rd:
            if len(rec) <= i_code:
                continue
            cid, name, vocab, code = rec[i_id], rec[i_name], rec[i_vocab], rec[i_code]
            if cid in omop:
                labels.setdefault("omop:" + cid, [name, src])
            if vocab == "SNOMED" and code in snomed:
                labels.setdefault("SNOMEDCT:" + code, [name, src])
            elif vocab == "ICD10CM" and code in icd:
                labels.setdefault("icd10cm:" + code, [name, src])
            elif vocab == "MeSH" and code in mesh:
                labels.setdefault("mesh:" + code, [name, src])

for concept_csv in (DB / "snomed" / "CONCEPT.csv", DB / "mesh-icd-ncit-clinvar" / "CONCEPT.csv"):
    print("scanning", concept_csv, flush=True)
    omop_pass(concept_csv)

# --- DOID (doid.owl) + UMLS CUI cross-references -----------------------------
# Top-level owl:Class blocks are indented four spaces; anonymous nested classes
# are indented further, so anchoring on indentation keeps a block intact.
print("scanning doid.owl", flush=True)
CLS_RE = re.compile(
    r'\n    <owl:Class rdf:about="http://purl\.obolibrary\.org/obo/DOID_(\d+)">(.*?)\n    </owl:Class>',
    re.S)
LABEL_RE = re.compile(r"<rdfs:label[^>]*>(.*?)</rdfs:label>", re.S)
XREF_RE = re.compile(r"<oboInOwl:hasDbXref[^>]*>(.*?)</oboInOwl:hasDbXref>", re.S)
umls_wanted, doid_wanted = g("umls"), g("DOID")
doid_text = (DB / "doid.owl").read_text(encoding="utf-8")
for local, blob in CLS_RE.findall(doid_text):
    lm = LABEL_RE.search(blob)
    if not lm:
        continue
    name, curie = lm.group(1).strip(), "DOID:" + local
    if local in doid_wanted:
        labels.setdefault(curie, [name, "doid.owl"])
    for x in XREF_RE.findall(blob):
        x = x.strip()
        if x.startswith("UMLS_CUI:") and x.split(":", 1)[1] in umls_wanted:
            labels.setdefault("umls:" + x.split(":", 1)[1],
                              [name, "doid.owl xref (%s)" % curie])
del doid_text

# --- MONDO (mondo.obo) + UMLS CUI cross-references ---------------------------
print("scanning mondo.obo", flush=True)
mondo_wanted = g("MONDO")

def take_mondo(term_id, term_name, xrefs):
    if not (term_id and term_name and ":" in term_id):
        return
    if term_id.startswith("MONDO:") and term_id.split(":", 1)[1] in mondo_wanted:
        labels.setdefault(term_id, [term_name, "mondo.obo"])
    for x in xrefs:
        if x.startswith("UMLS:") and x.split(":", 1)[1] in umls_wanted:
            labels.setdefault("umls:" + x.split(":", 1)[1],
                              [term_name, "mondo.obo xref (%s)" % term_id])

with (DB / "mondo.obo").open(encoding="utf-8") as fh:
    cur_id = cur_name = None
    xrefs = []
    for line in fh:
        line = line.rstrip("\n")
        if line.startswith("["):
            take_mondo(cur_id, cur_name, xrefs)
            cur_id = cur_name = None
            xrefs = []
        elif line.startswith("id: "):
            cur_id = line[4:].strip()
        elif line.startswith("name: "):
            cur_name = line[6:].strip()
        elif line.startswith("xref: "):
            xrefs.append(line[6:].split(" ")[0].strip())
    take_mondo(cur_id, cur_name, xrefs)

# --- OMIM (OMIM.ttl) ---------------------------------------------------------
print("scanning OMIM.ttl", flush=True)
SUBJ_RE = re.compile(r"^<http://purl\.bioontology\.org/ontology/OMIM/([^>]+)> a owl:Class")
PREF_RE = re.compile(r'skos:prefLabel """(.*?)"""')
omim_wanted = g("OMIM")
with (DB / "OMIM.ttl").open(encoding="utf-8") as fh:
    cur = None
    for line in fh:
        m = SUBJ_RE.match(line)
        if m:
            cur = m.group(1) if m.group(1) in omim_wanted else None
            continue
        if cur:
            pm = PREF_RE.search(line)
            if pm:
                labels.setdefault("OMIM:" + cur, [pm.group(1), "OMIM.ttl"])
                cur = None

# --- ORPHA / NCIT via EBI OLS4 ----------------------------------------------
def ols4_label(ontology, iri):
    quoted = urllib.parse.quote(urllib.parse.quote(iri, safe=""), safe="")
    url = "https://www.ebi.ac.uk/ols4/api/v2/ontologies/%s/classes/%s" % (ontology, quoted)
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.load(resp)
    lab = data.get("label")
    if isinstance(lab, list):
        lab = lab[0]
    if isinstance(lab, dict):
        lab = lab.get("value")
    return lab

for prefix, ontology, iri_tpl in (
        ("ORPHA", "ordo", "http://www.orpha.net/ORDO/Orphanet_%s"),
        ("ncit", "ncit", "http://purl.obolibrary.org/obo/NCIT_%s")):
    todo = sorted(i for i in g(prefix) if "%s:%s" % (prefix, i) not in labels)
    print("resolving %d %s ids via OLS4 (%s)" % (len(todo), prefix, ontology), flush=True)
    for local in todo:
        try:
            lab = ols4_label(ontology, iri_tpl % local)
        except Exception as exc:                  # noqa: BLE001
            print("%s %s: %s" % (prefix, local, exc), file=sys.stderr)
            continue
        if lab:
            labels["%s:%s" % (prefix, local)] = [lab, "EBI OLS4 (%s)" % ontology]

OUT.write_text(json.dumps(labels, indent=1, sort_keys=True), encoding="utf-8")
total = sum(len(v) for v in wanted.values())
print("resolved %d / %d distinct object ids -> %s" % (len(labels), total, OUT))
for p in sorted(wanted):
    hit = sum(1 for i in wanted[p] if "%s:%s" % (p, i) in labels)
    print("  %-10s %3d/%3d" % (p, hit, len(wanted[p])))
