// Editing: the global edit toggle, the disease-field editor, the per-category
// item CRUD (add / edit / delete) and the admin version-release dialog.

// ----------------------------------------------------------------- EDIT MODE
$('#edit-toggle').addEventListener('click', () => {
  if (!state.detail) return;
  state.editMode = !state.editMode;
  $('#edit-toggle').classList.toggle('active', state.editMode);
  $('#edit-toggle').innerHTML = state.editMode ? '✓ Done' : '✎ Edit';
  closeRightPanel();
  renderDetail(state.detail);
});

function fieldText(id, label, value){
  return `<div class="field"><label>${label}</label><input id="${id}" value="${esc(value)}"></div>`;
}
function fieldArea(id, label, value){
  return `<div class="field"><label>${label}</label><textarea id="${id}">${esc(value)}</textarea></div>`;
}

// Disease-level field editor (opens in the right panel, like the item editors)
function openDiseaseFieldEditor(d){
  state.activeBox = '__fields__';
  $('#layout').classList.add('split');
  $('#right-col').classList.add('open');
  $('#detail-pane').querySelectorAll('.box').forEach(b => b.classList.remove('active'));
  let html = `<button class="close-btn" onclick="closeRightPanel()">✕ Close</button>
    <div class="edit-form" style="padding:0"><h2>Edit fields: ${esc(d.name)}</h2>
    <p style="font-size:12px;color:var(--muted);margin:0 0 12px">IRI / ARI local id is fixed. Saving appends a changelog entry and writes the OWL file.</p>`;
  html += fieldText('f_name', 'Label', d.name);
  html += fieldArea('f_definition', 'Definition (markdown)', d.definition);
  html += fieldArea('f_synonyms', 'Synonyms (comma separated)', (d.synonyms||[]).join(', '));
  html += '<div class="field-grid">';
  html += fieldText('f_disease_category', 'Category', first(d.disease_category));
  html += fieldText('f_evidence_quality', 'Evidence quality', first(d.evidence_quality));
  html += fieldText('f_icd10', 'ICD-10 (comma separated)', (d.icd10||[]).join(', '));
  html += fieldText('f_snomed', 'SNOMED (comma separated)', (d.snomed||[]).join(', '));
  html += fieldText('f_omop', 'OMOP (comma separated)', (d.omop||[]).join(', '));
  html += fieldText('f_doid', 'DOID (comma separated)', (d.doid||[]).join(', '));
  html += fieldText('f_umls', 'UMLS (comma separated)', (d.umls||[]).join(', '));
  html += fieldText('f_mondo', 'MONDO (comma separated)', (d.mondo||[]).join(', '));
  html += fieldText('f_mesh', 'MeSH (comma separated)', (d.mesh||[]).join(', '));
  html += fieldText('f_nci', 'NCI (comma separated)', (d.nci||[]).join(', '));
  html += fieldText('f_prevalence_per_100k', 'Prevalence /100k', first(d.prevalence_per_100k));
  html += fieldText('f_prevalence_value', 'Estimated cases', first(d.prevalence_value));
  html += fieldText('f_incidence_rate', 'Incidence rate', first(d.incidence_rate));
  html += '</div>';
  html += fieldText('f_demographic_bias', 'Demographic bias', first(d.demographic_bias));
  html += fieldText('f_age_range', 'Age range', first(d.age_range));
  html += fieldArea('f_prevalence_desc', 'Prevalence description', first(d.prevalence_desc));
  html += fieldArea('f_def_source', 'Definition source (markdown)', first(d.def_source));
  html += `<div class="field field-row"><input type="checkbox" id="f_obsolete" ${d.obsolete?'checked':''}><label style="margin:0">Mark as obsolete</label></div>`;
  html += `<div class="field"><label>Editor name</label><input id="f_editor" value="${esc(state.editor)}"></div>`;
  html += `<div class="edit-actions"><button class="hbtn primary" id="save-btn">💾 Save changes</button>
    <button class="hbtn" onclick="closeRightPanel()">Cancel</button></div></div>`;
  $('#right-panel-content').innerHTML = html;
  $('#save-btn').addEventListener('click', saveEdits);
}

async function saveEdits(){
  const v = id => $('#'+id)?.value ?? '';
  const changes = {
    name: v('f_name'), definition: v('f_definition'),
    synonyms: v('f_synonyms'), disease_category: v('f_disease_category'),
    evidence_quality: v('f_evidence_quality'), icd10: v('f_icd10'), snomed: v('f_snomed'),
    doid: v('f_doid'), umls: v('f_umls'), mondo: v('f_mondo'),
    omop: v('f_omop'), mesh: v('f_mesh'), nci: v('f_nci'),
    prevalence_per_100k: v('f_prevalence_per_100k'), prevalence_value: v('f_prevalence_value'),
    incidence_rate: v('f_incidence_rate'), demographic_bias: v('f_demographic_bias'),
    age_range: v('f_age_range'), prevalence_desc: v('f_prevalence_desc'),
    def_source: v('f_def_source'),
    obsolete: $('#f_obsolete').checked ? 'true' : 'false',
  };
  state.editor = v('f_editor') || 'curator';
  try {
    $('#save-btn').disabled = true; $('#save-btn').textContent = 'Saving...';
    const updated = await api(`/api/v2/disease/${encodeURIComponent(state.activeIri)}`, {
      method: 'PUT', body: { changes, editor: state.editor }
    });
    state.detail = updated;
    closeRightPanel();
    renderDetail(updated);
    renderTab();
    init();
    toast('Saved ✓ changelog updated');
  } catch (err){
    toast('Save failed: ' + err.message);
    $('#save-btn').disabled = false; $('#save-btn').textContent = '💾 Save changes';
  }
}

// ----------------------------------------------------------------- ITEM CRUD (data items)
function itemSecondary(category, it){
  const map = {
    symptoms:'likelihood', environmental:'likelihood', antibodies:'frequency',
    genetic:'risk_effect', treatments:'type', etiology:'origin_type',
    biomarkers:'diagnostic_use', pathophysiology:'category',
  };
  return first(it[map[category] || 'relevance']);
}

function renderItemEditor(d, category, panel){
  const spec = state.schema[category];
  const items = d[DETAIL_KEY[category]] || [];
  let html = `<button class="close-btn" onclick="closeRightPanel()">✕ Close</button><h2>Manage ${esc(spec.label)} items</h2>`;
  html += panelDescHTML(category);
  html += `<div style="display:flex;gap:8px;margin-bottom:10px">`+
    `<button class="hbtn primary" id="item-add">＋ Add ${esc(spec.label)}</button>`+
    `<button class="hbtn" id="item-view">← Back to details</button></div>`;
  if (!items.length){
    html += '<div class="empty-state">No items yet — use “Add”.</div>';
  } else {
    html += `<table class="data-table"><thead><tr><th>${esc(spec.label)}</th><th style="width:74px"></th></tr></thead><tbody>`;
    items.forEach((it, i) => {
      const sec = itemSecondary(category, it);
      html += `<tr class="${it.obsolete?'obsolete':''}"><td><strong>${esc(it.name)}</strong>${it.obsolete?' <span class="obsolete-tag">(obsolete)</span>':''}`+
        (sec ? `<div style="font-size:11px;color:var(--muted)">${esc(sec)}</div>` : '')+
        `</td><td style="white-space:nowrap"><button class="icon-btn" data-edit="${i}" title="Edit">✎</button> <button class="icon-btn danger" data-del="${i}" title="Delete">🗑</button></td></tr>`;
    });
    html += `</tbody></table>`;
  }
  panel.innerHTML = html;
  $('#item-add').addEventListener('click', () => openItemModal(category, null));
  $('#item-view').addEventListener('click', () => renderReadView(d, category, panel));
  panel.querySelectorAll('[data-edit]').forEach(b => b.addEventListener('click', () => openItemModal(category, items[+b.dataset.edit])));
  panel.querySelectorAll('[data-del]').forEach(b => b.addEventListener('click', () => deleteItem(category, items[+b.dataset.del])));
}

function openItemModal(category, item){
  const spec = state.schema[category];
  const isEdit = !!item;
  let fields = '';
  for (const f of spec.fields){
    const cur = item ? first(item[f.read]) : '';
    const fid = 'itf_' + f.key;
    if (f.type === 'checkbox'){
      fields += `<div class="field field-row"><input type="checkbox" id="${fid}" ${item && item.obsolete ? 'checked':''}><label style="margin:0">${esc(f.label)}</label></div>`;
    } else if (f.type === 'select'){
      const opts = (f.options||[]).map(o => `<option ${String(cur)===o?'selected':''}>${esc(o)}</option>`).join('');
      fields += `<div class="field"><label>${esc(f.label)}</label><select id="${fid}"><option value=""></option>${opts}</select></div>`;
    } else if (f.type === 'area'){
      fields += `<div class="field"><label>${esc(f.label)}</label><textarea id="${fid}">${esc(cur)}</textarea></div>`;
    } else {
      const t = f.type === 'number' ? 'number' : 'text';
      fields += `<div class="field"><label>${esc(f.label)}</label><input type="${t}" id="${fid}" value="${esc(cur)}"></div>`;
    }
  }
  const html = `<div class="modal-overlay" id="item-overlay"><div class="modal">
    <div class="modal-head"><h2>${isEdit?'Edit':'Add'} ${esc(spec.label)}</h2><button class="hbtn" id="item-cancel">✕</button></div>
    <div class="modal-body">${fields}
      <div class="field"><label>Editor name</label><input id="itf_editor" value="${esc(state.editor)}"></div>
      <div class="edit-actions"><button class="hbtn primary" id="item-save">💾 Save</button>
        <button class="hbtn" id="item-cancel2">Cancel</button></div>
    </div></div></div>`;
  document.body.insertAdjacentHTML('beforeend', html);
  const close = () => $('#item-overlay')?.remove();
  $('#item-cancel').addEventListener('click', close);
  $('#item-cancel2').addEventListener('click', close);
  $('#item-overlay').addEventListener('click', e => { if (e.target.id === 'item-overlay') close(); });
  $('#item-save').addEventListener('click', () => saveItem(category, item));
}

async function saveItem(category, item){
  const spec = state.schema[category];
  const values = {};
  for (const f of spec.fields){
    const el = $('#itf_' + f.key);
    if (!el) continue;
    values[f.key] = f.type === 'checkbox' ? el.checked : el.value;
  }
  state.editor = $('#itf_editor')?.value || 'curator';
  try {
    $('#item-save').disabled = true; $('#item-save').textContent = 'Saving...';
    let updated;
    if (item){
      updated = await api(`/api/v2/item/${encodeURIComponent(item.iri)}`, {
        method:'PUT', body:{ category, changes: values, disease: state.activeIri, editor: state.editor }});
    } else {
      updated = await api(`/api/v2/disease/${encodeURIComponent(state.activeIri)}/item`, {
        method:'POST', body:{ category, values, editor: state.editor }});
    }
    $('#item-overlay')?.remove();
    afterItemChange(updated, category);
    toast(item ? 'Item updated ✓' : 'Item added ✓');
  } catch (err){
    toast('Save failed: ' + err.message);
    $('#item-save').disabled = false; $('#item-save').textContent = '💾 Save';
  }
}

async function deleteItem(category, item){
  if (!confirm(`Delete “${item.name}”? This removes it from the ontology.`)) return;
  try {
    const updated = await api(`/api/v2/item/${encodeURIComponent(item.iri)}`, {
      method:'DELETE', body:{ category, disease: state.activeIri, editor: state.editor }});
    afterItemChange(updated, category);
    toast('Item deleted ✓');
  } catch (err){ toast('Delete failed: ' + err.message); }
}

function afterItemChange(updated, category){
  state.detail = updated;
  renderDetail(updated);
  init();
  state.activeBox = category;
  $('#layout').classList.add('split');
  $('#right-col').classList.add('open');
  $('#detail-pane').querySelectorAll('.box').forEach(b => b.classList.toggle('active', b.dataset.box === category));
  renderItemEditor(updated, category, $('#right-panel-content'));
}

