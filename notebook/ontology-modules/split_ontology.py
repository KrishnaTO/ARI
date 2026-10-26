"""Split the ARI ontology into modules: core, disease, symptoms, anatomy and biomarkers.

A one-off, kept for the record. Before it ran, ontologies/ari_disease.owl was ari_t1d.owl, the
single file holding everything, and ontologies/ari_symptoms.owl held the ARIS symptom classes
together with a copy of the SYMP terms they link to. Afterwards:

  ari_core.owl        the key classes (AutoimmuneDisease, Symptom, MulticellularAnatomicalStructure,
                      AffectedCellTissueOrOrgan, Autoantibody, Antigen, ClinicalBiomarker) under
                      three new umbrella classes, and every property declaration
  ari_disease.owl     diseases and all per-disease entries; imports the four modules
  ari_symptoms.owl    the ARIS classes, their roots under Symptom; imports core and ari_symp
  ari_anatomy.owl     the tissue/system classes and the Tissue_* individuals; imports core and
                      ari_uberon
  ari_biomarkers.owl  empty for now; imports core
  ari_symp.owl        the SYMP terms split out of ari_symptoms.owl (a generated slice)
  catalog-v001.xml    maps every imported ontology IRI to its file

Every entity keeps its IRI. Two things the retired TSVs held move into the OWL:
  - uberon_mapping.tsv Notes become rdfs:comment on the tissue class, and its `no term` /
    `not linked` rows become ARI_NoConcept on the class;
  - Symptom individuals whose label symptom_mapping.tsv judged `not a symptom` get
    ARI_NoConcept "not a symptom".
symptomConcept is renamed to sharedConcept.

Elements are moved as parsed XML; the layout is left to tools/format-owl.sh, which must run
after this script (with the catalog this script writes, so imports resolve).

Usage: python notebook/ontology-modules/split_ontology.py
"""
import csv, os
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ONTOLOGIES = os.path.join(ROOT, "ontologies")
DISEASE = os.path.join(ONTOLOGIES, "ari_disease.owl")
SYMPTOMS = os.path.join(ONTOLOGIES, "ari_symptoms.owl")
CORE = os.path.join(ONTOLOGIES, "ari_core.owl")
ANATOMY = os.path.join(ONTOLOGIES, "ari_anatomy.owl")
BIOMARKERS = os.path.join(ONTOLOGIES, "ari_biomarkers.owl")
SYMP = os.path.join(ONTOLOGIES, "ari_symp.owl")
CATALOG = os.path.join(ONTOLOGIES, "catalog-v001.xml")
SYMPTOM_MAPPING = os.path.join(ROOT, "notebook", "symptom-mapping", "symptom_mapping.tsv")
UBERON_MAPPING = os.path.join(ROOT, "notebook", "uberon-mapping", "uberon_mapping.tsv")

ONT = "http://www.aurint.org/ontologies/"
DISEASE_IRI = ONT + "ari-disease"
CORE_IRI = ONT + "ari_core"
SYMPTOMS_IRI = ONT + "ari_symptoms"
ANATOMY_IRI = ONT + "ari_anatomy"
BIOMARKERS_IRI = ONT + "ari_biomarkers"
UBERON_IRI = ONT + "ari_uberon"
SYMP_IRI = ONT + "ari_symp"
# Imported ontology IRI -> file, for the catalog.
IMPORTED = {CORE_IRI: "ari_core.owl", SYMPTOMS_IRI: "ari_symptoms.owl", ANATOMY_IRI: "ari_anatomy.owl",
            BIOMARKERS_IRI: "ari_biomarkers.owl", UBERON_IRI: "ari_uberon.owl", SYMP_IRI: "ari_symp.owl"}

ARI = DISEASE_IRI + "#"
ARI_CORE = ONT + "ari-core#"
ARIS = ONT + "ari-symptoms#"
OBO = "http://purl.obolibrary.org/obo/"
SYMP_CLASS = OBO + "SYMP_"
SYMP_RELEASES = OBO + "symp/releases/"
SKOS = "http://www.w3.org/2004/02/skos/core#"
OBO_IN_OWL = "http://www.geneontology.org/formats/oboInOwl#"
DC = "http://purl.org/dc/elements/1.1/"

RDF = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
RDFS = "{http://www.w3.org/2000/01/rdf-schema#}"
OWL = "{http://www.w3.org/2002/07/owl#}"
XML_BASE = "{http://www.w3.org/XML/1998/namespace}base"
OWL_THING = "http://www.w3.org/2002/07/owl#Thing"
PROPERTY_TAGS = (OWL + "AnnotationProperty", OWL + "ObjectProperty", OWL + "DatatypeProperty")
NAMESPACES = {"rdf": RDF[1:-1], "rdfs": RDFS[1:-1], "owl": OWL[1:-1],
              "xsd": "http://www.w3.org/2001/XMLSchema#", "obo": OBO, "skos": SKOS,
              "oboInOwl": OBO_IN_OWL, "dc": DC, "ari-disease": ARI, "ari-core": ARI_CORE,
              "ari-symptoms": ARIS}

SYMPTOM_CONCEPT = ARI + "symptomConcept"
SHARED_CONCEPT = ARI + "sharedConcept"
NO_CONCEPT = ARI + "ARI_NoConcept"
SYMPTOM_CONCEPT_TAG = "{%s}symptomConcept" % ARI
SHARED_CONCEPT_TAG = "{%s}sharedConcept" % ARI
NO_CONCEPT_TAG = "{%s}ARI_NoConcept" % ARI
DC_SOURCE_TAG = "{%s}source" % DC
NO_CONCEPT_MAPPINGS = {"no term", "not linked"}
NOT_A_SYMPTOM = "not a symptom"
ANATOMY_ROOT = "MulticellularAnatomicalStructure"
SYMPTOM = ARI + "Symptom"

# Key class -> the new umbrella class it goes under (None: stays under owl:Thing).
KEY_CLASSES = {
    "AutoimmuneDisease": "Disease",
    "Symptom": None,
    "MulticellularAnatomicalStructure": "AnatomicalEntity",
    "AffectedCellTissueOrOrgan": "AnatomicalEntity",
    "Autoantibody": "Biomarker",
    "Antigen": "Biomarker",
    "ClinicalBiomarker": "Biomarker",
}
UMBRELLAS = {"Disease": "Disease", "AnatomicalEntity": "Anatomical entity", "Biomarker": "Biomarker"}
# Annotation properties the modules use that ari_t1d.owl did not declare.
NEW_PROPERTIES = [
    SHARED_CONCEPT, NO_CONCEPT, ARI + "ARI_EnrichmentSource",
    SKOS + "exactMatch", SKOS + "broadMatch", SKOS + "closeMatch", SKOS + "altLabel",
    OBO + "IAO_0000115", OBO_IN_OWL + "id", DC + "source",
]

EXPECTED = {"core classes": 7, "anatomy classes": 25, "tissue individuals": 23,
            "sharedConcept": 2248, "not a symptom": 46, "SYMP classes": 309}

CORE_COMMENT = ("ARI's key classes, under the umbrella classes Disease, Symptom, Anatomical entity and "
                "Biomarker, and every property the ARI modules use. No other ARI-owned file declares a "
                "property.")
ANATOMY_COMMENT = ("ARI tissue and system classes (under MulticellularAnatomicalStructure) and the "
                   "Tissue_* individuals that diseases target. Classes link to UBERON through the "
                   "ari_uberon import; ARI_NoConcept records a class deliberately left without a term.")
BIOMARKERS_COMMENT = ("Shared ARI biomarker concepts: ARIB classes under Autoantibody, Antigen and "
                      "ClinicalBiomarker. Empty until those concepts are added.")
SYMPTOMS_COMMENT = ("ARI symptom classes (ARIS), grouped into a hierarchy under Symptom and mapped to the "
                    "Symptom Ontology (SYMP) and the Human Phenotype Ontology (HPO). skos:exactMatch names a "
                    "SYMP or HPO term with the same meaning, skos:broadMatch the nearest broader one. Strings "
                    "merged into a symptom are skos:altLabel. The per-disease Symptom individuals in "
                    "ari_disease.owl point at their class with sharedConcept. SYMP terms come from the "
                    "ari_symp import; HPO terms are referenced by IRI.")
SYMP_COMMENT = ("SYMP terms ARI symptom classes link to, with their is_a ancestors. Generated by "
                "notebook/symptom-mapping/build_symp_import.py; do not edit by hand.")


def resolve(ref, base):
    """Absolute IRI of an rdf:about / rdf:resource, which may be relative to the file's xml:base."""
    return urljoin(base, ref)


def about(element, base):
    return resolve(element.get(RDF + "about"), base)


def resources(element, tag, base):
    """IRIs named by rdf:resource on element's `tag` children."""
    return [resolve(e.get(RDF + "resource"), base) for e in element.findall(tag) if e.get(RDF + "resource")]


def literal(parent, tag, text):
    ET.SubElement(parent, tag).text = text


def new_ontology(iri, comment, imports):
    """An rdf:RDF root holding only the ontology header."""
    root = ET.Element(RDF + "RDF", {XML_BASE: iri})
    header = ET.SubElement(root, OWL + "Ontology", {RDF + "about": iri})
    literal(header, RDFS + "comment", comment)
    for imported in imports:
        ET.SubElement(header, OWL + "imports", {RDF + "resource": imported})
    return root


def move(source, target, elements):
    for element in elements:
        source.remove(element)
        target.append(element)


def move_properties(disease, core):
    """Every property declaration goes to core, except symptomConcept, which is dropped."""
    for element in [e for e in disease if e.tag in PROPERTY_TAGS]:
        disease.remove(element)
        if about(element, DISEASE_IRI) != SYMPTOM_CONCEPT:
            core.append(element)


def move_key_classes(disease, core):
    """Move the key classes to core, each under its umbrella in place of owl:Thing. Returns the count."""
    umbrellas = {ARI + name: umbrella for name, umbrella in KEY_CLASSES.items()}
    found = [c for c in disease.findall(OWL + "Class") if about(c, DISEASE_IRI) in umbrellas]
    for cls in found:
        umbrella = umbrellas[about(cls, DISEASE_IRI)]
        if umbrella:
            for parent in cls.findall(RDFS + "subClassOf"):
                if resolve(parent.get(RDF + "resource"), DISEASE_IRI) == OWL_THING:
                    parent.set(RDF + "resource", ARI_CORE + umbrella)
    move(disease, core, found)
    return len(found)


def add_core_declarations(core):
    for name, label in UMBRELLAS.items():
        cls = ET.SubElement(core, OWL + "Class", {RDF + "about": ARI_CORE + name})
        literal(cls, RDFS + "label", label)
    for iri in NEW_PROPERTIES:
        ET.SubElement(core, OWL + "AnnotationProperty", {RDF + "about": iri})


def anatomy_classes(disease):
    """The classes whose ari-disease superclass chain reaches MulticellularAnatomicalStructure."""
    classes = {about(c, DISEASE_IRI): c for c in disease.findall(OWL + "Class")}
    parents = {iri: resources(c, RDFS + "subClassOf", DISEASE_IRI) for iri, c in classes.items()}

    def under_root(iri, seen=()):
        if iri == ARI + ANATOMY_ROOT:
            return True
        return any(p not in seen and under_root(p, seen + (iri,)) for p in parents.get(iri, []))

    return [c for iri, c in classes.items() if iri != ARI + ANATOMY_ROOT and under_root(iri)]


def move_anatomy(disease, anatomy):
    """Move the tissue classes and the individuals typed by them. Returns (classes, individuals)."""
    classes = anatomy_classes(disease)
    iris = {about(c, DISEASE_IRI) for c in classes}
    individuals = [i for i in disease.findall(OWL + "NamedIndividual")
                   if iris & set(resources(i, RDF + "type", DISEASE_IRI))]
    move(disease, anatomy, classes + individuals)
    return len(classes), len(individuals)


def annotate_tissue_classes(classes):
    """uberon_mapping.tsv Notes as rdfs:comment; `no term` / `not linked` rows as ARI_NoConcept."""
    with open(UBERON_MAPPING, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    for row in rows:
        cls = classes.get(ARI + row["ARI Class"])
        if cls is None:
            raise SystemExit(f"uberon_mapping.tsv: {row['ARI Class']} is not a tissue class")
        if row["Note"].strip():
            literal(cls, RDFS + "comment", row["Note"].strip())
        if row["Mapping"] in NO_CONCEPT_MAPPINGS:
            literal(cls, NO_CONCEPT_TAG, row["Mapping"])


def rename_symptom_concept(disease):
    """symptomConcept -> sharedConcept, keeping rdf:resource. Returns the count."""
    links = list(disease.iter(SYMPTOM_CONCEPT_TAG))
    for link in links:
        link.tag = SHARED_CONCEPT_TAG
    return len(links)


def not_a_symptom_labels():
    with open(SYMPTOM_MAPPING, encoding="utf-8", newline="") as f:
        return {r["Symptom"].strip() for r in csv.DictReader(f, delimiter="\t") if r["Mapping"] == NOT_A_SYMPTOM}


def mark_not_symptoms(disease):
    """ARI_NoConcept "not a symptom" on each Symptom individual whose label the TSV judged so."""
    labels = not_a_symptom_labels()
    marked = 0
    for individual in disease.findall(OWL + "NamedIndividual"):
        if SYMPTOM not in resources(individual, RDF + "type", DISEASE_IRI):
            continue
        if individual.find(RDFS + "label").text.strip() not in labels:
            continue
        if individual.find(SHARED_CONCEPT_TAG) is not None:
            raise SystemExit(f"{about(individual, DISEASE_IRI)} is `not a symptom` but has a sharedConcept")
        literal(individual, NO_CONCEPT_TAG, NOT_A_SYMPTOM)
        marked += 1
    return marked


def set_disease_imports(disease):
    header = disease.find(OWL + "Ontology")
    for imported in header.findall(OWL + "imports"):
        header.remove(imported)
    for iri in (CORE_IRI, SYMPTOMS_IRI, ANATOMY_IRI, BIOMARKERS_IRI):
        ET.SubElement(header, OWL + "imports", {RDF + "resource": iri})


def split_symptoms(symptoms, symp):
    """Drop the property declarations, move the SYMP classes. Returns the SYMP class count."""
    for element in [e for e in symptoms if e.tag in PROPERTY_TAGS]:
        symptoms.remove(element)
    base = symptoms.get(XML_BASE)
    found = [c for c in symptoms.findall(OWL + "Class") if about(c, base).startswith(SYMP_CLASS)]
    move(symptoms, symp, found)
    return len(found)


def attach_aris_roots(symptoms):
    """rdfs:subClassOf Symptom on each ARIS class with no ARIS parent. Returns (classes, roots)."""
    base = symptoms.get(XML_BASE)
    classes = symptoms.findall(OWL + "Class")
    roots = [c for c in classes
             if not any(p.startswith(ARIS) for p in resources(c, RDFS + "subClassOf", base))]
    for cls in roots:
        ET.SubElement(cls, RDFS + "subClassOf", {RDF + "resource": SYMPTOM})
    return len(classes), len(roots)


def rewrite_symptoms_header(symptoms):
    """New ontology IRI, comment and imports; keeps the dc:source releases. Returns the SYMP release.

    Runs after every other read of the file: the xml:base it changes is what relative IRIs resolve against."""
    header = symptoms.find(OWL + "Ontology")
    (release,) = [s for s in resources(header, DC_SOURCE_TAG, symptoms.get(XML_BASE))
                  if s.startswith(SYMP_RELEASES)]
    header.set(RDF + "about", SYMPTOMS_IRI)
    symptoms.set(XML_BASE, SYMPTOMS_IRI)
    header.find(RDFS + "comment").text = SYMPTOMS_COMMENT
    for iri in (CORE_IRI, SYMP_IRI):
        ET.SubElement(header, OWL + "imports", {RDF + "resource": iri})
    return release


def finish_symp_header(symp, release):
    """The SYMP release as dc:source, and the oboInOwl:id declaration the copied terms use."""
    ET.SubElement(symp.find(OWL + "Ontology"), DC_SOURCE_TAG, {RDF + "resource": release})
    ET.SubElement(symp, OWL + "AnnotationProperty", {RDF + "about": OBO_IN_OWL + "id"})


def write(root, path):
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def write_catalog():
    lines = ['<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
             '<catalog prefer="public" xmlns="urn:oasis:names:tc:entity:xmlns:xml:catalog">']
    lines += [f'    <uri name="{iri}" uri="{name}"/>' for iri, name in IMPORTED.items()]
    lines.append("</catalog>")
    with open(CATALOG, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def main():
    disease = ET.parse(DISEASE).getroot()
    symptoms = ET.parse(SYMPTOMS).getroot()
    core = new_ontology(CORE_IRI, CORE_COMMENT, [])
    anatomy = new_ontology(ANATOMY_IRI, ANATOMY_COMMENT, [CORE_IRI, UBERON_IRI])
    biomarkers = new_ontology(BIOMARKERS_IRI, BIOMARKERS_COMMENT, [CORE_IRI])
    symp = new_ontology(SYMP_IRI, SYMP_COMMENT, [])

    move_properties(disease, core)
    key_classes = move_key_classes(disease, core)
    add_core_declarations(core)
    anatomy_count, tissue_count = move_anatomy(disease, anatomy)
    tissue_classes = anatomy.findall(OWL + "Class") + core.findall(OWL + "Class")
    annotate_tissue_classes({about(c, DISEASE_IRI): c for c in tissue_classes})
    renamed = rename_symptom_concept(disease)
    not_symptoms = mark_not_symptoms(disease)
    set_disease_imports(disease)

    symp_count = split_symptoms(symptoms, symp)
    aris_count, aris_roots = attach_aris_roots(symptoms)
    finish_symp_header(symp, rewrite_symptoms_header(symptoms))

    found = {"core classes": key_classes, "anatomy classes": anatomy_count, "tissue individuals": tissue_count,
             "sharedConcept": renamed, "not a symptom": not_symptoms, "SYMP classes": symp_count}
    wrong = [f"{k}: {found[k]}, expected {v}" for k, v in EXPECTED.items() if found[k] != v]
    if wrong:
        raise SystemExit("Nothing written; counts differ:\n  " + "\n  ".join(wrong))

    for prefix, uri in NAMESPACES.items():
        ET.register_namespace(prefix, uri)
    for root, path in ((core, CORE), (disease, DISEASE), (symptoms, SYMPTOMS), (anatomy, ANATOMY),
                       (biomarkers, BIOMARKERS), (symp, SYMP)):
        write(root, path)
    write_catalog()
    properties = sum(1 for e in core if e.tag in PROPERTY_TAGS)
    print(f"core: {key_classes} key classes + {len(UMBRELLAS)} new, {properties} properties; "
          f"anatomy: {anatomy_count} classes, {tissue_count} individuals; "
          f"disease: {renamed} sharedConcept, {not_symptoms} ARI_NoConcept; "
          f"symptoms: {aris_count} classes, {aris_roots} under Symptom; ari_symp: {symp_count} classes")


if __name__ == "__main__":
    main()
