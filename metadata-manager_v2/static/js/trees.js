// Left-panel navigation: the three tree views (alphabetical / tissue / symptoms),
// tab switching, tree-click handling, and header search.

function twisty(collapsed, leaf){
  return `<span class="twisty${leaf ? ' leaf' : ''}">${leaf ? '' : (collapsed ? '▸' : '▾')}</span>`;
}

function renderAlphabetical(){
  showLoading('#tree-pane');
  api('/api/v2/tree/alphabetical').then(roots => {
    const node = (n) => {
      const kids = n.children || [];
      const hasKids = kids.length > 0;
      const sel = state.activeIri === n.iri ? ' selected' : '';
      const obs = n.obsolete ? ' obsolete' : '';
      const obsTag = n.obsolete ? ' <span class="obsolete-tag">(obsolete)</span>' : '';
      let h = `<div class="node${hasKids ? ' collapsed' : ''}">`;
      h += `<div class="node-row disease-row${sel}${obs}" data-iri="${esc(n.iri)}">${twisty(true, !hasKids)}📘 <span>${esc(n.name)}</span>${obsTag}</div>`;
      if (hasKids){ h += `<div class="children">${kids.map(node).join('')}</div>`; }
      h += `</div>`;
      return h;
    };
    $('#tree-pane').innerHTML = roots.length ? roots.map(node).join('') : '<div class="empty-state">No diseases.</div>';
  }).catch(() => $('#tree-pane').innerHTML = '<div class="empty-state">Error loading list.</div>');
}

function renderTissue(){
  showLoading('#tree-pane');
  api('/api/v2/tree/tissue').then(tree => {
    const node = (n) => {
      const subClasses = n.children || [];
      const diseases = n.diseases || [];
      const hasKids = subClasses.length > 0 || diseases.length > 0;
      const ari = n.ari_id ? `<span class="ari-chip">${esc(n.ari_id)}</span>` : '';
      let h = `<div class="node">`;
      h += `<div class="node-row tissue" data-toggle="1">${twisty(false, !hasKids)}🧬 <span>${esc(n.name)}</span>${ari}</div>`;
      if (hasKids){
        h += `<div class="children">`;
        h += subClasses.map(node).join('');
        for (const d of diseases){
          const sel = state.activeIri === d.iri ? ' selected' : '';
          const obs = d.obsolete ? ' obsolete' : '';
          const obsTag = d.obsolete ? ' <span class="obsolete-tag">(obsolete)</span>' : '';
          h += `<div class="node"><div class="node-row disease-row${sel}${obs}" data-iri="${esc(d.iri)}">${twisty(true, true)}📘 <span>${esc(d.name)}</span>${obsTag}</div></div>`;
        }
        h += `</div>`;
      }
      return h;
    };
    $('#tree-pane').innerHTML = tree.length ? tree.map(node).join('') : '<div class="empty-state">No tissue hierarchy.</div>';
  }).catch(() => $('#tree-pane').innerHTML = '<div class="empty-state">No tissue hierarchy available.</div>');
}

function renderSymptomsView(){
  showLoading('#tree-pane');
  api('/api/v2/symptoms').then(list => {
    if (!list.length){ $('#tree-pane').innerHTML = '<div class="empty-state">No symptoms in dataset.</div>'; return; }
    let html = '<div style="padding:4px">';
    html += `<div style="font-size:11px;color:var(--muted);padding:2px 6px 6px">${list.length} symptoms across diseases</div>`;
    for (const s of list){
      const lik = (s.likelihood || '').toLowerCase();
      let badge = 'badge-moderate';
      if (lik.includes('very common') || lik.includes('common')) badge = 'badge-common';
      if (lik.includes('rare') || lik.includes('weak')) badge = 'badge-rare';
      const obs = s.obsolete ? ' style="opacity:.5"' : '';
      const owner = s.diseases?.[0];
      html += `<div class="node-row" data-symptom-owner="${esc(s.diseases?.length ? owner : '')}"${obs} title="${esc((s.diseases||[]).join(', '))}">`;
      html += `<span class="badge ${badge}">${esc(s.likelihood || '')}</span> <span>${esc(s.name)}</span></div>`;
    }
    html += '</div>';
    $('#tree-pane').innerHTML = html;
  }).catch(() => $('#tree-pane').innerHTML = '<div class="empty-state">Error loading symptoms.</div>');
}

function renderTab(){
  if (state.activeTab === 'alphabetical') renderAlphabetical();
  else if (state.activeTab === 'tissue') renderTissue();
  else if (state.activeTab === 'symptoms') renderSymptomsView();
}

document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t === tab));
    state.activeTab = tab.dataset.view;
    renderTab();
  });
});

// Tree interactions: twisty toggles, disease rows select.
$('#tree-pane').addEventListener('click', e => {
  const tw = e.target.closest('.twisty');
  if (tw && !tw.classList.contains('leaf')){
    const nodeEl = tw.closest('.node');
    if (nodeEl) nodeEl.classList.toggle('collapsed');
    e.stopPropagation();
    return;
  }
  const tissue = e.target.closest('[data-toggle]');
  if (tissue){
    const nodeEl = tissue.closest('.node');
    if (nodeEl) nodeEl.classList.toggle('collapsed');
    return;
  }
  const dis = e.target.closest('[data-iri]');
  if (dis){ selectDisease(dis.dataset.iri); return; }
  const sym = e.target.closest('[data-symptom-owner]');
  if (sym && sym.dataset.symptomOwner){ selectDisease(sym.dataset.symptomOwner); }
});

// ----------------------------------------------------------------- SEARCH
let searchTimer;
$('#search').addEventListener('input', e => {
  clearTimeout(searchTimer);
  const q = e.target.value.trim();
  if (!q){ $('#search-results').classList.add('hidden'); return; }
  searchTimer = setTimeout(async () => {
    const rs = await api('/api/v2/search?q=' + encodeURIComponent(q));
    if (!rs.length){ $('#search-results').innerHTML = '<div class="node-row" style="padding:8px;color:var(--muted)">No matches</div>'; }
    else {
      $('#search-results').innerHTML = rs.slice(0, 20).map(r =>
        `<div class="node-row" data-iri="${esc(r.iri)}" style="border-bottom:1px solid var(--border)${r.obsolete?';opacity:.5':''}">${esc(r.name)} <span class="sub">${esc(r.local_name)}</span></div>`
      ).join('');
    }
    $('#search-results').classList.remove('hidden');
  }, 200);
});
$('#search-results').addEventListener('click', e => {
  const r = e.target.closest('[data-iri]');
  if (r){ selectDisease(r.dataset.iri); $('#search-results').classList.add('hidden'); $('#search').value = ''; }
});
$('#search').addEventListener('blur', () => setTimeout(() => $('#search-results').classList.add('hidden'), 200));
