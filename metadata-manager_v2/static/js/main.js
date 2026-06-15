// Bootstrap: load overview + the editable-field schema, then render the
// active tree. Runs last so every module's functions and wiring are ready.

async function init(){
  const o = await api('/api/v2/overview');
  $('#onto-meta').innerHTML =
    `<b>${esc(o.disease_count)}</b> disease(s) &middot; <b>${o.individuals}</b> individuals &middot; <b>${o.classes}</b> classes &middot; v<b>${esc(o.version)}</b>`;
  if (!Object.keys(state.schema).length){ try { state.schema = await api('/api/v2/schema'); } catch(e){} }
  renderTab();
}

init();
