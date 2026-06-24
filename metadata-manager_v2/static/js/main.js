// Bootstrap: load overview + the editable-field schema, then render the
// active tree. Runs last so every module's functions and wiring are ready.

async function init(){
  const o = await api('/api/v2/overview');
  $('#onto-meta').innerHTML =
    `Manager <b>${esc(o.app_version || '')}</b> &middot; <b>${esc(o.disease_count)}</b> disease(s) &middot; <b>${o.individuals}</b> individuals &middot; <b>${o.classes}</b> classes &middot; data v<b>${esc(o.version)}</b>`;
  if (!Object.keys(state.schema).length){ try { state.schema = await api('/api/v2/schema'); } catch(e){} }
  renderTab();
}

// ----------------------------------------------------------------- THEME
function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  try { localStorage.setItem('ari-theme', theme); } catch (e) {}
}
function initTheme() {
  const saved = (() => { try { return localStorage.getItem('ari-theme'); } catch (e) { return ''; } })();
  const pref = saved || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  applyTheme(pref);
}
document.getElementById('theme-toggle')?.addEventListener('click', () => {
  const cur = document.documentElement.getAttribute('data-theme');
  applyTheme(cur === 'dark' ? 'light' : 'dark');
});
initTheme();

init();
