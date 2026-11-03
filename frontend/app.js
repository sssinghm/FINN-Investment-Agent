/* FINN prototype — presentation and interaction layer. */
const state = {
  view: 'briefing', days: 1, feed: [], companies: [], filteredCompanies: [], rules: null,
  feedSourceMode: 'demo', lastWarning: null, portfolioLoaded: false, researchBusy: false,
};
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (ch) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const fmtINR = (value) => value == null || !Number.isFinite(Number(value)) ? '—' : '₹' + Number(value).toLocaleString('en-IN', {maximumFractionDigits:2, minimumFractionDigits:2});
const fmtNumber = (value) => value == null || !Number.isFinite(Number(value)) ? '—' : Number(value).toLocaleString('en-IN', {maximumFractionDigits:0});
const fmtPercent = (value) => value == null || !Number.isFinite(Number(value)) ? '—' : `${Number(value) >= 0 ? '+' : ''}${Number(value).toFixed(2)}%`;
const categoryLabel = (value) => ({'M&A':'M&A','fund_raise':'Fund raising','management_change':'Management','litigation':'Litigation','insider_trading':'Insider trading','earnings_call':'Earnings call','investor_meetings':'Investor meeting','credit_rating':'Credit rating','dividend':'Dividend','bonus_split':'Bonus / split','press_release':'Press release','postal_ballot':'Postal ballot','agm_egm':'AGM / EGM','market_alert':'Market alert','capex':'Capex','unclassified':'Routine filing','results':'Results','pledging':'Pledging'}[value] || (value || 'Announcement').replaceAll('_',' '));
const symbolForCategory = (category) => ({results:'▤','M&A':'↗',capex:'⌁',management_change:'♙',litigation:'⚖',market_alert:'⌁',dividend:'◈',credit_rating:'≋',fund_raise:'＋',earnings_call:'◖',press_release:'↗',unclassified:'▧'}[category] || '◈');

async function api(path, options = {}) {
  const response = await fetch(path, {headers: {'Content-Type':'application/json', ...(options.headers || {})}, ...options});
  let payload;
  try { payload = await response.json(); } catch { payload = {}; }
  if (!response.ok) throw new Error(payload.detail || `Request failed (${response.status})`);
  return payload;
}

function toast(message, error = false) {
  const el = $('#toast');
  el.textContent = message;
  el.style.borderColor = error ? '#67433d' : '#3b4b36';
  el.style.background = error ? '#2b1e1b' : '#1d271b';
  el.style.color = error ? '#f0b5ab' : '#d0e4c2';
  el.classList.add('show');
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => el.classList.remove('show'), 3200);
}

function setView(view) {
  if (!['briefing','research','watchlist'].includes(view)) view = 'briefing';
  state.view = view;
  $$('.view').forEach(el => el.classList.toggle('active', el.id === `view-${view}`));
  $$('[data-view]').forEach(el => el.classList.toggle('active', el.dataset.view === view && (el.classList.contains('nav-item') || el.classList.contains('mobile-nav-item'))));
  const labels = {briefing:'Briefing', research:'Research', watchlist:'Watchlist'};
  $('#breadcrumb-current').textContent = labels[view];
  document.title = `FINN — ${labels[view]}`;
  if (view === 'watchlist' && !state.companies.length) loadCompanies();
  window.scrollTo({top:0, behavior:'smooth'});
}

function formatDate(dateStr, withTime = true) {
  if (!dateStr) return 'Time not provided';
  const date = new Date(dateStr);
  if (Number.isNaN(date.getTime())) return String(dateStr);
  const datePart = new Intl.DateTimeFormat('en-IN', {day:'2-digit', month:'short', year:'numeric', timeZone:'Asia/Kolkata'}).format(date);
  if (!withTime) return datePart;
  const timePart = new Intl.DateTimeFormat('en-IN', {hour:'2-digit', minute:'2-digit', hour12:false, timeZone:'Asia/Kolkata'}).format(date);
  return `${datePart} · ${timePart} IST`;
}
function relativeTime(dateStr) {
  if (!dateStr) return 'Time unavailable';
  const date = new Date(dateStr); if (Number.isNaN(date.getTime())) return String(dateStr);
  const minutes = Math.max(0, Math.round((Date.now() - date.getTime()) / 60000));
  if (minutes < 1) return 'Just now'; if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes/60); if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours/24); return `${days}d ago`;
}
function priorityClass(priority) { return String(priority || 'Routine').toLowerCase().replace(/[^a-z]/g,''); }
function companyInitial(name='') { return name.split(/\s+/).map(s=>s.replace(/[^A-Za-z]/g,'')).filter(Boolean).slice(0,2).map(s=>s[0]).join('').toUpperCase() || 'F'; }
function titleCase(s='') { return s.replaceAll('_',' ').replace(/\b\w/g, c=>c.toUpperCase()); }

async function init() {
  const now = new Date();
  $('#current-date').textContent = new Intl.DateTimeFormat('en-GB', {day:'2-digit',month:'short',year:'numeric',timeZone:'Asia/Kolkata'}).format(now).toUpperCase();
  bindInteractions();
  await Promise.allSettled([loadHealth(), loadCompanies(), loadFeed(), loadRules()]);
  buildSectorMix();
  populateTickerOptions();
}

function bindInteractions() {
  $$('[data-view]').forEach(button => button.addEventListener('click', () => {
    const view = button.dataset.view;
    if (button.dataset.ticker) selectCompanyForResearch(button.dataset.ticker);
    else setView(view);
  }));
  $$('.segment').forEach(button => button.addEventListener('click', () => {
    $$('.segment').forEach(b=>b.classList.toggle('active', b===button));
    state.days = Number(button.dataset.days || 1); loadFeed();
  }));
  $('#refresh-feed').addEventListener('click', async () => { $('#refresh-feed').textContent='…'; await loadFeed(true); $('#refresh-feed').textContent='↻'; });
  $('#refresh-portfolio').addEventListener('click', async () => { await Promise.allSettled([loadCompanies(true), loadHealth(), loadFeed(true)]); toast('Portfolio and feed refreshed.'); });
  $('#dismiss-banner').addEventListener('click', () => $('#demo-banner').classList.add('hidden'));
  $('#feed-search').addEventListener('input', renderFeed);
  $('#priority-filter').addEventListener('change', renderFeed);
  $('#category-filter').addEventListener('change', renderFeed);
  $('#clear-filters').addEventListener('click', () => { $('#feed-search').value=''; $('#priority-filter').value='all'; $('#category-filter').value='all'; renderFeed(); });
  $('#research-form').addEventListener('submit', runResearch);
  $$('.prompt-chip').forEach(button => button.addEventListener('click', () => {
    $('#research-question').value = button.dataset.question;
    $$('.prompt-chip').forEach(b=>b.classList.toggle('active', b===button));
    $('#research-question').focus();
  }));
  $('#watchlist-search').addEventListener('input', renderCompanyGrid);
  $('#price-range').addEventListener('input', () => $('#price-range-value').textContent = `±${Number($('#price-range').value).toFixed(1)}%`);
  $('#volume-range').addEventListener('input', () => $('#volume-range-value').textContent = `${Number($('#volume-range').value).toFixed(2)}×`);
  $('#alert-settings-form').addEventListener('submit', saveRules);
  $('#test-alerts').addEventListener('click', previewAlerts);
  $('#modal-close').addEventListener('click', closeModal);
  $('#detail-modal').addEventListener('click', e => { if (e.target === $('#detail-modal')) closeModal(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });
  $('#help-button').addEventListener('click', showAbout);
}

async function loadHealth() {
  try {
    const health = await api('/api/health');
    const coverage = health.research_coverage || {};
    $('#connection-label').textContent = 'Source-aware mode';
    $('#connection-caption').textContent = coverage.document_count ? `${coverage.document_count} documents indexed` : 'Waiting for source documents';
  } catch (err) {
    $('#connection-label').textContent = 'Local mode';
    $('#connection-caption').textContent = 'API needs attention';
    $('#connection-dot').classList.remove('live');
    $('#connection-dot').classList.add('demo');
  }
}

async function loadCompanies(showToast = false) {
  try {
    const result = await api('/api/companies');
    state.companies = result.items || [];
    state.filteredCompanies = [...state.companies];
    renderMiniPortfolio(); renderCompanyGrid(); buildSectorMix(); populateTickerOptions();
    state.portfolioLoaded = true;
  } catch (err) {
    toast(`Could not load portfolio: ${err.message}`, true);
  }
  if (showToast) toast('Company list refreshed.');
}

function renderMiniPortfolio() {
  const root = $('#mini-portfolio');
  const picks = state.companies.filter(c=>['TCS','RELIANCE','HDFCBANK','INFY','BHARTIARTL','SUNPHARMA'].includes(c.ticker));
  root.innerHTML = picks.map(c=>`<div class="mini-company" role="button" tabindex="0" data-ticker="${esc(c.ticker)}" title="Research ${esc(c.name)}"><span class="company-monogram">${esc(companyInitial(c.name))}</span><span class="mini-company-copy"><strong>${esc(c.name)}</strong><small>${esc(c.sector)}</small></span><span class="mini-change neutral">↗</span></div>`).join('');
  $$('.mini-company',root).forEach(el=>{
    const go=()=>selectCompanyForResearch(el.dataset.ticker);
    el.addEventListener('click',go); el.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();go();}});
  });
}

function renderCompanyGrid() {
  const q = ($('#watchlist-search')?.value || '').trim().toLowerCase();
  const list = state.companies.filter(c=>!q || c.name.toLowerCase().includes(q) || c.ticker.toLowerCase().includes(q) || c.sector.toLowerCase().includes(q));
  const root = $('#company-grid');
  if (!root) return;
  if (!list.length) { root.innerHTML='<div class="empty-state" style="grid-column:1/-1"><h3>No matching companies</h3><p>Try a ticker or a sector name.</p></div>'; return; }
  root.innerHTML = list.map(c=>`<article class="company-card"><span class="company-monogram">${esc(companyInitial(c.name))}</span><div class="company-card-main"><strong>${esc(c.name)}</strong><small>${esc(c.ticker)} · ${esc(c.sector)}</small></div><div class="company-card-end"><button aria-label="Research ${esc(c.name)}" title="Research company" data-research-ticker="${esc(c.ticker)}">↗</button></div></article>`).join('');
  $$('[data-research-ticker]',root).forEach(button=>button.addEventListener('click',()=>selectCompanyForResearch(button.dataset.researchTicker)));
}

function populateTickerOptions() {
  $('#ticker-options').innerHTML = state.companies.map(c=>`<option value="${esc(c.ticker)}">${esc(c.name)}</option>`).join('');
}

function buildSectorMix() {
  const root = $('#sector-mix'); if (!root || !state.companies.length) return;
  const map = new Map(); state.companies.forEach(c=>map.set(c.sector,(map.get(c.sector)||0)+1));
  const values = [...map.entries()].sort((a,b)=>b[1]-a[1]); const max = Math.max(...values.map(x=>x[1]));
  root.innerHTML = values.map(([sector,count])=>`<div class="sector-row"><span title="${esc(sector)}">${esc(sector)}</span><div class="sector-track"><span style="width:${Math.max(12,count/max*100)}%"></span></div><b>${count}</b></div>`).join('');
}

async function loadFeed(force = false) {
  $('#feed-result-count').textContent = 'Refreshing signal feed…';
  if (force) state._lastFeedRefresh = Date.now();
  try {
    const result = await api(`/api/feed?days=${state.days}`);
    state.feed = result.items || [];
    state.feedSourceMode = result.source_mode || 'demo'; state.lastWarning = result.warning || null;
    renderFeed(); updateSourceStatus(result); updateStats(result); updateBanner(result);
    $('#last-updated').textContent = `Checked ${relativeTime(result.updated_at)}`;
    $('#nav-feed-count').textContent = String(state.feed.length).padStart(2,'0');
  } catch (err) {
    state.feed = [];
    $('#feed-list').innerHTML = '';
    $('#feed-result-count').textContent = 'Feed unavailable';
    $('#feed-empty').classList.remove('hidden');
    $('#feed-empty h3').textContent = 'Could not load the feed';
    $('#feed-empty p').textContent = 'Check that the FINN backend is running, then refresh the feed.';
    toast(`Feed error: ${err.message}`, true);
  }
}

function updateSourceStatus(result) {
  const demo = result.source_mode !== 'live';
  $('#connection-dot').classList.toggle('live', !demo);
  $('#connection-dot').classList.toggle('demo', demo);
  $('#connection-label').textContent = demo ? 'Illustrative mode' : 'NSE feed connected';
  $('#connection-caption').textContent = demo ? 'Live source unavailable' : 'Read-only public feed';
  $('#stat-source').textContent = demo ? 'Demo' : 'NSE live';
  $('#stat-source-sub').textContent = demo ? 'illustrative events' : 'exchange feed responding';
}
function updateStats(result) {
  $('#stat-signals').textContent = String(result.count ?? state.feed.length).padStart(2,'0');
  $('#stat-signals-sub').textContent = result.window_days === 1 ? 'in the last 24 hours' : `in the last ${result.window_days} days`;
  $('#stat-attention').textContent = String(state.feed.filter(x=>x.priority==='High').length).padStart(2,'0');
}
function updateBanner(result) {
  const banner = $('#demo-banner'); banner.classList.remove('hidden');
  if (result.source_mode === 'live') {
    banner.classList.add('is-live');
    banner.querySelector('strong').textContent = 'Public source connected';
    banner.querySelector('.demo-banner-icon').textContent = '✓';
    banner.children[1].querySelector('span').textContent = 'The feed contains exchange records returned by the NSE source. Price history is fetched separately and may still use a labeled fallback.';
  } else {
    banner.classList.remove('is-live');
    banner.querySelector('strong').textContent = 'Illustrative mode';
    banner.querySelector('.demo-banner-icon').textContent = 'i';
    banner.children[1].querySelector('span').textContent = 'Sample alert scenarios are shown until a live source responds. Sample records are not actual filings or market events.';
  }
}

function renderFeed() {
  const text = ($('#feed-search')?.value || '').trim().toLowerCase();
  const priority = $('#priority-filter')?.value || 'all';
  const category = $('#category-filter')?.value || 'all';
  const visible = state.feed.filter(item => {
    const hay = `${item.company} ${item.ticker} ${item.subject} ${item.summary} ${item.category}`.toLowerCase();
    return (!text || hay.includes(text)) && (priority === 'all' || item.priority === priority) && (category === 'all' || item.category === category);
  });
  const cats = [...new Set(state.feed.map(x=>x.category))].sort((a,b)=>categoryLabel(a).localeCompare(categoryLabel(b)));
  const categorySelect = $('#category-filter'); const selected = categorySelect.value;
  categorySelect.innerHTML = '<option value="all">All categories</option>' + cats.map(c=>`<option value="${esc(c)}">${esc(categoryLabel(c))}</option>`).join('');
  if (cats.includes(selected)) categorySelect.value = selected;
  $('#feed-result-count').textContent = `${visible.length} signal${visible.length === 1 ? '' : 's'} · ${state.days === 1 ? 'last 24 hours' : `last ${state.days} days`}`;
  const root = $('#feed-list');
  root.innerHTML = visible.map((item,index) => {
    const pc = priorityClass(item.priority); const iconclass = item.category === 'results' ? 'results' : item.category === 'litigation' ? 'litigation' : item.category === 'market_alert' ? 'market_alert' : '';
    const sample = item.is_demo || item.source_mode === 'demo';
    const summary = (item.summary || item.subject || '').trim();
    return `<article class="feed-card ${pc}" data-feed-index="${state.feed.indexOf(item)}"><div class="feed-card-main"><div class="event-symbol ${iconclass}">${esc(symbolForCategory(item.category))}</div><div class="feed-card-copy"><div class="feed-company-row"><span class="feed-company-name">${esc(item.company)}</span><span class="ticker-mini">${esc(item.ticker)}</span><span class="category-tag">${esc(categoryLabel(item.category))}</span>${sample ? '<span class="sample-tag">DEMO</span>' : ''}</div><h3 class="feed-card-title">${esc(item.subject)}</h3><p class="feed-card-summary">${esc(summary.length > 230 ? summary.slice(0,227)+'…' : summary)}</p><div class="feed-card-footer"><span class="feed-timestamp">${esc(relativeTime(item.published_at))}</span><span class="feed-card-source ${sample?'':'is-live'}">${sample?'Illustrative record':esc(item.source_name || 'NSE filing')}</span></div></div><div class="feed-card-actions"><span class="priority-badge ${pc}">${esc(item.priority || 'Routine')}</span><button class="feed-open-button" aria-label="Open details for ${esc(item.company)}" data-open-feed="${state.feed.indexOf(item)}">↗</button></div></div></article>`;
  }).join('');
  root.querySelectorAll('[data-open-feed]').forEach(btn=>btn.addEventListener('click',()=>openFeedDetail(state.feed[Number(btn.dataset.openFeed)])));
  root.querySelectorAll('.feed-card').forEach(card=>card.addEventListener('click',e=>{
    if (e.target.closest('button')) return;
    const item=state.feed[Number(card.dataset.feedIndex)]; if(item) openFeedDetail(item);
  }));
  $('#feed-empty').classList.toggle('hidden', visible.length !== 0);
  root.classList.toggle('hidden', visible.length === 0);
}

function openFeedDetail(item) {
  if (!item) return;
  const sample = item.is_demo || item.source_mode === 'demo';
  const source = item.source_url ? `<a class="modal-source-button" href="${esc(item.source_url)}" target="_blank" rel="noopener">Open original filing ↗</a>` : '<span class="modal-source-button disabled">Source link not available in this record</span>';
  $('#modal-content').innerHTML = `<div class="modal-content-head"><div class="feed-company-row"><span class="feed-company-name">${esc(item.company)}</span><span class="ticker-mini">${esc(item.ticker)}</span><span class="category-tag">${esc(categoryLabel(item.category))}</span>${sample?'<span class="sample-tag">DEMO</span>':''}</div><h2 id="modal-title">${esc(item.subject)}</h2><p>${esc(item.summary || '')}</p><div class="feed-card-footer"><span class="feed-timestamp">${esc(formatDate(item.published_at))}</span><span class="priority-badge ${priorityClass(item.priority)}">${esc(item.priority)}</span></div></div><div class="modal-content-body"><div class="modal-reason"><strong>Why FINN surfaced this</strong><p>${esc(item.priority_reason || 'Review the original filing to assess its relevance.')}</p></div><h3>What to check next</h3><p>${sample ? 'This is a synthetic scenario for testing the interaction. It is not a statement about the named company. In a live record, validate key facts in the original filing before drawing conclusions.' : 'Treat the priority as a prompt for review. Confirm the disclosed facts and compare them with the relevant financial period before making an investment judgment.'}</p>${source}<button class="modal-source-button" data-modal-research="${esc(item.ticker)}" style="margin-left:8px">Investigate in Research ↗</button></div>`;
  $('#modal-content').querySelector('[data-modal-research]').addEventListener('click',()=>{closeModal();selectCompanyForResearch(item.ticker, item.category==='results'?'Compare this company’s latest reported revenue, EBITDA, PBT and PAT with the previous quarter and the same quarter last year.':'What primary-source evidence helps explain this announcement and its possible financial relevance?');});
  $('#detail-modal').classList.remove('hidden'); document.body.style.overflow='hidden';
}
function closeModal(){ $('#detail-modal').classList.add('hidden'); document.body.style.overflow=''; }
function showAbout(){
  $('#modal-content').innerHTML = `<div class="modal-content-head"><div class="section-kicker">ABOUT THE PROTOTYPE</div><h2 id="modal-title">FINN. Less noise, more context.</h2><p>FINN is a mobile-first financial investment intelligence prototype built around two workflows: a prioritized announcement feed (Push) and source-grounded company research (Pull).</p></div><div class="modal-content-body"><h3>Data integrity by design</h3><p>The app tries public NSE announcement and Yahoo Finance daily-price sources. When a live source is unavailable, synthetic records are labeled DEMO and must not be treated as real financial data. Pull research uses indexed documents only; without source coverage, it says so rather than inventing financial figures.</p><p>To add source documents, use the local ingestion script described in the README. An optional LLM key can synthesize retrieved passages; the app otherwise runs in retrieval-only mode.</p><a class="modal-source-button" href="https://www.nseindia.com/companies-listing/corporate-filings-announcements" target="_blank" rel="noopener">NSE source page ↗</a></div>`;
  $('#detail-modal').classList.remove('hidden'); document.body.style.overflow='hidden';
}

function selectCompanyForResearch(ticker, question) {
  $('#research-ticker').value = ticker;
  if (question) $('#research-question').value = question;
  setView('research');
  $('#research-ticker').focus({preventScroll:true});
}

async function runResearch(event) {
  event.preventDefault(); if(state.researchBusy) return;
  const ticker = ($('#research-ticker').value || '').trim().toUpperCase();
  const question = ($('#research-question').value || '').trim();
  if(!ticker || !question){toast('Enter a ticker and research question.',true);return;}
  state.researchBusy=true;
  const button=$('.run-research-button'); button.disabled=true; $('.run-button-label').textContent='Working…'; $('.run-button-icon').textContent='◌';
  $('#research-status-panel').classList.add('hidden');
  const results=$('#research-results'); results.classList.remove('hidden'); results.innerHTML='<div class="research-loading"><div class="loading-spinner"></div><div><strong>Following the evidence</strong><span>Searching FINN’s indexed primary documents and checking source coverage…</span></div></div>';
  try {
    const result = await api('/api/research',{method:'POST',body:JSON.stringify({ticker,question,mode:'deep_dive'})});
    renderResearchResult(result);
  } catch(err) {
    results.innerHTML=`<div class="research-loading"><div class="research-status-symbol">!</div><div><strong>Research request failed</strong><span>${esc(err.message)}. Check the backend and try again.</span></div></div>`;
    toast(`Research failed: ${err.message}`,true);
  } finally { state.researchBusy=false; button.disabled=false; $('.run-button-label').textContent='Analyze'; $('.run-button-icon').textContent='↗'; }
}

function renderResearchResult(result) {
  const gap=result.status==='coverage_gap';
  const title=gap?'Primary-source coverage needed':'Research findings';
  const findings=(result.key_findings||[]).map(x=>`<li>${esc(x)}</li>`).join('') || '<li>No supported findings were returned.</li>';
  const risks=(result.risks||[]).map(x=>`<p>• ${esc(x)}</p>`).join('');
  const limitations=(result.limitations||[]).map(x=>`<p>${esc(x)}</p>`).join('');
  const selectedMetrics=(result.financial_metrics||[]).filter(m=>['Revenue from operations','EBIT','Profit before tax','Profit after tax'].includes(m.metric));
  const metricPeriods=selectedMetrics[0]?.periods?.map(p=>p.period) || [];
  const metricFmt=(v,unit)=>`${unit && unit.startsWith('₹')?'₹':''}${Number(v).toLocaleString('en-IN')}${unit && unit.startsWith('₹')?' '+unit.slice(1).trim():(unit?' '+unit:'')}`;
  const metricTable=selectedMetrics.length?`<div class="financial-metrics-block"><div class="metrics-title-row"><h3>Financial trajectory</h3><span>ANNUAL TREND TABLE · ${esc(metricPeriods[0]||'')}—${esc(metricPeriods[metricPeriods.length-1]||'')}</span></div><div class="metrics-table-wrap"><table class="metrics-table"><thead><tr><th>Metric</th>${metricPeriods.map(y=>`<th>${esc(y)}</th>`).join('')}<th>Latest YoY</th></tr></thead><tbody>${selectedMetrics.map(m=>`<tr><td>${esc(m.metric)}</td>${m.periods.map(p=>`<td>${esc(metricFmt(p.value,m.unit))}</td>`).join('')}<td><span class="metric-change ${(m.yoy_change_pct??0)>=0?'positive':'negative'}">${m.yoy_change_pct==null?'—':`${m.yoy_change_pct>=0?'+':''}${Number(m.yoy_change_pct).toFixed(1)}%`}</span></td></tr>`).join('')}</tbody></table></div><p class="metrics-note">Source-derived values from the annual performance-trend table. Check the report's footnotes for comparability and adjustments.</p></div>`:'';
  const sources=(result.sources||[]).map(source=>`<div class="source-item"><div class="source-item-label">${esc(source.id)} · ${esc(titleCase(source.document_type||'document'))}${source.period?' · '+esc(source.period):''}</div><strong>${esc(source.title)}</strong>${source.section?`<p>${esc(source.section)}</p>`:''}${source.page?`<p>Page ${esc(source.page)}</p>`:''}${source.excerpt?`<p class="source-excerpt">“${esc(source.excerpt.slice(0,320))}${source.excerpt.length>320?'…':''}”</p>`:''}${source.url?`<a href="${esc(source.url)}" target="_blank" rel="noopener">Open source ↗</a>`:'<p>Source URL not recorded</p>'}</div>`).join('');
  const suggestions=(result.source_suggestions||[]).map(s=>`<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.label)} ↗</a>`).join('');
  $('#research-results').innerHTML=`<div class="results-top"><div><div class="results-company">${esc(result.company)} · ${esc(result.ticker)} · ${esc(result.generator || 'FINN research')}</div><h2>${esc(title)}</h2></div><span class="coverage-pill ${gap?'gap':'grounded'}">${gap?'Coverage gap':'Evidence retrieved'}</span></div><div class="results-body"><div class="results-main"><div class="results-summary-label">EXECUTIVE SUMMARY</div><p class="results-summary">${esc(result.executive_summary || '')}</p>${metricTable}<section class="results-section"><h3>${gap?'What is needed next':'Key findings'}</h3><ul class="finding-list">${findings}</ul></section>${risks?`<section class="results-section" style="margin-top:20px"><h3>Risks to investigate</h3>${risks}</section>`:''}${limitations?`<section class="result-limitations"><h4>Limitations & confidence</h4>${limitations}</section>`:''}</div><aside class="sources-panel"><h3>Evidence used <span style="color:#778375;font:9px var(--mono)">(${(result.sources||[]).length})</span></h3>${sources || '<p style="font-size:10px;color:#9a8b6b;line-height:1.7">No primary-source excerpts were retrieved for this ticker. The links below are places to locate source material; they are not evidence used in this answer.</p>'}</aside></div><div class="source-suggestions"><span>PRIMARY-SOURCE SHORTCUTS</span>${suggestions}</div>`;
}

async function loadRules() {
  try {
    const rules=await api('/api/alerts/rules'); state.rules=rules;
    $('#price-range').value=rules.price_move_pct; $('#price-range-value').textContent=`±${Number(rules.price_move_pct).toFixed(1)}%`;
    $('#volume-range').value=rules.volume_multiple; $('#volume-range-value').textContent=`${Number(rules.volume_multiple).toFixed(2)}×`;
    $('#window-select').value=String(rules.window_days || 1);
    $$('input[name="alert-category"]').forEach(el=>el.checked=(rules.categories||[]).includes(el.value));
    $('#price-threshold-label').textContent=`±${Number(rules.price_move_pct).toFixed(1)}% daily move`;
    $('#volume-threshold-label').textContent=`${Number(rules.volume_multiple).toFixed(2)}× average volume`;
  } catch(err){ console.warn('Could not load alert rules',err); }
}

async function saveRules(event) {
  event.preventDefault();
  const payload={price_move_pct:Number($('#price-range').value),volume_multiple:Number($('#volume-range').value),window_days:Number($('#window-select').value),categories:$$('input[name="alert-category"]:checked').map(el=>el.value),collapse_routine:true};
  try {
    state.rules=await api('/api/alerts/rules',{method:'PUT',body:JSON.stringify(payload)});
    $('#price-threshold-label').textContent=`±${Number(payload.price_move_pct).toFixed(1)}% daily move`;
    $('#volume-threshold-label').textContent=`${Number(payload.volume_multiple).toFixed(2)}× average volume`;
    $('#settings-saved').classList.remove('hidden'); setTimeout(()=>$('#settings-saved').classList.add('hidden'),2800);
    toast('Alert rules saved.');
  } catch(err){toast(`Could not save rules: ${err.message}`,true);}
}

async function previewAlerts() {
  const button=$('#test-alerts'); button.textContent='Checking…'; button.disabled=true;
  try {
    const result=await api('/api/alerts/preview'); const root=$('#alert-preview'); root.classList.remove('hidden');
    if(!result.items.length){root.innerHTML='<div class="alert-preview-item">No threshold triggers in the current preview sample.<small>Try a lower threshold or check live data availability.</small></div>';}
    else root.innerHTML=result.items.map(item=>`<div class="alert-preview-item"><strong>${esc(item.company)} · ${esc(item.ticker)}</strong><br>${esc(item.message)}<small>${item.source_mode==='demo'?'Synthetic price series — demonstration only':'Yahoo Finance daily series'}</small></div>`).join('');
  } catch(err){toast(`Could not preview triggers: ${err.message}`,true);} finally {button.textContent='Preview current triggers ↗';button.disabled=false;}
}

window.addEventListener('DOMContentLoaded', init);
