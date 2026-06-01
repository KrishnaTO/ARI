#!/usr/bin/env python3
"""Build fully-linked ARI autoimmune-disease database (union of all sources).

Identity model (conservative):
  * Same SNOMED conceptId  -> same concept.
  * Same DOID curie        -> same concept.
  * SNOMED<->DOID merged ONLY for reciprocal 1:1 matches (mutually unique across
    the combined candidate-edge set from ARI-doid name-lookup + DOID db_xref).
  * All other SNOMED<->DOID links recorded in the Crosswalk table (not merged).
Each resolved concept gets a generated ARI_ID (ARI-#####).
"""
import openpyxl, os, re, json
from collections import defaultdict

BASE   = "/sessions/clever-zen-ritchie/mnt/data"
OUTDIR = os.path.join(BASE, "ARI-Linked-Database")
os.makedirs(OUTDIR, exist_ok=True)

def load(f, sheet):
    wb=openpyxl.load_workbook(os.path.join(BASE,f),read_only=True,data_only=True);ws=wb[sheet]
    data=list(ws.iter_rows(values_only=True));wb.close()
    hdr=[(str(c).strip() if c is not None else c) for c in data[0]]
    return [dict(zip(hdr,r)) for r in data[1:] if any(v is not None for v in r)]
def s(v):
    if v is None: return None
    v=str(v).strip(); return v if v else None
def norm_doid(v):
    v=s(v)
    if not v: return None
    m=re.search(r'(\d+)',v.replace(" ",""))
    return f"DOID:{int(m.group(1)):07d}" if m else None
def norm_snomed(v):
    v=s(v)
    if not v: return None
    m=re.match(r'^\d{6,}$',v.replace(" ",""))
    return m.group(0) if m else None
def split_pipe(v):
    v=s(v)
    if not v: return []
    return [p.strip() for p in re.split(r'\s*\|\s*|\n',v) if p and p.strip()]

ari      = load("ARI-doid/ARI-doid.xlsx","ARI-DOID-matches")
synkey   = {r['Syn']:r['meaning'] for r in load("ARI-doid/ARI-doid.xlsx","Syn Key")}
mesh_doid= load("ARI-MESH_Synonyms/ARI-MESHsynonyms-DOID.xlsx","ARI-X-DOID-simple")
snolook  = load("ARI-SNOMED-Athena/ARI_SNOMED_Lookup.xlsx","ARI-SNOMED Lookup")
ari_ath  = load("ARI-SNOMED-Athena/ARI_Athena_Matches.xlsx","Matches")
doid_all = load("DOID_autoimmune_diseases/DOID-all.xlsx","DOID-allAutoimmune")
doid_xref= load("DOID_autoimmune_diseases/DOID-all.xlsx","do_dbrefs_expanded")
sno_all  = load("SNOMED-Athena/SNOMED_Athena_Matches-all_autoimmune_disease.xlsx","SNOMED-AutoimmuneDisease")
sno_ath  = load("SNOMED-Athena/SNOMED_Athena_Matches-all_autoimmune_disease.xlsx","Athena_Match")

# ---- candidate SNOMED<->DOID edges (for crosswalk + reciprocal merge) ----
edges=[]  # (snomed, doid, basis)
for r in ari:
    sn=norm_snomed(r.get('SNOMED')); do=norm_doid(r.get('doid_curie'))
    if sn and do: edges.append((sn,do,'ARI-doid name lookup'))
for r in doid_xref:
    do=norm_doid(r.get('id')); src=s(r.get('source')); sid=s(r.get('source_id'))
    if do and src and src.upper().startswith('SNOMED') and sid:
        sn=norm_snomed(sid)
        if sn: edges.append((sn,do,'DOID db_xref'))
sno_cand=defaultdict(set); doid_cand=defaultdict(set)
for sn,do,_ in edges:
    sno_cand[sn].add(do); doid_cand[do].add(sn)
reciprocal=set()
for sn,do,_ in edges:
    if sno_cand[sn]=={do} and doid_cand[do]=={sn}:
        reciprocal.add((sn,do))

# ---- Union-Find (exact-id merges + reciprocal 1:1 bridges) ----
parent={}
def find(x):
    parent.setdefault(x,x)
    while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
    return x
def union(a,b):
    if not a or not b: return
    ra,rb=find(a),find(b)
    if ra!=rb: parent[ra]=rb
def nS(c): return f"SNOMED:{c}"
def nD(c): return f"DOID:{c}"
# register nodes
for r in ari:
    sn=norm_snomed(r.get('SNOMED'));  find(nS(sn)) if sn else None
for r in snolook:
    sn=norm_snomed(r.get('ARI_SNOMED_ID')); find(nS(sn)) if sn else None
for r in sno_all:
    sn=norm_snomed(r.get('conceptId')); find(nS(sn)) if sn else None
for r in doid_all:
    do=norm_doid(r.get('id')); find(nD(do)) if do else None
for r in mesh_doid:
    do=norm_doid(r.get('DOID')); find(nD(do)) if do else None
# reciprocal 1:1 bridges only
for sn,do in reciprocal:
    union(nS(sn),nD(do))

comp=defaultdict(lambda:{'snomed':set(),'doid':set(),'omop':set(),'names':[],'category':None,
    'ari_parent':None,'synonyms':[],'definitions':[],'xrefs':[],'sources':set(),'semantic_tag':None,'in_ari':False})
def C(n): return comp[find(n)]

# ARI-doid -> anchor on SNOMED (its DOID is a fuzzy lookup -> crosswalk only)
for r in ari:
    sn=norm_snomed(r.get('SNOMED'))
    if not sn: continue
    c=C(nS(sn)); c['in_ari']=True; c['sources'].add('ARI-doid'); c['snomed'].add(sn)
    omop=s(r.get('ConceptID'));  c['omop'].add(omop) if omop else None
    if r.get('Parent'): c['ari_parent']=c['ari_parent'] or s(r.get('Parent'))
    if r.get('Category'): c['category']=c['category'] or s(r.get('Category'))
    syn=s(r.get('Syn')); name=s(r.get('Disease'))
    if name:
        typ=synkey.get(syn,syn)
        if syn=='N':
            c['names'].append(name); c['synonyms'].append((name,'ARI primary name','ARI-doid'))
        else:
            c['synonyms'].append((name,('ARI %s: %s'%(syn,typ)) if typ else 'ARI variant','ARI-doid'))

for r in snolook:
    sn=norm_snomed(r.get('ARI_SNOMED_ID'))
    if not sn: continue
    c=C(nS(sn)); c['sources'].add('ARI-SNOMED-Lookup'); c['snomed'].add(sn)
    pt=s(r.get('PreferredTerm'));  c['names'].append(pt) if pt else None
    if r.get('SemanticTag'): c['semantic_tag']=c['semantic_tag'] or s(r.get('SemanticTag'))
    for syn in split_pipe(r.get('Synonyms')): c['synonyms'].append((syn,'SNOMED synonym','ARI-SNOMED-Lookup'))
    td=s(r.get('TextDefinition'));  c['definitions'].append((td,'SNOMED','ARI-SNOMED-Lookup')) if td else None

for r in ari_ath:
    sn=norm_snomed(r.get('LoD_SNOMED')) or norm_snomed(r.get('Athena_SNOMED'))
    if not sn: continue
    c=C(nS(sn)); c['sources'].add('ARI-Athena')
    omop=s(r.get('Athena_OMOP'));  c['omop'].add(omop) if omop else None

mesh_by_id=defaultdict(set)
for r in mesh_doid:
    do=norm_doid(r.get('DOID')); dis=s(r.get('Disease'))
    if do and dis: mesh_by_id[do].add(dis)
for do,syns in mesh_by_id.items():
    c=C(nD(do)); c['sources'].add('ARI-MESH'); c['doid'].add(do)
    for syn in syns: c['synonyms'].append((syn,'MESH synonym','ARI-MESH'))

for r in doid_all:
    do=norm_doid(r.get('id'))
    if not do: continue
    c=C(nD(do)); c['sources'].add('DOID-all'); c['doid'].add(do)
    lbl=s(r.get('label'));  c['names'].insert(0,lbl) if lbl else None
    df=s(r.get('definition'));  c['definitions'].append((df,'DOID','DOID-all')) if df else None
    for syn in split_pipe(r.get('exact_synonym')): c['synonyms'].append((syn,'DOID exact synonym','DOID-all'))
    for syn in split_pipe(r.get('related_synonym')): c['synonyms'].append((syn,'DOID related synonym','DOID-all'))
for r in doid_xref:
    do=norm_doid(r.get('id')); src=s(r.get('source')); sid=s(r.get('source_id'))
    if not (do and src and sid): continue
    c=C(nD(do)); c['doid'].add(do); c['xrefs'].append((src,sid,'DOID-all'))

for r in sno_all:
    sn=norm_snomed(r.get('conceptId'))
    if not sn: continue
    c=C(nS(sn)); c['sources'].add('SNOMED-all'); c['snomed'].add(sn)
    term=s(r.get('term'));  c['names'].append(term) if term else None
    if r.get('semanticTag'): c['semantic_tag']=c['semantic_tag'] or s(r.get('semanticTag'))
    td=s(r.get('textDefinition'));  c['definitions'].append((td,'SNOMED','SNOMED-all')) if td else None
for r in sno_ath:
    sn=norm_snomed(r.get('inputConceptId(SNOMED)'))
    if not sn: continue
    c=C(nS(sn)); c['sources'].add('SNOMED-Athena')
    omop=s(r.get('athenaConceptId(OMOP)'));  c['omop'].add(omop) if omop else None

def pick_name(c):
    for n in c['names']:
        if n: return n
    if c['ari_parent']: return c['ari_parent']
    for syn,_,_ in c['synonyms']: return syn
    return None

ordered=sorted(comp.items(),key=lambda kv:(not kv[1]['in_ari'],(pick_name(kv[1]) or 'zzz').lower()))
ids={root:f"ARI-{i:05d}" for i,(root,_) in enumerate(ordered,1)}

# map node -> ARI_ID for crosswalk
node_id={}
for root,_ in ordered:
    pass
def id_of_node(n): return ids[find(n)]

resolved=[]
for root,c in ordered:
    name=pick_name(c)
    seen=set(); syns=[]
    for txt,typ,src in c['synonyms']:
        k=(txt or '').lower()
        if not txt or k==(name or '').lower() or k in seen: continue
        seen.add(k); syns.append((txt,typ,src))
    seend=set(); defs=[]
    for txt,sysn,src in c['definitions']:
        k=(txt or '')[:80].lower()
        if not txt or k in seend: continue
        seend.add(k); defs.append((txt,sysn,src))
    seenx=set(); xrefs=[]
    for sn_,val,src in c['xrefs']:
        if (sn_,val) in seenx: continue
        seenx.add((sn_,val)); xrefs.append((sn_,val,src))
    resolved.append({'root':root,'ARI_ID':ids[root],'Primary_Name':name,'Category':c['category'],
        'ARI_Parent':c['ari_parent'],'In_ARI':'Y' if c['in_ari'] else 'N','SemanticTag':c['semantic_tag'],
        'SNOMED':sorted(c['snomed']),'DOID':sorted(c['doid']),'OMOP':sorted(c['omop']),
        'Sources':sorted(c['sources']),'Synonyms':syns,'Definitions':defs,'Xrefs':xrefs})

# crosswalk rows (all SNOMED<->DOID candidate edges, with merge flag + resolved ARI_IDs)
seen_e=set(); crosswalk=[]
for sn,do,basis in edges:
    key=(sn,do,basis)
    if key in seen_e: continue
    seen_e.add(key)
    sid=id_of_node(nS(sn)) if find(nS(sn)) in ids else None
    did=id_of_node(nD(do)) if find(nD(do)) in ids else None
    crosswalk.append({'SNOMED':sn,'DOID':do,'Basis':basis,
        'Merged':'Y' if (sn,do) in reciprocal else 'N',
        'SNOMED_ARI_ID':sid,'DOID_ARI_ID':did})

with open(os.path.join(OUTDIR,"_resolved.json"),"w") as f: json.dump(resolved,f)
with open(os.path.join(OUTDIR,"_crosswalk.json"),"w") as f: json.dump(crosswalk,f)

# stats
maxc=max((len(r['SNOMED'])+len(r['DOID']) for r in resolved))
print("Total concepts:",len(resolved),"| In ARI:",sum(1 for r in resolved if r['In_ARI']=='Y'))
print("w/ SNOMED:",sum(1 for r in resolved if r['SNOMED']),"| w/ DOID:",sum(1 for r in resolved if r['DOID']),
      "| w/ OMOP:",sum(1 for r in resolved if r['OMOP']))
print("w/ def:",sum(1 for r in resolved if r['Definitions']),"| w/ syn:",sum(1 for r in resolved if r['Synonyms']),
      "| w/ xref:",sum(1 for r in resolved if r['Xrefs']))
print("reciprocal 1:1 merges:",len(reciprocal),"| crosswalk edges:",len(crosswalk))
print("max concept (SNOMED+DOID):",maxc,"| multi-SNOMED:",sum(1 for r in resolved if len(r['SNOMED'])>1),
      "| multi-DOID:",sum(1 for r in resolved if len(r['DOID'])>1))
