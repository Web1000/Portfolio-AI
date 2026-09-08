'use strict';
window.PA = (() => {
  const $ = id => document.getElementById(id);
  const demo = document.body.dataset.mode === 'demo';
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt = (value, decimals = 2) => value == null ? 'Unavailable' : Number(value).toLocaleString('en-US', {minimumFractionDigits: decimals, maximumFractionDigits: decimals});
  const money = value => value == null ? 'Unavailable' : '$' + fmt(value);
  const pct = value => value == null ? 'Unavailable' : fmt(value * 100, 1) + '%';
  const text = (id, value) => { if ($(id)) $(id).textContent = value ?? 'Unavailable'; };
  function status(message = '', error = false) {
    $('status').textContent = message;
    $('status').classList.toggle('is-error', error);
  }
  async function request(workflow, payload) {
    const response = await fetch('/api/' + workflow, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'The analysis could not be completed.');
    return data;
  }
  function sources(items) {
    const target = $('sources'); target.replaceChildren();
    const title = document.createElement('p'); title.className = 'research-note';
    title.textContent = items.length ? 'Source links' : demo ? 'Synthetic fixtures; no external sources were used.' : 'No external sources were available.';
    target.append(title);
    const list = document.createElement('ul'); list.className = 'research-sources';
    for (const item of items) {
      try {
        const url = new URL(item.url);
        if (!['https:', 'http:'].includes(url.protocol)) continue;
        const a = document.createElement('a'); a.href = url.href; a.textContent = item.title; a.target='_blank'; a.rel='noopener noreferrer';
        const li = document.createElement('li'); li.append(a); list.append(li);
      } catch { /* Malformed provider URLs are not rendered. */ }
    }
    target.append(list);
  }
  function download(data, workflow) {
    const target = $('report-tools'); target.replaceChildren();
    const button = document.createElement('button'); button.className = 'report-download'; button.textContent = 'Download JSON'; button.type = 'button';
    button.addEventListener('click', () => {
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], {type:'application/json'}));
      const a = document.createElement('a'); a.href=url; a.download=`portfolioai-${workflow}-${data.mode}.json`;
      document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 30000);
    });
    target.append(button);
  }
  function trace(id, steps, kind) {
    const target = $(id); target.replaceChildren();
    for (const step of steps) {
      const item = document.createElement('div'); item.className = kind === 'value' ? 'bf-trace-step' : kind === 'news' ? 'explainer-step' : 'ta-trace-step';
      const dot = document.createElement('span'); dot.className = kind === 'value' ? 'bf-trace-dot done' : kind === 'news' ? 'explainer-step-dot' : 'ta-trace-dot done';
      const copy = document.createElement('div'); const name = document.createElement('strong'); name.textContent=step.name;
      const detail = document.createElement('p'); detail.textContent=step.detail; copy.append(name,detail); item.append(dot,copy); target.append(item);
    }
  }
  return {$,demo,esc,fmt,money,pct,text,status,request,sources,download,trace};
})();
