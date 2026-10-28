"""The review table: notebook/biomarker-concepts/review/<kind>.tsv, one model.Row per line.

Tab-separated with a header of model.COLUMNS and no quoting: a value is written as it is. A tab or a
line break in one would split the row, so writing one raises ValueError.
"""
from model import COLUMNS, Row


def write(path, rows):
    lines = ["\t".join(COLUMNS)]
    for row in rows:
        values = [getattr(row, column) for column in COLUMNS]
        for column, value in zip(COLUMNS, values):
            if any(c in value for c in "\t\r\n"):
                raise ValueError(f"row {row.row}: {column} has a tab or a line break: {value!r}")
        lines.append("\t".join(values))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        lines = f.read().splitlines()
    if not lines or lines[0].split("\t") != COLUMNS:
        raise ValueError(f"{path}: the header is not {COLUMNS}")
    rows = []
    for number, line in enumerate(lines[1:], start=2):
        values = line.split("\t")
        if len(values) != len(COLUMNS):
            raise ValueError(f"{path}:{number}: {len(values)} columns, expected {len(COLUMNS)}")
        rows.append(Row(*values))
    return rows
