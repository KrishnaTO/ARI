"""Write data/4-reports/9_Synonym_Review.tsv from candidates.json."""
import csv, json, sys
from collections import Counter

C = json.load(open(sys.argv[1], encoding='utf-8'))
OUT = sys.argv[2]
DATE = sys.argv[3]

ROLE = {'label': 'label', 'exact': 'exact', 'related': 'related', 'narrow': 'narrow', 'broad': 'broad'}
ORDER = {'synonym': 0, 'subtype': 1, 'variant': 2, 'broader': 3, 'distinct': 4, 'non-disease': 5}


def ari_fields(t):
    f = []
    for e in t['evidence']:
        if e['src'] != 'ARI':
            continue
        if e['role'] == 'synonym':
            f.append('ARI_Synonym')
        elif e['role'] == 'clinical_subtype':
            f.append('ARI_ClinicalSubtype')
        else:
            f.append('ARI_SynonymWithdrawn (' + e['role'].split(':')[1] + ')')
    return list(dict.fromkeys(f))


def evidence(t):
    kinds = t['source_kinds']
    parts = {}
    for e in t['evidence']:
        if e['src'] == 'ARI':
            continue
        r = e['role']
        if r in ROLE:
            tag = ROLE[r]
            item = e['id']
            if e['id'] in kinds:
                item += f" ({kinds[e['id']]} than entry)"
        elif r == 'parent':
            tag, item = 'parent of mapped term', e['id']
        elif r == 'descendant':
            tag, item = 'child term', f"{e['id']} under {e['extra']}"
        elif r == 'descendant_synonym':
            tag, item = 'synonym of child term', f"{e['id']} under {e['extra']}"
        else:
            continue
        parts.setdefault(tag, [])
        if item not in parts[tag]:
            parts[tag].append(item)
    order = ['label', 'exact', 'related', 'narrow', 'broad', 'parent of mapped term', 'child term', 'synonym of child term']
    out = []
    for tag in order:
        if tag in parts:
            items = parts[tag]
            shown = ', '.join(items[:4]) + (f' +{len(items) - 4} more' if len(items) > 4 else '')
            out.append(f'{tag}: {shown}')
    return '; '.join(out) if out else 'no database match'


def action(fields, verdict):
    reason = 'subtype' if verdict == 'variant' else verdict
    if 'ARI_Synonym' in fields:
        return 'keep' if verdict == 'synonym' else f'withdraw synonym ({reason})'
    if any(f.startswith('ARI_SynonymWithdrawn') for f in fields):
        if verdict == 'synonym':
            return 'restore synonym'
        return 'none (already withdrawn)'
    if 'ARI_ClinicalSubtype' in fields:
        if verdict == 'subtype':
            return 'keep'
        if verdict == 'synonym':
            return 'move clinical subtype to synonyms'
        return f'remove clinical subtype ({verdict})'
    if verdict == 'synonym':
        return 'candidate synonym'
    if verdict == 'subtype':
        return 'candidate clinical subtype'
    return 'none'


def field_of(e):
    if e['role'] == 'synonym':
        return 'ARI_Synonym'
    if e['role'] == 'clinical_subtype':
        return 'ARI_ClinicalSubtype'
    return 'ARI_SynonymWithdrawn (' + e['role'].split(':')[1] + ')'


rows = []
for aid, d in C.items():
    for k, t in d['terms'].items():
        if t['verdict'] == 'preferred' and not t['in_ari']:
            continue
        verdict = 'synonym' if t['verdict'] == 'preferred' else t['verdict']
        ari = {}
        for e in t['evidence']:
            if e['src'] == 'ARI':
                ari.setdefault(e['name'], []).append(field_of(e))
        db_names = [n for n in t['names'] if n not in ari]
        note = ''
        if t['verdict'] == 'preferred':
            note = 'Spelling or word-order variant of the entry name.'
        elif t['manual']:
            note = t['manual']['note']
        else:
            same_old = [o for o in t['old'] if o['verdict'] == verdict and o['note']]
            if same_old:
                note = same_old[0]['note']
            elif verdict == 'variant':
                note = 'Site, laterality, episode, complication or residual code of the disease, not a separate disease.'
            elif 'non-autoimmune-cause' in t['flags']:
                note = 'Names an infectious, traumatic or iatrogenic cause; a subtype in the source classification, but not autoimmune.'
        decided = ('curator research' if t['manual'] else
                   'earlier review' if 'old-only' in t['flags'] else
                   'entry name' if t['verdict'] == 'preferred' else 'database evidence')
        ev = evidence(t)
        entries = [(n, list(dict.fromkeys(f))) for n, f in ari.items()] or [(t['names'][0], [])]
        for term, fields in entries:
            others = [n for n in db_names if n != term]
            rows.append({
                'ari_id': aid, 'disease': d['label'], 'term': term,
                'ari_field': '; '.join(fields), 'verdict': verdict,
                'action': action(fields, verdict), 'decided_by': decided,
                'evidence': ev, 'note': note,
                'other_names': ' | '.join(others[:8]) + (f' | +{len(others) - 8} more' if len(others) > 8 else ''),
                'review_date': DATE,
            })

rows.sort(key=lambda r: (r['ari_id'], 0 if r['ari_field'] else 1, ORDER[r['verdict']], r['term'].lower()))
cols = ['ari_id', 'disease', 'term', 'ari_field', 'verdict', 'action', 'decided_by', 'evidence', 'note', 'other_names', 'review_date']
with open(OUT, 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, cols, delimiter='\t', lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
print(len(rows))
print(Counter(r['action'] for r in rows).most_common())
print(Counter((r['ari_field'].split(' (')[0] if r['ari_field'] else '-', r['verdict']) for r in rows).most_common())
