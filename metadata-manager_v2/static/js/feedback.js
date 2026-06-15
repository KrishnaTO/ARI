// Feedback panel: per-term comments saved to a server-side log file. Feedback is
// cleared at the next version release unless the author flags "keep after release".
// Opened from the Feedback box in the Record step of the disease story.

function renderFeedback(d, panel){
  let html = closeHeader('💬 Feedback');
  html += `<div class="fb-form">
      <textarea id="fb-message" rows="3" placeholder="Leave feedback about “${esc(d.name)}”…"></textarea>
      <div class="fb-form-row">
        <label class="fb-keep"><input type="checkbox" id="fb-keep"> Keep after release</label>
        <input id="fb-author" class="fb-author" placeholder="Your name" value="${esc(state.editor || '')}">
        <button class="hbtn primary" id="fb-submit">Post feedback</button>
      </div>
    </div>`;
  html += `<div class="section-label">Comments</div><div id="fb-list"><div class="loading">Loading…</div></div>`;
  panel.innerHTML = html;
  $('#fb-submit').addEventListener('click', () => submitFeedback(d));
  $('#fb-message').addEventListener('keydown', e => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) submitFeedback(d);
  });
  loadFeedbackList(d);
}

async function loadFeedbackList(d){
  let items = [];
  try { items = await api('/api/v2/feedback?disease=' + encodeURIComponent(d.iri)); }
  catch(e){ /* fall through to empty */ }
  const list = $('#fb-list');
  if (!list) return;
  if (!items.length){ list.innerHTML = '<div class="empty-state" style="padding:14px">No feedback yet — be the first to comment.</div>'; return; }
  list.innerHTML = items.map(feedbackItemHTML).join('');
  list.querySelectorAll('[data-fb-edit]').forEach(b =>
    b.addEventListener('click', () => editFeedback(d, items.find(x => x.id === b.dataset.fbEdit))));
  list.querySelectorAll('[data-fb-del]').forEach(b =>
    b.addEventListener('click', () => deleteFeedback(d, b.dataset.fbDel)));
}

function feedbackItemHTML(it){
  return `<div class="fb-item" data-fb="${esc(it.id)}">
    <div class="fb-msg">${esc(it.message)}</div>
    <div class="fb-meta"><span>${esc(it.author || 'anonymous')} &middot; ${esc(it.updated || it.created)}</span>
      ${it.keep ? '<span class="fb-pill">kept after release</span>' : ''}
      <span class="fb-actions"><button class="icon-btn" data-fb-edit="${esc(it.id)}" title="Edit">✎</button>`+
      `<button class="icon-btn danger" data-fb-del="${esc(it.id)}" title="Delete">🗑</button></span></div>
  </div>`;
}

async function submitFeedback(d){
  const message = $('#fb-message').value.trim();
  if (!message){ toast('Write some feedback first'); return; }
  const keep = $('#fb-keep').checked;
  state.editor = $('#fb-author').value.trim() || state.editor || 'curator';
  try {
    $('#fb-submit').disabled = true;
    await api('/api/v2/feedback', { method:'POST',
      body:{ disease: d.iri, term: d.name, message, keep, author: state.editor } });
    $('#fb-message').value = ''; $('#fb-keep').checked = false;
    await loadFeedbackList(d);
    toast('Feedback posted ✓');
  } catch (err){ toast('Failed: ' + err.message); }
  finally { const b = $('#fb-submit'); if (b) b.disabled = false; }
}

// Swap a feedback item for an inline editor.
function editFeedback(d, it){
  if (!it) return;
  const row = $(`.fb-item[data-fb="${CSS.escape(it.id)}"]`);
  if (!row) return;
  row.innerHTML = `<textarea class="fb-edit-msg" rows="3">${esc(it.message)}</textarea>
    <div class="fb-form-row">
      <label class="fb-keep"><input type="checkbox" class="fb-edit-keep" ${it.keep ? 'checked' : ''}> Keep after release</label>
      <span class="fb-actions"><button class="hbtn primary fb-edit-save">Save</button>
        <button class="hbtn fb-edit-cancel">Cancel</button></span>
    </div>`;
  row.querySelector('.fb-edit-cancel').addEventListener('click', () => loadFeedbackList(d));
  row.querySelector('.fb-edit-save').addEventListener('click', async () => {
    const message = row.querySelector('.fb-edit-msg').value.trim();
    const keep = row.querySelector('.fb-edit-keep').checked;
    if (!message){ toast('Message cannot be empty'); return; }
    try {
      await api('/api/v2/feedback/' + encodeURIComponent(it.id), {
        method:'PUT', body:{ message, keep, author: state.editor } });
      await loadFeedbackList(d);
      toast('Feedback updated ✓');
    } catch (err){ toast('Update failed: ' + err.message); }
  });
}

async function deleteFeedback(d, fid){
  if (!confirm('Delete this feedback comment?')) return;
  try {
    await api('/api/v2/feedback/' + encodeURIComponent(fid), { method:'DELETE' });
    await loadFeedbackList(d);
    toast('Feedback deleted ✓');
  } catch (err){ toast('Delete failed: ' + err.message); }
}
