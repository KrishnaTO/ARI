"""Gather ARI synonyms/clinical subtypes and target-database synonyms/descendants.

Writes gather.json: {ari_id: {label, synonyms, withdrawn, subtypes, sources: [...]}}
Each source entry: {db, id, label, synonyms: [[name, scope]], parents: [label],
                    descendants: [{id, label, depth, synonyms: [[name, scope]]}]}
"""
import csv, json, os, re, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict, deque

csv.field_size_limit(10**9)
WT = sys.argv[1]
DB = sys.argv[2]
OUT = sys.argv[3]
CACHE = os.path.join(os.path.dirname(OUT), 'cache')
os.makedirs(CACHE, exist_ok=True)

RDF = '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}'
RDFS = '{http://www.w3.org/2000/01/rdf-schema#}'
OWL = '{http://www.w3.org/2002/07/owl#}'
OIO = '{http://www.geneontology.org/formats/oboInOwl#}'
A = '{http://www.aurint.org/ontologies/ari-disease#}'

# ---------- ARI ----------
ari = {}
root = ET.parse(os.path.join(WT, 'ontologies/ari_t1d.owl')).getroot()
for ind in root.iter(OWL + 'NamedIndividual'):
    idel = ind.find(A + 'ARI_ID')
    if idel is None:
        continue
    types = [t.get(RDF + 'resource') for t in ind.findall(RDF + 'type')]
    if not any(t and t.endswith('#AutoimmuneDisease') for t in types):
        continue
    if (ind.findtext(A + 'ARI_Obsolete') or 'false') == 'true':
        continue
    ari[idel.text] = {
        'label': ind.findtext(RDFS + 'label'),
        'synonyms': [e.text for e in ind.findall(A + 'ARI_Synonym') if e.text],
        'withdrawn': [e.text for e in ind.findall(A + 'ARI_SynonymWithdrawn') if e.text],
        'subtypes': [e.text for e in ind.findall(A + 'ARI_ClinicalSubtype') if e.text],
        'sources': [],
    }
print('ARI diseases', len(ari), file=sys.stderr)

# ---------- confirmed mappings ----------
maps = defaultdict(list)
with open(os.path.join(WT, 'mappings/ari.sssom.tsv'), encoding='utf-8') as f:
    rows = csv.DictReader((l for l in f if not l.startswith('#')), delimiter='\t')
    for r in rows:
        if r['predicate_modifier'] == 'Not' or 'NoTermFound' in r['object_id']:
            continue
        p, i = r['object_id'].split(':', 1)
        if (p, i) not in maps[r['subject_id']]:
            maps[r['subject_id']].append((p, i))


def cached_get(url, key):
    path = os.path.join(CACHE, re.sub(r'[^A-Za-z0-9_.-]', '_', key) + '.json')
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    for attempt in range(10):
        try:
            req = urllib.request.Request(url, headers={'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.load(r)
            break
        except Exception as e:
            if attempt == 9:
                raise
            time.sleep(5 * (attempt + 1))
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    return data


# ---------- MONDO (obo) ----------
def parse_obo(path):
    terms, cur = {}, None
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if line.startswith('['):
                cur = {'syn': [], 'isa': [], 'obs': False} if line == '[Term]' else None
                continue
            if cur is None or ': ' not in line:
                continue
            k, v = line.split(': ', 1)
            if k == 'id':
                terms[v] = cur
            elif k == 'name':
                cur['name'] = v
            elif k == 'synonym':
                m = re.match(r'"((?:[^"\\]|\\.)*)" (\w+)', v)
                cur['syn'].append([m.group(1).replace('\\"', '"'), m.group(2)])
            elif k == 'is_a':
                cur['isa'].append(v.split(' ')[0])
            elif k == 'is_obsolete' and v == 'true':
                cur['obs'] = True
    return terms


def tree_source(db, tid, terms):
    t = terms[tid]
    kids = defaultdict(list)
    for k, v in terms.items():
        if not v['obs']:
            for p in v['isa']:
                kids[p].append(k)
    return t, kids


def descend(tid, kids, terms):
    out, seen, q = [], {tid}, deque([(tid, 0)])
    while q:
        n, d = q.popleft()
        for c in kids.get(n, []):
            if c in seen:
                continue
            seen.add(c)
            out.append({'id': c, 'label': terms[c].get('name', ''), 'depth': d + 1,
                        'synonyms': terms[c]['syn']})
            q.append((c, d + 1))
    return out


mondo = parse_obo(os.path.join(DB, 'mondo.obo'))
mkids = defaultdict(list)
for k, v in mondo.items():
    if not v['obs']:
        for p in v['isa']:
            mkids[p].append(k)
print('MONDO terms', len(mondo), file=sys.stderr)

# ---------- DOID (owl) ----------
doid = {}
SCOPES = {'hasExactSynonym': 'EXACT', 'hasRelatedSynonym': 'RELATED',
          'hasNarrowSynonym': 'NARROW', 'hasBroadSynonym': 'BROAD'}
for _, el in ET.iterparse(os.path.join(DB, 'doid.owl')):
    if el.tag != OWL + 'Class':
        continue
    about = el.get(RDF + 'about') or ''
    if 'DOID_' not in about:
        el.clear()
        continue
    tid = 'DOID:' + about.rsplit('DOID_', 1)[1]
    syn = []
    for s, sc in SCOPES.items():
        syn += [[e.text, sc] for e in el.findall(OIO + s) if e.text]
    doid[tid] = {'name': el.findtext(RDFS + 'label') or '', 'syn': syn,
                 'isa': ['DOID:' + e.get(RDF + 'resource').rsplit('DOID_', 1)[1]
                         for e in el.findall(RDFS + 'subClassOf')
                         if (e.get(RDF + 'resource') or '').count('DOID_')],
                 'obs': (el.findtext(OWL + 'deprecated') or '') == 'true'}
    el.clear()
dkids = defaultdict(list)
for k, v in doid.items():
    if not v['obs']:
        for p in v['isa']:
            dkids[p].append(k)
print('DOID terms', len(doid), file=sys.stderr)


def obo_entry(db, tid, terms, kids):
    t = terms[tid]
    return {'db': db, 'id': tid, 'label': t.get('name', ''), 'synonyms': t['syn'],
            'obsolete': t['obs'],
            'parents': [terms[p].get('name', p) for p in t['isa'] if p in terms],
            'descendants': descend(tid, kids, terms)}


# ---------- SNOMED via OMOP ----------
need_sct = set()
need_omop = set()
for s, lst in maps.items():
    for p, i in lst:
        if p == 'SNOMEDCT':
            need_sct.add(i)
        if p == 'omop':
            need_omop.add(i)
import pickle
SPK = os.path.join(os.path.dirname(OUT), 'snomed.pkl')
if os.path.exists(SPK):
    sct_by_code, sct_name, sct_code, roots, desc, parents, sct_syn = pickle.load(open(SPK, 'rb'))
else:
    sct_by_code, sct_name, sct_code = {}, {}, {}
    with open(os.path.join(DB, 'snomed/CONCEPT.csv'), encoding='utf-8') as f:
        for r in csv.reader(f, delimiter='\t'):
            if r[3] == 'SNOMED':
                sct_by_code[r[6]] = r[0]
                sct_name[r[0]] = r[1]
                sct_code[r[0]] = (r[6], r[9])
    roots = {sct_by_code[c] for c in need_sct if c in sct_by_code} | {o for o in need_omop if o in sct_name}
    desc = defaultdict(list)
    parents = defaultdict(list)
    with open(os.path.join(DB, 'snomed/CONCEPT_ANCESTOR.csv'), encoding='utf-8') as f:
        next(f)
        for line in f:
            a, d, mn, mx = line.rstrip('\n').split('\t')
            if a in roots and a != d and d in sct_name:
                desc[a].append((d, int(mn)))
            if d in roots and mn == '1':
                parents[d].append(a)
    need_syn = set(roots) | {d for v in desc.values() for d, _ in v}
    sct_syn = defaultdict(list)
    with open(os.path.join(DB, 'snomed/CONCEPT_SYNONYM.csv'), encoding='utf-8') as f:
        next(f)
        for line in f:
            c, n, lang = line.rstrip('\n').split('\t')
            if c in need_syn and lang == '4180186':
                sct_syn[c].append(n)
    keep = need_syn | {p for v in parents.values() for p in v}
    sct_name = {k: v for k, v in sct_name.items() if k in keep}
    sct_code = {k: v for k, v in sct_code.items() if k in keep}
    pickle.dump((sct_by_code, sct_name, sct_code, roots, desc, parents, sct_syn), open(SPK, 'wb'))


def sct_entry(cid):
    return {'db': 'SNOMEDCT', 'id': 'SNOMEDCT:' + sct_code[cid][0], 'label': sct_name[cid],
            'synonyms': [[n, 'EXACT'] for n in sct_syn[cid] if n != sct_name[cid]],
            'obsolete': bool(sct_code[cid][1]),
            'parents': [sct_name[p] for p in parents[cid] if p in sct_name],
            'descendants': [{'id': 'SNOMEDCT:' + sct_code[d][0], 'label': sct_name[d], 'depth': lvl,
                             'synonyms': [[n, 'EXACT'] for n in sct_syn[d] if n != sct_name[d]]}
                            for d, lvl in sorted(desc[cid], key=lambda x: (x[1], sct_name[x[0]]))]}


print('SNOMED roots', len(roots), file=sys.stderr)

# ---------- ICD10CM via OMOP ----------
icd = {}
with open(os.path.join(DB, 'mesh-icd-ncit-clinvar/CONCEPT.csv'), encoding='utf-8') as f:
    for r in csv.reader(f, delimiter='\t'):
        if r[3] == 'ICD10CM':
            icd[r[6]] = (r[0], r[1])
icd_ids = {v[0] for v in icd.values()}
icd_syn = defaultdict(list)
with open(os.path.join(DB, 'mesh-icd-ncit-clinvar/CONCEPT_SYNONYM.csv'), encoding='utf-8') as f:
    next(f)
    for line in f:
        c, n, lang = line.rstrip('\n').split('\t')
        if c in icd_ids:
            icd_syn[c].append(n)


def icd_entry(code):
    cid, name = icd[code]
    kids = sorted(k for k in icd if k != code and k.startswith(code))
    par = code[:-1].rstrip('.') if len(code) > 3 else None
    return {'db': 'icd10cm', 'id': 'icd10cm:' + code, 'label': name,
            'synonyms': [[n, 'EXACT'] for n in icd_syn[cid] if n != name],
            'obsolete': False,
            'parents': [icd[par][1]] if par in icd else [],
            'descendants': [{'id': 'icd10cm:' + k, 'label': icd[k][1],
                             'depth': len(k.replace('.', '')) - len(code.replace('.', '')),
                             'synonyms': [[n, 'EXACT'] for n in icd_syn[icd[k][0]] if n != icd[k][1]]}
                            for k in kids]}


# ---------- OMIM ----------
omim = {}
need_omim = {i for lst in maps.values() for p, i in lst if p == 'OMIM'}
with open(os.path.join(DB, 'OMIM.ttl'), encoding='utf-8') as f:
    txt = f.read()
for i in need_omim:
    start = txt.find(f'<http://purl.bioontology.org/ontology/OMIM/{i}> a owl:Class ;')
    if start < 0:
        continue
    body = txt[start:txt.find(chr(10) + ' .' + chr(10), start)]
    pl = re.search(r'skos:prefLabel """(.*?)"""', body)
    al = re.search(r'skos:altLabel (.*?) ;$', body, re.S | re.M)
    omim[i] = (pl.group(1) if pl else '', re.findall(r'"""(.*?)"""@en', al.group(1)) if al else [])
del txt


def omim_entry(i):
    name, alts = omim[i]
    return {'db': 'OMIM', 'id': 'OMIM:' + i, 'label': name,
            'synonyms': [[a, 'EXACT'] for a in alts], 'obsolete': False, 'parents': [], 'descendants': []}


# ---------- OLS4 (Orphanet, NCIt) ----------
def ols_entry(db, onto, iri, curie):
    enc = urllib.parse.quote(urllib.parse.quote(iri, safe=''), safe='')
    base = f'https://www.ebi.ac.uk/ols4/api/ontologies/{onto}/terms/{enc}'
    t = cached_get(base, f'{onto}_{curie}')

    def syns(term):
        if term.get('obo_synonym'):
            return [[s['name'], s['scope'].replace('has', '').replace('Synonym', '').upper()]
                    for s in term['obo_synonym']]
        return [[s, 'EXACT'] for s in (term.get('synonyms') or [])]

    def paged(rel):
        out, page = [], 0
        while True:
            d = cached_get(f'{base}/{rel}?size=500&page={page}', f'{onto}_{curie}_{rel}_{page}')
            out += d.get('_embedded', {}).get('terms', [])
            if page + 1 >= d['page']['totalPages']:
                return out
            page += 1

    kids = paged('hierarchicalDescendants') if t.get('has_children') else []
    pars = paged('hierarchicalParents')
    return {'db': db, 'id': curie, 'label': t['label'], 'synonyms': syns(t),
            'obsolete': t.get('is_obsolete', False),
            'parents': [p['label'] for p in pars],
            'descendants': [{'id': k.get('obo_id') or k['short_form'], 'label': k['label'], 'depth': None,
                             'synonyms': syns(k)} for k in kids]}


# ---------- MeSH (SPARQL) ----------
MESH_SPARQL = 'https://id.nlm.nih.gov/mesh/sparql'
PFX = 'PREFIX meshv: <http://id.nlm.nih.gov/mesh/vocab#> PREFIX mesh: <http://id.nlm.nih.gov/mesh/> PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> '


def sparql(q, key):
    url = MESH_SPARQL + '?' + urllib.parse.urlencode({'query': PFX + q, 'format': 'JSON', 'limit': 1000, 'inference': 'true'})
    return cached_get(url, key)['results']['bindings']


def mesh_entry(i):
    lab = sparql(f'SELECT ?l WHERE {{ mesh:{i} rdfs:label ?l }}', f'mesh_{i}_label')
    rows = sparql(f'''SELECT ?rel ?term WHERE {{
        {{ mesh:{i} meshv:preferredConcept ?c . BIND("preferred" AS ?rel) }}
        UNION {{ mesh:{i} meshv:preferredConcept ?pc . ?pc ?r ?c .
                 FILTER(?r IN (meshv:narrowerConcept, meshv:broaderConcept, meshv:relatedConcept))
                 BIND(STRAFTER(STR(?r), "#") AS ?rel) }}
        ?c meshv:preferredTerm|meshv:term ?t . ?t meshv:prefLabel ?term }}''', f'mesh_{i}_terms')
    scope = {'preferred': 'EXACT', 'narrowerConcept': 'NARROW', 'broaderConcept': 'BROAD', 'relatedConcept': 'RELATED',
             'broader': 'BROAD', 'narrower': 'NARROW', 'related': 'RELATED'}
    kids = sparql(f'''SELECT ?d ?l WHERE {{ ?d meshv:broaderDescriptor+ mesh:{i} . ?d rdfs:label ?l }}''', f'mesh_{i}_desc')
    pars = sparql(f'SELECT ?l WHERE {{ mesh:{i} meshv:broaderDescriptor ?p . ?p rdfs:label ?l }}', f'mesh_{i}_par')
    label = lab[0]['l']['value'] if lab else ''
    return {'db': 'mesh', 'id': 'mesh:' + i, 'label': label,
            'synonyms': [[r['term']['value'], scope[r['rel']['value']]] for r in rows if r['term']['value'] != label and r['rel']['value'] in scope],
            'obsolete': False,
            'parents': [p['l']['value'] for p in pars],
            'descendants': [{'id': 'mesh:' + k['d']['value'].rsplit('/', 1)[1], 'label': k['l']['value'],
                             'depth': None, 'synonyms': []} for k in kids]}


# ---------- assemble ----------
missing = []
for aid, d in ari.items():
    for p, i in maps.get(aid, []):
        try:
            if p == 'MONDO':
                e = obo_entry('MONDO', 'MONDO:' + i, mondo, mkids) if 'MONDO:' + i in mondo else None
            elif p == 'DOID':
                e = obo_entry('DOID', 'DOID:' + i, doid, dkids) if 'DOID:' + i in doid else None
            elif p == 'SNOMEDCT':
                e = sct_entry(sct_by_code[i]) if i in sct_by_code else None
            elif p == 'omop':
                if i in sct_name and any(x['id'] == 'SNOMEDCT:' + sct_code[i][0] for x in d['sources']):
                    continue
                e = sct_entry(i) if i in sct_name else None
            elif p == 'icd10cm':
                e = icd_entry(i) if i in icd else None
            elif p == 'OMIM':
                e = omim_entry(i) if i in omim else None
            elif p == 'ORPHA':
                e = ols_entry('ORPHA', 'ordo', f'http://www.orpha.net/ORDO/Orphanet_{i}', 'ORPHA:' + i)
            elif p == 'ncit':
                e = ols_entry('ncit', 'ncit', f'http://purl.obolibrary.org/obo/NCIT_{i}', 'ncit:' + i)
            elif p == 'mesh':
                e = mesh_entry(i)
            elif p == 'umls':
                continue
            else:
                raise ValueError(p)
        except urllib.error.HTTPError as ex:
            e = None
            print('HTTP', p, i, ex, file=sys.stderr)
        if e is None:
            missing.append(f'{aid} {p}:{i}')
            continue
        d['sources'].append(e)
    print(aid, len(d['sources']), file=sys.stderr)

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump({'diseases': ari, 'missing': missing,
               'umls': {a: [i for p, i in m if p == 'umls'] for a, m in maps.items()}}, f, ensure_ascii=False, indent=1)
print('missing', missing, file=sys.stderr)
