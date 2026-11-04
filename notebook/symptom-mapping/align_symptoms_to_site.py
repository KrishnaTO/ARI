"""Make report 4's Symptoms sheet list exactly what the registry site lists, in the site's order.

The sheet was copied from the master list's Symptoms sheet, which holds rows the site never showed:
7 search terms marked "find" in the latin column and 39 rows the master list appended later. It
also orders some diseases' symptoms differently from the site, which puts symptoms under the wrong
heading ("Blisters" under "Non-inflammatory EBA:"). The site is the source, so for each disease:

  - its rows follow the site's order, from a snapshot written by fetch_site_symptoms.py;
  - a row the site does not list for that disease is dropped;
  - an entry the site lists that the sheet lacks is added, with the site's text;
  - a kept row keeps its own text and cells (the ontology links symptoms by that text);
  - its body-system rows (latin "cat") follow its symptoms, as they are not on the site.

A disease's rows are those with its ARI ID, or its name where the sheet has no ARI ID. It matches
the site profile whose name equals one of its names, ignoring case; SITE_PAGE names the rest. seq
is renumbered 1..n, the running row number it was in the master list. The Index sheet's Symptoms
column is recounted. Rerun build_symptom_report.py afterwards: it refills the mapping columns and
the Symptom Mapping sheet, and stops on an added entry the ontology does not know.

Usage: python align_symptoms_to_site.py <path to the Site Symptoms snapshot>
"""
import collections, copy, csv, os, sys

import openpyxl
from openpyxl.styles import PatternFill

from build_symptom_report import REPORT, ROOT

# Report 4 disease name -> the site profile holding its symptoms, or None when the site lists none.
SITE_PAGE = {
    "Immune thrombocytopenia": "Autoimmune thrombocytopenic purpura",
    # The site has one profile for both.
    "Male infertility associated with antisperm antibodies": "Infertility associated with antisperm antibodies",
    "Female infertility associated with antisperm antibodies": "Infertility associated with antisperm antibodies",
    # Only master-list additions: its one row was appended after the site was built.
    "Female infertility due to antisperm antibody": None,
    # The site lists it as a synonym of Temporal arteritis, a separate ARI disease, and has no list for it.
    "Takayasu's arteritis": None,
    # Its profile lists no symptoms.
    "Autoimmune encephalitis caused by N-methyl D-aspartate receptor antibody": None,
}
BASE_COLUMNS = ["ARI ID", "seq", "disease", "symptom", "latin", "col4", "col5"]


def norm(text):
    return " ".join(str(text).split()).casefold()


def read_site(path):
    """site disease (casefolded) -> [entry] in the site's order."""
    with open(path, encoding="utf-8", newline="") as f:
        lines = list(csv.reader(f, dialect="excel-tab"))
    if lines[0] != ["page", "disease", "position", "entry", "heading"]:
        raise SystemExit(f"{path}: unexpected header {lines[0]}")
    site = collections.defaultdict(list)
    for page, disease, position, entry, heading in lines[1:]:
        if int(position) != len(site[disease.casefold()]):
            raise SystemExit(f"{page}: entry {position} is out of order")
        site[disease.casefold()].append(entry)
    return site


def site_entries(names, site):
    """The site's entries for a disease known by names, or [] when the site lists none."""
    pages = {SITE_PAGE[n] and SITE_PAGE[n].casefold() for n in names if n in SITE_PAGE}
    if not pages:
        pages = {n.casefold() for n in names if n.casefold() in site}
    if len(pages) != 1:
        raise SystemExit(f"{sorted(names)} match {len(pages)} site profiles {sorted(pages, key=str)}: "
                         f"name the one in SITE_PAGE")
    page = pages.pop()
    return site[page] if page else []


def aligned(rows, site):
    """The sheet's data rows (lists of cell values) rearranged per disease to the site's lists."""
    groups = collections.OrderedDict()
    for row in rows:
        groups.setdefault(row[0] or row[2], []).append(row)
    out, dropped, added = [], [], []
    for group in groups.values():
        symptoms = [r for r in group if r[4] != "cat"]
        waiting = collections.defaultdict(collections.deque)
        for r in symptoms:
            waiting[norm(r[3])].append(r)
        names = {r[2] for r in group}
        disease = (symptoms or group)[0][2]
        for entry in site_entries(names, site):
            if waiting[norm(entry)]:
                out.append(waiting[norm(entry)].popleft())
            else:
                out.append([group[0][0], None, disease, entry] + [None] * (len(group[0]) - 4))
                added.append((disease, entry))
        dropped += [(r[2], r[3]) for queue in waiting.values() for r in queue]
        out += [r for r in group if r[4] == "cat"]
    for seq, row in enumerate(out, 1):
        row[1] = seq
    return out, dropped, added


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    site = read_site(sys.argv[1])
    wb = openpyxl.load_workbook(REPORT)
    ws = wb["Symptoms"]
    if [c.value for c in ws[1]][:len(BASE_COLUMNS)] != BASE_COLUMNS:
        raise SystemExit(f"Symptoms sheet layout changed: the first columns are no longer {BASE_COLUMNS}")
    width = ws.max_column
    rows = [[c.value for c in r] for r in ws.iter_rows(min_row=2, max_col=width)]
    out, dropped, added = aligned(rows, site)

    link_free = copy.copy(ws.cell(row=2, column=len(BASE_COLUMNS) + 1).font)
    link_free.color, link_free.underline = None, None
    for n, values in enumerate(out, 2):
        for i, v in enumerate(values, 1):
            cell = ws.cell(row=n, column=i)
            cell.value = v  # ws.cell(value=None) would leave the old value in place
            if i > len(BASE_COLUMNS):  # build_symptom_report.py relinks the mapping columns
                cell.hyperlink, cell.font = None, link_free
    ws.delete_rows(len(out) + 2, ws.max_row - len(out) - 1)

    counts = collections.Counter(r[0] for r in out)
    index = wb["Index"]
    col = [c.value for c in index[1]].index("Symptoms") + 1
    filled = next(copy.copy(c.fill) for (c,) in index.iter_rows(min_row=2, min_col=col, max_col=col) if c.value)
    for r in range(2, index.max_row + 1):
        cell = index.cell(row=r, column=col)
        n = counts[index.cell(row=r, column=1).value]
        cell.value, cell.fill = (n, filled) if n else (None, PatternFill())
    wb.save(REPORT)
    print(f"{len(out)} rows: dropped {len(dropped)}, added {len(added)} -> {os.path.relpath(REPORT, ROOT)}")
    for disease, entry in dropped:
        print(f"  - {disease}: {entry}")
    for disease, entry in added:
        print(f"  + {disease}: {entry}")


if __name__ == "__main__":
    main()
