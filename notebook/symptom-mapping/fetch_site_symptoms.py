"""Snapshot the symptom list of every disease profile on diseases.autoimmuneregistry.org.

The registry site is where report 4's Symptoms sheet comes from. Each profile page lists its
symptoms as checkboxes numbered sym0, sym1, ... in the site's order, and its headings ("Inflammatory
eba:", "Early stages:") as bold labels with no checkbox. The page lays them out in columns, so the
numbers, not the position in the HTML, give the order.

Writes data/1-master/Site Symptoms - <YYYY-MM-DD>.tsv: one row per profile and entry, in the site's
order, with columns page, disease, position, entry, heading. `entry` is the label's text with HTML
entities decoded and any markup kept (one cross-reference holds links). `heading` is "heading" for
a bold label, else empty. A profile with no symptoms has no rows. The file is tab-separated, UTF-8
with no byte-order mark and LF line ends (the csv module's excel-tab dialect).

Usage: python fetch_site_symptoms.py
"""
import csv, datetime, html, os, re, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SITE = "https://diseases.autoimmuneregistry.org/"
LIST_PAGE = SITE + "Autoimmune-Diseases.aspx"
COLUMNS = ["page", "disease", "position", "entry", "heading"]
PROFILE_LINK = re.compile(r'href="(Disease_Profile/[^"]+)"[^>]*>(.*?)</a>', re.S)
LABEL = re.compile(r'<label for="sym(\d+)"([^>]*)>(.*?)</label>', re.S)


def get(url):
    req = urllib.request.Request(urllib.parse.quote(url, safe=":/?=&"), headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read().decode("utf-8")


def profiles():
    """[(page, disease)] in list order; a page's first link is its disease, later links its synonyms."""
    seen = {}
    for page, name in PROFILE_LINK.findall(get(LIST_PAGE)):
        seen.setdefault(page, html.unescape(re.sub(r"<[^>]+>", "", name)).strip())
    if not seen:
        raise SystemExit(f"No profile links on {LIST_PAGE}: the page layout changed")
    return list(seen.items())


def symptoms(page):
    """[(position, entry, is_heading)] of a profile page, in the site's order."""
    text = get(SITE + page)
    start = text.find('class="jeffrow-profile"')
    if start < 0:
        return []
    cell = text[start:text.index("</td>", start)]
    items = sorted((int(n), html.unescape(label).strip(), bool(style.strip()))
                   for n, style, label in LABEL.findall(cell))
    if [i[0] for i in items] != list(range(len(items))):
        raise SystemExit(f"{page}: symptom numbers {[i[0] for i in items]} are not 0..{len(items) - 1}")
    return items


def main():
    out = os.path.join(ROOT, "data", "1-master", f"Site Symptoms - {datetime.date.today().isoformat()}.tsv")
    rows = []
    for page, disease in profiles():
        for position, entry, is_heading in symptoms(page):
            rows.append([page, disease, str(position), entry, "heading" if is_heading else ""])
        time.sleep(0.5)  # be gentle with the registry's server
    for row in rows:
        if any(c in v for v in row for c in "\t\r\n"):
            raise SystemExit(f"{row[0]}: {row[3]!r} has a tab or a line break")
    with open(out, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, dialect="excel-tab", lineterminator="\n")
        writer.writerow(COLUMNS)
        writer.writerows(rows)
    print(f"{len(rows)} entries over {len({r[0] for r in rows})} profiles -> {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    main()
