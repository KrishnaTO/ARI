"""List the terms that still need a curator verdict: database conflicts, related-only
synonyms, qualified names, and ARI strings whose verdict changed since the last report."""
import json, sys
c = json.load(open(sys.argv[1], encoding='utf-8'))
n = 0
out = open(sys.argv[2], 'w', encoding='utf-8')
for a, d in c.items():
    for k, t in d['terms'].items():
        if t['manual'] or t['verdict'] == 'preferred':
            continue
        oldv = {o['verdict'] for o in t['old']}
        changed = t['in_ari'] and t['old'] and t['verdict'] not in oldv
        if any(f.startswith('conflict') or f in ('related-only', 'no-evidence', 'qualifier') for f in t['flags']) or changed:
            n += 1
            ev = '; '.join(dict.fromkeys(
                (e['src'] + ' ' + e['role'] + (f"[{e['id']} {e['name']}]" if e['role'] in ('descendant', 'descendant_synonym', 'parent') else '')
                 + ('(' + t['source_kinds'][e['id']] + ' term)' if e['id'] in t['source_kinds'] else ''))
                for e in t['evidence']))
            out.write('\t'.join([str(n), a, d['label'], k, t['names'][0], t['verdict'], ','.join(t['flags']) + (',changed-from:' + '/'.join(oldv) if changed else ''), ev[:300]]) + '\n')
print(n)
