#!/usr/bin/env python3
"""Validate the ARI cross-reference mapping files.

Checks `mappings/ari.sssom.tsv` and `mappings/ari.equivalencies.tsv` for
structural problems, malformed identifiers and internal contradictions, that
the two files agree with each other, and that both agree with the stored
cross-references in `ontologies/ari_t1d.owl`.

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
import html
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass
from datetime import date

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SSSOM_PATH = "mappings/ari.sssom.tsv"
EQUIV_PATH = "mappings/ari.equivalencies.tsv"
ONTOLOGY_PATH = "ontologies/ari_t1d.owl"

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
]
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

ARI_SUBJECT_RE = re.compile(r"ARI:\d{4,7}")
AUTHOR_RE = re.compile(r"github:[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
ICD9_RE = re.compile(r"\d{2,3}(\.\d{1,2})?")

ENTITY_OPEN_RE = re.compile(r"<owl:(?:NamedIndividual|Class)\b")
ENTITY_CLOSE_RE = re.compile(r"</owl:(?:NamedIndividual|Class)>")
ANNOTATION_RE = re.compile(r"<(ARI_\w+)[^>]*>(.*?)</\1>")
LABEL_RE = re.compile(r"<rdfs:label[^>]*>(.*?)</rdfs:label>")
CURIE_MAP_RE = re.compile(r"#\s{2,}([A-Za-z0-9_.]+):\s")


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


def load_ontology(report: Report) -> dict[str, Disease] | None:
    """Parse ARI disease entities and their cross-reference annotations."""
    text = read_text(ONTOLOGY_PATH, report)
    if text is None:
        return None
    try:
        ElementTree.fromstring(text)
    except ElementTree.ParseError as exc:
        report.error("ontology-not-well-formed", ONTOLOGY_PATH, 0, f"OWL/XML does not parse: {exc}.")
        return None

    diseases: dict[str, Disease] = {}
    current: dict | None = None
    for index, line in enumerate(text.replace("\r\n", "\n").split("\n"), start=1):
        if ENTITY_OPEN_RE.search(line):
            current = {"label": None, "annotations": collections.defaultdict(list)}
        if current is None:
            continue
        label_match = LABEL_RE.search(line)
        if label_match:
            current["label"] = html.unescape(label_match.group(1)).strip()
        for prop, value in ANNOTATION_RE.findall(line):
            current["annotations"][prop].append((html.unescape(value).strip(), index))
        if ENTITY_CLOSE_RE.search(line):
            ids = current["annotations"].get("ARI_ID", [])
            ari_id = ids[0][0] if ids else None
            if ari_id and ari_id.startswith("ARI:"):
                if ari_id in diseases:
                    report.error(
                        "duplicate-ari-id",
                        ONTOLOGY_PATH,
                        ids[0][1],
                        f"{ari_id} is used by more than one entity, so mappings for it are ambiguous.",
                    )
                else:
                    diseases[ari_id] = Disease(ari_id, current["label"], dict(current["annotations"]))
            current = None
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
    today = date.today().isoformat()
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
                "date-format", SSSOM_PATH, line, f"`mapping_date` {mapping_date!r} is not ISO YYYY-MM-DD."
            )
        elif mapping_date > today:
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
        modifiers_by_pair[(subject, object_id)][modifier] = line

    for (subject, object_id), by_modifier in modifiers_by_pair.items():
        if len(by_modifier) > 1:
            lines = ", ".join(str(by_modifier[m]) for m in sorted(by_modifier))
            report.error(
                "contradiction",
                SSSOM_PATH,
                min(by_modifier.values()),
                f"{subject} -> {object_id} is recorded as both confirmed and flagged-wrong "
                f"(lines {lines}). One of the two judgments has to go.",
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
    trailing zero, `0111157` losing its leading zeros, `ARI:0003` re-padded to
    a different width.
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


def baseline_lines(ref: str, path: str) -> set[str] | None:
    """Exact text of every line in `path` at `ref`, or None if it did not exist."""
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return set(result.stdout.decode("utf-8", "replace").replace("\r\n", "\n").split("\n"))


def current_lines(path: str) -> list[str]:
    full = os.path.join(REPO_ROOT, path)
    if not os.path.exists(full):
        return []
    return open(full, encoding="utf-8", errors="replace").read().replace("\r\n", "\n").split("\n")


def filter_to_changes(findings: list[Finding], ref: str) -> list[Finding]:
    """Keep only findings on lines this branch added or rewrote since `ref`.

    Pre-existing problems are real, but a curator submitting one disease should
    not be blocked by debt they did not introduce; the scheduled audit covers
    the standing backlog.
    """
    baselines: dict[str, set[str] | None] = {}
    currents: dict[str, list[str]] = {}
    kept = []
    for finding in findings:
        path = finding.path
        if path not in baselines:
            baselines[path] = baseline_lines(ref, path)
            currents[path] = current_lines(path)
        baseline = baselines[path]
        if baseline is None or finding.line == 0:
            kept.append(finding)
            continue
        lines = currents[path]
        if finding.line - 1 >= len(lines):
            kept.append(finding)
            continue
        if lines[finding.line - 1] not in baseline:
            kept.append(finding)
    return kept


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

    diseases = load_ontology(report)
    if diseases is not None:
        check_against_ontology(sssom_rows, diseases, report)
        check_equiv_against_ontology(equiv_rows, diseases, report)
        check_ontology_values(diseases, report)

    findings = sorted(report.findings, key=Finding.sort_key)
    scope = "whole repository"
    if args.since:
        findings = filter_to_changes(findings, args.since)
        scope = f"lines changed since `{args.since}`"

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
