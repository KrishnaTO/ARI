// "Search by symptoms" — multi-selection board. Pick one or more (deduplicated)
// symptoms; diseases are ranked by how many of the selected symptoms they have.
(function () {
  let DATA = null;            // [{name, key, diseases:[name]}]
  let byKey = new Map();      // key -> symptom
  let name2iri = {};          // disease name(norm) -> iri
  let selected = new Map();   // key -> display name
  let requireAll = false;

  const norm = s => String(s || '').trim().toLowerCase();
  function el(h){ const t = document.createElement('template'); t.innerHTML = h.trim(); return t.content.firstChild; }

  async function load(){
    const [syms, dz] = await Promise.all([api('/api/v2/symptoms'), api('/api/v2/diseases')]);
    name2iri = {};
    for (const d of dz) name2iri[norm(d.name)] = d.iri;
    const map = new Map();                      // dedup symptoms by name
    for (const s of syms){
      const k = norm(s.name);
      if (!k) continue;
      let e = map.get(k);
      if (!e){ e = { name: s.name, key: k, diseases: [] }; map.set(k, e); }
      for (const dn of (s.diseases || [])) if (!e.diseases.some(x => norm(x) === norm(dn))) e.diseases.push(dn);
    }
    DATA = [...map.values()].sort((a, b) => a.name.localeCompare(b.name));
    byKey = map;
  }

  function toggle(key, name){
    if (selected.has(key)) selected.delete(key); else selected.set(key, name);
    renderChips(); renderList($('#sym-q').value); renderResults();
  }

  function renderChips(){
    const wrap = $('#sym-chips');
    if (!selected.size){ wrap.innerHTML = '<span style="font-size:12px;color:var(--muted)">No symptoms selected — pick some on the left.</span>'; return; }
    wrap.innerHTML = [...selected].map(([k, n]) =>
      `<span class="badge badge-common" style="cursor:pointer" data-rm="${esc(k)}">${esc(n)} ✕</span>`).join(' ');
    wrap.querySelectorAll('[data-rm]').forEach(b => b.addEventListener('click', () => toggle(b.dataset.rm, '')));
  }

  function renderList(filter){
    const q = norm(filter);
    const rows = DATA.filter(s => !q || s.key.includes(q));
    $('#sym-list').innerHTML = rows.map(s => {
      const on = selected.has(s.key);
      return `<label class="sym-pick" style="display:flex;gap:8px;align-items:center;padding:5px 6px;border-radius:6px;cursor:pointer;${on ? 'background:var(--accent-soft)' : ''}">
        <input type="checkbox" data-k="${esc(s.key)}" ${on ? 'checked' : ''}>
        <span style="flex:1">${esc(s.name)}</span>
        <span class="badge badge-moderate">${s.diseases.length}</span></label>`;
    }).join('') || '<div class="empty-state" style="padding:12px">No symptoms match.</div>';
    $('#sym-list').querySelectorAll('input[data-k]').forEach(c =>
      c.addEventListener('change', () => { const s = byKey.get(c.dataset.k); toggle(s.key, s.name); }));
  }

  function results(){
    const sel = [...selected.keys()];
    if (!sel.length) return [];
    const counts = {};
    for (const k of sel){
      for (const dn of (byKey.get(k)?.diseases || [])){
        const dk = norm(dn);
        (counts[dk] || (counts[dk] = { name: dn, count: 0 })).count++;
      }
    }
    let arr = Object.values(counts);
    if (requireAll) arr = arr.filter(x => x.count === sel.length);
    return arr.sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
  }

  function renderResults(){
    const sel = selected.size;
    const arr = results();
    $('#sym-res-count').textContent = sel ? `${arr.length} disease${arr.length === 1 ? '' : 's'} (of ${sel} symptom${sel === 1 ? '' : 's'})` : '';
    if (!sel){ $('#sym-results').innerHTML = '<div class="empty-state" style="padding:12px">Select symptoms to see matching diseases.</div>'; return; }
    $('#sym-results').innerHTML = arr.map(d => {
      const iri = name2iri[norm(d.name)];
      const nm = iri ? `<a href="#" class="sym-dz" data-iri="${esc(iri)}">${esc(d.name)}</a>` : esc(d.name);
      const full = d.count === sel;
      return `<div style="display:flex;justify-content:space-between;gap:8px;padding:6px 4px;border-bottom:1px solid var(--border)">
        <span>${nm}</span>
        <span class="badge ${full ? 'badge-common' : 'badge-moderate'}" title="${d.count} of ${sel} selected symptoms">${d.count}/${sel}</span></div>`;
    }).join('') || '<div class="empty-state" style="padding:12px">No disease has all selected symptoms.</div>';
    $('#sym-results').querySelectorAll('.sym-dz').forEach(a => a.addEventListener('click', ev => {
      ev.preventDefault(); close(); if (typeof selectDisease === 'function') selectDisease(a.dataset.iri);
    }));
  }

  function close(){ const o = $('#sym-overlay'); if (o) o.remove(); }

  async function open(){
    selected = new Map(); requireAll = false;
    const m = el(`<div class="modal-overlay" id="sym-overlay"><div class="modal" style="max-width:820px;width:94%">
      <div class="modal-head"><h2>&#129657; Search diseases by symptoms</h2><button class="hbtn" id="sym-close">✕</button></div>
      <div class="modal-body">
        <div id="sym-chips" style="display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-bottom:10px;min-height:24px"></div>
        <div style="display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:14px">
          <div>
            <div class="field" style="margin-bottom:6px"><input id="sym-q" placeholder="Filter symptoms..."></div>
            <div id="sym-list" style="max-height:52vh;overflow:auto;border:1px solid var(--border);border-radius:6px;padding:4px"><div class="loading">Loading...</div></div>
          </div>
          <div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
              <label style="font-size:12px;color:var(--muted)"><input type="checkbox" id="sym-all"> Require all selected</label>
              <span id="sym-res-count" style="font-size:12px;color:var(--muted)"></span>
            </div>
            <div id="sym-results" style="max-height:52vh;overflow:auto;border:1px solid var(--border);border-radius:6px;padding:4px"></div>
          </div>
        </div>
      </div></div></div>`);
    document.body.appendChild(m);
    $('#sym-close').addEventListener('click', close);
    $('#sym-overlay').addEventListener('click', e => { if (e.target.id === 'sym-overlay') close(); });
    $('#sym-all').addEventListener('change', e => { requireAll = e.target.checked; renderResults(); });
    try {
      if (!DATA) await load();
      renderChips(); renderList(''); renderResults();
      $('#sym-q').addEventListener('input', e => renderList(e.target.value));
      $('#sym-q').focus();
    } catch (e){ $('#sym-list').innerHTML = '<div class="empty-state">Error loading symptoms.</div>'; }
  }

  function bind(){ const b = document.getElementById('symptom-search-btn'); if (b) b.addEventListener('click', open); }
  if (document.readyState !== 'loading') bind();
  else document.addEventListener('DOMContentLoaded', bind);
})();
