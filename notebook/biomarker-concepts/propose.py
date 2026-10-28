"""Propose ARIB biomarker concepts for one kind, as a review table and as the OWL it would give.

Reads the live antibody, antigen or clinical biomarker entries of ontologies/ari_disease.owl that have
neither sharedConcept nor ARI_NoConcept, the current ontologies/ari_biomarkers.owl and the local source
releases, and proposes, one review row each (plan Decision 2):

  1. per entry: `not_a_biomarker` for a sentence, `label_fix` for a stray trailing value, one `link`
     per marker of a bundle, and a confident `link` when an existing concept of the kind has the label;
  2. groups of the other labels by names.normalise, merging keys at most two edits apart that share a
     first token and their numbers (a judgement): one `concept`, an `altLabel` per other label and a
     `link` per entry;
  3. nesting: a qualified antibody ("Anti-MOG IgG") under its unqualified concept, created when no
     entry names it; a family's members under the family;
  4. each new concept's external term (HPO; PR and HGNC, or ChEBI; LOINC), or `no_term`;
  5. antigens only: a `target` for every antibody concept on main with no targetsAntigen on itself or
     an ancestor, to the antigen its name names, creating that antigen concept when there is none.

Judgement rows come first, then confident ones. Existing ARIB classes are never changed; the one thing
added to one is a `target` (step 5). Every row is applied with model.write_rows, so the PR shows the
result; apply_review.py later re-applies only the rows reviewers accepted.

Usage: python propose.py --kind {antibodies,antigens,tests} <data/2-databases> [--out DIR]
Writes notebook/biomarker-concepts/review/<kind>.tsv and applies the rows to the two OWL files in
place; with --out, writes the TSV and copies of the two files into DIR instead. Then run
tools/format-owl.sh on the OWL files.
"""
import argparse
import os
import re
import shutil
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import NamedTuple

import model
import names
import review_table
import sources
from build_biomarker_slices import RELEASES, to_iri
from model import ARI, KIND_CLASSES, NEW, Row

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DISEASE_PATH = os.path.join(ROOT, "ontologies", "ari_disease.owl")
BIOMARKERS_PATH = os.path.join(ROOT, "ontologies", "ari_biomarkers.owl")
OBO = "http://purl.obolibrary.org/obo/"

FILES = {
    "hp": ("hp.obo", sources.read_hp),
    **RELEASES,
    "iedb": (os.path.join("iedb", "bcell_full_v3.csv"), sources.read_iedb_bcell),
}
NEEDS = {"antibodies": ("hp",), "antigens": ("hgnc", "pr", "chebi", "iedb"), "tests": ("loinc",)}

DECIDING = ("exactMatch", "closeMatch", "broadMatch")
ACTION_ORDER = {a: i for i, a in enumerate((
    "concept", "altLabel", "exactMatch", "closeMatch", "broadMatch", "relatedMatch", "no_term",
    "target", "link", "label_fix", "not_a_biomarker"))}
MAX_EDITS = 2
ROMAN = re.compile(r"(?=[ivx]+$)x{0,3}(ix|iv|v?i{0,3})")
# Words around the antibody name in an HPO term: "Increased anti-X IgE antibody level",
# "Anti-X antibody positivity", "X antibody titer high in blood".
HPO_LEADING = {"increased", "elevated", "positive", "presence", "of", "circulating", "serum"}
HPO_TRAILING = {"positivity", "positive", "level", "levels", "titer", "titre", "high", "in", "blood", "serum"}
MIN_CONTAINED = 3  # a key shorter than this is too short to look for inside a longer name
ISOTYPES = {q.lower() for q in names.QUALIFIERS}  # never looked for alone inside an HPO name


@dataclass
class Sources:
    """Each source reader's output; a kind needs only some (NEEDS)."""
    hp: dict = field(default_factory=dict)
    pr: dict = field(default_factory=dict)
    chebi: dict = field(default_factory=dict)
    hgnc: dict = field(default_factory=dict)
    loinc: dict = field(default_factory=dict)
    iedb: list = field(default_factory=list)


class Match(NamedTuple):
    action: str
    iri: str
    label: str
    evidence: str
    judgement: bool


@dataclass
class Mention:
    label: str  # the name grouped on: the entry's label, its clean form, or one marker of a bundle
    entry: model.Entry
    bundle: str | None = None  # the whole label, when this is one marker of a bundle


@dataclass
class Group:
    """A proposed new concept: its preferred label, the labels and entries that name it, and so on."""
    label: str
    key: str
    labels: list[str]
    mentions: list[Mention]
    fuzzy: dict[str, str] = field(default_factory=dict)  # label merged in by a judgement -> why
    parent: str = ""  # core class IRI, an existing ARIB IRI or a concept key
    evidence: str = ""
    judged: list[str] = field(default_factory=list)  # why the concept row is a judgement
    matches: list[Match] = field(default_factory=list)
    no_term: str = ""  # evidence for no_term
    no_term_judged: bool = False

    @property
    def ckey(self):
        return NEW + self.label


class Table:
    """Rows in the making; `needs` holds the rows each depends on until ids are given."""

    def __init__(self):
        self.rows, self.needs = [], {}

    def add(self, judgement, action, concept, value="", value_label="", entries=(), evidence="", needs=()):
        row = Row("", "judgement" if judgement else "confident", action, concept, value, value_label,
                  diseases_text(entries), entries_text(entries), evidence, "", "", "", "")
        self.rows.append(row)
        self.needs[id(row)] = [n for n in needs if n is not None]
        return row

    def finish(self):
        rows = sorted(self.rows, key=lambda r: (r.group != "judgement", r.concept.casefold(), r.concept,
                                                ACTION_ORDER[r.action], r.value, r.entries))
        for number, row in enumerate(rows, start=1):
            row.row = str(number)
        for row in rows:
            row.depends = ",".join(sorted({n.row for n in self.needs[id(row)]}, key=int))
        return rows


def entries_text(entries):
    out = []
    for entry in entries:
        if not entry.iri.startswith(ARI):
            raise ValueError(f"entry {entry.iri} is not in the ari-disease namespace")
        out.append(f"{entry.iri.removeprefix(ARI)} {entry.label}")
    return " | ".join(dict.fromkeys(out))


def diseases_text(entries):
    found = sorted({d for entry in entries for d in entry.diseases})
    return " | ".join(f"{iri.rsplit('/', 1)[-1]} {label}" for iri, label in found)


def compact(text):
    """A name with case and every non-alphanumeric dropped, for matching against a source's names."""
    return re.sub(r"[\W_]+", "", text.casefold())


def name_candidates(labels):
    """The names a marker goes by: each label, it without its brackets, and each bracketed alias
    ("Aquaporin-4 (AQP4)" -> "Aquaporin-4 (AQP4)", "Aquaporin-4", "AQP4"; "(ACPA / anti-CCP)" gives
    both). A bracket with a comma lists parts or members ("Ro/SSA (Ro52, Ro60)"), not aliases."""
    out = []
    for label in labels:
        out += [label, re.sub(r"\([^()]*\)", " ", label)]
        for inner in re.findall(r"\(([^()]*)\)", label):
            if "," not in inner:
                out += re.split(r"\s/\s", inner)
    out = [" ".join(n.split()) for n in out]
    return [n for n in dict.fromkeys(out) if len(compact(n)) >= 2]


# --------------------------------------------------------------------------
# Grouping
# --------------------------------------------------------------------------


def edits(a, b, limit=MAX_EDITS):
    """Levenshtein distance between a and b, or limit + 1 once it is over limit."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        if min(current) > limit:
            return limit + 1
        previous = current
    return previous[-1]


def numbers(key):
    """The digits and roman-numeral tokens of a key: keys differing here name different molecules."""
    return re.findall(r"\d+", key), [t for t in key.split() if ROMAN.fullmatch(t)]


def mergeable(a, b):
    """Keys a spelling slip apart: same first token, same numbers, at most MAX_EDITS edits."""
    return (a.split()[0] == b.split()[0] and numbers(a) == numbers(b)
            and edits(a, b) <= MAX_EDITS)


def group_mentions(mentions, kind):
    """Groups of mentions with the same normalised key, then merged (each a judgement) where two
    labels share a name (name_candidates: "GAD65 (glutamic acid decarboxylase 65)" and "Glutamic acid
    decarboxylase 65 (GAD65)"), or where two keys are a spelling slip apart ("Type VII Colagen")."""
    by_key = defaultdict(list)
    for mention in mentions:
        by_key[names.normalise(mention.label, kind)].append(mention)
    keys = sorted(by_key)
    root = {k: k for k in keys}
    why = {}  # key -> how it was merged

    def find(k):
        while root[k] != k:
            k = root[k]
        return k

    def union(a, b, reason):
        if find(a) != find(b):
            root[find(b)] = find(a)
            why.setdefault(a, reason)
            why.setdefault(b, reason)

    seen = {}  # a name's key -> (key, label) of the first label that reads it
    for key in keys:
        for label in sorted({m.label for m in by_key[key]}):
            for name in name_candidates([label]):
                read = names.normalise(name, kind)
                if not read:
                    continue
                if read not in seen:
                    seen[read] = (key, label)
                elif seen[read][0] != key:
                    union(seen[read][0], key, f"{seen[read][1]!r} and {label!r} both read {read!r}")
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if mergeable(a, b):
                union(a, b, f"spelling: {a!r} and {b!r} are {edits(a, b)} edit(s) apart")
    components = defaultdict(list)
    for k in keys:
        components[find(k)].append(k)

    groups = []
    for members in components.values():
        found = [m for k in members for m in by_key[k]]
        counts = Counter(m.label for m in found)
        label = min(counts, key=lambda l: (-counts[l], len(l), l))
        key = names.normalise(label, kind)
        group = Group(label, key, sorted(counts, key=lambda l: (l != label, l)), found)
        for other in group.labels:
            other_key = names.normalise(other, kind)
            if other_key != key:
                group.fuzzy[other] = why[other_key]
        groups.append(group)
    return sorted(groups, key=lambda g: (g.label.casefold(), g.label))


def label_index(concepts):
    """Exact label or altLabel -> IRI, and normalised key -> IRI, for existing concepts of one kind."""
    exact, keyed = {}, {}
    for concept in concepts:
        for label in [concept.label, *concept.alt_labels]:
            exact.setdefault(label, concept.iri)
            keyed.setdefault(names.normalise(label, concept.kind), concept.iri)
    return exact, keyed


# --------------------------------------------------------------------------
# Entries
# --------------------------------------------------------------------------


def read_entry_labels(entries, kind, existing_exact, table):
    """Step 1: rows for sentences, stray values, empty names and existing labels; mentions for the rest.

    Returns the mentions to group, and the label_fix row of each entry (to name its concept later).
    """
    mentions, fixes = [], {}
    for entry in entries:
        label = entry.label
        if names.sentence_like(label):
            table.add(True, "not_a_biomarker", "", entries=[entry], evidence="the label is a sentence, not a name")
            continue
        clean = names.noisy(label)
        if clean:
            fixes[entry.iri] = table.add(
                True, "label_fix", "", clean, clean, [entry],
                f"the label ends in a stray value: {label[len(clean):].strip()!r}")
        name = clean or label
        parts = [p for p in names.split_bundle(name) if names.normalise(p, kind)]
        if not parts:
            table.add(True, "not_a_biomarker", "", entries=[entry],
                      evidence=f"{name!r} has no name left once antibody words and punctuation are dropped")
            continue
        bundle = name if len(parts) > 1 else None
        for part in parts:
            if part in existing_exact:
                iri = existing_exact[part]
                table.add(bundle is not None, "link", iri, iri, part, [entry],
                          f"{part!r} is a label of {iri}" + (f"; one marker of {bundle!r}" if bundle else ""))
            else:
                mentions.append(Mention(part, entry, bundle))
    return mentions, fixes


# --------------------------------------------------------------------------
# Nesting
# --------------------------------------------------------------------------


def nest(groups, kind, existing_keyed):
    """Step 3: set each group's parent, adding the parents and family members no entry names."""
    core = KIND_CLASSES[kind]
    for group in groups:
        group.parent = core
    by_key = {}  # every name a group goes by -> the group
    for group in groups:
        for name in name_candidates(group.labels):
            by_key.setdefault(names.normalise(name, kind), group)
    by_ckey = {g.ckey: g for g in groups}

    def created(label, key, parent, evidence, judged=None):
        group = Group(label, key, [label], [], parent=parent, evidence=evidence)
        if judged:
            group.judged.append(judged)
        groups.append(group)
        by_key[key] = group
        by_ckey[group.ckey] = group
        return group

    def lineage(group):
        """The group and the new groups above it."""
        found = [group]
        while found[-1].parent in by_ckey:
            found.append(by_ckey[found[-1].parent])
        return found

    if kind == "antibodies":
        for group in list(groups):
            stem, qualifier = names.parse_antibody(group.label)
            stem_key = names.normalise(stem, kind)
            if not qualifier or not stem_key:
                continue
            group.evidence = f"{group.label!r} is {stem!r} with the qualifier {qualifier!r}"
            keys = list(dict.fromkeys([stem_key] + [names.normalise(n, kind) for n in name_candidates([stem])]))
            found = [by_key[k] for k in keys if k in by_key and by_key[k] is not group]
            known = [existing_keyed[k] for k in keys if k in existing_keyed]
            if found:
                group.parent = found[0].ckey
            elif known:
                group.parent = known[0]
            else:
                parent = created(f"Anti-{stem} antibody", stem_key, core,
                                 f"the unqualified concept of {group.label!r}; no entry names it")
                group.parent = parent.ckey

    for group in list(groups):
        families = [f for f in map(names.parse_family, group.labels) if f]
        for member in dict.fromkeys(m for f in families for m in f.members):
            member_key = names.normalise(member, kind)
            why = f"{member!r} is a member of the family {group.label!r}"
            if not member_key or member_key in existing_keyed:
                continue
            if member_key in by_key:
                child = by_key[member_key]
                if child.parent == core and child not in lineage(group):
                    child.parent = group.ckey
                    child.judged.append(why)
            else:
                created(member, member_key, group.ckey, "no entry names it", why)
    groups.sort(key=lambda g: (g.label.casefold(), g.label))


# --------------------------------------------------------------------------
# External terms
# --------------------------------------------------------------------------


def term_label(term):
    return f"{term.label} ({term.id})"


def hpo_index(hp):
    """(term, the name's tokens, the name's core key) for every HPO name that says antibody."""
    index = []
    for term in sorted(hp.values(), key=lambda t: t.id):
        for name in [term.label, *term.synonyms]:
            if "antibod" not in name.casefold():
                continue
            tokens = [t for t in names.normalise(name, "antibodies").split() if t != "autoantibody"]
            core = list(tokens)
            while core and core[0] in HPO_LEADING:
                core.pop(0)
            while core and core[-1] in HPO_TRAILING:
                core.pop()
            index.append((term, name, tokens, " ".join(core)))
    return index


def contains(tokens, key):
    words = key.split()
    return any(tokens[i:i + len(words)] == words for i in range(len(tokens) - len(words) + 1))


def match_antibody(labels, index):
    """exactMatch to the HPO antibody term whose name, less the antibody words, is one of the
    concept's names (compared without spaces or hyphens); else closeMatch (judgement) to the
    shortest HPO antibody name that contains one."""
    keys = sorted({k for k in (names.normalise(n, "antibodies") for n in name_candidates(labels)) if k})
    compact_keys = {compact(k) for k in keys}
    for term, name, _, core in index:
        if compact(core) in compact_keys:
            return [Match("exactMatch", OBO + term.id.replace(":", "_"), term_label(term),
                          f"HPO {name!r} names {core!r}", False)], ""
    searched = [k for k in keys if len(k) >= MIN_CONTAINED and k not in ISOTYPES]
    found = [(len(core), term.id, term, name, key) for term, name, tokens, core in index
             for key in searched if contains(tokens, key)]
    if found:
        _, _, term, name, key = min(found, key=lambda f: (f[0], f[1], f[3], f[4]))
        others = len({f[1] for f in found}) - 1
        return [Match("closeMatch", OBO + term.id.replace(":", "_"), term_label(term),
                      f"HPO {name!r} contains {key!r}"
                      + (f"; {others} other HPO term(s) contain a name of it" if others else ""), True)], ""
    return [], f"no HPO antibody term names {', '.join(map(repr, keys))}"


@dataclass
class AntigenIndex:
    genes: dict  # compact name -> [(how, Gene)], how = "symbol", "name" or "alias"
    chebi: dict  # compact name -> [(how, Term)], how = "label" or "synonym"
    pr: dict


def antigen_index(srcs):
    genes, chebi = defaultdict(list), defaultdict(list)
    for gene in sorted(srcs.hgnc.values(), key=lambda g: int(g.hgnc_id.split(":")[1])):
        genes[compact(gene.symbol)].append(("symbol", gene))
        genes[compact(gene.name)].append(("name", gene))
        for alias in gene.aliases:
            genes[compact(alias)].append(("alias", gene))
    for term in sorted(srcs.chebi.values(), key=lambda t: t.id):
        chebi[compact(term.label)].append(("label", term))
        for synonym in term.synonyms:
            chebi[compact(synonym)].append(("synonym", term))
    return AntigenIndex(genes, chebi, srcs.pr)


def first_hit(candidates, table, strong):
    """The first (name, how, item, all hits) whose `how` is in `strong`, else the first of any kind."""
    hits = [(name, table[compact(name)]) for name in candidates if table.get(compact(name))]
    for name, found in hits:
        best = [(how, item) for how, item in found if how in strong]
        if best:
            return name, best[0][0], best[0][1], found
    if hits:
        name, found = hits[0]
        return name, found[0][0], found[0][1], found
    return None


def match_antigen(labels, index):
    """PR (exactMatch) and HGNC (relatedMatch) for a protein, else ChEBI. Returns (matches, no_term
    evidence, no_term is a judgement)."""
    candidates = name_candidates(labels)
    hit = first_hit(candidates, index.genes, ("symbol", "name"))
    if hit:
        name, how, gene, found = hit
        judged = how == "alias"
        others = sorted({g.hgnc_id for _, g in found} - {gene.hgnc_id})
        why = f"{name!r} is the HGNC {how} of {gene.symbol}" + (f" (also {', '.join(others)})" if others else "")
        hgnc = Match("relatedMatch", to_iri("hgnc", gene.hgnc_id), f"{gene.symbol} ({gene.hgnc_id})", why, judged)
        for accession in gene.uniprot:
            term = index.pr.get("PR:" + accession)
            if term:
                return [Match("exactMatch", to_iri("pr", term.id), term_label(term),
                              f"{why}; UniProt {accession}", judged), hgnc], "", False
        return [hgnc._replace(judgement=True)], (
            f"{why}, but PR has no term for its UniProt {', '.join(gene.uniprot) or 'accession'}"), True
    hit = first_hit(candidates, index.chebi, ("label",))
    if hit:
        name, how, term, found = hit
        others = len({t.id for _, t in found}) - 1
        return [Match("exactMatch", to_iri("chebi", term.id), term_label(term),
                      f"{name!r} is the ChEBI {how} of {term.id}" + (f"; {others} other term(s) too" if others else ""),
                      how != "label")], "", False
    return [], f"no HGNC gene or ChEBI term is named {', '.join(map(repr, candidates))}", False


def loinc_index(loinc):
    index = defaultdict(list)
    for term in sorted(loinc.values(), key=lambda t: t.id):
        index[compact(term.label)].append(("name", term))
        for synonym in term.synonyms:
            index[compact(synonym)].append(("other name", term))
    return index


def match_test(labels, index):
    hit = first_hit(labels, index, ("name",))
    if not hit:
        return [], f"no LOINC name is {', '.join(map(repr, labels))}"
    name, how, term, found = hit
    others = len({t.id for _, t in found}) - 1
    action = "exactMatch" if how == "name" else "closeMatch"
    return [Match(action, to_iri("loinc", term.id), term_label(term),
                  f"{name!r} is a LOINC {how} of {term.id}" + (f"; {others} other code(s) too" if others else ""),
                  how != "name" or others > 0)], ""


def matcher(kind, srcs):
    """The step 4 function for a kind: labels -> (matches, no_term evidence, no_term is a judgement)."""
    if kind == "antibodies":
        index = hpo_index(srcs.hp)
        return lambda labels: (*match_antibody(labels, index), False)
    if kind == "antigens":
        index = antigen_index(srcs)
        return lambda labels: match_antigen(labels, index)
    index = loinc_index(srcs.loinc)
    return lambda labels: (*match_test(labels, index), False)


def set_matches(group, match):
    group.matches, group.no_term, group.no_term_judged = match(group.labels)


def terms_above(group, groups_by_key, concepts):
    """The exact, close and broad terms of the concepts above a group."""
    found, parent = set(), group.parent
    while parent in groups_by_key:
        found |= {m.iri for m in groups_by_key[parent].matches if m.action in DECIDING}
        parent = groups_by_key[parent].parent
    if parent in concepts:
        for iri in [parent, *model.ancestors(parent, concepts)]:
            found |= {t for a in DECIDING for t in concepts[iri].matches.get(a, [])}
    return found


def drop_inherited_terms(groups, concepts):
    """A child matched to its parent's term (a qualified antibody's alias names the parent) inherits
    the term instead of repeating it."""
    groups_by_key = {g.ckey: g for g in groups}
    above = {g.ckey: terms_above(g, groups_by_key, concepts) for g in groups}
    for group in groups:
        group.matches = [m for m in group.matches if m.iri not in above[group.ckey]]


def flag_shared_terms(groups, existing):
    """A new concept whose exact, close or broad term another concept of the kind already has is
    likely the same marker under another name: its concept row becomes a judgement. Confident
    matches claim a term before judged ones."""
    owner = {iri: c.iri for c in existing for a in DECIDING for iri in c.matches.get(a, [])}
    for judged in (False, True):
        for group in groups:
            for m in group.matches:
                if m.action not in DECIDING or m.judgement != judged:
                    continue
                if m.iri in owner:
                    group.judged.append(f"{owner[m.iri]} has the same term {m.iri}; the same marker?")
                else:
                    owner[m.iri] = group.ckey


def decided(group, groups_by_key, concepts):
    """True when the group or a concept above it has an exact, close or broad match."""
    if any(m.action in DECIDING for m in group.matches):
        return True
    if group.parent in groups_by_key:
        return decided(groups_by_key[group.parent], groups_by_key, concepts)
    if group.parent in concepts:
        return any(concepts[i].matches.get(a) for i in [group.parent, *model.ancestors(group.parent, concepts)]
                   for a in DECIDING)
    return False


# --------------------------------------------------------------------------
# Targets (antigens)
# --------------------------------------------------------------------------


def stem_of(label):
    """The antigen an antibody name names, or "" when it does not read "Anti-X" or "X antibodies"."""
    stem = names.parse_antibody(label).stem.strip()
    return "" if stem.casefold().startswith("anti") or "antibod" in stem.casefold() else stem


class Target(NamedTuple):
    antibody: model.Concept
    antigen: str  # concept key
    judgement: bool
    evidence: str


def iedb_antigens(assays):
    """(antigen name, UniProt accession or "", assay count) per IEDB source molecule, most assays first."""
    counts = Counter((a.antigen_name, a.antigen_iri) for a in assays if a.antigen_name)
    return sorted(((n, iri.rstrip("/").rsplit("/", 1)[-1] if iri else "", c) for (n, iri), c in counts.items()),
                  key=lambda x: (-x[2], x[0]))


def propose_targets(concepts, groups, match, srcs):
    """Step 5: a target per antibody concept on main that has none on itself or an ancestor.

    A stem is looked up among the antigen concepts by label, then by normalised name; then resolved
    through HGNC / PR / ChEBI to an antigen concept with that term; then by a bracket-free name or
    alias (a judgement); then the resolved term makes a new antigen concept; then IEDB (a
    judgement). A target is a judgement when the stem or the antigen's term was matched by
    alias, when ChEBI gave it (its names include plain words: "retinal", "thyroid"), and from IEDB;
    an antigen concept created for a judged target is judged too. A name that does not read
    "Anti-X" ("Antinuclear antibodies (ANA)") has no stem. Ancestors go first, and a concept whose
    ancestor got a target is skipped.
    """
    by_iri = {c.iri: c for c in concepts}
    antigens = [c for c in concepts if c.kind == "antigens"]
    exact, keyed = label_index(antigens)
    named = {}  # the key of any name an antigen concept goes by (name_candidates) -> its key
    by_term = {iri: (c.iri, False) for c in antigens for a in DECIDING for iri in c.matches.get(a, [])}
    for concept in antigens:
        for name in name_candidates([concept.label, *concept.alt_labels]):
            named.setdefault(names.normalise(name, "antigens"), concept.iri)
    groups_by_key = {g.ckey: g for g in groups}

    def register(group):
        for label in group.labels:
            exact.setdefault(label, group.ckey)
            keyed.setdefault(names.normalise(label, "antigens"), group.ckey)
        for name in name_candidates(group.labels):
            named.setdefault(names.normalise(name, "antigens"), group.ckey)
        for m in group.matches:
            if m.action in DECIDING and (m.iri not in by_term or (by_term[m.iri][1] and not m.judgement)):
                by_term[m.iri] = (group.ckey, m.judgement)
        groups_by_key[group.ckey] = group

    for group in groups:
        register(group)

    def new_antigen(label, evidence, matches=None):
        group = Group(label, names.normalise(label, "antigens"), [label], [], parent=KIND_CLASSES["antigens"],
                      evidence=evidence)
        if matches is None:
            set_matches(group, match)
        else:
            group.matches, group.no_term, group.no_term_judged = matches
        groups.append(group)
        register(group)
        return group

    def lookup(stems):
        for stem in stems:
            if stem in exact:
                return exact[stem], False, f"{stem!r} is a label of the antigen concept"
        for stem in stems:
            if names.normalise(stem, "antigens") in keyed:
                return keyed[names.normalise(stem, "antigens")], False, f"{stem!r} names the antigen concept"
        resolved = []  # (stem, its match result, its first deciding match, judged)
        for stem in stems:
            result = match([stem])
            deciding = [m for m in result[0] if m.action in DECIDING] or result[0]
            if not deciding:
                continue
            first = deciding[0]
            judged = first.judgement or first.iri.startswith(to_iri("chebi", ""))
            if first.iri in by_term:
                key, term_judged = by_term[first.iri]
                return key, judged or term_judged, f"{first.evidence}, the antigen concept's term"
            resolved.append((stem, result, first, judged))
        for stem in stems:
            for name in name_candidates([stem]):
                if names.normalise(name, "antigens") in named:
                    return (named[names.normalise(name, "antigens")], True,
                            f"{name!r}, read from {stem!r}, is a name of the antigen concept")
        if resolved:
            stem, result, first, judged = resolved[0]
            group = new_antigen(stem, f"the antigen {stem!r} names; no entry lists it", result)
            if judged:
                group.judged.append(f"created only as the target of {stem!r}")
            return group.ckey, judged, first.evidence
        for stem in stems:
            words = names.normalise(stem, "antigens")
            if len(words) < MIN_CONTAINED:
                continue
            found = [a for a in iedb if contains(names.normalise(a[0], "antigens").split(), words)]
            if not found:
                continue
            name, accession, count = found[0]
            why = (f"{count} IEDB assay(s) name {name!r} (UniProt {accession or 'none'}) for {stem!r}"
                   + (f"; {len(found) - 1} other IEDB antigen(s) match" if len(found) > 1 else ""))
            term = srcs.pr.get("PR:" + accession) if accession else None
            if term and to_iri("pr", term.id) in by_term:
                return by_term[to_iri("pr", term.id)][0], True, why
            if name in exact or names.normalise(name, "antigens") in keyed:
                return exact.get(name) or keyed[names.normalise(name, "antigens")], True, why
            matches = ([Match("exactMatch", to_iri("pr", term.id), term_label(term), why, True)], "", False) \
                if term else ([], f"PR has no term for IEDB's {name!r}", True)
            group = new_antigen(name, f"the IEDB antigen for {stem!r}; no entry lists it", matches)
            group.judged.append(why)
            return group.ckey, True, why
        return None

    iedb = iedb_antigens(srcs.iedb)
    depth = {c.iri: len(model.ancestors(c.iri, by_iri)) for c in concepts}
    targeted, targets = set(), []
    for concept in sorted((c for c in concepts if c.kind == "antibodies"), key=lambda c: depth[c.iri]):
        above = model.ancestors(concept.iri, by_iri)
        if concept.targets or any(by_iri[a].targets or a in targeted for a in above):
            continue
        stems = list(dict.fromkeys(s for s in (stem_of(n) for n in [concept.label, *concept.alt_labels]) if s))
        found = lookup(stems)
        if found:
            key, judgement, why = found
            targets.append(Target(concept, key, judgement, why))
            targeted.add(concept.iri)
    return targets, groups_by_key


# --------------------------------------------------------------------------
# Rows
# --------------------------------------------------------------------------


def concept_label(key, groups_by_key, concepts):
    if key in groups_by_key:
        return groups_by_key[key].label
    if key in concepts:
        return concepts[key].label
    return key.rsplit("#", 1)[-1]


def group_rows(groups, groups_by_key, concepts, table, kind):
    """The concept, altLabel, match, no_term and link rows of every new group; returns concept rows."""
    concept_rows = {}
    for group in groups:
        entries = [m.entry for m in group.mentions]
        evidence = "; ".join(filter(None, [
            f"{len(entries)} entr{'y' if len(entries) == 1 else 'ies'} named {names.normalise(group.label, kind)!r}"
            if entries else "", group.evidence, *group.judged]))
        concept_rows[group.ckey] = table.add(
            bool(group.judged), "concept", group.ckey, group.parent,
            concept_label(group.parent, groups_by_key, concepts), entries, evidence)
    for group in groups:
        row = concept_rows[group.ckey]
        if group.parent in concept_rows:
            table.needs[id(row)].append(concept_rows[group.parent])
        entries = [m.entry for m in group.mentions]
        alt_rows = {}
        for label in group.labels[1:]:
            named = [m.entry for m in group.mentions if m.label == label]
            alt_rows[label] = table.add(
                label in group.fuzzy, "altLabel", group.ckey, label, label, named,
                group.fuzzy.get(label, f"{label!r} and {group.label!r} are both {group.key!r}"), [row])
        for m in group.matches:
            table.add(m.judgement, m.action, group.ckey, m.iri, m.label, entries, m.evidence, [row])
        if not decided(group, groups_by_key, concepts):
            table.add(group.no_term_judged, "no_term", group.ckey, "", "no term", entries, group.no_term, [row])
        linked = set()
        for m in group.mentions:
            if m.entry.iri in linked:
                continue
            linked.add(m.entry.iri)
            table.add(m.bundle is not None, "link", group.ckey, group.ckey, group.label, [m.entry],
                      f"{m.label!r} is a label of the concept"
                      + (f"; one marker of {m.bundle!r}" if m.bundle else ""),
                      [row, alt_rows.get(m.label)])
    return concept_rows


def propose(kind, disease_text, biomarkers_text, srcs):
    """The review rows for `kind` ("antibodies", "antigens" or "tests"), numbered, judgement rows first."""
    if kind not in KIND_CLASSES:
        raise ValueError(f"kind must be one of {list(KIND_CLASSES)}, got {kind!r}")
    entries = model.read_entries(disease_text)
    concept_list = model.read_concepts(biomarkers_text)
    concepts = {c.iri: c for c in concept_list}
    existing_exact, existing_keyed = label_index([c for c in concept_list if c.kind == kind])
    table = Table()

    live = [e for e in entries if e.kind == kind and not e.obsolete and not e.shared and e.no_concept is None]
    mentions, fixes = read_entry_labels(live, kind, existing_exact, table)
    groups = group_mentions(mentions, kind)
    nest(groups, kind, existing_keyed)
    for group in groups:
        if group.mentions and all(m.bundle for m in group.mentions):
            group.judged.append(f"named only as one marker of {group.mentions[0].bundle!r}")
        if group.key in existing_keyed:
            group.judged.append(f"{existing_keyed[group.key]} has the same normalised name; "
                                "accept only if they are different markers")
    match = matcher(kind, srcs)
    for group in groups:
        set_matches(group, match)
    drop_inherited_terms(groups, concepts)
    flag_shared_terms(groups, [c for c in concept_list if c.kind == kind])

    targets = []
    groups_by_key = {g.ckey: g for g in groups}
    if kind == "antigens":
        targets, groups_by_key = propose_targets(concept_list, groups, match, srcs)
        groups.sort(key=lambda g: (g.label.casefold(), g.label))
    keys = [g.ckey for g in groups]
    if len(set(keys)) != len(keys):
        raise ValueError(f"two proposed concepts share a label: {[k for k, n in Counter(keys).items() if n > 1]}")

    concept_rows = group_rows(groups, groups_by_key, concepts, table, kind)
    linked_from = defaultdict(list)
    for entry in entries:
        for iri in entry.shared:
            linked_from[iri].append(entry)
    for t in targets:
        table.add(t.judgement, "target", t.antibody.iri, t.antigen,
                  concept_label(t.antigen, groups_by_key, concepts), linked_from[t.antibody.iri],
                  f"{t.antibody.label!r} targets it: {t.evidence}", [concept_rows.get(t.antigen)])

    links = defaultdict(list)
    for row in table.rows:
        if row.action == "link":
            links[model.entry_local(row)].append(row.value)
    for iri, fix in fixes.items():
        found = links.get(iri.removeprefix(ARI), [])
        fix.concept = found[0] if len(found) == 1 else ""
    return table.finish()


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def load_sources(kind, database):
    """The sources `kind` needs, read from the data/2-databases folder; any missing file fails first."""
    paths = {name: os.path.join(database, FILES[name][0]) for name in NEEDS[kind]}
    missing = [path for path in paths.values() if not os.path.isfile(path)]
    if missing:
        raise FileNotFoundError("missing source release(s): " + ", ".join(missing))
    return Sources(**{name: FILES[name][1](path) for name, path in paths.items()})


def summary(rows):
    concepts = sum(r.action == "concept" for r in rows)
    judged = sum(r.group == "judgement" for r in rows)
    actions = Counter((r.action, r.group) for r in rows)
    lines = [f"{len(rows)} rows: {concepts} concepts, {judged} judgement rows, "
             f"{sum(r.action == 'no_term' for r in rows)} no_term"]
    for action in ACTION_ORDER:
        if actions[(action, "judgement")] or actions[(action, "confident")]:
            lines.append(f"  {action}: {actions[(action, 'judgement')]} judgement, "
                         f"{actions[(action, 'confident')]} confident")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--kind", required=True, choices=list(KIND_CLASSES))
    parser.add_argument("database", help="the data/2-databases folder")
    parser.add_argument("--out", help="write the TSV and copies of the two OWL files here instead")
    args = parser.parse_args()

    srcs = load_sources(args.kind, args.database)
    with open(DISEASE_PATH, encoding="utf-8") as f:
        disease_text = f.read()
    with open(BIOMARKERS_PATH, encoding="utf-8") as f:
        biomarkers_text = f.read()
    rows = propose(args.kind, disease_text, biomarkers_text, srcs)

    if args.out:
        os.makedirs(args.out, exist_ok=True)
        table_path = os.path.join(args.out, f"{args.kind}.tsv")
        disease_path = shutil.copy(DISEASE_PATH, args.out)
        biomarkers_path = shutil.copy(BIOMARKERS_PATH, args.out)
    else:
        os.makedirs(os.path.join(HERE, "review"), exist_ok=True)
        table_path = os.path.join(HERE, "review", f"{args.kind}.tsv")
        disease_path, biomarkers_path = DISEASE_PATH, BIOMARKERS_PATH
    review_table.write(table_path, rows)
    keys = model.write_rows(rows, biomarkers_path, disease_path)
    print(summary(rows))
    print(f"{len(keys)} classes written; table {table_path}")
    print(f"Now run: MSYS_NO_PATHCONV=1 wsl -e tools/format-owl.sh {biomarkers_path} {disease_path}")


if __name__ == "__main__":
    main()
