// "Search by symptoms" modal. Loads the symptom index, DEDUPLICATES symptoms by
// name (merging the diseases that have each), and lets you jump to a disease.
(function () {
  let DATA = null, name2iri = {};
  const norm = s => String(s || '').trim().toLowerCase();
  function el(h){ const t = document.createElement('template'); t.innerHTML = h.trim(); return t.content.firstChild; }

  async function load(){
    const [syms, dz] = await Promise.all([api('/api/v2/symptoms'), api('/api/v2/diseases')]);
    name2iri = {};
    for (const d of dz) name2iri[norm(d.name)] = d.iri;
    const map = new Map();                       // dedup by symptom name
    for (const s of syms){
      const k = norm(s.name);
      if (!k) continue;
      let e = map.get(k);
      if (!e){ e = { name: s.name, diseases: [], obsolete: !!s.obsolete }; map.set(k, e); }
      for (const dn of (s.diseases || [])) if (!e.diseases.some(x => norm(x) === norm(dn))) e.diseases.push(dn);
      if (!s.obsolete) e.obsolete = false;
    }
    DATA = [...map.values()].sort((a, b) => a.name.localeCompare(b.name));
  }

  function render(filter){
    const q = norm(filter);
    const rows = DATA.filter(s => !q || norm(s.name).includes(q) || s.diseases.some(d => norm(d).includes(q)));
    $('#sym-count').textContent = rows.length + ' of ' + DATA.length + ' unique symptoms';
    $('#sym-list').innerHTML = rows.map(s => {
      const chips = s.diseases.map(d => {
        const iri = name2iri[norm(d)];
        return iri ? `<a href="#" class="sym-dz" data-iri="${esc(iri)}">${esc(d)}</a>` : `<span>${esc(d)}</span>`;
      }).join(', ');
      return `<div style="padding:8px 4px;border-bottom:1px solid var(--border)${s.obsolete ? ';opacity:.5' : ''}">
        <div style="font-weight:600">${esc(s.name)} <span class="badge badge-moderate">${s.diseases.length}</span></div>
        <div style="font-size:12px;color:var(--muted);margin-top:2px">${chips || '—'}</div></div>`;
    }).join('') || '<div class="empty-state" style="padding:16px">No symptoms match.</div>';
    $('#sym-list').querySelectorAll('.sym-dz').forEach(a => a.addEventListener('click', ev => {
      ev.preventDefault(); close();
      if (typeof selectDisease === 'function') selectDisease(a.dataset.iri);
    }));
  }

  function close(){ const o = $('#sym-overlay'); if (o) o.remove(); }

  async function open(){
    const m = el(`<div class="modal-overlay" id="sym-overlay"><div class="modal" style="max-width:640px;width:90%">
      <div class="modal-head"><h2>&#129657; Search by symptoms</h2><button class="hbtn" id="sym-close">✕</button></div>
      <div class="modal-body">
        <div class="field"><input id="sym-q" placeholder="Search a symptom or disease..."></div>
        <div id="sym-count" style="font-size:12px;color:var(--muted);margin-bottom:6px"></div>
        <div id="sym-list" style="max-height:60vh;overflow:auto"><div class="loading">Loading...</div></div>
      </div></div></div>`);
    document.body.appendChild(m);
    $('#sym-close').addEventListener('click', close);
    $('#sym-overlay').addEventListener('click', e => { if (e.target.id === 'sym-overlay') close(); });
    try { if (!DATA) await load(); render(''); }
    catch (e){ $('#sym-list').innerHTML = '<div class="empty-state">Error loading symptoms.</div>'; }
    $('#sym-q').addEventListener('input', e => render(e.target.value));
    $('#sym-q').focus();
  }

  function bind(){ const b = document.getElementById('symptom-search-btn'); if (b) b.addEventListener('click', open); }
  if (document.readyState !== 'loading') bind();
  else document.addEventListener('DOMContentLoaded', bind);
})();
