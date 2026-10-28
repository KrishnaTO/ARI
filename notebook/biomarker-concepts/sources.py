"""Readers for the locally downloaded source releases the biomarker concepts are matched against.

HPO (hp.obo), Protein Ontology (pro_nonreasoned.obo), ChEBI (chebi_lite.obo), HGNC
(hgnc_complete_set.txt), LOINC (loinc/LoincTable/Loinc.csv) and IEDB (bcell_full_v3.csv). Each reader takes
the path of its file, streams it, skips obsolete / withdrawn / inactive entries and returns a dict
keyed by the source's own id string (a list of assays for IEDB). A missing file raises
FileNotFoundError naming it. Pure functions: nothing is downloaded or written.

The files live in data/2-databases (untracked, see CLAUDE.md); the scripts that use these readers take
that folder as an argument.
"""
import csv
import os
import re
from dataclasses import dataclass

HUMAN = "NCBITaxon:9606"
UNIPROT_ACCESSION = re.compile(r"[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}")
QUOTED = re.compile(r'"((?:[^"\\]|\\.)*)"')


@dataclass
class Term:
    id: str
    label: str
    synonyms: list[str]
    parents: list[str]
    release: str


@dataclass
class Gene:
    hgnc_id: str
    symbol: str
    name: str
    aliases: list[str]
    uniprot: list[str]


@dataclass
class Assay:
    antigen_name: str
    antigen_iri: str
    organism: str
    disease: str


def _require(path):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"{os.path.basename(path)} not found at {path}")


def _unescape(text):
    return re.sub(r"\\(.)", r"\1", text)


def _obo_terms(path):
    """Yield (Term, taxon ids) for every non-obsolete [Term] stanza of an OBO file.

    Parents are the is_a ids plus the genus of an intersection_of definition (the line with no relation).

    Taxon ids come from `in_taxon` / `only_in_taxon`, written as a relationship or an intersection_of.
    """
    _require(path)
    release = ""
    date = ""
    stanza = None  # None before the first stanza; otherwise the raw fields of the current one
    skip = False  # inside a stanza that is not a [Term]

    def finish():
        if stanza is None or stanza["obsolete"] or "id" not in stanza:
            return None
        parents = list(dict.fromkeys(stanza["parents"]))
        term = Term(stanza["id"], stanza.get("name", ""), stanza["synonyms"], parents, release or date)
        return term, stanza["taxa"]

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("["):
                done = finish()
                if done:
                    yield done
                skip = line != "[Term]"
                stanza = None if skip else {"obsolete": False, "synonyms": [], "parents": [], "taxa": []}
                continue
            tag, _, value = line.partition(": ")
            if stanza is None:
                if not skip:  # header
                    if tag == "data-version":
                        release = value
                    elif tag == "date":
                        date = value
                continue
            if tag == "id":
                stanza["id"] = value
            elif tag == "name":
                stanza["name"] = value
            elif tag == "synonym":
                stanza["synonyms"].append(_unescape(QUOTED.match(value).group(1)))
            elif tag == "is_a":
                stanza["parents"].append(value.split()[0])
            elif tag in ("relationship", "intersection_of"):
                parts = value.split()
                if parts[0] in ("in_taxon", "only_in_taxon"):
                    stanza["taxa"].append(parts[1])
                elif tag == "intersection_of" and (len(parts) == 1 or parts[1][0] in "!{"):
                    stanza["parents"].append(parts[0])  # the genus: a term defined by it is its subclass
            elif tag == "is_obsolete":
                stanza["obsolete"] = value == "true"
    done = finish()
    if done:
        yield done


def read_hp(path):
    """HPO id (HP:0000118) -> Term, from hp.obo."""
    return {t.id: t for t, _ in _obo_terms(path)}


def read_chebi(path):
    """ChEBI id (CHEBI:15377) -> Term, from chebi_lite.obo."""
    return {t.id: t for t, _ in _obo_terms(path)}


def read_pr(path):
    """PR id (PR:Q05329) -> Term, from pro_nonreasoned.obo.

    Keeps the human terms (in_taxon NCBITaxon:9606), all their ancestors, and non-human terms
    whose id is a UniProt accession (optionally with an isoform suffix).
    """
    terms = {}
    human = set()
    for term, taxa in _obo_terms(path):
        terms[term.id] = term
        if HUMAN in taxa:
            human.add(term.id)
    keep = set(human)
    keep.update(i for i in terms if UNIPROT_ACCESSION.fullmatch(i.removeprefix("PR:").split("-")[0]))
    pending = list(human)
    while pending:
        for parent in terms[pending.pop()].parents:
            if parent in terms and parent not in keep:
                keep.add(parent)
                pending.append(parent)
    return {i: t for i, t in terms.items() if i in keep}


def _split(value, sep):
    return [v.strip() for v in value.split(sep) if v.strip()]


def read_hgnc(path):
    """HGNC id (HGNC:4093) -> Gene, from hgnc_complete_set.txt. Only Approved entries."""
    _require(path)
    genes = {}
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row["status"] != "Approved":
                continue
            genes[row["hgnc_id"]] = Gene(
                row["hgnc_id"],
                row["symbol"],
                row["name"],
                _split(row["alias_symbol"], "|") + _split(row["prev_symbol"], "|"),
                _split(row["uniprot_ids"], "|"),
            )
    return genes


def read_loinc(path):
    """LOINC code (4548-4) -> Term, from loinc/LoincTable/Loinc.csv. Only ACTIVE entries."""
    _require(path)
    terms = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row["STATUS"] != "ACTIVE":
                continue
            names = [row["SHORTNAME"].strip(), row["COMPONENT"].strip()] + _split(row["RELATEDNAMES2"], ";")
            synonyms = list(dict.fromkeys(n for n in names if n))
            terms[row["LOINC_NUM"]] = Term(row["LOINC_NUM"], row["LONG_COMMON_NAME"], synonyms, [], "")
    return terms


IEDB_COLUMNS = {
    "antigen_name": "Epitope - Source Molecule",
    "antigen_iri": "Epitope - Source Molecule IRI",
    "organism": "Epitope - Source Organism",
    "disease": "1st in vivo Process - Disease",
}


def read_iedb_bcell(path):
    """One Assay per row of bcell_full_v3.csv.

    The export has two header lines, a category then the field name; a column is named
    "<category> - <field>", and a blank category continues the one before it.
    """
    _require(path)
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = csv.reader(f)
        categories, fields = next(rows), next(rows)
        names, category = [], ""
        for c, field in zip(categories, fields):
            category = c or category
            names.append(f"{category} - {field}")
        index = {key: names.index(name) for key, name in IEDB_COLUMNS.items()}
        return [Assay(**{key: row[i] for key, i in index.items()}) for row in rows]
