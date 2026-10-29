"""Apply a reviewed biomarker table: only the rows a reviewer accepted or corrected reach the OWL.

Usage (from anywhere in the repo):
  python notebook/biomarker-concepts/apply_review.py notebook/biomarker-concepts/review/<kind>.tsv --base <ref>

propose.py wrote the table and an OWL preview with every row applied. This restores
ontologies/ari_biomarkers.owl and ontologies/ari_disease.owl from <ref> (git show, byte for byte),
re-runs model.write_rows on the decided rows, deletes the table and prints what it did. Paths are
relative to the repo root. Every check on the table itself (a blank or unknown decision, an empty
correction, a corrected link, a correction to a new key no written concept row creates, an unknown
`depends` row, a missing original label) runs first, and any failure leaves every file untouched.
model.write_rows can still refuse a value that is not in the files (an IRI that is no ARIB class, an
entry that is not there) after the two files were restored; the table is then kept, so fix it and
run again. Then build the slices and run tools/format-owl.sh on the two files.
"""
import argparse
import os
import subprocess
from collections import Counter
from dataclasses import dataclass, replace

import model
import review_table
from model import ARI, NEW, Row
from propose import DECIDING

HERE = os.path.dirname(os.path.abspath(__file__))
DISEASE = "ontologies/ari_disease.owl"
BIOMARKERS = "ontologies/ari_biomarkers.owl"
DECISIONS = ("accept", "reject", "correct")


@dataclass
class Skipped(Row):
    """A row left out of the OWL for a reason other than its own rejection."""
    reason: str = ""


def depends_of(row):
    return [d.strip() for d in row.depends.split(";") if d.strip()]


def effective_depends(rows):
    """Row id -> the row ids it needs. A corrected `concept` row needs the concept row of its
    corrected parent when that is a new key, and nothing else: its old parent no longer matters."""
    creators = {r.concept: r.row for r in rows if r.action == "concept"}
    return {r.row: ([creators[r.correction]] if r.correction in creators else [])
            if r.action == "concept" and r.decision == "correct" else depends_of(r) for r in rows}


def drops(rows, depends):
    """(dropped row ids, skipped row ids): the rejected rows and, however deep, the rows that
    depend on a dropped row; the skipped ones are the latter."""
    dropped = {r.row for r in rows if r.decision == "reject"}
    skipped_ids, changed = set(), True
    while changed:
        changed = False
        for r in rows:
            if r.row not in dropped and any(d in dropped for d in depends[r.row]):
                dropped.add(r.row)
                skipped_ids.add(r.row)
                changed = True
    return dropped, skipped_ids


def check(rows, labels, dropped):
    """Raise one ValueError naming every problem in the table. `dropped` is drops()'s first set."""
    seen, problems = set(), []
    for row in rows:
        if row.row in seen:
            problems.append(f"row {row.row}: more than one row has this id")
        seen.add(row.row)
    written_keys = {r.concept for r in rows if r.action == "concept" and r.row not in dropped}
    for row in rows:
        if row.decision not in DECISIONS:
            problems.append(f"row {row.row}: decision is {row.decision!r}, not accept, reject or correct")
        elif row.decision == "correct" and not row.correction.strip():
            problems.append(f"row {row.row}: correct, but the correction is empty")
        elif row.decision == "correct" and row.action == "link":
            problems.append(f"row {row.row}: a link cannot be corrected. Reject it, and the altLabel row "
                            "that carries the entry's label if there is one, then fix the entry's concept "
                            "in Protégé after the merge")
        elif row.decision == "correct" and row.correction.startswith(NEW) and row.correction not in written_keys:
            problems.append(f"row {row.row}: corrected to {row.correction}, which no written concept row creates")
        for dep in depends_of(row):
            if dep not in seen:
                problems.append(f"row {row.row}: depends on row {dep}, which is not in the table")
        if row.action == "label_fix" and row.decision == "reject" and model.entry_local(row) not in labels:
            problems.append(f"row {row.row}: label_fix rejected, but entry {model.entry_local(row)} "
                            "has no original label in the base disease file")
    if problems:
        raise ValueError("the table cannot be applied:\n  " + "\n  ".join(problems))


def decide(rows, labels=None):
    """(rows to write, rows skipped), in table order.

    `labels` maps an entry's ari-disease local name to its label in the base disease file. `correct`
    swaps the correction in as the value; a corrected `concept` row depends only on its corrected
    parent's concept row (effective_depends). `reject` drops a row; a row that depends on a dropped
    row, however deep, is skipped. A label_fix leaves its entry with a label no concept holds unless
    one is added: a rejected one adds an altLabel row holding the entry's original label, a corrected
    one an altLabel row holding the corrected label, on the concept its link row names, unless that
    link row was dropped. Each altLabel not added is listed as skipped.
    Raises ValueError (check) listing every blank or unknown decision, empty correction, corrected
    link, correction to a new key no written concept row creates, unknown `depends` row and missing
    original label.
    """
    labels = labels or {}
    depends = effective_depends(rows)
    dropped, skipped_ids = drops(rows, depends)
    check(rows, labels, dropped)

    def reason(r):
        dep = next(d for d in depends[r.row] if d in dropped)
        return f"depends on row {dep}, which was {'skipped' if dep in skipped_ids else 'rejected'}"

    written, skipped = [], []
    for r in rows:
        if r.row in skipped_ids:
            skipped.append(Skipped(**vars(r), reason=reason(r)))
        elif r.decision == "reject":
            if r.action == "label_fix":
                alt, why = label_row(r, labels[model.entry_local(r)], rows, dropped, skipped_ids, written)
                if alt:
                    written.append(alt)
                else:
                    skipped.append(Skipped(**vars(r), reason=f"label_fix rejected; no altLabel, {why}"))
        else:
            fixed = replace(r, value=r.correction) if r.decision == "correct" else r
            written.append(fixed)
            if r.action == "label_fix" and r.decision == "correct":
                alt, why = label_row(fixed, fixed.value, rows, dropped, skipped_ids, written)
                if alt:
                    written.append(alt)
                else:
                    lost = replace(fixed, row=f"{r.row}-alt", action="altLabel")  # the label_fix is written
                    skipped.append(Skipped(**vars(lost), reason=f"label_fix {r.row} corrected; no altLabel, {why}"))
    return written, skipped


def label_row(fix, label, rows, dropped, skipped_ids, written):
    """(altLabel row holding `label`, "") on the concept the label_fix's entry links, or (None, why
    there is none)."""
    entry = model.entry_local(fix)
    links = [r for r in rows if r.action == "link" and model.entry_local(r) == entry]
    if not links:
        return None, "the entry has no link row"
    if len(links) > 1:
        return None, f"the entry has {len(links)} link rows"
    link = links[0]
    if link.row in dropped:
        return None, f"its link row {link.row} was {'skipped' if link.row in skipped_ids else 'rejected'}"
    if any(w.action == "altLabel" and w.concept == link.value and w.value == label for w in written):
        return None, f"the concept already has {label!r} as an altLabel"
    return replace(fix, row=f"{fix.row}-alt", action="altLabel", concept=link.value, value=label,
                   value_label=label, evidence="the entry's label, kept for lookup",
                   depends="", decision="accept", correction=""), ""


def undecided(rows, concepts):
    """Keys of the new concepts that, among `rows`, neither they nor a concept above them has an
    exact, close or broad match, and that have no no_term (the validator warns on each).
    `concepts` maps IRI -> model.Concept for the existing ARIB classes."""
    parents = {r.concept: r.value for r in rows if r.action == "concept"}
    matched = {r.concept for r in rows if r.action in DECIDING}
    no_term = {r.concept for r in rows if r.action == "no_term"}
    found = []
    for key in parents:
        if key in no_term:
            continue
        above, visited, deciding = key, set(), False
        while above not in visited:  # a corrected cycle of new keys ends here
            visited.add(above)
            if above in matched:
                deciding = True
            elif above.startswith(NEW) and above in parents:
                above = parents[above]
                continue
            elif above in concepts:
                deciding = any(concepts[i].matches.get(a) for i in [above, *model.ancestors(above, concepts)]
                               for a in DECIDING)
            break
        if not deciding:
            found.append(key)
    return found


def git_show(root, base, path):
    return subprocess.run(["git", "-C", root, "show", f"{base}:{path}"], check=True, capture_output=True).stdout


def summary(rows, written, skipped, left):
    decisions = Counter((r.action, r.decision) for r in rows)
    lines = [f"{len(rows)} rows: " + ", ".join(f"{d} {sum(n for (_, k), n in decisions.items() if k == d)}"
                                               for d in DECISIONS)]
    lines.append(f"{'action':<18}{'accept':>7}{'reject':>7}{'correct':>8}")
    for action in sorted({r.action for r in rows}):
        lines.append(f"{action:<18}" + "".join(f"{decisions[(action, d)]:>{w}}" for d, w in zip(DECISIONS, (7, 7, 8))))
    lines.append(f"{len(written)} rows written, {len(skipped)} skipped")
    for r in skipped:
        lines.append(f"  skipped {r.row} {r.action} {r.concept} {r.value}: {r.reason}")
    lines.append(f"{len(left)} concepts left undecided (validator will warn):")
    lines.extend(f"  {key}" for key in left)
    return "\n".join(lines)


def apply(root, table, base):
    """Apply the table at `table` (relative to `root`) onto the files as they are in `base`; returns
    the summary. Every check on the table runs before a file is touched (see the module docstring)."""
    table = os.path.join(root, table)
    rows = review_table.read(table)
    biomarkers, disease = git_show(root, base, BIOMARKERS), git_show(root, base, DISEASE)
    labels = {e.iri.removeprefix(ARI): e.label for e in model.read_entries(disease.decode("utf-8"))}
    written, skipped = decide(rows, labels)
    concepts = {c.iri: c for c in model.read_concepts(biomarkers.decode("utf-8"))}
    left = undecided(written, concepts)

    paths = {}
    for path, content in ((BIOMARKERS, biomarkers), (DISEASE, disease)):
        paths[path] = os.path.join(root, path)
        with open(paths[path], "wb") as f:
            f.write(content)
    model.write_rows(written, paths[BIOMARKERS], paths[DISEASE])
    os.remove(table)
    return summary(rows, written, skipped, left)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("table", help="review/<kind>.tsv, relative to the repo root")
    parser.add_argument("--base", required=True, help="the git ref to restore the two module files from")
    args = parser.parse_args()
    root = subprocess.run(["git", "-C", HERE, "rev-parse", "--show-toplevel"], check=True,
                          capture_output=True, text=True).stdout.strip()
    print(apply(root, args.table, args.base))
    print(f"Now build the slices and run: MSYS_NO_PATHCONV=1 wsl -e tools/format-owl.sh {BIOMARKERS} {DISEASE}")


if __name__ == "__main__":
    main()
