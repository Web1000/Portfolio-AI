/* Original Buffett dashboard components, using corrected report fields. */
(() => {
'use strict';
const {$,demo,esc,fmt,money,pct,text,status,request,sources,download,trace} = PA;
let loading=false, latest=null, modalTrigger=null;
function iconFor(title) {
  if (title.indexOf("Business") >= 0) return "building";
  if (title.indexOf("Cash") >= 0) return "dollar";
  if (title.indexOf("Moat") >= 0) return "shield";
  if (title.indexOf("Debt") >= 0) return "scale";
  return "target";
}

function iconSvg(kind) {
  var icons = {
    building: '<path d="M3 21h18"/><path d="M5 21V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v16"/><path d="M9 7h1"/><path d="M14 7h1"/><path d="M9 12h1"/><path d="M14 12h1"/><path d="M9 17h1"/><path d="M14 17h1"/>',
    dollar: '<circle cx="12" cy="12" r="9"/><path d="M12 7v10"/><path d="M15 9.5A3 3 0 0 0 12 8c-1.7 0-3 1-3 2.3 0 1.4 1.2 2 3 2.4 1.8.4 3 .9 3 2.3S13.7 17 12 17a3.5 3.5 0 0 1-3.3-1.8"/>',
    shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10"/><path d="m9 12 2 2 4-4"/>',
    scale: '<path d="m16 16 3-8 3 8c-.9.7-1.9 1-3 1s-2.1-.3-3-1Z"/><path d="m2 16 3-8 3 8c-.9.7-1.9 1-3 1s-2.1-.3-3-1Z"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 8h18"/>',
    target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>'
  };
  return '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' + icons[kind] + '</svg>';
}

function score(value,max) {return value == null ? 'Unavailable' : value+'/'+max;}
function tone(value) {return value == null ? '' : value>=70?'text-green':value>=50?'text-amber':'text-red';}
function bigMoney(value) {return value == null ? 'Unavailable' : Math.abs(value)>=1e9?'$'+fmt(value/1e9,2)+'B':money(value);}
function metric(label,value,note) {
  return '<div class="bf-metric"><span class="bf-metric-label">'+esc(label)+'</span><strong>'+esc(value)+'</strong><span>'+esc(note)+'</span></div>';
}
function row(title,body,points,max,detail) {
  return '<div class="bf-analysis-row"><div class="bf-analysis-icon bf-icon-'+iconFor(title)+'">'+iconSvg(iconFor(title))+'</div>'+
    '<div class="bf-analysis-copy"><h3><button type="button" class="bf-row-toggle" aria-expanded="false">'+esc(title)+' ▾</button></h3><p>'+esc(body)+'</p></div>'+
    '<div class="bf-analysis-score"><div><span>Rubric</span><strong>'+esc(score(points,max))+'</strong></div>'+
    '<progress max="'+max+'" value="'+(points??0)+'" aria-label="'+esc(title)+' score"></progress></div>'+
    '<div class="bf-row-detail">'+esc(detail)+'</div></div>';
}
function updateScorecard(report) {
  const scores=report.scores;
  text('buffett-score',report.score??'—');text('buffett-score-word',report.assessment);
  $('buffett-score-word').className='bf-score-word '+tone(report.score);
  for(const [id,key,max] of [['business','Business understanding',20],['cash','Cash flow',25],['moat','Moat evidence',25],['debt','Debt',15],['valuation','Valuation',15]]) text('score-'+id,score(scores[key][0],max));
  text('side-total-score',report.score??'—');text('side-total-label',report.assessment);
  document.querySelector('.bf-score-ring').style.setProperty('--score-fill',String((report.score??0)*.72)+'%');
}
function resetScorecard() {
  text('buffett-score','—');text('buffett-score-word','Waiting');text('side-total-score','—');text('side-total-label','Waiting');
  for(const id of ['business','cash','moat','debt','valuation'])text('score-'+id,'—');
  document.querySelector('.bf-score-ring').style.setProperty('--score-fill','0%');
}
function render(data) {
  const r=data.report, scores=r.scores;
  const cash='Annual owner-earnings proxy: '+bigMoney(r.owner_earnings_proxy)+'. Proxy per share: '+money(r.owner_earnings_per_share)+'.';
  const debt=r.debt_to_earnings==null?'A comparable debt ratio is unavailable.':'Reported debt is '+fmt(r.debt_to_earnings)+'× positive owner-earnings proxy.';
  const valuation='Modeled value: '+money(r.value_per_share)+' per share. Quote: '+money(r.current_price)+'. Margin of safety: '+pct(r.margin_of_safety)+'.';
  $('buffett-report-card').innerHTML='<div class="bf-company-head"><div class="bf-company-logo">'+esc(r.ticker.slice(0,1))+'</div>'+
    '<div><span>'+(demo?'Synthetic company overview':'Company overview')+'</span><h2>'+esc(r.company_name)+'</h2><p>'+esc(r.ticker)+' · Fiscal year ended '+esc(r.period_end)+'</p></div>'+
    '<div class="bf-date-pill">Quote date: '+esc(r.price_as_of??'Unavailable')+'</div></div>'+
    '<div class="bf-metrics">'+metric('Current Price',money(r.current_price),'USD quote')+metric('Modeled Value',money(r.value_per_share),'Per share · 12× proxy')+
    metric('Owner Earnings',bigMoney(r.owner_earnings_proxy),'Simplified annual proxy')+metric('Owner EPS',money(r.owner_earnings_per_share),'Annual proxy per share')+
    metric('Debt / OE',r.debt_to_earnings==null?'Unavailable':fmt(r.debt_to_earnings)+'×','Reported debt / proxy')+metric('Total Score',score(r.score,100),'Educational rubric')+'</div>'+
    '<div class="bf-decision-banner '+tone(r.score)+'"><div class="bf-decision-icon">'+iconSvg('shield')+'</div><div><strong>'+esc(r.assessment)+'</strong><p>'+esc(r.valuation_note)+'</p></div>'+
    '<button type="button" class="bf-view-valuation">View Valuation Details <span>›</span></button></div>'+
    '<div class="bf-analysis-list">'+row('Business Summary',r.business_summary,scores['Business understanding'][0],20,r.business_summary)+
    row('Cash Flow Analysis',cash,scores['Cash flow'][0],25,'Operating cash flow less capital expenditure. This is a simplified proxy, not a full owner-earnings calculation. Missing capex is not treated as zero.')+
    row('Moat Analysis',r.moat_analysis,scores['Moat evidence'][0],25,r.moat_analysis)+
    row('Debt Safety Analysis',debt,scores.Debt[0],15,'The debt measure uses supported annual SEC concepts. It can be incomplete; review the limitations below.')+
    row('Valuation Estimate',valuation,scores.Valuation[0],15,r.method)+'</div>';
  $('evidence-card').hidden=false;
  $('value-limitations').replaceChildren();
  for(const line of [r.method,'Cash-flow filing date: '+(r.filed??'Unavailable'),...r.warnings]) {const p=document.createElement('p');p.className='research-note';p.textContent=line;$('value-limitations').append(p);}
  updateScorecard(r);trace('buffett-trace',data.trace,'value');sources(r.sources);download(data,'value');
}
function openModal(html) {
  closeModal();modalTrigger=document.activeElement;
  const backdrop=document.createElement('div');backdrop.className='bf-modal-backdrop';
  backdrop.innerHTML='<div class="bf-modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"><button class="bf-modal-close" type="button" aria-label="Close">×</button>'+html+'</div>';
  document.body.append(backdrop);requestAnimationFrame(()=>backdrop.classList.add('open'));
  backdrop.querySelector('button').focus();
  backdrop.addEventListener('click',event=>{if(event.target===backdrop||event.target.closest('.bf-modal-close'))closeModal();});
  backdrop.addEventListener('keydown',event=>{
    if(event.key==='Escape'){event.preventDefault();closeModal();}
    if(event.key==='Tab'){
      const targets=[...backdrop.querySelectorAll('button,a[href],[tabindex="0"]')];const first=targets[0],last=targets.at(-1);
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
      else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
    }
  });
}
function closeModal(){const modal=document.querySelector('.bf-modal-backdrop');if(modal){modal.remove();modalTrigger?.focus();}}
function methodology() {
  openModal('<div class="bf-modal-kicker">Educational research rubric</div><h2 id="modal-title">How This Agent Scores</h2><p class="bf-modal-lead">A transparent teaching rubric. Scores are not probabilities, investment recommendations, or an assessment by Warren Buffett.</p>'+
    '<div class="bf-method-list"><div><strong>Business understanding</strong><span>20 points</span></div><div><strong>Cash flow</strong><span>25 points</span></div><div><strong>Moat evidence</strong><span>25 points</span></div><div><strong>Debt</strong><span>15 points</span></div><div><strong>Valuation</strong><span>15 points</span></div></div>'+
    '<div class="bf-thinking-box"><h3>Calculations</h3><p>Annual operating cash flow − capex gives the owner-earnings proxy. Divide by fiscal-end shares, then multiply by 12 for a per-share value. Margin of safety is (modeled value − quote) / modeled value.</p><h3>Interpretation</h3><p>85+ is a strong rubric score; 70–84 watchlist; 50–69 mixed; below 50 weak. Missing subscores suppress the total. A separate comparison tests a 15% margin of safety.</p><h3>Limitations</h3><p>Missing inputs stay unavailable. SEC identity profiles cannot establish a moat; demo qualitative scores are prepared illustrations. This is a fixed-multiple heuristic, not a DCF or trading model.</p></div>');
}
function valuationDetails() {
  if(!latest)return;
  const r=latest.report;
  openModal('<div class="bf-modal-kicker">Per-share valuation</div><h2 id="modal-title">Valuation Details</h2><p class="bf-modal-lead">'+esc(r.method)+'</p><div class="bf-reason-grid">'+
    '<div><span>Annual owner-earnings proxy</span><strong>'+esc(bigMoney(r.owner_earnings_proxy))+'</strong><p>Operating cash flow minus capital expenditure.</p></div>'+
    '<div><span>Proxy per share</span><strong>'+esc(money(r.owner_earnings_per_share))+'</strong><p>Uses comparable fiscal-end shares.</p></div>'+
    '<div><span>Modeled value per share</span><strong>'+esc(money(r.value_per_share))+'</strong><p>Positive proxy per share × 12.</p></div>'+
    '<div><span>Margin of safety</span><strong>'+esc(pct(r.margin_of_safety))+'</strong><p>Compared with '+esc(money(r.current_price))+' per share.</p></div></div><div class="bf-thinking-box"><p>'+esc(r.valuation_note)+'</p><p>'+esc(r.warnings.join(' '))+'</p></div>');
}
async function analyze() {
  if(loading)return;
  const ticker=$('buffett-ticker-input').value.trim();
  if(!ticker){status('Enter a company ticker.',true);return;}
  loading=true;latest=null;$('buffett-analyze-btn').disabled=true;$('buffett-ticker-input').disabled=true;
  text('buffett-analyze-btn','Analyzing…');resetScorecard();$('buffett-report-card').replaceChildren();$('evidence-card').hidden=true;
  trace('buffett-trace',[{name:'Analysis in progress',detail:'Completed steps will appear when the workflow finishes.'}],'value');
  status(demo?'Running the synthetic company example…':'Gathering annual financial evidence and preparing the report…');
  try{latest=await request('value',{ticker});render(latest);status();}
  catch(error){status(error.message,true);trace('buffett-trace',[{name:'Analysis unavailable',detail:'No completed report was returned.'}],'value');}
  finally{loading=false;$('buffett-analyze-btn').disabled=false;$('buffett-ticker-input').disabled=false;updateLabel();}
}
function updateLabel(){text('buffett-analyze-btn','Analyze '+($('buffett-ticker-input').value.trim().toUpperCase()||'Company'));}
$('buffett-analyze-btn').addEventListener('click',analyze);
$('buffett-hero-btn').addEventListener('click',()=>{$('buffett-ticker-input').focus();analyze();});
$('buffett-ticker-input').addEventListener('input',updateLabel);
$('buffett-ticker-input').addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();analyze();}});
$('buffett-clear-btn')?.addEventListener('click',()=>{$('buffett-ticker-input').value='';updateLabel();$('buffett-ticker-input').focus();});
document.querySelector('.bf-about-card button').addEventListener('click',methodology);
document.querySelector('.bf-collapse').addEventListener('click',()=>{document.body.classList.toggle('bf-sidebar-collapsed');document.querySelectorAll('.bf-nav-link').forEach(a=>a.setAttribute('aria-label',a.textContent.trim()));});
document.querySelector('.bf-menu').addEventListener('click',event=>{const sidebar=document.querySelector('.bf-sidebar');const hidden=sidebar.classList.toggle('is-hidden');event.currentTarget.setAttribute('aria-expanded',String(!hidden));});
document.querySelector('.bf-all-agents').addEventListener('click',()=>{window.location.href='/';});
document.querySelector('.bf-icon-btn').addEventListener('click',()=>status('No new notifications.'));
$('buffett-report-card').addEventListener('click',event=>{
  if(event.target.closest('.bf-view-valuation'))valuationDetails();
  const button=event.target.closest('.bf-row-toggle');if(button){const row=button.closest('.bf-analysis-row');const opened=row.classList.toggle('open');button.setAttribute('aria-expanded',String(opened));}
});
updateLabel();
})();
