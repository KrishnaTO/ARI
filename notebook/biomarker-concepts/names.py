"""Reads the biomarker labels curators wrote on the per-disease entries.

Pure string functions (standard library only) that turn a label into the pieces Task 6 groups on:
a normalised key, an antibody's target and isotype, the markers in a bundle, a family's members,
and flags for labels that need a human (stray numbers, sentence-like text).

None of them guesses. Each returns the label's own pieces or says it cannot read it, so a label that
is odd falls out for review instead of merging into the wrong concept.
"""
import re
from typing import NamedTuple

QUALIFIERS = ("IgG4", "IgG", "IgA", "IgM", "IgE", "neutralizing", "blocking", "stimulating")
KINDS = ("antibodies", "antigens", "tests")

ANTIBODY_WORDS = r"(?:anti|antibodies|autoantibodies|antibody)"
VERB_PHRASE = re.compile(
    r"\b(?:is|are|was|were|may|can|occurs?|explains?|interacts?|regulates?|reported|seen in|associated with|not found)\b",
    re.IGNORECASE,
)
PARENTHETICAL = re.compile(r"\([^()]*\)")
BUNDLE_SEPARATOR = re.compile(r"\s*,\s*(?:and\s+)?|\s+and\s+|\s+/\s+|\s+&\s+", re.IGNORECASE)
TRAILING_ANTIBODY_WORD = re.compile(r"\s+(?:auto)?antibod(?:y|ies)$", re.IGNORECASE)
LEADING_ANTI = re.compile(r"^anti[\s-]+", re.IGNORECASE)
FAMILY = re.compile(r"^(?P<name>[^()]+?)\s*\((?P<inner>[^()]+)\)$")
MEMBER_PREFIX = re.compile(r"^(?:e\.g\.,?\s*|such as\s+|including\s+|[^\s:,]{1,10}:\s*)", re.IGNORECASE)
# A number, percentage or "<50%" left at the end of the name by a pasted table cell.
TRAILING_NUMBER = re.compile(r"(?P<gap>\s+)(?P<value>[<>~≈≤≥]\s?\d+(?:\.\d+)?\s?%?|\d+(?:\.\d+)?\s?%|\d+)$")

MAX_BUNDLE_PART_WORDS = 6
MAX_FAMILY_MEMBER_WORDS = 2
MAX_LABEL_WORDS = 8


class Antibody(NamedTuple):
    stem: str
    qualifier: str | None


class Family(NamedTuple):
    name: str
    members: list[str]


def normalise(label: str, kind: str) -> str:
    """The grouping key: lower case, hyphens and apostrophes dropped, other punctuation a space.

    For kind "antibodies" the words anti, antibody, antibodies and autoantibodies are removed first
    (whole words only, so "antinuclear" stays). It does not correct spelling.
    """
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}, got {kind!r}")
    text = label.lower()
    if kind == "antibodies":
        text = re.sub(rf"(?<![^\W_]){ANTIBODY_WORDS}(?![^\W_])", " ", text)
    text = re.sub(r"[-_'‐‑’]", "", text)
    text = re.sub(r"[^\w]+", " ", text)
    return text.strip()


def parse_antibody(label: str) -> Antibody:
    """Split "Anti-CNTN1 IgG4" into the target ("CNTN1") and the qualifier ("IgG4").

    The qualifier is the run of QUALIFIERS words (whole words, any case) that ends the label, kept
    as written. It is only read on labels that start with "anti" and only when a target remains
    ("Anti-IgE autoantibodies" targets IgE). A trailing parenthetical stays in the stem.
    """
    stem = label.strip()
    anti = LEADING_ANTI.match(stem)
    if anti:
        stem = stem[anti.end():]
    while TRAILING_ANTIBODY_WORD.search(stem):
        stem = TRAILING_ANTIBODY_WORD.sub("", stem)
    if not anti:
        return Antibody(stem, None)
    words = stem.split()
    lowered = {q.lower() for q in QUALIFIERS}
    count = 0
    while count < len(words) - 1 and words[-1 - count].lower() in lowered:
        count += 1
    if count == 0:
        return Antibody(stem, None)
    return Antibody(" ".join(words[:-count]), " ".join(words[-count:]))


def _outside_parentheses(label: str) -> str:
    text = label
    while PARENTHETICAL.search(text):
        text = PARENTHETICAL.sub(" ", text)
    return text


def _depth_zero(label: str) -> list[bool]:
    depth, flags = 0, []
    for char in label:
        if char == ")":
            depth -= 1
        flags.append(depth == 0)
        if char == "(":
            depth += 1
    return flags


def _looks_like_marker(part: str) -> bool:
    words = _outside_parentheses(part).split()
    return bool(words) and len(words) <= MAX_BUNDLE_PART_WORDS and not sentence_like(part)


def split_bundle(label: str) -> list[str]:
    """The marker names in "ANA, anti-dsDNA and anti-Sm", or [label] when it is not a bundle.

    Splits on a comma, " and ", " / " and " & " outside parentheses, and only when every part reads
    as a marker name on its own.
    """
    if sentence_like(label):
        return [label]
    depth_zero = _depth_zero(label)
    parts, start = [], 0
    for match in BUNDLE_SEPARATOR.finditer(label):
        if depth_zero[match.start()]:
            parts.append(label[start:match.start()])
            start = match.end()
    if not parts:
        return [label]
    parts.append(label[start:])
    parts = [part.strip() for part in parts]
    if not all(_looks_like_marker(part) for part in parts):
        return [label]
    return parts


def parse_family(label: str) -> Family | None:
    """Split "Sperm surface antigens (SP-10, YLP-12, Izumo1)" into the family and its members.

    Needs a plural name (last word ends in "s") and at least two comma-separated members of at most
    two words each in a parenthetical that ends the label. A singular name with a bracket is an alias
    list for one marker ("BP180 (LAD-1, 120 kDa)"), and a longer member is a description ("IAA,
    high-titer polyclonal IgG"); neither is a family. A leading "e.g.", "such as" or "ABBR:" on a
    member is dropped.
    """
    match = FAMILY.match(label.strip())
    if not match:
        return None
    name = match["name"].strip()
    if not name.lower().endswith("s"):
        return None
    members = [MEMBER_PREFIX.sub("", member.strip(), count=1) for member in match["inner"].split(",")]
    members = [member for member in members if member]
    if len(members) < 2 or any(len(member.split()) > MAX_FAMILY_MEMBER_WORDS for member in members):
        return None
    return Family(name, members)


def noisy(label: str) -> str | None:
    """The label without a stray trailing number, percentage or "<50%", or None if it has none.

    A number after two or more spaces, or with a % or comparison sign, is stray. A single space and
    a bare one or two digit number is stray only in the "anti-villin 40" shape: an anti- label of
    two words. Names that end in a number ("Neurofascin-155", "Contactin 1") are left alone.
    """
    match = TRAILING_NUMBER.search(label)
    if not match:
        return None
    value = match["value"]
    marked = len(match["gap"]) >= 2 or not value.isdigit()
    bare_pair = (
        value.isdigit()
        and len(value) <= 2
        and len(label.split()) == 2
        and LEADING_ANTI.match(label) is not None
    )
    if not (marked or bare_pair):
        return None
    clean = label[:match.start()].rstrip()
    return clean or None


def sentence_like(label: str) -> bool:
    """True when the label is prose, not a name: over 8 words outside brackets, a verb phrase
    ("is", "are", "may", "seen in", "associated with"...), a heading ending ":", a sentence ending
    ".", a URL, or a name followed by " - description"."""
    text = label.strip()
    if len(_outside_parentheses(text).split()) > MAX_LABEL_WORDS:
        return True
    if VERB_PHRASE.search(text):
        return True
    return text.endswith((":", ".")) or "://" in text or bool(re.search(r"\s[-–—]\s", text))
