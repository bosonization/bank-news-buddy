const CATEGORIES = ['全部','メガバンク','地銀','最新AI技術','NTTデータ','その他'];
let state = { data:null, category:'全部', q:'' };
const app = document.getElementById('app');

async function loadData(){
  try{
    const res = await fetch('data/news.json?ts=' + Date.now());
    state.data = await res.json();
  }catch(e){
    state.data = { generated_at:'取得失敗', items:[] };
  }
  render();
}
function esc(s){return String(s||'').replace(/[&<>\"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[ch]));}
function filtered(){
  const q = state.q.trim().toLowerCase();
  return (state.data?.items || []).filter(x => {
    const catOk = state.category === '全部' || x.category === state.category;
    const text = `${x.title} ${x.summary} ${(x.tags||[]).join(' ')} ${x.source}`.toLowerCase();
    return catOk && (!q || text.includes(q));
  });
}
function categoryCounts(){
  const c = Object.fromEntries(CATEGORIES.map(x => [x,0]));
  const items = state.data?.items || [];
  c['全部'] = items.length;
  items.forEach(x => c[x.category] = (c[x.category] || 0) + 1);
  return c;
}
function topTalks(items){
  return [...items].sort((a,b)=>(b.importance||0)-(a.importance||0)).slice(0,4);
}
function hero(){
  const count = state.data?.items?.length || 0;
  return `<section class="hero"><div class="heroCard"><div><div class="badge">☀️ 6時 / 🕛 12時 / 🌙 18時 更新</div><h1>地銀トークナビ</h1><p>メガバンク・地銀・最新AI技術・NTTデータのニュースを、地銀営業マンがお客様と話しやすい「営業トーク」と「聞くなら」に変換するダッシュボードです。</p><div class="heroActions"><button class="btn" onclick="scrollToNews()">今日のニュースを見る</button><button class="btn secondary" onclick="location.reload()">最新データを再読込</button></div><div class="status"><span>掲載 ${count}件</span><span>生成: ${esc(state.data?.generated_at || '読み込み中')}</span><span>無料ロジックAI判定</span></div></div><div class="buddyBox"><img src="assets/banker-buddy.svg" alt="バンカーリス"><div class="speech">今日の話題、<br>持ってきたよ！</div></div></div></section>`;
}
function sidebar(){
  const counts = categoryCounts();
  return `<aside class="panel"><h2>カテゴリ</h2><div class="tabs">${CATEGORIES.map(c => `<button class="tab ${state.category===c?'active':''}" data-cat="${c}">${c} <span>(${counts[c]||0})</span></button>`).join('')}</div><input class="search" id="search" placeholder="キーワード検索" value="${esc(state.q)}"><p class="meta">ニュースタイトル・RSS要約を無料ロジックで個別判定し、地銀営業向けの会話ネタに変換します。</p></aside>`;
}
function newsCard(x){
  return `<article class="newsCard"><div class="cardTop"><span class="cat">${esc(x.category)}</span><span class="imp">重要度 ${x.importance ?? '-'} / 100</span></div><h3><a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.title)}</a></h3><div class="source">${esc(x.source)} ${x.published ? '・' + esc(x.published) : ''} / 判定信頼度: ${esc(x.confidence || '-')}</div><p class="summary">${esc(x.summary)}</p><div class="aiBox"><div class="aiItem"><b>なぜ地銀営業に関係あるか</b><p>${esc(x.why_matters)}</p></div><div class="aiItem"><b>営業トーク</b><p>${esc(x.talk)}</p></div><div class="aiItem"><b>お客様に聞くなら</b><p>${esc(x.question)}</p></div><div class="aiItem"><b>NTTデータ文脈</b><p>${esc(x.nttdata_angle)}</p></div><div class="aiItem"><b>注意点</b><p>${esc(x.risk_note)}</p></div><div class="aiItem"><b>検出シグナル</b><p>${esc((x.signals||[]).join(' / ') || 'なし')}</p></div></div><div class="tags">${(x.tags||[]).map(t=>`<span class="tag">#${esc(t)}</span>`).join('')}</div></article>`;
}
function mainList(){
  const items = filtered();
  return `<main id="news" class="newsList">${items.length ? items.map(newsCard).join('') : '<div class="empty panel">該当ニュースがありません。</div>'}</main>`;
}
function rightPanel(){
  const items = topTalks(filtered());
  return `<aside class="panel"><h2>今日の営業ネタ</h2><div class="talkList">${items.map(x=>`<div class="talkItem"><b>${esc(x.title)}</b><p>${esc(x.question)}</p></div>`).join('') || '<p class="meta">ニュース取得後に表示されます。</p>'}</div><h3 style="margin-top:20px">使い方</h3><p class="meta">商談前にカテゴリを選び、「営業トーク」と「お客様に聞くなら」を1つだけメモ。記事本文は元リンクで確認してください。</p></aside>`;
}
function render(){
  app.className='app';
  if(!state.data){ app.innerHTML = '<div class="hero"><div class="heroCard"><p>読み込み中...</p></div></div>'; return; }
  app.innerHTML = `${hero()}<div class="main">${sidebar()}${mainList()}${rightPanel()}</div><div class="footer">※本アプリはニュース本文を転載せず、RSS等から得られるタイトル・概要・リンクをもとに営業向けメモを生成します。重要な事実確認は必ず元記事をご確認ください。</div>`;
  document.querySelectorAll('[data-cat]').forEach(btn => btn.onclick = () => { state.category = btn.dataset.cat; render(); });
  const s = document.getElementById('search'); if(s) s.oninput = e => { state.q = e.target.value; render(); };
}
function scrollToNews(){ document.getElementById('news')?.scrollIntoView({behavior:'smooth'}); }
loadData();
