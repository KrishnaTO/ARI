"""The review table: notebook/biomarker-concepts/review/<kind>.tsv, one model.Row per line.

Tab-separated with a header of model.COLUMNS, written and read with the csv module's excel-tab
dialect, so a reviewer can open it in a spreadsheet, fill `decision` and save it as tab-delimited
text (UTF-8): reading accepts the byte-order mark and the quoting a spreadsheet adds. It is written
in UTF-8 with no byte-order mark and LF line ends, as the rest of the repository. A tab or a line
break in a value would not show in the table, so writing one raises ValueError.
"""
import csv

from model import COLUMNS, Row


def write(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, dialect="excel-tab", lineterminator="\n")
        writer.writerow(COLUMNS)
        for row in rows:
            values = [getattr(row, column) for column in COLUMNS]
            for column, value in zip(COLUMNS, values):
                if any(c in value for c in "\t\r\n"):
                    raise ValueError(f"row {row.row}: {column} has a tab or a line break: {value!r}")
            writer.writerow(values)


def read(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        lines = list(csv.reader(f, dialect="excel-tab"))
    if not lines or lines[0] != COLUMNS:
        raise ValueError(f"{path}: the header is not {COLUMNS}")
    rows = []
    for number, values in enumerate(lines[1:], start=2):
        if len(values) != len(COLUMNS):
            raise ValueError(f"{path}:{number}: {len(values)} columns, expected {len(COLUMNS)}")
        rows.append(Row(*values))
    return rows
