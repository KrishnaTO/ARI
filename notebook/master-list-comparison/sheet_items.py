"""Reading list cells from the master list, and deciding when two items name the same thing."""
import re, unicodedata

# Cell contents that mean "no information" in the list columns.
PLACEHOLDERS = {'unknown', 'unconfirmed', 'unknown / unconfirmed'}
STOP = {'a', 'an', 'and', 'or', 'the', 'of', 'in', 'on', 'with', 'to', 'for', 'by', 'at', 'as', 'from',
        'due', 'e', 'g', 'eg', 'etc', 'i', 'cell', 'cells'}


def norm(s):
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"['’]s\b", '', s)
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', s).split())


def items(text):
    """The cell's lines, without bullets and placeholders."""
    out = []
    for line in str(text or '').split('\n'):
        line = line.strip().lstrip('•-*·').strip()
        if line and norm(line) not in {norm(p) for p in PLACEHOLDERS}:
            out.append(line)
    return out


def tokens(s):
    s = re.sub(r'\([^)]*%[^)]*\)', '', s)          # drop frequencies such as (80-90%)
    return {t for t in norm(s).split() if t not in STOP}


def same_item(a, b):
    ta, tb = tokens(a), tokens(b)
    return bool(ta and tb) and len(ta & tb) / min(len(ta), len(tb)) > 0.5
