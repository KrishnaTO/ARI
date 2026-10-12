"""Merge ARI and target-database names per disease and assign a first-pass verdict.

Writes candidates.json: {ari_id: {label, terms: {key: {...}}}}
"""
import csv, json, os, re, sys, unicodedata
from collections import Counter

G = json.load(open(sys.argv[1], encoding='utf-8'))
OLD = sys.argv[2]
OUT = sys.argv[3]

# MONDO:1060002 (ocular myasthenia gravis) is newer than the local mondo.obo; taken from OLS4.
G['diseases']['ARI:0001145']['sources'].append({
    'db': 'MONDO', 'id': 'MONDO:1060002', 'label': 'ocular myasthenia gravis',
    'synonyms': [['OMG', 'EXACT'], ['ocular myasthenia', 'EXACT']], 'obsolete': False,
    'parents': ['myasthenia gravis'], 'descendants': []})

SPELL = [('haemo', 'hemo'), ('anaemi', 'anemi'), ('oesophag', 'esophag'), ('leukaem', 'leukem'),
         ('aemia', 'emia'), ('oedema', 'edema'), ('paediatric', 'pediatric'), ('coeliac', 'celiac'),
         ('ischaem', 'ischem'), ('foetal', 'fetal'), ('tumour', 'tumor'), ('sjoegren', 'sjogren'),
         ('schoenlein', 'schonlein'), ('oestr', 'estr')]


def key(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower().strip()
    s = re.sub(r'\s*\((disorder|finding|morphologic abnormality|clinical|disease)\)$', '', s)
    m = re.fullmatch(r"([^,]+), ([^,]+)", s)
    if m and len(m.group(2).split()) <= 3 and not re.search(
            r'\b(type|class|with|without|due|of|in|and|unspecified|nos|other|stage|grade)\b', m.group(2)):
        s = m.group(2) + ' ' + m.group(1)
    s = re.sub(r"'s\b|s'(?=\s|$)", '', s)
    for a, b in SPELL:
        s = s.replace(a, b)
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def subtype_name(s):
    return re.split(r'\s+[-–—]\s+', s, maxsplit=1)[0].strip()


SITE = (r'joint|joints|knee|knees|hip|hips|ankle|ankles|foot|feet|hand|hands|wrist|wrists|elbow|elbows|'
        r'shoulder|shoulders|vertebra|vertebrae|spine|finger|fingers|toe|toes|forearm|upper arm|lower leg|'
        r'thigh|pelvic region|multiple sites|site|sites|eyelid|eyelids|eye|eyes|ear|ears|limb|limbs')
VARIANT = re.compile(
    r'\b(left|right|bilateral|unilateral)\b'
    r'|\bin remission\b|\bflare\b|\bremission\b'
    r'|\b(of|in|involving)\s+(the\s+)?(' + SITE + r')\b'
    r'|^(' + SITE + r')\b'
    r'|\bunspecified\b|\bother specified\b|^other\b|\bnot elsewhere classified\b'
    r'|\bwithout complication\b|\bwith(out)? (rectal bleeding|intestinal obstruction|fistula|abscess|other complication|complications?)\b'
    r'|\bwith(out)? (hyperglycemia|hypoglycemia|ketoacidosis|coma)\b'
    r'|\bwith(out)? (status epilepticus|intractable|intractability)\b|\bintractable\b|\bnot intractable\b'
    r'|\bin (pregnancy|childbirth|the puerperium)\b|\bcomplicating\b',
    re.I)
CODED = re.compile(r'\bwith(out)?\b|\bco-occurrent\b|\bassociated with\b', re.I)
NONAUTO = re.compile(r'infect|bacteri|viral|virus|tubercul|syphil|toxoplasm|herpe|fung|parasit|candid|'
                     r'cytomegalo|trauma|injur|post-?operative|radiation|drug-induced|alcohol', re.I)

old = {}
with open(OLD, encoding='utf-8') as f:
    for r in csv.DictReader(f, delimiter='	'):
        if 'synonym' in r:  # 2026-09 layout: one row per ARI synonym, verdict "withdrawn" + reason
            term, verdict = r['synonym'], (r['reason'] if r['verdict'] == 'withdrawn' else 'synonym')
        else:
            term, verdict = r['term'], r['verdict']
        old[(r['ari_id'], term)] = {'term': term, 'verdict': verdict, 'note': r['note'], 'review_date': r['review_date']}

QUALIFIERS = {'hereditary', 'familial', 'juvenile', 'adult', 'childhood', 'infantile', 'neonatal', 'acute', 'subacute', 'chronic', 'primary', 'secondary', 'congenital', 'sporadic', 'type', 'localized', 'localised', 'generalized', 'generalised', 'systemic', 'cutaneous', 'ocular', 'limited', 'diffuse', 'early', 'late', 'onset', 'seropositive', 'seronegative', 'refractory', 'recurrent', 'relapsing', 'progressive', 'severe', 'mild', 'paraneoplastic', 'drug', 'induced', 'idiopathic', 'autoimmune'}
DEC = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'decisions.json'), encoding='utf-8'))
ROW_ROLES = {'synonym', 'clinical_subtype', 'label', 'exact', 'related', 'narrow', 'broad', 'descendant'}

out = {}
for aid, d in sorted(G['diseases'].items()):
    terms = {}
    lab_key = key(d['label'])

    def add(name, src, role, tid='', extra=''):
        if not name or not name.strip():
            return
        if src != 'ARI':  # Orphanet epidemiology prefix on database labels
            name = re.sub(r'^NON RARE IN EUROPE: ', '', name)
        k = key(name)
        if not k:
            return
        t = terms.setdefault(k, {'names': [], 'evidence': []})
        if name not in t['names']:
            t['names'].append(name)
        ev = {'src': src, 'role': role, 'id': tid, 'name': name, 'extra': extra}
        if ev not in t['evidence']:
            t['evidence'].append(ev)

    for s in d['synonyms']:
        add(s, 'ARI', 'synonym')
    for w in d['withdrawn']:
        parts = [p.strip() for p in w.split(' | ')]
        add(parts[0], 'ARI', 'withdrawn:' + parts[1], extra=parts[2] if len(parts) > 2 else '')
    for s in d['subtypes']:
        add(subtype_name(s), 'ARI', 'clinical_subtype', extra=s)
    for src in d['sources']:
        db = src['db']
        add(src['label'], db, 'label', src['id'])
        # a mapped term that lists the entry's own name as NARROW is broader than the entry
        # (and as BROAD, narrower), so that scope says nothing about the entry
        own = {sc for n, sc in src['synonyms'] if key(n) == lab_key}
        for n, sc in src['synonyms']:
            if sc in own and sc in ('NARROW', 'BROAD'):
                sc = 'RELATED'
            add(n, db, sc.lower(), src['id'])
        if not VARIANT.search(src['label']):  # a residual code's parent is the concept itself
            same_db_labels = {key(x['label']) for x in d['sources'] if x['db'] == db} | {lab_key}
            for p in src['parents']:
                if key(p) not in same_db_labels:
                    add(p, db, 'parent', src['id'])
        for c in src['descendants']:
            if lab_key in {key(c['label'])} | {key(n) for n, sc in c['synonyms']}:
                continue  # the entry's own concept sitting under a broader mapped term
            add(c['label'], db, 'descendant', c['id'], extra=src['id'])
            for n, sc in c['synonyms']:
                if sc == 'EXACT':
                    add(n, db, 'descendant_synonym', c['id'], extra=src['id'])

    # merge plural variants (MeSH entry terms) into the singular key
    for k in sorted(terms, key=len, reverse=True):
        if k.endswith('s') and k[:-1] in terms and k in terms:
            t = terms.pop(k)
            tgt = terms[k[:-1]]
            tgt['names'] += [n for n in t['names'] if n not in tgt['names']]
            tgt['evidence'] += [e for e in t['evidence'] if e not in tgt['evidence']]

    def judge(k, t, src_kind):
        ev = t['evidence']
        roles = {e['role'] for e in ev}
        is_label = k == lab_key
        old_rows = [old[(aid, n)] for n in t['names'] if (aid, n) in old]
        kind = lambda e: src_kind.get(e['id']) if e['role'] in ('label', 'exact') else None
        named_sub = [e for e in ev if e['role'] in ('narrow', 'clinical_subtype', 'withdrawn:subtype') or kind(e) == 'narrower']
        desc = [e for e in ev if e['role'] in ('descendant', 'descendant_synonym')
                and src_kind.get(e['extra']) != 'broader']
        broad = [e for e in ev if e['role'] in ('broad', 'parent', 'withdrawn:broader') or kind(e) == 'broader']
        exact = [e for e in ev if e['role'] in ('label', 'exact') and e['src'] != 'ARI' and kind(e) is None]
        related = [e for e in ev if e['role'] == 'related']
        other_w = [e for e in ev if e['role'] in ('withdrawn:distinct', 'withdrawn:non-disease')]
        coded = desc and all(e['src'] in ('SNOMEDCT', 'icd10cm') for e in desc)
        is_var = lambda n: VARIANT.search(n) or (coded and CODED.search(n))
        variant = bool(is_var(t['names'][0])) and all(is_var(e['name']) for e in desc)
        flags = []
        if any(e['role'] == 'label' and kind(e) is None for e in ev) and (named_sub or desc or broad):
            flags.append('conflict:label')
        if is_label:
            verdict = 'preferred'
        elif any(re.search(r'susceptibility', n, re.I) for n in t['names']):
            verdict = 'non-disease'
        elif named_sub or (desc and not variant):
            verdict = 'subtype'
            if exact:
                flags.append('conflict:exact')
            if broad:
                flags.append('conflict:broader')
        elif desc and variant:
            verdict = 'variant'
        elif other_w:
            verdict = other_w[0]['role'].split(':')[1]
        elif broad:
            verdict = 'broader'
            if exact:
                flags.append('conflict:exact')
        elif exact:
            verdict = 'synonym'
            extra_words = set(k.split()) - set(lab_key.split())
            if extra_words & QUALIFIERS:
                flags.append('qualifier')
        elif old_rows:
            o = old_rows[0]
            verdict = o['verdict']
            flags.append('old-only')
        elif related:
            verdict = 'review'
            flags.append('related-only')
        else:
            verdict = 'review'
            flags.append('no-evidence')
        if verdict in ('subtype', 'variant') and NONAUTO.search(' '.join(t['names'])):
            flags.append('non-autoimmune-cause')
        manual = DEC.get(aid + '	' + k)
        auto = verdict
        if manual and not is_label:
            verdict = manual['verdict']
        return {'auto': auto, 'manual': manual, 'names': t['names'], 'evidence': ev, 'verdict': verdict,
                'flags': flags, 'in_ari': any(e['src'] == 'ARI' for e in ev), 'is_label': is_label,
                'old': old_rows}

    keep = {k: t for k, t in terms.items()
            if {e['role'] for e in t['evidence']} & ROW_ROLES or any(e['src'] == 'ARI' for e in t['evidence'])}
    first = {k: judge(k, t, {}) for k, t in keep.items()}
    # a mapped term whose own label is judged broader (or narrower) than the entry passes
    # that judgement to its exact synonyms
    src_kind = {}
    for src in d['sources']:
        lk = key(re.sub(r'^NON RARE IN EUROPE: ', '', src['label']))
        v = first[lk]['verdict'] if lk in first else None
        if v == 'broader':
            src_kind[src['id']] = 'broader'
        elif v in ('subtype', 'variant'):
            src_kind[src['id']] = 'narrower'
    rows = {}
    for k, t in keep.items():
        live = [e for e in t['evidence'] if not (e['role'] in ('descendant', 'descendant_synonym')
                                                 and src_kind.get(e['extra']) == 'broader')]
        if not ({e['role'] for e in live} & ROW_ROLES or any(e['src'] == 'ARI' for e in live)):
            continue
        rows[k] = judge(k, t, src_kind)
    for k, r in rows.items():
        r['source_kinds'] = {i: src_kind[i] for i in {e['id'] for e in r['evidence']} if i in src_kind}
    out[aid] = {'label': d['label'], 'terms': rows,
                'sources': [s['id'] for s in d['sources']]}

json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
c = Counter((v['verdict'], v['in_ari']) for d in out.values() for v in d['terms'].values())
for k, v in sorted(c.items()):
    print(k, v)
f = Counter(fl for d in out.values() for v in d['terms'].values() for fl in v['flags'])
print(f)
