#!/usr/bin/env python3
"""Validate the ARI cross-reference mapping files.

Checks `mappings/ari.sssom.tsv`, `mappings/ari.equivalencies.tsv` and the
predictor's `mappings/ari.synonym_blocklist.tsv` for
structural problems, malformed identifiers and internal contradictions, that
the two files agree with each other, and that both agree with the stored
cross-references in `ontologies/ari_disease.owl`. Also checks the ontology
modules (core, disease, symptoms, anatomy, biomarkers) against each other: every
Symptom individual's `sharedConcept` is the ARIS class its label names in
`ontologies/ari_symptoms.owl`, every live biomarker entry's the ARIB class of its
kind its label names in `ontologies/ari_biomarkers.owl`, every ARIB class has
one kind, valid relation targets and its external terms in their slices, only
`ari_core.owl` declares properties, no subject is described in two modules, and
every tissue class links an UBERON term or says why not.

Usage:
    python .github/scripts/validate_mappings.py                # audit everything
    python .github/scripts/validate_mappings.py --since main   # only new problems
    python .github/scripts/validate_mappings.py --annotate     # GitHub annotations
    python .github/scripts/validate_mappings.py --summary FILE # markdown report

Exits 1 when any error-level finding is reported, 0 otherwise. Warnings never
fail the run.

Standard library only, so CI needs no install step.
"""

from __future__ import annotations

import argparse
import collections
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from urllib.parse import urljoin
from xml.parsers import expat

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SSSOM_PATH = "mappings/ari.sssom.tsv"
EQUIV_PATH = "mappings/ari.equivalencies.tsv"
ONTOLOGY_PATH = "ontologies/ari_disease.owl"
CORE_PATH = "ontologies/ari_core.owl"
SYMPTOMS_PATH = "ontologies/ari_symptoms.owl"
ANATOMY_PATH = "ontologies/ari_anatomy.owl"
BIOMARKERS_PATH = "ontologies/ari_biomarkers.owl"
UBERON_PATH = "ontologies/ari_uberon.owl"
# The modules curators edit. The generated slices (ari_symp.owl, ari_uberon.owl,
# the biomarker slices) are copies of upstream releases, so nothing here holds
# them to ARI's rules.
ARI_OWNED = (CORE_PATH, ONTOLOGY_PATH, SYMPTOMS_PATH, ANATOMY_PATH, BIOMARKERS_PATH)
# The slice that declares each external term a biomarker concept matches, by IRI
# prefix. HPO terms are referenced with no slice, so nothing checks them.
BIOMARKER_SLICES = {
    "http://purl.obolibrary.org/obo/PR_": "ontologies/ari_pr.owl",
    "http://purl.obolibrary.org/obo/CHEBI_": "ontologies/ari_chebi.owl",
    "http://identifiers.org/hgnc/": "ontologies/ari_hgnc.owl",
    "https://loinc.org/": "ontologies/ari_loinc.owl",
}
# The generated slices read only to resolve what an ARI module points at.
GENERATED = (UBERON_PATH, *BIOMARKER_SLICES.values())
# Curator-editable input to the editor app's cross-reference predictor: each row
# names a synonym stored on an ARI disease that actually names a *different*
# disease, so the predictor must not match on it. `ari.mis_curated_synonyms.tsv`
# beside it is the generated evidence behind these decisions and is a report, so
# nothing here validates it.
BLOCKLIST_PATH = "mappings/ari.synonym_blocklist.tsv"

SSSOM_COLUMNS = [
    "subject_id",
    "subject_label",
    "predicate_id",
    "predicate_modifier",
    "object_id",
    "object_source",
    "mapping_justification",
    "author_id",
    "mapping_date",
    "comment",
]
BLOCKLIST_COLUMNS = ["ari_id", "synonym", "names_instead"]
EQUIV_COLUMNS = [
    "source_prefix",
    "source_id",
    "source_name",
    "relation",
    "target_prefix",
    "target_id",
    "type",
    "source",
]

# A reversed judgment keeps BOTH rows: the editor app annotates the withdrawn one
# in `comment` instead of deleting it, so a consumer can see which of two
# contradictory rows was withdrawn without reimplementing the ordering. Kept in
# step with `SUPERSEDED_PREFIX` in the app's `app/sssom_service.py`. Only rows
# without this marker count as live judgments.
SUPERSEDED_MARKER = "Superseded by the "

ALLOWED_PREDICATES = {"skos:exactMatch"}
ALLOWED_JUSTIFICATIONS = {"semapv:ManualMappingCuration", "semapv:LexicalMatching"}
ALLOWED_MODIFIERS = {"", "Not"}
ALLOWED_EQUIV_TYPES = {"manual", "manual-negative", "manual-absent"}

# `manual-absent` records "we looked and there is no term"; SSSOM spells that
# as the object `sssom:NoTermFound` with `object_source` naming the vocabulary
# that was searched.
NO_TERM_FOUND = "sssom:NoTermFound"

# Values that mean "the editor had nothing to write here". Any of these reaching
# the mapping files is a bug in the export, not a curation decision.
PLACEHOLDER_IDS = {"null", "none", "nil", "nan", "n/a", "na", "undefined", "-", "--", "#n/a", "?"}

# One pattern per vocabulary, matched against the local part of the CURIE.
ID_PATTERNS = {
    "SNOMEDCT": re.compile(r"\d{6,18}"),
    "omop": re.compile(r"\d{4,10}"),
    "DOID": re.compile(r"\d{1,7}"),
    "MONDO": re.compile(r"\d{7}"),
    "ncit": re.compile(r"C\d{2,7}"),
    # A single ICD-10-CM code, never a range. U07.1 and U09.9 are in current use.
    "icd10cm": re.compile(r"[A-Z]\d[0-9A-Z](\.[0-9A-Z]{1,4})?"),
    "ORPHA": re.compile(r"\d{1,7}"),
    "OMIM": re.compile(r"\d{6}"),
    "umls": re.compile(r"C\d{7}"),
    "mesh": re.compile(r"[CD]\d{6,9}"),
}
ID_SHAPES = {
    "SNOMEDCT": "6-18 digits",
    "omop": "4-10 digits",
    "DOID": "up to 7 digits, no prefix",
    "MONDO": "exactly 7 digits, no prefix",
    "ncit": "C followed by 2-7 digits",
    "icd10cm": "a single code — a letter, a digit, an alphanumeric, then an optional "
    ".subdivision — not a range",
    "ORPHA": "up to 7 digits, no prefix",
    "OMIM": "exactly 6 digits",
    "umls": "C followed by 7 digits",
    "mesh": "C or D followed by 6-9 digits",
}

# Where each vocabulary's identifiers live on a disease in the ontology.
# ARI_DXCODE mirrors ARI_SNOMED, so a SNOMED code can be stored under either.
ONTOLOGY_PROPERTIES = {
    "SNOMEDCT": ("ARI_SNOMED", "ARI_DXCODE"),
    "omop": ("ARI_OMOP",),
    "DOID": ("ARI_DOID",),
    "icd10cm": ("ARI_ICD10",),
    "mesh": ("ARI_MESH",),
    "ncit": ("ARI_NCI",),
    "umls": ("ARI_UMLS",),
    "MONDO": ("ARI_MONDO",),
    "ORPHA": ("ARI_ORPHANET",),
    "OMIM": ("ARI_OMIM",),
}
# Ontology properties whose stored values must satisfy the same shape as the
# matching vocabulary in the mapping files.
ONTOLOGY_VALUE_PATTERNS = {
    "ARI_SNOMED": "SNOMEDCT",
    "ARI_DXCODE": "SNOMEDCT",
    "ARI_OMOP": "omop",
    "ARI_DOID": "DOID",
    "ARI_ICD10": "icd10cm",
    "ARI_MESH": "mesh",
    "ARI_NCI": "ncit",
    "ARI_UMLS": "umls",
    "ARI_MONDO": "MONDO",
    "ARI_ORPHANET": "ORPHA",
    "ARI_OMIM": "OMIM",
}

ARI_SUBJECT_RE = re.compile(r"ARI:\d{7}")
AUTHOR_RE = re.compile(r"github:[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?")
# SSSOM types `mapping_date` as a date, but the editor app publishes a full ISO
# 8601 timestamp because two judgments on one pair in one day need an order.
# Both are accepted; the date part is what the check is really about.
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})?)?")
ICD9_RE = re.compile(r"\d{2,3}(\.\d{1,2})?")
CURIE_MAP_RE = re.compile(r"#\s{2,}([A-Za-z0-9_.]+):\s")

ARI_DISEASE_BASE = "http://www.aurint.org/ontologies/ari-disease#"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDF_TYPE = RDF + "type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
RDFS_SUBCLASS_OF = "http://www.w3.org/2000/01/rdf-schema#subClassOf"
SKOS = "http://www.w3.org/2004/02/skos/core#"
SKOS_ALT_LABEL = SKOS + "altLabel"
OBOINOWL_ID = "http://www.geneontology.org/formats/oboInOwl#id"
OWL = "http://www.w3.org/2002/07/owl#"
OWL_CLASS = OWL + "Class"
PROPERTY_TYPES = {OWL + "AnnotationProperty", OWL + "ObjectProperty", OWL + "DatatypeProperty"}
XML_BASE = "http://www.w3.org/XML/1998/namespace base"
SYMPTOM_CLASS = ARI_DISEASE_BASE + "Symptom"
# A Symptom individual links the shared ARIS class its label names, or says with
# ARI_NoConcept why it links none ("not a symptom", "no term", "not linked"). A biomarker
# concept adds "not a biomarker".
SHARED_CONCEPT = ARI_DISEASE_BASE + "sharedConcept"
NO_CONCEPT = ARI_DISEASE_BASE + "ARI_NoConcept"
NO_CONCEPT_VALUES = ("not a symptom", "no term", "not linked", "not a biomarker")
UBERON = "http://purl.obolibrary.org/obo/UBERON_"
OBSOLETE = ARI_DISEASE_BASE + "ARI_Obsolete"
# A biomarker concept is an ARIB class under one of these core classes, directly
# or through other ARIB classes. Its kind is the name the scripts and the app use.
# A per-disease biomarker entry has one of them as its rdf:type.
ARIB = "http://www.aurint.org/ontologies/ari-biomarkers#ARIB_"
BIOMARKER_KINDS = {
    ARI_DISEASE_BASE + "Autoantibody": "antibodies",
    ARI_DISEASE_BASE + "Antigen": "antigens",
    ARI_DISEASE_BASE + "ClinicalBiomarker": "tests",
}
TARGETS_ANTIGEN = ARI_DISEASE_BASE + "targetsAntigen"
EXPRESSED_IN = ARI_DISEASE_BASE + "expressedIn"
ASSOCIATED_SYMPTOM = ARI_DISEASE_BASE + "associatedSymptom"
# The matches that settle a concept's external term. relatedMatch (a protein's
# HGNC gene) points at a relative, not the concept itself.
DECIDING_MATCHES = (SKOS + "exactMatch", SKOS + "closeMatch", SKOS + "broadMatch")
MATCHES = (*DECIDING_MATCHES, SKOS + "narrowMatch", SKOS + "relatedMatch")


@dataclass(frozen=True)
class Finding:
    level: str  # "error" or "warning"
    code: str
    path: str
    line: int  # 0 when the finding is about the file as a whole
    message: str

    def sort_key(self) -> tuple:
        return (0 if self.level == "error" else 1, self.path, self.line, self.code)


@dataclass
class Row:
    line: int
    fields: dict


class Report:
    def __init__(self) -> None:
        self.findings: list[Finding] = []

    def error(self, code: str, path: str, line: int, message: str) -> None:
        self.findings.append(Finding("error", code, path, line, message))

    def warning(self, code: str, path: str, line: int, message: str) -> None:
        self.findings.append(Finding("warning", code, path, line, message))


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


def read_text(path: str, report: Report) -> str | None:
    """Read a repository file, reporting encoding and line-ending problems."""
    full = os.path.join(REPO_ROOT, path)
    if not os.path.exists(full):
        report.error("missing-file", path, 0, "File does not exist.")
        return None
    raw = open(full, "rb").read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        report.error("encoding", path, 0, f"File is not valid UTF-8: {exc}.")
        return None
    if text.startswith("﻿"):
        report.error(
            "byte-order-mark",
            path,
            1,
            "File starts with a UTF-8 byte-order mark, which corrupts the first column name. "
            "Save as UTF-8 without BOM.",
        )
        text = text.lstrip("﻿")
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n")
    if crlf not in (0, lf):
        report.error(
            "mixed-line-endings",
            path,
            0,
            f"Mixed line endings: {crlf} CRLF out of {lf} lines. Use one convention throughout, "
            "otherwise every unrelated edit rewrites the whole file.",
        )
    if raw and not raw.endswith(b"\n"):
        report.error(
            "no-trailing-newline", path, 0, "File does not end with a newline, so the last row "
            "merges with the first row of the next edit."
        )
    return text


def split_rows(text: str, path: str, columns: list[str], report: Report) -> list[Row]:
    """Split a TSV into rows, validating the header and column counts."""
    lines = text.replace("\r\n", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()

    header_index = None
    for index, line in enumerate(lines):
        if line.startswith("#"):
            continue
        header_index = index
        break
    if header_index is None:
        report.error("empty-file", path, 0, "File contains no rows.")
        return []

    header = lines[header_index].split("\t")
    if header != columns:
        report.error(
            "header-schema",
            path,
            header_index + 1,
            f"Header is {header}, expected {columns}. A column added, removed or reordered here "
            "silently shifts every value in the file.",
        )
        return []

    rows: list[Row] = []
    for index in range(header_index + 1, len(lines)):
        line = lines[index]
        number = index + 1
        if not line.strip():
            report.error("blank-row", path, number, "Blank line inside the data block.")
            continue
        if line.startswith("#"):
            report.error(
                "comment-in-data",
                path,
                number,
                "Comment line after the header. SSSOM metadata must precede the header row.",
            )
            continue
        values = line.split("\t")
        if len(values) != len(columns):
            report.error(
                "column-count",
                path,
                number,
                f"Row has {len(values)} columns, expected {len(columns)}. "
                "A literal tab or an unescaped newline inside a value will do this.",
            )
            continue
        rows.append(Row(number, dict(zip(columns, values))))
    return rows


@dataclass
class Disease:
    ari_id: str
    label: str | None
    annotations: dict  # property -> list of (value, line)


@dataclass
class Entity:
    """One top-level node of the RDF/XML: everything said about one subject."""
    iri: str
    line: int
    types: set
    statements: list  # (property IRI, value, line); value is the literal text or resource IRI

    def values(self, prop: str) -> list:
        return [(value, line) for p, value, line in self.statements if p == prop]


def read_entities(text: str) -> list[Entity]:
    """Every top-level node with an rdf:about, read as XML rather than by line.

    Any RDF/XML layout reads the same: the formatter's (tools/format-owl.sh) or
    another tool's. A node may be `<owl:NamedIndividual>` with `rdf:type`
    children or a typed node such as `<Symptom>`, and IRIs may be relative to
    xml:base. Raises ExpatError when the file is not well-formed XML.
    """
    parser = expat.ParserCreate(namespace_separator=" ")
    entities: list[Entity] = []
    bases: list[str] = []  # xml:base in force at each open element
    current: Entity | None = None
    literal: list | None = None  # [property IRI, line, text parts] of the open literal property

    def resolve(ref: str) -> str:
        return urljoin(bases[-1], ref)

    def start(name: str, attrs: dict) -> None:
        nonlocal current, literal
        bases.append(attrs.get(XML_BASE, bases[-1] if bases else ""))
        depth = len(bases)
        iri = name.replace(" ", "", 1)
        line = parser.CurrentLineNumber
        if depth == 2 and RDF + " about" in attrs:
            types = set() if iri == RDF + "Description" else {iri}
            current = Entity(resolve(attrs[RDF + " about"]), line, types, [])
        elif depth == 3 and current is not None:
            if RDF + " resource" in attrs:
                value = resolve(attrs[RDF + " resource"])
                current.statements.append((iri, value, line))
                if iri == RDF_TYPE:
                    current.types.add(value)
            else:
                literal = [iri, line, []]

    def end(name: str) -> None:
        nonlocal current, literal
        depth = len(bases)
        bases.pop()
        if depth == 3 and literal is not None and current is not None:
            current.statements.append((literal[0], "".join(literal[2]).strip(), literal[1]))
            literal = None
        elif depth == 2 and current is not None:
            entities.append(current)
            current = None

    def chars(data: str) -> None:
        if literal is not None and len(bases) == 3:
            literal[2].append(data)

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = chars
    parser.Parse(text, True)
    return entities


def load_ontology(report: Report) -> dict[str, Disease] | None:
    """Parse ARI disease entities and their cross-reference annotations."""
    text = read_text(ONTOLOGY_PATH, report)
    if text is None:
        return None
    try:
        return parse_ontology(text, report)
    except expat.ExpatError as exc:
        report.error("ontology-not-well-formed", ONTOLOGY_PATH, 0, f"OWL/XML does not parse: {exc}.")
        return None


def parse_ontology(text: str, report: Report | None = None) -> dict[str, Disease]:
    """Diseases keyed by ARI id, from already-read OWL text.

    The element name is not what makes an entity a disease; its ARI_ID is.
    """
    diseases: dict[str, Disease] = {}
    for entity in read_entities(text):
        annotations = collections.defaultdict(list)
        for prop, value, line in entity.statements:
            if prop.startswith(ARI_DISEASE_BASE + "ARI_"):
                annotations[prop[len(ARI_DISEASE_BASE):]].append((value, line))
        ids = annotations.get("ARI_ID", [])
        ari_id = ids[0][0] if ids else None
        if not (ari_id and ari_id.startswith("ARI:")):
            continue
        if ari_id in diseases:
            if report is not None:
                report.error(
                    "duplicate-ari-id",
                    ONTOLOGY_PATH,
                    ids[0][1],
                    f"{ari_id} is used by more than one entity, so mappings for it "
                    "are ambiguous.",
                )
            continue
        labels = entity.values(RDFS_LABEL)
        diseases[ari_id] = Disease(ari_id, labels[-1][0] if labels else None, dict(annotations))
    return diseases


def stored_ids(disease: Disease, prefix: str) -> dict[str, int]:
    """Cross-reference ids stored on a disease for one vocabulary, value -> line.

    Values are sometimes packed several to an annotation as a comma-separated
    string, so each is unpacked before comparison.
    """
    found: dict[str, int] = {}
    for prop in ONTOLOGY_PROPERTIES.get(prefix, ()):
        for value, line in disease.annotations.get(prop, []):
            for part in value.split(","):
                part = part.strip()
                if part:
                    found.setdefault(part, line)
    return found


# --------------------------------------------------------------------------
# Row checks
# --------------------------------------------------------------------------


def check_sssom_rows(rows: list[Row], report: Report) -> None:
    # The app stamps `mapping_date` in UTC, so "today" has to be UTC too. Against
    # a local date this reported every evening publish west of UTC as tomorrow's
    # work — CI runners are UTC and never saw it, curators running the validator
    # locally did.
    today = datetime.now(timezone.utc).date().isoformat()
    seen: dict[tuple, int] = {}
    modifiers_by_pair: dict[tuple, dict[str, int]] = collections.defaultdict(dict)
    labels: dict[str, dict[str, int]] = collections.defaultdict(dict)

    for row in rows:
        fields = row.fields
        line = row.line
        for column, value in fields.items():
            if value != value.strip():
                report.error(
                    "whitespace",
                    SSSOM_PATH,
                    line,
                    f"Column `{column}` has leading or trailing whitespace: {value!r}.",
                )

        subject = fields["subject_id"].strip()
        if not ARI_SUBJECT_RE.fullmatch(subject):
            report.error(
                "subject-format",
                SSSOM_PATH,
                line,
                f"`subject_id` {subject!r} is not an ARI CURIE of the form ARI:0001234.",
            )
        if not fields["subject_label"].strip():
            report.error("empty-label", SSSOM_PATH, line, "`subject_label` is empty.")
        else:
            labels[subject].setdefault(fields["subject_label"].strip(), line)

        if fields["predicate_id"] not in ALLOWED_PREDICATES:
            report.error(
                "predicate",
                SSSOM_PATH,
                line,
                f"`predicate_id` {fields['predicate_id']!r} is not one of {sorted(ALLOWED_PREDICATES)}.",
            )
        modifier = fields["predicate_modifier"]
        if modifier not in ALLOWED_MODIFIERS:
            report.error(
                "predicate-modifier",
                SSSOM_PATH,
                line,
                f"`predicate_modifier` {modifier!r} is not one of {sorted(ALLOWED_MODIFIERS)}. "
                "Only `Not` marks a curator-rejected mapping.",
            )
        if fields["mapping_justification"] not in ALLOWED_JUSTIFICATIONS:
            report.error(
                "justification",
                SSSOM_PATH,
                line,
                f"`mapping_justification` {fields['mapping_justification']!r} is not one of "
                f"{sorted(ALLOWED_JUSTIFICATIONS)}.",
            )

        author = fields["author_id"]
        if not AUTHOR_RE.fullmatch(author):
            report.error(
                "author",
                SSSOM_PATH,
                line,
                f"`author_id` {author!r} is not a `github:<login>` handle, so the judgment has no "
                "attributable owner.",
            )
        mapping_date = fields["mapping_date"]
        if not DATE_RE.fullmatch(mapping_date):
            report.error(
                "date-format", SSSOM_PATH, line, f"`mapping_date` {mapping_date!r} is not an ISO 8601 date or timestamp."
            )
        elif mapping_date[:10] > today:
            # Compare the date part only: a timestamp sorts after the bare date it
            # falls on, so the whole string would read as tomorrow.
            report.error(
                "date-future",
                SSSOM_PATH,
                line,
                f"`mapping_date` {mapping_date} is in the future (today is {today}).",
            )

        check_object_id(row, report)

        object_id = distinct_object_id(fields)
        key = (subject, object_id, modifier)
        if key in seen:
            report.error(
                "duplicate-row",
                SSSOM_PATH,
                line,
                f"Duplicate of line {seen[key]}: same subject, object and modifier.",
            )
        else:
            seen[key] = line
        superseded = fields["comment"].startswith(SUPERSEDED_MARKER)
        modifiers_by_pair[(subject, object_id)][modifier] = (line, superseded)

    for (subject, object_id), by_modifier in modifiers_by_pair.items():
        live = sorted(line for line, superseded in by_modifier.values() if not superseded)
        if len(live) > 1:
            lines = ", ".join(str(line) for line in live)
            report.error(
                "contradiction",
                SSSOM_PATH,
                live[0],
                f"{subject} -> {object_id} is recorded as both confirmed and flagged-wrong "
                f"(lines {lines}) with neither row marked superseded. A reversal must annotate "
                f"the withdrawn row in `comment`; otherwise one of the two judgments has to go.",
            )

    for subject, by_label in labels.items():
        if len(by_label) > 1:
            variants = "; ".join(f"{label!r} (line {line})" for label, line in sorted(by_label.items()))
            report.error(
                "label-drift",
                SSSOM_PATH,
                min(by_label.values()),
                f"{subject} appears under more than one `subject_label`: {variants}.",
            )


def check_target_id(path: str, line: int, prefix: str, local: str, report: Report) -> None:
    """Validate one cross-reference identifier against its vocabulary."""
    curie = f"{prefix}:{local}"

    if local.lower() in PLACEHOLDER_IDS:
        report.error(
            "placeholder-id",
            path,
            line,
            f"The target identifier is {curie!r}. A missing identifier reached the file as a "
            "literal placeholder. Supply the real id, or record the row as `NoTermFound` if the "
            "vocabulary genuinely has no term for this disease.",
        )
        return

    if ":" in local:
        report.error(
            "double-prefix",
            path,
            line,
            f"{curie!r} carries its prefix twice. The local part must be the bare identifier, so "
            f"this should read {prefix}:{local.split(':', 1)[1]}.",
        )
        return

    if prefix not in ID_PATTERNS:
        report.error(
            "unknown-prefix",
            path,
            line,
            f"Prefix {prefix!r} is not a mapped vocabulary ({', '.join(sorted(ID_PATTERNS))}).",
        )
        return

    if ID_PATTERNS[prefix].fullmatch(local):
        return

    if prefix == "icd10cm" and ICD9_RE.fullmatch(local):
        report.error(
            "icd9-under-icd10",
            path,
            line,
            f"{curie} is an ICD-9-CM code stored under the ICD-10-CM prefix — every ICD-10-CM "
            "code starts with a letter. ICD-9 was retired from this registry; replace it with the "
            "ICD-10-CM equivalent or remove the row.",
        )
    else:
        report.error(
            "id-shape",
            path,
            line,
            f"{curie} does not look like a {prefix} identifier (expected {ID_SHAPES[prefix]}).",
        )


def check_object_id(row: Row, report: Report) -> None:
    """Validate an SSSOM `object_id` CURIE and its `object_source`."""
    line = row.line
    object_id = row.fields["object_id"].strip()
    source = row.fields["object_source"].strip()

    if object_id == NO_TERM_FOUND:
        if source not in ID_PATTERNS:
            report.error(
                "no-term-found-source",
                SSSOM_PATH,
                line,
                f"`{NO_TERM_FOUND}` rows must name the vocabulary that was searched in "
                f"`object_source`; got {source!r}.",
            )
        return

    if ":" not in object_id:
        report.error(
            "object-not-curie",
            SSSOM_PATH,
            line,
            f"`object_id` {object_id!r} is not a CURIE. Expected `prefix:localid`.",
        )
        return

    prefix, local = object_id.split(":", 1)
    if prefix in ID_PATTERNS and source != prefix:
        report.error(
            "object-source",
            SSSOM_PATH,
            line,
            f"`object_source` is {source!r} but `object_id` uses prefix {prefix!r}.",
        )
    check_target_id(SSSOM_PATH, line, prefix, local, report)


def check_curie_map(text: str, rows: list[Row], report: Report) -> None:
    """Every prefix used in the file must be declared in the SSSOM curie_map."""
    header_lines = [line for line in text.replace("\r\n", "\n").split("\n") if line.startswith("#")]
    if not header_lines or not header_lines[0].startswith("# curie_map:"):
        report.error(
            "curie-map-missing",
            SSSOM_PATH,
            1,
            "File does not start with a `# curie_map:` block, so the CURIEs cannot be expanded.",
        )
        return
    declared = {match.group(1) for line in header_lines for match in [CURIE_MAP_RE.match(line)] if match}
    used = {"ARI"}
    for row in rows:
        for field in ("predicate_id", "object_id", "mapping_justification"):
            value = row.fields[field]
            if ":" in value:
                used.add(value.split(":", 1)[0])
    for prefix in sorted(used - declared):
        report.error(
            "curie-map-incomplete",
            SSSOM_PATH,
            1,
            f"Prefix {prefix!r} is used in the file but not declared in the `# curie_map:` block.",
        )


def check_equiv_rows(rows: list[Row], report: Report) -> None:
    for row in rows:
        fields = row.fields
        line = row.line
        for column, value in fields.items():
            if value != value.strip():
                report.error(
                    "whitespace",
                    EQUIV_PATH,
                    line,
                    f"Column `{column}` has leading or trailing whitespace: {value!r}.",
                )
        if fields["source_prefix"] != "ARI":
            report.error(
                "equiv-source-prefix",
                EQUIV_PATH,
                line,
                f"`source_prefix` is {fields['source_prefix']!r}, expected 'ARI'.",
            )
        if fields["relation"] not in ALLOWED_PREDICATES:
            report.error(
                "equiv-relation",
                EQUIV_PATH,
                line,
                f"`relation` {fields['relation']!r} is not one of {sorted(ALLOWED_PREDICATES)}.",
            )
        if fields["type"] not in ALLOWED_EQUIV_TYPES:
            report.error(
                "equiv-type",
                EQUIV_PATH,
                line,
                f"`type` {fields['type']!r} is not one of {sorted(ALLOWED_EQUIV_TYPES)}.",
            )
        if not AUTHOR_RE.fullmatch(fields["source"]):
            report.error(
                "equiv-author",
                EQUIV_PATH,
                line,
                f"`source` {fields['source']!r} is not a `github:<login>` handle.",
            )
        target = fields["target_id"].strip()
        if fields["type"] == "manual-absent":
            if target != "NoTermFound":
                report.error(
                    "equiv-absent-target",
                    EQUIV_PATH,
                    line,
                    f"`manual-absent` rows must use target_id 'NoTermFound'; got {target!r}.",
                )
        else:
            check_target_id(EQUIV_PATH, line, fields["target_prefix"].strip(), target, report)


def normalized_subject(curie: str) -> str:
    """ARI CURIE with the digits unpadded, for joining across the two files.

    Padding disagreements are reported once each by `subject-unknown`, against
    the ontology as the single source of truth; folding them here keeps the
    cross-file comparison focused on the object ids.
    """
    prefix, _, local = curie.partition(":")
    return f"{prefix}:{local.lstrip('0') or '0'}"


def distinct_object_id(fields: dict) -> str:
    """Object id that distinguishes one row from another.

    Every `manual-absent` row carries the same literal `sssom:NoTermFound`
    object, so the searched vocabulary in `object_source` is what separates
    "no ORPHA term" from "no OMIM term" for the same subject.
    """
    object_id = fields["object_id"].strip()
    if object_id == NO_TERM_FOUND:
        return f"{fields['object_source'].strip()}:NoTermFound"
    return object_id


def sssom_key(fields: dict) -> tuple:
    """Comparable identity of an SSSOM row, exact strings so id drift shows."""
    object_id = distinct_object_id(fields)
    modifier = "Not" if fields["predicate_modifier"] == "Not" else ""
    return (
        normalized_subject(fields["subject_id"].strip()),
        object_id,
        modifier,
        fields["author_id"].strip(),
    )


def equiv_key(fields: dict) -> tuple:
    object_id = f"{fields['target_prefix'].strip()}:{fields['target_id'].strip()}"
    modifier = "Not" if fields["type"] == "manual-negative" else ""
    return (
        normalized_subject(f"{fields['source_prefix'].strip()}:{fields['source_id'].strip()}"),
        object_id,
        modifier,
        fields["source"].strip(),
    )


def check_cross_file(sssom: list[Row], equiv: list[Row], report: Report) -> None:
    """The two exports must describe exactly the same set of judgments.

    A row present in one file and absent from the other is nearly always a
    spreadsheet round-trip that reformatted an id — `362.50` losing its
    trailing zero, `0111157` losing its leading zeros, an ARI id written at the wrong
    width.
    """
    sssom_index = collections.defaultdict(list)
    for row in sssom:
        sssom_index[sssom_key(row.fields)].append(row)
    equiv_index = collections.defaultdict(list)
    for row in equiv:
        equiv_index[equiv_key(row.fields)].append(row)

    for key, rows in sorted(sssom_index.items()):
        if key not in equiv_index:
            report.error(
                "cross-file-drift",
                SSSOM_PATH,
                rows[0].line,
                f"{key[0]} -> {key[1]} ({'flagged wrong' if key[2] else 'confirmed'}, {key[3]}) "
                f"has no counterpart in {EQUIV_PATH}. The two exports must stay identical row for row.",
            )
    for key, rows in sorted(equiv_index.items()):
        if key not in sssom_index:
            report.error(
                "cross-file-drift",
                EQUIV_PATH,
                rows[0].line,
                f"{key[0]} -> {key[1]} ({'flagged wrong' if key[2] else 'confirmed'}, {key[3]}) "
                f"has no counterpart in {SSSOM_PATH}. The two exports must stay identical row for row.",
            )


def check_subject_exists(
    path: str, line: int, subject: str, diseases: dict[str, Disease], report: Report
) -> Disease | None:
    """The ontology's `ARI_ID` is the one spelling of a disease id both files must use."""
    disease = diseases.get(subject)
    if disease is not None:
        return disease
    alternatives = [
        known for known in diseases if normalized_subject(known) == normalized_subject(subject)
    ]
    if alternatives:
        report.error(
            "subject-padding",
            path,
            line,
            f"{subject} is written with different zero-padding than the ontology, which spells it "
            f"{alternatives[0]}. Use the ontology's spelling so the two mapping files and the "
            "ontology join.",
        )
    else:
        report.error(
            "subject-unknown",
            path,
            line,
            f"{subject} has no matching disease in {ONTOLOGY_PATH}. The mapping points at nothing.",
        )
    return None


def check_equiv_against_ontology(
    equiv: list[Row], diseases: dict[str, Disease], report: Report
) -> None:
    for row in equiv:
        subject = f"{row.fields['source_prefix'].strip()}:{row.fields['source_id'].strip()}"
        disease = check_subject_exists(EQUIV_PATH, row.line, subject, diseases, report)
        if disease and disease.label and disease.label != row.fields["source_name"].strip():
            report.error(
                "label-mismatch",
                EQUIV_PATH,
                row.line,
                f"`source_name` is {row.fields['source_name']!r} but {subject} is labelled "
                f"{disease.label!r} in the ontology.",
            )


def check_against_ontology(sssom: list[Row], diseases: dict[str, Disease], report: Report) -> None:
    """Reconcile curated judgments with the ids the ontology actually serves."""
    for row in sssom:
        fields = row.fields
        subject = fields["subject_id"].strip()
        disease = check_subject_exists(SSSOM_PATH, row.line, subject, diseases, report)
        if disease is None:
            continue
        if disease.label and disease.label != fields["subject_label"].strip():
            report.error(
                "label-mismatch",
                SSSOM_PATH,
                row.line,
                f"`subject_label` is {fields['subject_label']!r} but {subject} is labelled "
                f"{disease.label!r} in the ontology.",
            )

        object_id = fields["object_id"].strip()
        if object_id == NO_TERM_FOUND or ":" not in object_id:
            continue
        prefix, local = object_id.split(":", 1)
        if prefix not in ONTOLOGY_PROPERTIES or local.lower() in PLACEHOLDER_IDS:
            continue
        if fields["comment"].startswith(SUPERSEDED_MARKER):
            continue
        stored = stored_ids(disease, prefix)

        if fields["predicate_modifier"] == "Not":
            if local in stored:
                properties = " or ".join(ONTOLOGY_PROPERTIES[prefix])
                report.error(
                    "flagged-still-stored",
                    SSSOM_PATH,
                    row.line,
                    f"{object_id} is flagged wrong for {subject} but is still stored on the "
                    f"disease ({properties}, {ONTOLOGY_PATH}:{stored[local]}) and is still served "
                    "to users. Remove the id from the ontology in the same change.",
                )
        elif local not in stored:
            report.warning(
                "confirmed-not-stored",
                SSSOM_PATH,
                row.line,
                f"{object_id} is confirmed for {subject} but is not stored on the disease in "
                f"{ONTOLOGY_PATH}, so the confirmation is not reflected in what users see.",
            )


def check_ontology_values(diseases: dict[str, Disease], report: Report) -> None:
    """The ontology's own cross-reference values must satisfy the same shapes."""
    for disease in diseases.values():
        if not ARI_SUBJECT_RE.fullmatch(disease.ari_id):
            report.error(
                "ari-id-shape",
                ONTOLOGY_PATH,
                disease.annotations["ARI_ID"][0][1],
                f"{disease.ari_id} ({disease.label!r}) is not a registry id of the form "
                "ARI:0001234.",
            )
        # ARI_FormerID records an id a disease was renumbered from, so the deletion
        # check can follow it. A former id still in use would make it ambiguous.
        for value, line in disease.annotations.get("ARI_FormerID", []):
            if value in diseases:
                report.error(
                    "former-id-in-use",
                    ONTOLOGY_PATH,
                    line,
                    f"{disease.ari_id} lists {value} as a former id, but {value} is still the "
                    f"ARI_ID of {diseases[value].label!r}.",
                )
        for prop, prefix in ONTOLOGY_VALUE_PATTERNS.items():
            for value, line in disease.annotations.get(prop, []):
                for part in [item.strip() for item in value.split(",")]:
                    if not part:
                        continue
                    if part.lower() in PLACEHOLDER_IDS:
                        report.error(
                            "placeholder-id",
                            ONTOLOGY_PATH,
                            line,
                            f"{disease.ari_id} stores {part!r} as its {prop} value.",
                        )
                    elif ID_PATTERNS[prefix].fullmatch(part):
                        continue
                    elif prop == "ARI_ICD10" and ICD9_RE.fullmatch(part):
                        report.error(
                            "icd9-under-icd10",
                            ONTOLOGY_PATH,
                            line,
                            f"{disease.ari_id} stores ICD-9-CM code {part!r} in {prop}. ICD-9 was "
                            "retired from this registry; replace it with the ICD-10-CM equivalent "
                            "or remove it.",
                        )
                    else:
                        report.error(
                            "id-shape",
                            ONTOLOGY_PATH,
                            line,
                            f"{disease.ari_id} stores {part!r} in {prop}, which does not look like "
                            f"a {prefix} identifier (expected {ID_SHAPES[prefix]}).",
                        )

        # An ARI_SynonymWithdrawn marker is what lets a synonym leave ARI_Synonym.
        # It must be shaped "<synonym> | <reason> | <note>" with a known reason, and
        # must not name a synonym that is still present (that is a contradiction,
        # not a withdrawal).
        live_synonyms = _values(disease, "ARI_Synonym")
        for value, line in disease.annotations.get("ARI_SynonymWithdrawn", []):
            parts = [p.strip() for p in value.split("|")]
            if len(parts) < 3 or not parts[0] or not parts[2]:
                report.error(
                    "withdrawn-synonym-shape",
                    ONTOLOGY_PATH,
                    line,
                    f"{disease.ari_id} has an ARI_SynonymWithdrawn value {value!r} that is not "
                    "'<synonym> | <reason> | <note>'.",
                )
                continue
            if parts[1] not in WITHDRAWAL_REASONS:
                report.error(
                    "withdrawn-synonym-reason",
                    ONTOLOGY_PATH,
                    line,
                    f"{disease.ari_id} withdraws {parts[0]!r} with reason {parts[1]!r}; expected "
                    f"one of {sorted(WITHDRAWAL_REASONS)}.",
                )
            if parts[0] in live_synonyms:
                report.error(
                    "withdrawn-synonym-still-present",
                    ONTOLOGY_PATH,
                    line,
                    f"{disease.ari_id} still lists {parts[0]!r} as an ARI_Synonym but also marks "
                    "it withdrawn. Remove the ARI_Synonym line or the marker.",
                )

        # ARI_DXCODE mirrors ARI_SNOMED. A DXCODE value with no SNOMED counterpart is how a
        # rejected SNOMED code survives removal, so it is worth surfacing; the reverse
        # (SNOMED recorded without a DXCODE copy) is common and harmless.
        snomed = {
            part.strip()
            for value, _ in disease.annotations.get("ARI_SNOMED", [])
            for part in value.split(",")
            if part.strip()
        }
        orphan_dxcodes = {
            part.strip(): line
            for value, line in disease.annotations.get("ARI_DXCODE", [])
            for part in value.split(",")
            if part.strip() and part.strip() not in snomed
        }
        if orphan_dxcodes:
            report.warning(
                "dxcode-without-snomed",
                ONTOLOGY_PATH,
                min(orphan_dxcodes.values()),
                f"{disease.ari_id} stores ARI_DXCODE {sorted(orphan_dxcodes)} with no matching "
                "ARI_SNOMED value. DXCODE mirrors SNOMED, so a code removed from one can survive "
                "under the other.",
            )


# --------------------------------------------------------------------------
# Diff scoping and output
# --------------------------------------------------------------------------


def baseline_text(ref: str, path: str) -> str | None:
    """Text of `path` at `ref`, or None if it did not exist."""
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.decode("utf-8", "replace").replace("\r\n", "\n")


def current_text(path: str) -> str:
    full = os.path.join(REPO_ROOT, path)
    if not os.path.exists(full):
        return ""
    return open(full, encoding="utf-8", errors="replace").read().replace("\r\n", "\n")


def current_lines(path: str) -> list[str]:
    return current_text(path).split("\n")


# Curation records that only ever accumulate. Nothing a curator decides removes
# one, so a branch that drops one is reverting somebody rather than reviewing.
APPEND_ONLY_PROPERTIES = {
    "ARI_Synonym": "synonym",
    "ARI_ClinicalSubtype": "clinical subtype",
    "ARI_ChangeLog": "changelog entry",
    "ARI_SynonymWithdrawn": "withdrawn-synonym record",
    "ARI_FormerID": "former id",
}
# A synonym may leave `ARI_Synonym` only when the same disease carries an
# `ARI_SynonymWithdrawn` marker naming it: "<synonym text> | <reason> | <note>",
# where <reason> is one of subtype / broader / distinct / non-disease. The marker
# is itself append-only, so the review that retired the synonym stays on record.
WITHDRAWAL_REASONS = {"subtype", "broader", "distinct", "non-disease"}
# How many deleted values to name before the message just gives the count.
DELETION_SAMPLE = 3


def _withdrawn_synonyms(disease: Disease) -> set[str]:
    """Synonym texts this disease has an ARI_SynonymWithdrawn marker for.

    Tokenised the same way as `_values` (comma-split) so the result lines up with
    `_values(disease, "ARI_Synonym")` for set subtraction.
    """
    out: set[str] = set()
    for value, _ in disease.annotations.get("ARI_SynonymWithdrawn", []):
        head = value.split("|", 1)[0]
        out.update(part.strip() for part in head.split(",") if part.strip())
    return out


def _values(disease: Disease, prop: str) -> set[str]:
    out = set()
    for value, _ in disease.annotations.get(prop, []):
        out.update(part.strip() for part in value.split(",") if part.strip())
    return out


def summarise(values: set[str]) -> str:
    shown = sorted(values)[:DELETION_SAMPLE]
    rendered = ", ".join(repr(v if len(v) <= 60 else v[:57] + "...") for v in shown)
    extra = len(values) - len(shown)
    return rendered + (f" and {extra} more" if extra else "")


def check_deletions(ref: str, sssom_rows: list[Row], report: Report) -> None:
    """Report curation this branch removes from the ontology without reviewing it.

    The row checks only see rows that exist, so a save that reverts somebody
    else's work passes them all. This is the check that fails on absence.

    A cross-reference may legitimately go: flagging one wrong on the review page
    is exactly how a bad code is retired, and that judgment is in the mapping set.
    A synonym may go when an `ARI_SynonymWithdrawn` marker on the same disease
    names it, which records why (subtype / broader / distinct / non-disease).
    Anything else -- a subtype, a changelog entry, an unmarked synonym, or an id
    no curator ruled against -- has no decision behind its removal.
    """
    before_text = baseline_text(ref, ONTOLOGY_PATH)
    if before_text is None:
        return  # the ontology is new on this branch; nothing to have deleted
    before = parse_ontology(before_text)
    after = parse_ontology(current_text(ONTOLOGY_PATH))
    if not before or not after:
        return

    flagged = collections.defaultdict(set)
    for row in sssom_rows:
        if row.fields["predicate_modifier"].strip() != "Not":
            continue
        object_id = row.fields["object_id"].strip()
        if ":" in object_id:
            prefix, local = object_id.split(":", 1)
            flagged[(row.fields["subject_id"].strip(), prefix)].add(local)

    # A renumbered disease carries its old id in ARI_FormerID; follow it.
    renumbered = {
        former: disease
        for disease in after.values()
        for former in _values(disease, "ARI_FormerID")
    }
    for ari_id, was in sorted(before.items()):
        now = after.get(ari_id) or renumbered.get(ari_id)
        if now is None:
            report.error(
                "disease-deleted",
                ONTOLOGY_PATH,
                0,
                f"{ari_id} ({was.label!r}) is in {ref} but not in this branch. A disease is "
                "retired by setting ARI_Obsolete, never by deleting the individual.",
            )
            continue

        for prop, noun in APPEND_ONLY_PROPERTIES.items():
            lost = _values(was, prop) - _values(now, prop)
            if prop == "ARI_Synonym":
                lost -= _withdrawn_synonyms(now)
            if lost:
                remedy = (
                    "restore the value, or record an ARI_SynonymWithdrawn marker "
                    "saying why it is being withdrawn"
                    if prop == "ARI_Synonym"
                    else "restore the value, or say in review why it is being withdrawn"
                )
                report.error(
                    "record-deleted",
                    ONTOLOGY_PATH,
                    0,
                    f"{ari_id} loses {len(lost)} {noun}(s) this branch did not add: "
                    f"{summarise(lost)}. {prop} is an append-only record — {remedy}.",
                )

        for prefix, properties in ONTOLOGY_PROPERTIES.items():
            was_ids = set().union(*(_values(was, p) for p in properties))
            now_ids = set().union(*(_values(now, p) for p in properties))
            lost = was_ids - now_ids - flagged[(now.ari_id, prefix)]
            # A value that is not a well-formed identifier for its vocabulary was
            # never a usable cross-reference: an ICD-9 code under ICD-10, a range,
            # a doubly-prefixed CURIE. Dropping or re-spelling one is a repair, and
            # the shape checks already report it if it is still there.
            lost = {value for value in lost if ID_PATTERNS[prefix].fullmatch(value)}
            if lost:
                report.error(
                    "xref-deleted",
                    ONTOLOGY_PATH,
                    0,
                    f"{ari_id} loses {prefix} {summarise(lost)} with no matching "
                    f"`predicate_modifier: Not` row in {SSSOM_PATH}. Flag the id wrong on the "
                    "review page so the judgment is recorded, or restore it.",
                )


def statements(text: str) -> list[tuple]:
    """(line, (subject, property, value)) for every statement in OWL text."""
    return [
        (line, (entity.iri, prop, value))
        for entity in read_entities(text)
        for prop, value, line in entity.statements
    ]


def filter_to_changes(findings: list[Finding], ref: str) -> list[Finding]:
    """Keep only findings on content this branch added or rewrote since `ref`.

    Pre-existing problems are real, but a curator submitting one disease should
    not be blocked by debt they did not introduce; the scheduled audit covers
    the standing backlog.

    TSV findings compare line text. Ontology findings, in any module, compare
    the statement on the finding's line, (subject, property, value), so
    re-laying-out the file changes nothing here.

    One exception: when the symptoms module differs from `ref`, every symptom
    link finding is kept, and likewise every biomarker link finding when the
    biomarkers module differs. A label or altLabel moving between classes
    changes what every link should be without touching a disease line, so the
    lines cannot say which findings the branch caused.
    """
    baselines: dict[str, set | None] = {}
    currents: dict[str, list | dict] = {}
    kept = []
    for finding in findings:
        path = finding.path
        if path not in baselines:
            before = baseline_text(ref, path)
            if path.endswith(".owl"):
                baselines[path] = None if before is None else {s for _, s in statements(before)}
                by_line = collections.defaultdict(set)
                for line, statement in statements(current_text(path)):
                    by_line[line].add(statement)
                currents[path] = by_line
            else:
                baselines[path] = None if before is None else set(before.split("\n"))
                currents[path] = current_lines(path)
        baseline = baselines[path]
        if baseline is None or finding.line == 0:
            kept.append(finding)
            continue
        if path.endswith(".owl"):
            on_line = currents[path].get(finding.line)
            if not on_line or not on_line <= baseline:
                kept.append(finding)
            continue
        lines = currents[path]
        if finding.line - 1 >= len(lines):
            kept.append(finding)
            continue
        if lines[finding.line - 1] not in baseline:
            kept.append(finding)
    if baseline_text(ref, SYMPTOMS_PATH) != current_text(SYMPTOMS_PATH):
        kept += [f for f in findings if f not in kept and is_symptom_link_finding(f)]
    if baseline_text(ref, BIOMARKERS_PATH) != current_text(BIOMARKERS_PATH):
        kept += [f for f in findings if f not in kept and is_biomarker_link_finding(f)]
    return kept


def is_symptom_link_finding(finding: Finding) -> bool:
    """A finding that holds a Symptom's link up against the symptoms module,
    or a label or id the symptoms module gives to two classes."""
    return finding.code.startswith("symptom-concept-") or finding.code in (
        "symptom-decided-and-linked",
        "symptom-unmapped",
        "shared-concept-target-missing",
        "concept-label-ambiguous",
        "concept-id-repeated",
    )


def is_biomarker_link_finding(finding: Finding) -> bool:
    """A finding that holds a biomarker entry's link, or a concept's place,
    up against the biomarkers module, or a label or id it gives to two classes.
    A relation or an external match sits on its own line, so those are left to
    the line comparison."""
    if finding.code in ("biomarker-relation-target", "biomarker-external-missing"):
        return False
    return finding.code.startswith("biomarker-") or finding.code in (
        "shared-concept-target-missing",
        "concept-label-ambiguous",
        "concept-id-repeated",
    )


def annotate(finding: Finding) -> str:
    message = finding.message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    title = f"{finding.code}".replace(",", "%2C")
    location = f"file={finding.path}"
    if finding.line:
        location += f",line={finding.line}"
    return f"::{finding.level} {location},title=mappings/{title}::{message}"


def write_summary(path: str, findings: list[Finding], scope: str) -> None:
    errors = [f for f in findings if f.level == "error"]
    warnings = [f for f in findings if f.level == "warning"]
    lines = ["# Mapping validation", "", f"Scope: {scope}", ""]
    if not findings:
        lines.append("No problems found.")
    else:
        lines.append(f"**{len(errors)} error(s), {len(warnings)} warning(s)**")
        lines.append("")
        by_code = collections.Counter((f.level, f.code) for f in findings)
        lines.append("| Level | Check | Count |")
        lines.append("| --- | --- | --- |")
        for (level, code), count in sorted(by_code.items(), key=lambda item: (item[0], -item[1])):
            lines.append(f"| {level} | `{code}` | {count} |")
        lines.append("")
        lines.append("<details><summary>All findings</summary>")
        lines.append("")
        for finding in findings:
            where = f"`{finding.path}`" + (f":{finding.line}" if finding.line else "")
            lines.append(f"- **{finding.level}** `{finding.code}` {where} — {finding.message}")
        lines.append("")
        lines.append("</details>")
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def check_blocklist(rows: list[Row], diseases: dict[str, Disease] | None, report: Report) -> None:
    """Validate the predictor's synonym blocklist.

    A blocklist row only does anything if it matches a synonym the predictor
    actually sees, so the two ways it can rot silently are a duplicate pair
    (dead weight, and the sign of a bad merge) and an `ari_id` no longer in the
    ontology (the row excludes nothing at all, while still reading as a decision
    someone made).
    """
    seen: dict[tuple[str, str], int] = {}
    for row in rows:
        ari_id = row.fields["ari_id"].strip()
        synonym = row.fields["synonym"].strip()

        if not synonym:
            report.error(
                "blocklist-empty-synonym", BLOCKLIST_PATH, row.line,
                f"{ari_id or 'A row'} blocks an empty synonym, which matches nothing.",
            )
            continue

        key = (ari_id, synonym)
        if key in seen:
            report.error(
                "blocklist-duplicate", BLOCKLIST_PATH, row.line,
                f"Duplicate of line {seen[key]}: {ari_id} already blocks {synonym!r}.",
            )
        else:
            seen[key] = row.line

        if diseases is not None and ari_id not in diseases:
            report.error(
                "blocklist-unknown-disease", BLOCKLIST_PATH, row.line,
                f"{ari_id} is not a disease in {ONTOLOGY_PATH}, so blocking {synonym!r} on it "
                "excludes nothing. Correct the id or drop the row.",
            )


def concept_labels(path: str, text: str, report: Report) -> dict[str, str]:
    """Label or alternative label -> the shared concept class that carries it.

    This is the lookup a Symptom individual's label goes through, so a string
    that names two classes would link whichever came first. The same
    `oboInOwl:id` on two classes is the same fault one level up.
    """
    classes = [entity for entity in read_entities(text) if OWL_CLASS in entity.types]
    check_repeated_ids(path, classes, report)
    return label_lookup(path, classes, report)


def label_lookup(path: str, classes: list[Entity], report: Report) -> dict[str, str]:
    """Label or alternative label -> the one of `classes` that carries it.

    A string two of them carry is reported on the line of every class that
    carries it: the `--since` gate keeps a finding only when its line changed,
    and the branch may have added the string to either class.
    """
    label_lines: dict[str, list] = collections.defaultdict(list)  # value -> [(class, line)]
    for entity in classes:
        for prop, value, line in entity.statements:
            if prop in (RDFS_LABEL, SKOS_ALT_LABEL):
                label_lines[value].append((entity.iri, line))
    for value, carriers in label_lines.items():
        owners = list(dict.fromkeys(iri for iri, _ in carriers))
        if len(owners) > 1:
            for _, line in carriers:
                report.error(
                    "concept-label-ambiguous", path, line,
                    f"{value!r} is a label of {', '.join(owners)}, so an entry with that label "
                    f"cannot tell which one it means. Remove it from all but one of them in "
                    f"{path}, or merge the classes.",
                )
    return {value: carriers[0][0] for value, carriers in label_lines.items()}


def check_repeated_ids(path: str, classes: list[Entity], report: Report) -> None:
    """No `oboInOwl:id` is on two of `classes`; reported on each class's id line."""
    id_lines: dict[str, list] = collections.defaultdict(list)
    for entity in classes:
        for value, line in entity.values(OBOINOWL_ID):
            id_lines[value].append((entity.iri, line))
    for value, carriers in id_lines.items():
        owners = list(dict.fromkeys(iri for iri, _ in carriers))
        if len(owners) > 1:
            for _, line in carriers:
                report.error(
                    "concept-id-repeated", path, line,
                    f"oboInOwl:id {value!r} is on {', '.join(owners)}. Give each class its own "
                    f"id in {path}.",
                )


def entity_label(entity: Entity) -> tuple:
    """(label, line) of an individual: its last rdfs:label, or none on its own line."""
    names = entity.values(RDFS_LABEL)
    return names[-1] if names else (None, entity.line)


def check_symptom_concepts(disease_text: str, labels: dict[str, str], report: Report) -> None:
    """Every Symptom individual links the shared concept its label names.

    A Symptom is one symptom, so repeated links are an error on each link line;
    otherwise `check_label_link` holds its link to the lookup in ari_symptoms.owl.
    """
    for entity in read_entities(disease_text):
        if SYMPTOM_CLASS not in entity.types:
            continue
        links = entity.values(SHARED_CONCEPT)
        if len(links) > 1:
            label, _ = entity_label(entity)
            for _, link_line in links:
                report.error(
                    "symptom-concept-repeated", ONTOLOGY_PATH, link_line,
                    f"Symptom {label!r} has {len(links)} sharedConcept values; it is one "
                    "symptom. Keep the one its label names.",
                )
            continue
        check_label_link(entity, "Symptom", "symptom", SYMPTOMS_PATH, labels, report)


def check_label_link(
    entity: Entity, noun: str, code: str, module: str, labels: dict[str, str], report: Report
) -> None:
    """An individual with at most one sharedConcept links the class its label names.

    The label is the key: a class in `module` carries the label or an
    `skos:altLabel`, and sharedConcept is that lookup applied to each
    per-disease individual. `ARI_NoConcept` is the curator's decision that a
    string links nothing. A label with no class yet, or one that names a class
    and is not linked yet, is a warning: the curator added an entry and the
    concept module catches up. A link that disagrees with the label is an error.
    `noun` names the individual in a finding, and `code` prefixes the finding
    codes and is what ARI_NoConcept says it is not.

    Where a finding sits decides whether the `--since` gate sees it, so it sits
    on every statement that could have caused it: a mismatch on the label line
    (a rename leaves the link stale) and on the link line (a repoint); a
    decision that clashes with a link on the ARI_NoConcept line and the link
    line. A label with no class or no link sits on the label line alone, as the
    label is what has no match.
    """
    label, line = entity_label(entity)
    links = entity.values(SHARED_CONCEPT)
    decided = entity.values(NO_CONCEPT)
    if decided and links:
        for clash_line in [decided[0][1], links[0][1]]:
            report.error(
                f"{code}-decided-and-linked", ONTOLOGY_PATH, clash_line,
                f"{noun} {label!r} has both ARI_NoConcept ({decided[0][0]!r}) and "
                f"sharedConcept {links[0][0]}. Remove whichever is wrong: the link if it is "
                f"not a {code}, ARI_NoConcept if it is.",
            )
        return
    if decided:
        return
    have = links[0][0] if links else None
    want = labels.get(label)
    if have is not None and have == want:
        return
    fix = (f"Add the label or an skos:altLabel to the right class in {module}, "
           f"or set ARI_NoConcept on the {code}.")
    if want is None:
        report.warning(
            f"{code}-unmapped", ONTOLOGY_PATH, line,
            f"{noun} {label!r} is not a label of any class in {module}"
            + (f", so its sharedConcept {have} is left from a former label" if have else "")
            + f". {fix}",
        )
    elif have is None:
        report.warning(
            f"{code}-concept-missing", ONTOLOGY_PATH, line,
            f"{noun} {label!r} names {want} in {module} but has no sharedConcept. "
            "Link it to that class.",
        )
    else:
        for mismatch_line in [line, links[0][1]]:
            report.error(
                f"{code}-concept-mismatch", ONTOLOGY_PATH, mismatch_line,
                f"{noun} {label!r} links {have}, but {module} gives that label to "
                f"{want}. Link {want}, or fix the label: {fix[0].lower() + fix[1:]}",
            )


def check_shared_concept_targets(disease_text: str, concept_iris: set[str], report: Report) -> None:
    """Every sharedConcept points at a class a concept module declares.

    A link to a class that is not there reads as a link to nothing: the app and
    the reports resolve it and find no label.
    """
    for entity in read_entities(disease_text):
        for target, line in entity.values(SHARED_CONCEPT):
            if target not in concept_iris:
                report.error(
                    "shared-concept-target-missing", ONTOLOGY_PATH, line,
                    f"{entity.iri} links {target}, which is not a class in {SYMPTOMS_PATH}, "
                    f"{ANATOMY_PATH} or {BIOMARKERS_PATH}. Link an existing class, or add this one.",
                )


def check_property_declarations(texts: dict[str, str], report: Report) -> None:
    """Only ari_core.owl declares a property.

    A property declared in a second module is a second definition of it. It
    also appears when a tool formats a module without resolving its imports and
    guesses the property types it cannot see.
    """
    for path in ARI_OWNED:
        if path == CORE_PATH:
            continue
        for entity in read_entities(texts[path]):
            if entity.types & PROPERTY_TYPES:
                report.error(
                    "property-outside-core", path, entity.line,
                    f"{entity.iri} is declared as a property in {path}. Properties are declared "
                    f"only in {CORE_PATH}; move the declaration there.",
                )


def check_module_subjects(texts: dict[str, str], report: Report) -> None:
    """One module describes each subject.

    Two modules both saying things about an IRI means an edit landed in the
    wrong file, and the module that owns the entity no longer tells the whole
    story. Reported in each file after the first, in ARI_OWNED order.
    """
    first: dict[str, str] = {}
    for path in ARI_OWNED:
        for entity in read_entities(texts[path]):
            owner = first.setdefault(entity.iri, path)
            if owner != path:
                report.error(
                    "subject-in-two-modules", path, entity.line,
                    f"{entity.iri} is described in both {owner} and {path}. Keep its statements "
                    "in the one module that owns it.",
                )


def check_tissue_links(texts: dict[str, str], report: Report) -> None:
    """Every anatomy class links an UBERON term or records why it does not."""
    for entity in read_entities(texts[ANATOMY_PATH]):
        if OWL_CLASS not in entity.types:
            continue
        linked = any(value.startswith(UBERON) for value, _ in entity.values(RDFS_SUBCLASS_OF))
        if not linked and not entity.values(NO_CONCEPT):
            report.warning(
                "tissue-unlinked", ANATOMY_PATH, entity.line,
                f"Tissue class {entity.iri} has no rdfs:subClassOf an UBERON term and no "
                f"ARI_NoConcept. Add the UBERON parent in {ANATOMY_PATH}, or set ARI_NoConcept to "
                "`no term` or `not linked`.",
            )


def check_no_concept_values(texts: dict[str, str], report: Report) -> None:
    """ARI_NoConcept holds one of its decisions, spelled exactly.

    The app, the reports and the checks above compare the value as a string, so
    a variant spelling reads as a decision nobody can act on.
    """
    for path in ARI_OWNED:
        for entity in read_entities(texts[path]):
            for value, line in entity.values(NO_CONCEPT):
                if value not in NO_CONCEPT_VALUES:
                    report.error(
                        "no-concept-value", path, line,
                        f"{entity.iri} has ARI_NoConcept {value!r}. It must be exactly one of "
                        + ", ".join(repr(v) for v in NO_CONCEPT_VALUES) + ".",
                    )


def declared_classes(text: str) -> set[str]:
    """IRI of every owl:Class a module declares."""
    return {entity.iri for entity in read_entities(text) if OWL_CLASS in entity.types}


def concept_iris(texts: dict[str, str]) -> set[str]:
    """Every class a sharedConcept may point at: those of the concept modules."""
    return set().union(*(declared_classes(texts[path])
                         for path in (SYMPTOMS_PATH, ANATOMY_PATH, BIOMARKERS_PATH)))


def biomarker_classes(text: str) -> dict[str, Entity]:
    """The ARIB classes of ari_biomarkers.owl, by IRI."""
    return {entity.iri: entity for entity in read_entities(text)
            if OWL_CLASS in entity.types and entity.iri.startswith(ARIB)}


def arib_ancestors(iri: str, classes: dict[str, Entity]) -> set[str]:
    """The ARIB classes above `iri` through named rdfs:subClassOf parents."""
    seen: set[str] = set()
    stack = [iri]
    while stack:
        for parent, _ in classes[stack.pop()].values(RDFS_SUBCLASS_OF):
            if parent in classes and parent not in seen:
                seen.add(parent)
                stack.append(parent)
    seen.discard(iri)
    return seen


def reached_kinds(iri: str, classes: dict[str, Entity]) -> set[str]:
    """The kinds of the core classes `iri` is under, directly or through ARIB classes."""
    return {
        BIOMARKER_KINDS[parent]
        for owner in {iri} | arib_ancestors(iri, classes)
        for parent, _ in classes[owner].values(RDFS_SUBCLASS_OF)
        if parent in BIOMARKER_KINDS
    }


def biomarker_kinds(text: str) -> dict[str, str]:
    """ARIB class -> its kind, for every class under exactly one core kind."""
    classes = biomarker_classes(text)
    kinds = {}
    for iri in classes:
        reached = reached_kinds(iri, classes)
        if len(reached) == 1:
            kinds[iri] = reached.pop()
    return kinds


def biomarker_labels(text: str, report: Report) -> dict[str, dict[str, str]]:
    """Kind -> {label or altLabel: ARIB class of that kind}.

    An entry's label is looked up only among the concepts of its own kind, so
    an antibody and its antigen may share a name, and two concepts of one kind
    may not. An `oboInOwl:id` is unique across every ARIB class.
    """
    classes = biomarker_classes(text)
    kinds = biomarker_kinds(text)
    check_repeated_ids(BIOMARKERS_PATH, list(classes.values()), report)
    return {
        kind: label_lookup(
            BIOMARKERS_PATH, [entity for iri, entity in classes.items() if kinds.get(iri) == kind],
            report,
        )
        for kind in BIOMARKER_KINDS.values()
    }


def check_biomarker_hierarchy(text: str, report: Report) -> None:
    """Every ARIB class has one kind and an external term, or says it has none.

    A class reaching no core class, or two, has no kind for an entry to be
    checked against; the error sits on each rdfs:subClassOf line, as a parent is
    what put it there (on the class line when it has none). A class is decided
    when it or an ARIB class above it has an exact, close or broad match, or it
    carries ARI_NoConcept: a child without its own term is covered by its
    parent's. An undecided class is a warning on its class line, as for tissues.
    """
    classes = biomarker_classes(text)
    for iri, entity in classes.items():
        reached = reached_kinds(iri, classes)
        if len(reached) != 1:
            parents = entity.values(RDFS_SUBCLASS_OF)
            for _, line in parents or [(iri, entity.line)]:
                report.error(
                    "biomarker-concept-kind", BIOMARKERS_PATH, line,
                    f"{iri} is under "
                    + (" and ".join(sorted(reached)) if reached else "no biomarker kind")
                    + ". Make it a subclass of exactly one of Autoantibody, Antigen and "
                    "ClinicalBiomarker, or of an ARIB class of that kind.",
                )
        matched = any(
            classes[owner].values(prop)
            for owner in {iri} | arib_ancestors(iri, classes)
            for prop in DECIDING_MATCHES
        )
        if not matched and not entity.values(NO_CONCEPT):
            report.warning(
                "biomarker-concept-unlinked", BIOMARKERS_PATH, entity.line,
                f"Biomarker class {iri} has no skos:exactMatch, closeMatch or broadMatch, none "
                f"on a class above it, and no ARI_NoConcept. Add its external term in "
                f"{BIOMARKERS_PATH}, or set ARI_NoConcept to `no term`.",
            )


def check_biomarker_targets(texts: dict[str, str], kinds: dict[str, str], report: Report) -> None:
    """Every relation and external match on an ARIB class points at something there.

    `targetsAntigen` goes to an antigen concept, `expressedIn` to an anatomy
    class or an UBERON term, `associatedSymptom` to an ARIS class. A match to a
    PR, ChEBI, HGNC or LOINC term needs that term in its generated slice, or
    the slice is stale and the term has no label. Each finding sits on the
    statement that points.
    """
    body_parts = declared_classes(texts[ANATOMY_PATH]) | declared_classes(texts[UBERON_PATH])
    targets = {
        TARGETS_ANTIGEN: ({iri for iri, kind in kinds.items() if kind == "antigens"},
                          f"an antigens class in {BIOMARKERS_PATH}"),
        EXPRESSED_IN: (body_parts, f"a class in {ANATOMY_PATH} or {UBERON_PATH}"),
        ASSOCIATED_SYMPTOM: (declared_classes(texts[SYMPTOMS_PATH]),
                             f"an ARIS class in {SYMPTOMS_PATH}"),
    }
    sliced = {prefix: declared_classes(texts[path]) for prefix, path in BIOMARKER_SLICES.items()}
    for entity in biomarker_classes(texts[BIOMARKERS_PATH]).values():
        for prop, (allowed, wanted) in targets.items():
            for target, line in entity.values(prop):
                if target not in allowed:
                    report.error(
                        "biomarker-relation-target", BIOMARKERS_PATH, line,
                        f"{entity.iri} {prop[len(ARI_DISEASE_BASE):]} {target}, which is not "
                        f"{wanted}. Point it at one, or remove it.",
                    )
        for prop in MATCHES:
            for term, line in entity.values(prop):
                for prefix, declared in sliced.items():
                    if term.startswith(prefix) and term not in declared:
                        report.error(
                            "biomarker-external-missing", BIOMARKERS_PATH, line,
                            f"{entity.iri} matches {term}, which is not in "
                            f"{BIOMARKER_SLICES[prefix]}. Regenerate the slice.",
                        )


def check_biomarker_entries(
    disease_text: str,
    kinds: dict[str, str],
    labels: dict[str, dict[str, str]],
    concepts: set[str],
    report: Report,
) -> None:
    """Every live biomarker entry links concepts of its kind, by its label.

    An entry's kind is its rdf:type: Autoantibody, Antigen or ClinicalBiomarker.
    Each sharedConcept must be an ARIB class of that kind; one pointing at no
    class at all is `shared-concept-target-missing`'s. An entry with several
    links is a bundle naming several markers, so no single lookup holds for
    it; one with at most one link goes through `check_label_link`, looking its
    label up among its own kind's concepts. Obsolete entries are left alone.
    """
    for entity in read_entities(disease_text):
        core = sorted(entity.types & BIOMARKER_KINDS.keys())
        if not core or any(value == "true" for value, _ in entity.values(OBSOLETE)):
            continue
        kind = BIOMARKER_KINDS[core[0]]
        links = entity.values(SHARED_CONCEPT)
        for target, line in links:
            if target in concepts and kinds.get(target) != kind:
                report.error(
                    "biomarker-link-wrong-kind", ONTOLOGY_PATH, line,
                    f"{entity.iri} is in {kind} but links {target}, which is "
                    + (f"in {kinds[target]}" if target in kinds else "not a biomarker concept")
                    + f". Link a {kind} class in {BIOMARKERS_PATH}.",
                )
        if len(links) > 1:
            continue
        check_label_link(
            entity, core[0][len(ARI_DISEASE_BASE):], "biomarker",
            f"{BIOMARKERS_PATH} ({kind})", labels[kind], report,
        )


def check_biomarker_concepts(texts: dict[str, str], report: Report) -> None:
    """The biomarker concepts in ari_biomarkers.owl, and the entries that link them."""
    text = texts[BIOMARKERS_PATH]
    kinds = biomarker_kinds(text)
    labels = biomarker_labels(text, report)
    check_biomarker_hierarchy(text, report)
    check_biomarker_targets(texts, kinds, report)
    check_biomarker_entries(texts[ONTOLOGY_PATH], kinds, labels, concept_iris(texts), report)


def load_modules(report: Report) -> dict[str, str] | None:
    """Text of every ARI-owned module and generated slice, or None when one
    cannot be read as XML."""
    texts: dict[str, str] = {}
    for path in (*ARI_OWNED, *GENERATED):
        text = read_text(path, report)
        if text is None:
            return None
        try:
            read_entities(text)
        except expat.ExpatError as exc:
            report.error("ontology-not-well-formed", path, 0, f"OWL/XML does not parse: {exc}.")
            return None
        texts[path] = text
    return texts


def check_modules(texts: dict[str, str], report: Report) -> None:
    """The checks that read the modules against each other."""
    labels = concept_labels(SYMPTOMS_PATH, texts[SYMPTOMS_PATH], report)
    check_symptom_concepts(texts[ONTOLOGY_PATH], labels, report)
    check_shared_concept_targets(texts[ONTOLOGY_PATH], concept_iris(texts), report)
    check_biomarker_concepts(texts, report)
    check_property_declarations(texts, report)
    check_module_subjects(texts, report)
    check_tissue_links(texts, report)
    check_no_concept_values(texts, report)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--since",
        metavar="REF",
        help="Only report findings on lines changed since this git ref.",
    )
    parser.add_argument("--annotate", action="store_true", help="Emit GitHub Actions annotations.")
    parser.add_argument("--summary", metavar="FILE", help="Append a markdown report to FILE.")
    args = parser.parse_args()

    report = Report()

    sssom_text = read_text(SSSOM_PATH, report)
    sssom_rows = split_rows(sssom_text, SSSOM_PATH, SSSOM_COLUMNS, report) if sssom_text else []
    equiv_text = read_text(EQUIV_PATH, report)
    equiv_rows = split_rows(equiv_text, EQUIV_PATH, EQUIV_COLUMNS, report) if equiv_text else []

    if sssom_text:
        check_curie_map(sssom_text, sssom_rows, report)
    check_sssom_rows(sssom_rows, report)
    check_equiv_rows(equiv_rows, report)
    if sssom_rows and equiv_rows:
        check_cross_file(sssom_rows, equiv_rows, report)

    blocklist_text = read_text(BLOCKLIST_PATH, report)
    blocklist_rows = (split_rows(blocklist_text, BLOCKLIST_PATH, BLOCKLIST_COLUMNS, report)
                      if blocklist_text else [])

    diseases = load_ontology(report)
    check_blocklist(blocklist_rows, diseases, report)
    if diseases is not None:
        check_against_ontology(sssom_rows, diseases, report)
        check_equiv_against_ontology(equiv_rows, diseases, report)
        check_ontology_values(diseases, report)
    modules = load_modules(report)
    if modules is not None:
        check_modules(modules, report)

    findings = sorted(report.findings, key=Finding.sort_key)
    scope = "whole repository"
    if args.since:
        findings = filter_to_changes(findings, args.since)
        # Deletions are reported after the diff filter, not through it: the filter
        # keeps findings that sit on a changed line, and a deleted record has no
        # line left to sit on.
        deletions = Report()
        check_deletions(args.since, sssom_rows, deletions)
        findings = sorted(findings + deletions.findings, key=Finding.sort_key)
        scope = f"changes since `{args.since}`"

    for finding in findings:
        if args.annotate:
            print(annotate(finding))
        else:
            where = f"{finding.path}:{finding.line}" if finding.line else finding.path
            print(f"{finding.level:7} {finding.code:24} {where}  {finding.message}")

    errors = sum(1 for f in findings if f.level == "error")
    warnings = len(findings) - errors
    print(f"\n{errors} error(s), {warnings} warning(s) over {scope}.")

    if args.summary:
        write_summary(args.summary, findings, scope)

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
