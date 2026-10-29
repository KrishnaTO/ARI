"""The biomarker records as the scripts see them, and the one writer that puts review rows into the OWL.

`read_entries` reads the per-disease antibody, antigen and clinical biomarker entries of
ontologies/ari_disease.owl; `read_concepts` reads the ARIB classes of ontologies/ari_biomarkers.owl.
`write_rows` applies review rows to both files. propose.py calls it with every row it proposes (the
PR preview) and apply_review.py with the accepted rows only, so it is deterministic: the same rows on
the same files give the same bytes. Layout is left to tools/format-owl.sh.

A row names a concept by key: an existing ARIB IRI, or "new:<label>" for a class its `concept` row
creates. A row about an entry names it first in `entries` by its ari-disease local name
("Ab_0001001_1 Type VII Colagen").
"""
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, fields
from urllib.parse import urljoin

ARI = "http://www.aurint.org/ontologies/ari-disease#"
ARIB = "http://www.aurint.org/ontologies/ari-biomarkers#ARIB_"
NEW = "new:"
KIND_CLASSES = {
    "antibodies": ARI + "Autoantibody",
    "antigens": ARI + "Antigen",
    "tests": ARI + "ClinicalBiomarker",
}
DISEASE_LINKS = tuple(f"{{{ARI}}}{p}" for p in ("hasAntibody", "involvesAntigen", "hasBiomarker"))  # as XML tags
MATCH_ACTIONS = ("exactMatch", "broadMatch", "closeMatch", "relatedMatch")

RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS_NS = "http://www.w3.org/2000/01/rdf-schema#"
OWL_NS = "http://www.w3.org/2002/07/owl#"
SKOS_NS = "http://www.w3.org/2004/02/skos/core#"
OBOINOWL_NS = "http://www.geneontology.org/formats/oboInOwl#"
XML_NS = "http://www.w3.org/XML/1998/namespace"

ABOUT = f"{{{RDF_NS}}}about"
RESOURCE = f"{{{RDF_NS}}}resource"
RDF_TYPE = f"{{{RDF_NS}}}type"
DESCRIPTION = f"{{{RDF_NS}}}Description"
XML_BASE = f"{{{XML_NS}}}base"
LABEL = f"{{{RDFS_NS}}}label"
SUBCLASS_OF = f"{{{RDFS_NS}}}subClassOf"
OWL_CLASS = f"{{{OWL_NS}}}Class"
ALT_LABEL = f"{{{SKOS_NS}}}altLabel"
OBO_ID = f"{{{OBOINOWL_NS}}}id"
SHARED = f"{{{ARI}}}sharedConcept"
NO_CONCEPT = f"{{{ARI}}}ARI_NoConcept"
OBSOLETE = f"{{{ARI}}}ARI_Obsolete"
TARGETS = f"{{{ARI}}}targetsAntigen"
ARIB_NUMBER = re.compile(re.escape(ARIB) + r"(\d{7})$")


@dataclass
class Entry:
    iri: str
    kind: str
    label: str
    diseases: list[tuple[str, str]]  # (disease IRI, disease label)
    obsolete: bool
    shared: list[str]
    no_concept: str | None


@dataclass
class Concept:
    iri: str
    kind: str
    label: str
    alt_labels: list[str]
    parents: list[str]
    matches: dict[str, list[str]]  # "exactMatch" -> IRIs, and so on
    targets: list[str]
    no_concept: str | None


@dataclass
class Row:
    """One line of the review table (plan Decision 2). Every field is text."""
    row: str
    group: str
    action: str
    concept: str
    value: str
    value_label: str
    diseases: str
    entries: str
    evidence: str
    depends: str
    decision: str
    correction: str
    note: str


COLUMNS = [f.name for f in fields(Row)]


# --------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------


def _nodes(text):
    """(IRI, types, element) for every top-level node with an rdf:about, as the validator reads them:
    IRIs resolved against xml:base, a typed node's tag counted as a type."""
    root = ET.fromstring(text)
    base = root.get(XML_BASE, "")
    for el in root:
        about = el.get(ABOUT)
        if about is None:
            continue
        types = {urljoin(base, t.get(RESOURCE)) for t in el.findall(RDF_TYPE)}
        if el.tag != DESCRIPTION:
            types.add(el.tag[1:].replace("}", "", 1))
        yield urljoin(base, about), types, el, base


def _text(el):
    return (el.text or "").strip()


def _resources(el, tag, base):
    return [urljoin(base, child.get(RESOURCE)) for child in el.findall(tag)]


def _last_label(el):
    labels = el.findall(LABEL)
    return _text(labels[-1]) if labels else ""


def read_entries(disease_text):
    """The antibody, antigen and clinical biomarker entries of ari_disease.owl, in file order.

    An entry's kind is its rdf:type; its diseases are those that point at it through hasAntibody,
    involvesAntigen or hasBiomarker.
    """
    nodes = list(_nodes(disease_text))
    labels = {iri: _last_label(el) for iri, _, el, _ in nodes}
    diseases = {}
    for iri, _, el, base in nodes:
        for prop in DISEASE_LINKS:
            for target in _resources(el, prop, base):
                diseases.setdefault(target, []).append((iri, labels[iri]))
    kinds = {cls: kind for kind, cls in KIND_CLASSES.items()}
    entries = []
    for iri, types, el, base in nodes:
        core = sorted(types & kinds.keys())
        if not core:
            continue
        if len(core) > 1:
            raise ValueError(f"{iri} has more than one biomarker type: {', '.join(core)}")
        no_concept = el.findall(NO_CONCEPT)
        entries.append(Entry(
            iri, kinds[core[0]], _last_label(el), diseases.get(iri, []),
            any(_text(o) == "true" for o in el.findall(OBSOLETE)),
            _resources(el, SHARED, base),
            _text(no_concept[0]) if no_concept else None,
        ))
    return entries


def read_concepts(biomarkers_text):
    """The ARIB classes of ari_biomarkers.owl, in file order. A class's kind is the one core class it
    is under, directly or through other ARIB classes; a class under none or two raises ValueError."""
    raw = {}
    for iri, types, el, base in _nodes(biomarkers_text):
        if f"{OWL_NS}Class" not in types or not iri.startswith(ARIB):
            continue
        matches = {}
        for action in MATCH_ACTIONS:
            found = _resources(el, f"{{{SKOS_NS}}}{action}", base)
            if found:
                matches[action] = found
        no_concept = el.findall(NO_CONCEPT)
        raw[iri] = Concept(
            iri, "", _last_label(el), [_text(a) for a in el.findall(ALT_LABEL)],
            _resources(el, SUBCLASS_OF, base), matches, _resources(el, TARGETS, base),
            _text(no_concept[0]) if no_concept else None,
        )
    kinds = {cls: kind for kind, cls in KIND_CLASSES.items()}
    for iri, concept in raw.items():
        reached, seen, stack = set(), set(), [iri]
        while stack:
            for parent in raw[stack.pop()].parents:
                if parent in kinds:
                    reached.add(kinds[parent])
                elif parent in raw and parent not in seen:
                    seen.add(parent)
                    stack.append(parent)
        if len(reached) != 1:
            raise ValueError(f"{iri} is under {sorted(reached) or 'no biomarker kind'}; it needs exactly one")
        concept.kind = reached.pop()
    return list(raw.values())


def ancestors(iri, concepts):
    """The ARIB classes above `iri`, nearest first, given concepts by IRI."""
    found, stack = [], [iri]
    while stack:
        for parent in concepts[stack.pop(0)].parents:
            if parent in concepts and parent not in found:
                found.append(parent)
                stack.append(parent)
    return found


# --------------------------------------------------------------------------
# Writing
# --------------------------------------------------------------------------


def entry_local(row):
    """The ari-disease local name a row's `entries` starts with."""
    if not row.entries.strip():
        raise ValueError(f"row {row.row} ({row.action}) names no entry")
    return row.entries.split()[0]


def _declared_namespaces(path):
    """(prefix, URI) of every namespace the file declares, in order."""
    return [ns for _, ns in ET.iterparse(path, events=("start-ns",))]


def _used_namespaces(root):
    used = set()
    for el in root.iter():
        for name in (el.tag, *el.attrib):
            if name.startswith("{"):
                used.add(name[1:].split("}", 1)[0])
    return used


def _serialise(root, declared):
    """The document as text, declaring every namespace the original declared.

    ElementTree declares only the namespaces it uses, under the prefix registered for them. Each used
    namespace is registered under the file's own prefix for it (the default one when the file makes
    it the default), and a declared prefix ElementTree would not write is added as an attribute, so
    the formatter sees the prefixes it wrote. A namespace used but not declared raises ValueError.
    """
    prefixes = {}
    for prefix, uri in declared:
        if prefix != "xml":
            prefixes.setdefault(uri, []).append(prefix)
    written = set()
    for uri in sorted(_used_namespaces(root) - {XML_NS}):
        if uri not in prefixes:
            raise ValueError(f"namespace {uri} is used but the file does not declare it")
        prefix = "" if "" in prefixes[uri] else prefixes[uri][0]
        ET.register_namespace(prefix, uri)
        written.add((prefix, uri))
    for prefix, uri in declared:
        if prefix != "xml" and (prefix, uri) not in written:
            root.set(f"xmlns:{prefix}" if prefix else "xmlns", uri)
    return '<?xml version="1.0"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def _sub(parent, tag, text=None, resource=None):
    el = ET.SubElement(parent, tag)
    if resource is not None:
        el.set(RESOURCE, resource)
    else:
        el.text = text
    return el


def write_rows(rows, biomarkers_path, disease_path):
    """Apply `rows` to the two OWL files in place and return concept key -> ARIB IRI.

    `concept` rows create classes, given ids in row order after the highest ARIB id present. Then,
    in row order: `altLabel` (value: the label), the four matches and `no_term` go on the concept's
    class; `target` sets targetsAntigen from the concept to the value; `link` adds a sharedConcept
    from the entry to the value; `label_fix` replaces the entry's rdfs:label; `not_a_biomarker` sets
    the entry's ARI_NoConcept. A key with no concept row, or an entry or class that is not there,
    raises ValueError.
    """
    biomarkers_ns = _declared_namespaces(biomarkers_path)
    disease_ns = _declared_namespaces(disease_path)
    biomarkers = ET.parse(biomarkers_path).getroot()
    disease = ET.parse(disease_path).getroot()
    b_base, d_base = biomarkers.get(XML_BASE, ""), disease.get(XML_BASE, "")
    classes = {urljoin(b_base, el.get(ABOUT)): el for el in biomarkers.findall(OWL_CLASS) if el.get(ABOUT)}
    individuals = {urljoin(d_base, el.get(ABOUT)): el for el in disease if el.get(ABOUT)}

    numbers = [int(m.group(1)) for iri in classes if (m := ARIB_NUMBER.match(iri))]
    next_number = max(numbers, default=0) + 1
    keys = {}
    for row in rows:
        if row.action != "concept":
            continue
        if not row.concept.startswith(NEW) or row.concept in keys:
            raise ValueError(f"row {row.row}: a concept row needs a new, unique key, got {row.concept!r}")
        keys[row.concept] = f"{ARIB}{next_number:07d}"
        next_number += 1

    def resolve(key, row):
        if key.startswith(NEW):
            if key not in keys:
                raise ValueError(f"row {row.row} ({row.action}) names {key}, which no concept row creates")
            return keys[key]
        if key in classes or key in KIND_CLASSES.values():
            return key
        raise ValueError(f"row {row.row} ({row.action}) names {key}, which is not an ARIB class here")

    def cls(row):
        iri = resolve(row.concept, row)
        if iri not in classes:
            raise ValueError(f"row {row.row} ({row.action}) needs a class, got {row.concept}")
        return classes[iri]

    def individual(row):
        iri = ARI + entry_local(row)
        if iri not in individuals:
            raise ValueError(f"row {row.row} ({row.action}) names entry {entry_local(row)}, which is not there")
        return individuals[iri]

    for row in rows:
        if row.action != "concept":
            continue
        iri = keys[row.concept]
        el = ET.SubElement(biomarkers, OWL_CLASS, {ABOUT: iri})
        _sub(el, SUBCLASS_OF, resource=resolve(row.value, row))
        _sub(el, OBO_ID, "ARIB:" + iri.removeprefix(ARIB))
        _sub(el, LABEL, row.concept.removeprefix(NEW))
        classes[iri] = el

    for row in rows:
        action = row.action
        if action == "concept":
            continue
        if action == "altLabel":
            _sub(cls(row), ALT_LABEL, row.value)
        elif action in MATCH_ACTIONS:
            _sub(cls(row), f"{{{SKOS_NS}}}{action}", resource=row.value)
        elif action == "no_term":
            _sub(cls(row), NO_CONCEPT, "no term")
        elif action == "target":
            _sub(cls(row), TARGETS, resource=resolve(row.value, row))
        elif action == "link":
            _sub(individual(row), SHARED, resource=resolve(row.value, row))
        elif action == "label_fix":
            labels = individual(row).findall(LABEL)
            if len(labels) != 1:
                raise ValueError(f"row {row.row}: entry {entry_local(row)} has {len(labels)} labels")
            labels[0].text = row.value
        elif action == "not_a_biomarker":
            _sub(individual(row), NO_CONCEPT, "not a biomarker")
        else:
            raise ValueError(f"row {row.row}: unknown action {action!r}")

    for path, root, declared in ((biomarkers_path, biomarkers, biomarkers_ns), (disease_path, disease, disease_ns)):
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(_serialise(root, declared))
    return keys
