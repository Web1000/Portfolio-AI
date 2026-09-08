/* Original chat and context layout, with safe text rendering and explicit demo mode. */
(() => {
'use strict';
const {$,demo,text,status,request,sources,download,trace} = PA;
let loading=false;
function message(role, content) {
  const row=document.createElement('div'); row.className='explainer-msg '+role;
  const avatar=document.createElement('span'); avatar.className='explainer-avatar'; avatar.textContent=role==='ai'?'AI':'YOU';
  const bubble=document.createElement('div'); bubble.className='explainer-bubble';
  const copy=document.createElement('p');copy.className='research-answer';copy.textContent=content;
  bubble.append(copy);row.append(avatar,bubble);$('chat-messages').append(row);
  $('chat-messages').scrollTop=$('chat-messages').scrollHeight;
}
async function explain() {
  if(loading)return;
  const question=$('question-input').value.trim();
  if(!question){status('Enter a question to explain.',true);return;}
  loading=true; $('send-btn').disabled=true; $('question-input').disabled=true;
  document.querySelectorAll('.explainer-chip').forEach(b=>b.disabled=true);
  message('user',question);status(demo?'Running the prepared ETF example…':'Researching context and preparing an explanation…');
  text('detected-topic','Analyzing');text('route-label','Waiting for the workflow');text('context-list','');$('sources').replaceChildren();$('report-tools').replaceChildren();
  trace('graph-trace',[{name:'Analysis in progress',detail:'Completed steps will appear when the workflow finishes.'}],'news');
  try {
    const data=await request('news',{question});
    text('detected-topic',data.topic);text('route-label',data.topic+' explanation');text('context-list',data.context);
    message('ai',data.answer);trace('graph-trace',data.trace,'news');sources(data.sources);download(data,'news');status();
    if(!demo)$('question-input').value='';
  }catch(error){status(error.message,true);text('detected-topic','Unavailable');text('route-label','Workflow did not complete');trace('graph-trace',[{name:'Analysis unavailable',detail:'No completed report was returned.'}],'news');}
  finally{loading=false;$('send-btn').disabled=false;$('question-input').disabled=false;document.querySelectorAll('.explainer-chip').forEach(b=>b.disabled=false);}
}
const examples=demo?['What is an index ETF?']:['Why did Nvidia stock move?','What is an ETF?','Explain Bitcoin volatility','How does diversification reduce risk?'];
for(const question of examples){const button=document.createElement('button');button.type='button';button.className='explainer-chip';button.textContent=question;button.addEventListener('click',()=>{$('question-input').value=question;});$('prompt-chips').append(button);}
message('ai',demo?'Try the prepared index-ETF example. This demo uses a fixed educational answer and no live news.':'Ask an investing question. The agent will route it, gather context, and write a plain-language explanation.');
text('context-list','Evidence will appear after the analysis completes.');
trace('graph-trace',[{name:'Waiting for a question',detail:'No workflow has run yet.'}],'news');
$('send-btn').addEventListener('click',explain);
$('question-input').addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();explain();}});
})();
