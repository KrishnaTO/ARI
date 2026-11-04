"""Apply the accepted decisions of report 13 (data/4-reports/13_Non_Symptom_Review.tsv) to the OWL.

Every row whose decision is "accept" is handled here, or the script stops. A row is one of:

  - nothing to do: "drop" (the entry is already obsolete and listed by no disease, or only report 4
    has it), "no field", "check the source" (still open), or a cross-reference whose condition holds;
  - already held: the content is in the disease record already, mostly in its description
    (rdfs:comment; ari_disease.owl holds no IAO_0000115) or as a biomarker, antibody, trigger or
    associated disease. HELD names where, and the script checks that it is there;
  - an edit (EDITS, and the heading rules below): a symptomDescription or likelihood on entries the
    disease lists, a symptom restored, a trigger, treatment or associated disease added, or a
    sentence added to the description.

A heading's proposal applies to the entries it heads (the row's `after`): a stage or population
heading becomes their symptomDescription, a frequency heading their likelihood. Each changed disease
gets an ARI_ChangeLog line. A rerun finds everything applied and changes nothing. Run
tools/format-owl.sh on ontologies/ari_disease.owl and ontologies/ari_symptoms.owl afterwards, then
build_symptom_report.py and build_non_symptom_review.py.

Usage: python apply_non_symptom_review.py
"""
import collections, csv, datetime, hashlib, os, re, sys
import xml.etree.ElementTree as ET

from build_non_symptom_review import REVIEW
from build_symptom_report import ARI, ARI_BASE, DISEASE, NOT_A_SYMPTOM, OWL, RDF, RDFS, ROOT

sys.path.insert(0, os.path.join(ROOT, "notebook", "biomarker-concepts"))
from model import _declared_namespaces, _serialise  # noqa: E402

SYMPTOMS = os.path.join(ROOT, "ontologies", "ari_symptoms.owl")
ARIS = "http://www.aurint.org/ontologies/ari-symptoms#"
SKOS = "{http://www.w3.org/2004/02/skos/core#}"
OBO_IN_OWL = "{http://www.geneontology.org/formats/oboInOwl#}"
OBO = "http://purl.obolibrary.org/obo/"
CURATOR = "KrishnaTO"
LOG = "Report 13 review (ARI#162)"

# ARIS classes a restored symptom needs that ari_symptoms.owl lacks.
NEW_CLASSES = {
    "ARIS_0000766": dict(label="Post-exertional malaise", parent=ARIS + "ARIS_0000301",  # Malaise
                         exact=[OBO + "HP_0030973"],  # Postexertional symptom exacerbation
                         broad=[OBO + "SYMP_0019176"]),  # malaise: SYMP has no narrower term
}

# Text a stage or population heading gives the entries under it, where it is not the heading less
# its colon.
HEADING_TEXT = {"Women:": "In women", "Men:": "In men"}

# (ARI ID, entry) -> what already holds the content: ("comment", text in rdfs:comment),
# ("biomarker", its rdfs:comment), ("antibody",), ("trigger", label), ("associated", value),
# ("parent", ARI ID of a disease whose hasParentDisease must name this one).
HELD = {
    ("ARI:0001001", "Arises in younger individuals, usually under the age of 70 years"):
        [("comment", "arises in younger individuals, usually under the age of 70")],
    ("ARI:0001001", "Has prominent involvement of the head and neck"):
        [("comment", "prominent involvement of the head and neck")],
    ("ARI:0001001", "Involves mucous membranes"): [("comment", "skin and mucus membranes")],
    ("ARI:0001016", "Clinically amyopathic presentation / minimal muscle weakness"):
        [("comment", "clinically amyopathic presentation with minimal muscle weakness")],
    ("ARI:0001022", "Antecedent gastroenteritis or upper respiratory prodrome"):
        [("trigger", "Viral gastroenteritis or respiratory infections")],
    ("ARI:0001036", "Temporal association with adjuvant/foreign material exposure"):
        [("trigger", "Aluminum adjuvants in vaccines"), ("trigger", "Silicone breast implants")],
    ("ARI:0001039", "Extreme elevation of serum creatine kinase (>10–50× ULN)"):
        [("biomarker", "Extreme elevation of serum creatine kinase (>10–50× ULN)")],
    ("ARI:0001039", "Absence of extramuscular systemic manifestations"):
        [("comment", "no extramuscular systemic manifestations")],
    ("ARI:0001043", "Symptoms can be similar to pancreatic cancer"):
        [("comment", "often mistaken for pancreatic cancer")],
    ("ARI:0001050", "See: autoimmune urticaria and autoimmune angioedema."):
        [("parent", "ARI:0001023"), ("parent", "ARI:0001049")],
    ("ARI:0001050", 'See: <a href="/disease_profile?disease=autoimmune-urticaria">autoimmune urticaria</a>'
                    ' and <a href="/disease_profile?disease=autoimmune-angioedema">autoimmune angioedema</a>.'):
        [("parent", "ARI:0001023"), ("parent", "ARI:0001049")],
    ("ARI:0001057", "Flare/remission pattern to symptoms"): [("comment", "flare and remission pattern")],
    ("ARI:0001058", "Active systemic lupus erythematosus manifestations"):
        [("associated", "Systemic lupus erythematosus (definitive)")],
    ("ARI:0001094", "Severely abnormal post-coital test (poor sperm motility and survival in cervical mucus)"):
        [("biomarker", "Severely abnormal post-coital test (poor sperm motility and survival in cervical mucus)")],
    ("ARI:0001113", "Spontaneous clinical remission within 3–6 months"):
        [("comment", "spontaneous clinical remission within 3–6 months")],
    ("ARI:0001114", "Concomitant systemic autoimmune disease (SLE, Sjögren's)"):
        [("associated", "Systemic lupus erythematosus (present in >50% of Type B patients)"),
         ("associated", "Sjogren's syndrome")],
    ("ARI:0001151", "Donath-Landsteiner biphasic hemolysin antibody positivity"): [("antibody",)],
    ("ARI:0001164", "Absence of orthostatic hypotension"): [("comment", "without orthostatic hypotension")],
    ("ARI:0001191", "Normal motor examination and preserved deep tendon reflexes"):
        [("comment", "Motor examination and deep tendon reflexes are normal")],
    ("ARI:0001219", "Asymptomatic presentation prior to dissection or rupture"):
        [("comment", "no symptoms before dissection or rupture")],
    ("ARI:0001227", "Failure of cervical mucus penetration on postcoital testing"):
        [("biomarker", "Failure of cervical mucus penetration on postcoital testing")],
    ("ARI:0001227", "Spontaneous macroscopic or microscopic sperm agglutination in ejaculate"):
        [("biomarker", "Spontaneous macroscopic or microscopic sperm agglutination in ejaculate")],
    ("ARI:0001227", "Markedly decreased progressive sperm forward motility"):
        [("biomarker", "Markedly decreased progressive sperm forward motility")],
    ("ARI:0001228", "Completely normal cognition, sleep, and mood between distinct episodes"):
        [("comment", "completely normal between episodes")],
}

# (ARI ID, entry) -> [edit]: ("describe", text, [entry labels]), ("restore", ARIS id),
# ("trigger", label), ("treatment", label, description), ("associated", value),
# ("comment", sentence to add).
EDITS = {
    ("ARI:0001001", "Healing with minimal scarring"):
        [("describe", "Heals with minimal scarring", ["Widespread blisters that are not localized to trauma-prone sites"])],
    ("ARI:0001049", "Symptoms can flare with triggers such as heat, exercise and stress"):
        [("trigger", "Exercise")],  # heat and stress are held already, under their own triggers
    ("ARI:0001049", "Symptoms persist for more than 6 weeks and recur frequently and unexpectedly"):
        [("comment", "Symptoms recur frequently and unexpectedly.")],  # the 6 weeks is held already
    ("ARI:0001062", "Symptoms worsen after physical or mental activity"): [("restore", "ARIS_0000766")],
    ("ARI:0001076", "Symptoms worsen in sunlight"): [("restore", "ARIS_0000478")],
    ("ARI:0001086", "No response to gastroesophageal reflux disease (gerd) medication"):
        [("treatment", "Gastroesophageal reflux disease medication", "Symptoms do not respond to it")],
    ("ARI:0001087", "Temporary"): [("describe", "Temporary", ["Confusion"])],
    ("ARI:0001154", "Does not cause mouth blisters"):
        [("describe", "Does not cause mouth blisters",
          ["Causes blisters on the chest, back and shoulders", "Itchy blisters"])],
    ("ARI:0001184", "Near sites of irritation"):
        [("describe", "Near sites of irritation", ["Firm bumps of tissue under the skin on your arms"])],
    ("ARI:0001202", "Very high risk of internal malignancy within 3 years of diagnosis"):
        [("associated", "Internal malignancy (very high risk within 3 years of diagnosis)")],
    ("ARI:0001224", "Refractoriness to IVIG with high response rate to rituximab"):
        [("treatment", "Rituximab", "High response rate"),
         ("treatment", "Intravenous immunoglobulin", "80–90% of patients are refractory to it")],
}

NOTHING = re.compile(r"^(drop|no field|check the source)")
STAGE_OR_POPULATION = re.compile(r"^qualifier: note the (stage|population) in symptomDescription of the entries under it$")
FREQUENCY = "qualifier: set likelihood of the entries under it"
SYMPTOM_IRI = re.compile(r"#Sym_(\d{7})_\d+$")


def local_id(prefix, *parts):
    """A stable id in the app's form, <prefix>_<8 hex>, from the parts it is made for."""
    return f"{prefix}_{hashlib.sha1('|'.join(parts).encode()).hexdigest()[:8]}"


class Record:
    """ari_disease.owl and ari_symptoms.owl, with the lookups the edits need."""

    def __init__(self):
        self.disease_ns, self.symptoms_ns = _declared_namespaces(DISEASE), _declared_namespaces(SYMPTOMS)
        self.root = ET.parse(DISEASE).getroot()
        self.symptoms = ET.parse(SYMPTOMS).getroot()
        self.by_iri = {el.get(RDF + "about"): el for el in self.root if el.get(RDF + "about")}
        self.diseases = {el.findtext(ARI + "ARI_ID"): el for el in self.root if el.findtext(ARI + "ARI_ID")}
        self.symptom = collections.defaultdict(list)  # (ARI ID, casefolded label) -> [individual]
        for ind in self.root.findall(OWL + "NamedIndividual"):
            m = SYMPTOM_IRI.search(ind.get(RDF + "about"))
            if m and ind.findtext(RDFS + "label"):
                self.symptom[f"ARI:{m.group(1)}", ind.findtext(RDFS + "label").strip().casefold()].append(ind)
        self.classes = {el.get(RDF + "about"): el for el in self.symptoms.findall(OWL + "Class")}
        self.changed = collections.defaultdict(list)  # ARI ID -> [what changed]

    def linked(self, ari_id, prop):
        return [self.by_iri[ref.get(RDF + "resource")] for ref in self.diseases[ari_id].findall(ARI + prop)]

    def entry(self, ari_id, label):
        found = self.symptom[ari_id, label.strip().casefold()]
        if len(found) != 1:
            raise SystemExit(f"{ari_id} {label!r}: {len(found)} Symptom individuals carry this label")
        return found[0]

    def save(self):
        for path, root, declared in ((DISEASE, self.root, self.disease_ns), (SYMPTOMS, self.symptoms, self.symptoms_ns)):
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(_serialise(root, declared))


def check_held(rec, ari_id, entry, held):
    disease = rec.diseases[ari_id]
    for kind, *value in held:
        if kind == "comment":
            ok = any(value[0] in (c.text or "") for c in disease.findall(RDFS + "comment"))
        elif kind == "biomarker":
            ok = any(m.findtext(RDFS + "comment") == value[0] for m in rec.linked(ari_id, "hasBiomarker"))
        elif kind == "antibody":
            ok = bool(rec.linked(ari_id, "hasAntibody"))
        elif kind == "trigger":
            ok = any(t.findtext(RDFS + "label") == value[0] for t in rec.linked(ari_id, "hasEnvironmentalTrigger"))
        elif kind == "associated":
            ok = value[0] in [c.text for c in disease.findall(ARI + "ARI_AssociatedDisease")]
        elif kind == "parent":
            ok = disease.get(RDF + "about") in [r.get(RDF + "resource")
                                                for r in rec.diseases[value[0]].findall(ARI + "hasParentDisease")]
        else:
            raise SystemExit(f"unknown held kind {kind!r}")
        if not ok:
            raise SystemExit(f"{ari_id} {entry!r}: the record does not hold {kind} {value}")


def describe(rec, ari_id, text, labels, prop="symptomDescription"):
    for label in labels:
        ind = rec.entry(ari_id, label)
        values = [el.text for el in ind.findall(ARI + prop)]
        if values == [text]:
            continue
        if values:
            raise SystemExit(f"{ind.get(RDF + 'about')} already has {prop} {values}, not {text!r}")
        ET.SubElement(ind, ARI + prop).text = text
        rec.changed[ari_id].append(f"{prop} of '{label}' set to '{text}'")


def ensure_class(rec, aris_id):
    iri = ARIS + aris_id
    if iri in rec.classes or aris_id not in NEW_CLASSES:
        return
    spec = NEW_CLASSES[aris_id]
    cls = ET.SubElement(rec.symptoms, OWL + "Class", {RDF + "about": iri})
    ET.SubElement(cls, RDFS + "subClassOf", {RDF + "resource": spec["parent"]})
    ET.SubElement(cls, OBO_IN_OWL + "id").text = aris_id.replace("_", ":")
    ET.SubElement(cls, RDFS + "label").text = spec["label"]
    for match in spec["exact"]:
        ET.SubElement(cls, SKOS + "exactMatch", {RDF + "resource": match})
    for match in spec["broad"]:
        ET.SubElement(cls, SKOS + "broadMatch", {RDF + "resource": match})
    rec.classes[iri] = cls


def restore(rec, ari_id, entry, aris_id):
    ensure_class(rec, aris_id)
    cls = rec.classes.get(ARIS + aris_id)
    if cls is None:
        raise SystemExit(f"{aris_id} is not a class in {os.path.relpath(SYMPTOMS, ROOT)}")
    ind = rec.entry(ari_id, entry)
    iri = ind.get(RDF + "about")
    names = [cls.findtext(RDFS + "label")] + [el.text for el in cls.findall(SKOS + "altLabel")]
    if entry not in names:
        ET.SubElement(cls, SKOS + "altLabel").text = entry
    for el in ind.findall(ARI + "ARI_NoConcept"):
        if el.text != NOT_A_SYMPTOM:
            raise SystemExit(f"{iri} has ARI_NoConcept {el.text!r}")
        ind.remove(el)
    for el in ind.findall(ARI + "ARI_Obsolete"):
        el.text = "false"
    if ind.find(ARI + "sharedConcept") is None:
        ET.SubElement(ind, ARI + "sharedConcept", {RDF + "resource": cls.get(RDF + "about")})
    disease = rec.diseases[ari_id]
    if iri not in [r.get(RDF + "resource") for r in disease.findall(ARI + "hasSymptom")]:
        ET.SubElement(disease, ARI + "hasSymptom", {RDF + "resource": iri})
        rec.changed[ari_id].append(f"Restored symptom '{entry}' ({aris_id.replace('_', ':')})")


def add_item(rec, ari_id, prop, cls, prefix, label, fields=()):
    disease = rec.diseases[ari_id]
    if any(el.findtext(RDFS + "label") == label for el in rec.linked(ari_id, prop)):
        return
    iri = ARI_BASE + local_id(prefix, ari_id, label)
    if iri in rec.by_iri:
        raise SystemExit(f"{iri} exists but {ari_id} does not list it")
    ind = ET.SubElement(rec.root, OWL + "NamedIndividual", {RDF + "about": iri})
    ET.SubElement(ind, RDF + "type", {RDF + "resource": ARI_BASE + cls})
    for name, value in fields:
        ET.SubElement(ind, ARI + name).text = value
    ET.SubElement(ind, ARI + "ARI_Obsolete").text = "false"
    ET.SubElement(ind, RDFS + "label").text = label
    ET.SubElement(disease, ARI + prop, {RDF + "resource": iri})
    rec.by_iri[iri] = ind
    rec.changed[ari_id].append(f"Added {cls}: {label}")


def apply_edit(rec, ari_id, entry, edit):
    kind, *args = edit
    disease = rec.diseases[ari_id]
    if kind == "describe":
        describe(rec, ari_id, args[0], args[1])
    elif kind == "restore":
        restore(rec, ari_id, entry, args[0])
    elif kind == "trigger":
        add_item(rec, ari_id, "hasEnvironmentalTrigger", "EnvironmentalFactor", "Env", args[0])
    elif kind == "treatment":
        add_item(rec, ari_id, "hasTreatment", "Treatment", "Tx", args[0], [("treatmentDescription", args[1])])
    elif kind == "associated":
        if args[0] not in [c.text for c in disease.findall(ARI + "ARI_AssociatedDisease")]:
            ET.SubElement(disease, ARI + "ARI_AssociatedDisease").text = args[0]
            rec.changed[ari_id].append(f"Added associated disease: {args[0]}")
    elif kind == "comment":
        comments = disease.findall(RDFS + "comment")
        if len(comments) != 1:
            raise SystemExit(f"{ari_id} has {len(comments)} descriptions")
        if args[0] not in comments[0].text:
            comments[0].text = comments[0].text.rstrip() + " " + args[0]
            rec.changed[ari_id].append(f"Description: added '{args[0]}'")
    else:
        raise SystemExit(f"unknown edit {kind!r}")


def main():
    with open(REVIEW, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, dialect="excel-tab"))
    rec = Record()
    handled = set()
    for row in rows:
        ari_id, entry, proposed = row["ari_id"], row["entry"], row["proposed"]
        if row["decision"] != "accept":
            continue
        key = (ari_id, entry)
        if key in EDITS:
            for edit in EDITS[key]:
                apply_edit(rec, ari_id, entry, edit)
        elif key in HELD:
            check_held(rec, ari_id, entry, HELD[key])
        elif STAGE_OR_POPULATION.match(proposed):
            text = HEADING_TEXT.get(entry, entry.rstrip(":"))
            describe(rec, ari_id, text, row["after"].split("; "))
        elif proposed == FREQUENCY:
            describe(rec, ari_id, entry.rstrip(":"), row["after"].split("; "), prop="likelihood")
        elif NOTHING.match(proposed):
            if row["individual"]:
                ind = rec.by_iri[ARI_BASE + row["individual"]]
                listed = [d for d, el in rec.diseases.items()
                          if ind.get(RDF + "about") in [r.get(RDF + "resource") for r in el.findall(ARI + "hasSymptom")]]
                if listed or ind.findtext(ARI + "ARI_Obsolete") != "true":
                    raise SystemExit(f"{row['individual']} is to be dropped but is listed by {listed} or not obsolete")
        else:
            raise SystemExit(f"{ari_id} {entry!r}: no rule applies proposal {proposed!r}")
        handled.add(key)
    unused = (set(EDITS) | set(HELD)) - handled
    if unused:
        raise SystemExit(f"Rules for rows not accepted in report 13: {sorted(unused)}")

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    for ari_id, changes in rec.changed.items():
        ET.SubElement(rec.diseases[ari_id], ARI + "ARI_ChangeLog").text = f"{now} | {CURATOR} | {LOG}: {'; '.join(changes)}"
    rec.save()
    print(f"{len(handled)} accepted rows; changed {sum(map(len, rec.changed.values()))} things on "
          f"{len(rec.changed)} diseases")
    for ari_id, changes in sorted(rec.changed.items()):
        for change in changes:
            print(f"  {ari_id} {change}")


if __name__ == "__main__":
    main()
