const names={ndx:'纳斯达克100指数',nq:'纳斯达克100期货',hstech:'恒生科技指数',shcomp:'上证指数',chinext:'创业板指数',momenta:'魔门塔',unitree:'宇树科技'};
const periods={intraday:'单日',day:'日',week:'周',month:'月',quarter:'季',year:'年'};
let selected='ndx',period='day',quotes={},candles=[],start=0,visible=70,drag=null,raf=0;
const $=id=>document.getElementById(id), chart=$('chart'),ctx=chart.getContext('2d'),wrap=document.querySelector('.chart-wrap');
const currency={USD:'$',CNY:'¥',HKD:'HK$'};
function fmt(v,cur='USD',digits){if(v==null||!Number.isFinite(Number(v)))return '—';let n=Number(v);return (currency[cur]||'')+n.toLocaleString('en-US',{minimumFractionDigits:digits??(n<100?2:2),maximumFractionDigits:digits??2})}
function compact(v,cur){if(v==null||!Number.isFinite(+v))return '暂无公开数据';let n=+v,s=n>=1e12?(n/1e12).toFixed(2)+'T':n>=1e9?(n/1e9).toFixed(2)+'B':n>=1e6?(n/1e6).toFixed(2)+'M':n.toLocaleString('en-US');return (currency[cur]||'')+s}
function setText(id,t){$(id).textContent=t}
function priceFormat(v,q){return fmt(v,q?.isIndex?'':q?.currency)}
function quoteText(q){return q&&q.price!=null?priceFormat(q.price,q):'—'}
async function loadQuotes(){try{let d=await fetchQuotes();quotes=d.quotes||{};for(const k of Object.keys(names)){let q=quotes[k];if(!q||q.error){setText('price-'+k,'行情暂不可用');setText('change-'+k,q?.error||'连接失败');continue}setText('price-'+k,quoteText(q));let change=q.change||0,pct=q.changePercent||0,el=$('change-'+k);el.textContent=`${change>=0?'▲':'▼'} ${priceFormat(Math.abs(change),q)}  ${pct>=0?'+':''}${pct.toFixed(2)}%`;el.className='card-change '+(pct>=0?'up-text':'down-text');}renderSummary();const failed=Object.values(quotes).filter(q=>q.error).length;setText('lastUpdated',(failed?`行情 ${Object.keys(quotes).length-failed}/${Object.keys(quotes).length} 项可用 · `:'')+'最近刷新 '+new Date(d.updatedAt).toLocaleTimeString('zh-CN',{hour12:false}));$('clock').textContent=new Date().toLocaleTimeString('zh-CN',{hour12:false})}catch(e){setText('lastUpdated','行情连接失败，请检查网络');console.warn(e)}}
function renderSummary(){let q=quotes[selected]||{},isIndex=q.isIndex;setText('chartName',names[selected]);setText('marketBadge',q.market||'MARKET');setText('heroPrice',quoteText(q));let pct=q.changePercent||0;let c=$('heroChange');c.textContent=q.price!=null?`${q.change>=0?'▲':'▼'} ${priceFormat(Math.abs(q.change||0),q)} (${pct>=0?'+':''}${pct.toFixed(2)}%)`:'行情暂不可用';c.className=pct>=0?'up-text':'down-text';setText('quoteStamp',q.asOf||'');setText('metricLabel',isIndex?'指数点位':'最新价');setText('metricValue',q.price==null?'—':priceFormat(q.price,q));setText('metricNote',q.market||'当前最新值');if(isIndex){setText('peValue','不适用');setText('peNote','指数不对应单一公司市盈率')}else if(q.pe&&q.pe>0){setText('peValue',q.pe.toFixed(2)+'×');setText('peNote','市盈率 TTM · 行情源数据')}else{setText('peValue','暂无正 PE');setText('peNote','可能处于亏损或行情源未提供')}setText('turnoverValue',q.turnover?compact(q.turnover,q.currency):(isIndex?'—':'暂无数据'));setText('turnoverNote',isIndex&&!q.turnover?'指数行情源未提供成交额':q.turnover?'当日累计 · 行情源数据':'行情源暂未提供');setText('turnoverRateValue',isIndex?'不适用':q.turnoverRate!=null?q.turnoverRate.toFixed(2)+'%':'暂无数据');setText('turnoverRateNote',isIndex?'指数不适用换手率':q.turnoverRate!=null?'当日换手率 · 腾讯行情':'行情源暂未提供换手率');setText('marketStatus',new Date().toLocaleTimeString('zh-CN',{hour12:false}));setText('statusSub','行情接口更新 · 约 30 秒轮询');document.querySelector('.chart-foot span:last-child').textContent='K 线：腾讯行情 · 报价：腾讯行情（估值取东方财富）'}
let chartRequestId=0;
async function loadCandles(preserveView=false){
  const requestId=++chartRequestId, key=selected, requestedPeriod=period;
  if(!preserveView){candles=[];start=0;render();$('chartMessage').style.display='flex';$('chartMessage').textContent=requestedPeriod==='intraday'?'正在读取全天分时…':'正在读取 K 线…'}
  try{
    const data=await fetchCandles(key,requestedPeriod);
    if(requestId!==chartRequestId)return;
    if(!data.length)throw Error('暂无行情数据');
    const wasFull=visible>=candles.length;
    candles=data;
    if(!preserveView||wasFull)visible=requestedPeriod==='intraday'?candles.length:Math.min(70,candles.length);
    $('chartMessage').style.display='none';
    if(requestedPeriod==='intraday'&&candles.length<2){$('chartMessage').textContent='行情源仅返回一个快照，暂无完整分时数据';$('chartMessage').style.display='flex'}
    chart.dataset.mode=requestedPeriod==='intraday'?'line':'candlestick';
    render();updateOhlc(Math.min(visible,candles.length)-1);
  }catch(e){
    if(requestId!==chartRequestId)return;
    if(!preserveView){candles=[];render();$('chartMessage').textContent=e.message;$('chartMessage').style.display='flex'}
  }
}

function resize(){let b=wrap.getBoundingClientRect(),dpr=devicePixelRatio||1;chart.width=Math.round(b.width*dpr);chart.height=Math.round(b.height*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);render()}
function layout(){let w=wrap.clientWidth,h=wrap.clientHeight,p={l:8,r:67,t:15,b:24},volH=45,priceBottom=h-p.b-volH-12;return {w,h,p,volH,priceBottom,volBottom:h-p.b,plotW:w-p.l-p.r}}
const MA_LINES=[{n:5,color:'#f0a020'},{n:10,color:'#e0559a'},{n:20,color:'#7b61ff'}];
function movingAverage(i,n){if(i<n-1)return null;let sum=0;for(let k=i-n+1;k<=i;k++)sum+=candles[k].close;return sum/n}
function render(){
  if(!chart.width||!chart.height)return;
  let {w,h,p,volH,priceBottom,volBottom,plotW}=layout();
  ctx.clearRect(0,0,w,h);
  if(!candles.length)return;
  let maxStart=Math.max(0,candles.length-visible);
  start=Math.max(0,Math.min(start,maxStart));
  let end=candles.length-start,from=Math.max(0,end-visible),list=candles.slice(from,end),n=list.length;
  if(!n)return;
  let min=Math.min(...list.map(x=>x.low)),max=Math.max(...list.map(x=>x.high));
  let pad=(max-min)*.08||Math.abs(max)*.01||1;min-=pad;max+=pad;
  let maxVol=Math.max(...list.map(x=>x.volume||0),1),cw=plotW/n,gap=Math.min(3,cw*.22),body=Math.max(1,cw-gap);
  let y=v=>p.t+(max-v)/(max-min)*(priceBottom-p.t);
  ctx.font='10px DM Mono, monospace';ctx.textBaseline='middle';
  for(let i=0;i<5;i++){
    let val=max-(max-min)*i/4,yy=y(val);ctx.strokeStyle='#e8edf3';ctx.lineWidth=1;
    ctx.beginPath();ctx.moveTo(p.l,yy);ctx.lineTo(w-p.r,yy);ctx.stroke();
    ctx.fillStyle='#78869a';ctx.textAlign='left';ctx.fillText(Number(val).toLocaleString('en-US',{maximumFractionDigits:2}),w-p.r+8,yy);
  }
  ctx.strokeStyle='#dce4ed';ctx.setLineDash([3,4]);ctx.beginPath();ctx.moveTo(p.l,priceBottom+5);ctx.lineTo(w-p.r,priceBottom+5);ctx.stroke();ctx.setLineDash([]);
  if(period==='intraday'){
    let rising=list[n-1].close>=list[0].open,color=rising?'#16a875':'#df5362';
    ctx.beginPath();
    for(let i=0;i<n;i++){let x=p.l+i*cw+cw/2,yy=y(list[i].close);if(i===0)ctx.moveTo(x,yy);else ctx.lineTo(x,yy)}
    ctx.strokeStyle=color;ctx.lineWidth=2;ctx.lineJoin='round';ctx.lineCap='round';ctx.stroke();
    let gradient=ctx.createLinearGradient(0,p.t,0,priceBottom);gradient.addColorStop(0,rising?'#16a87524':'#df536224');gradient.addColorStop(1,rising?'#16a87500':'#df536200');
    ctx.lineTo(p.l+(n-1)*cw+cw/2,priceBottom);ctx.lineTo(p.l+cw/2,priceBottom);ctx.closePath();ctx.fillStyle=gradient;ctx.fill();
    if(n===1){ctx.beginPath();ctx.arc(p.l+cw/2,y(list[0].close),3,0,Math.PI*2);ctx.fillStyle=color;ctx.fill()}
    for(let i=0;i<n;i++){let x=p.l+i*cw+cw/2,vh=(list[i].volume||0)/maxVol*(volH-7);ctx.globalAlpha=.38;ctx.fillStyle=color;ctx.fillRect(x-body/2,volBottom-vh,body,vh);ctx.globalAlpha=1}
  }else{
    for(let i=0;i<n;i++){
      let c=list[i],x=p.l+i*cw+cw/2,up=c.close>=c.open,color=up?'#25c98b':'#fa6672',yo=y(c.open),yc=y(c.close);
      ctx.strokeStyle=color;ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x,y(c.high));ctx.lineTo(x,y(c.low));ctx.stroke();
      ctx.fillStyle=color;ctx.fillRect(x-body/2,Math.min(yo,yc),body,Math.max(1,Math.abs(yc-yo)));
      let vh=(c.volume||0)/maxVol*(volH-7);ctx.globalAlpha=.45;ctx.fillRect(x-body/2,volBottom-vh,body,vh);ctx.globalAlpha=1;
    }
    // MA lines use the full history, so the first visible points are already valid.
    ctx.save();ctx.beginPath();ctx.rect(p.l,p.t,plotW,priceBottom-p.t);ctx.clip();
    for(const ma of MA_LINES){
      ctx.beginPath();let started=false;
      for(let i=0;i<n;i++){let v=movingAverage(from+i,ma.n);if(v==null)continue;let x=p.l+i*cw+cw/2,yy=y(v);if(started)ctx.lineTo(x,yy);else{ctx.moveTo(x,yy);started=true}}
      ctx.strokeStyle=ma.color;ctx.lineWidth=1.4;ctx.lineJoin='round';ctx.stroke();
    }
    ctx.restore();
  }
  let last=list[n-1],ly=y(last.close),up=last.close>=(period==='intraday'?list[0].close:last.open);ctx.strokeStyle=up?'#25c98b':'#fa6672';ctx.setLineDash([4,4]);ctx.beginPath();ctx.moveTo(p.l,ly);ctx.lineTo(w-p.r,ly);ctx.stroke();ctx.setLineDash([]);
  ctx.fillStyle=up?'#d6f3e8':'#fbe0e3';ctx.fillRect(w-p.r+4,ly-9,p.r-8,18);ctx.fillStyle=up?'#087b53':'#bd3547';ctx.textAlign='left';ctx.fillText(last.close.toLocaleString('en-US',{maximumFractionDigits:2}),w-p.r+8,ly);
  ctx.fillStyle='#78869a';ctx.textAlign='center';
  for(let i=0;i<5;i++){
    let idx=Math.round((n-1)*i/4),date=new Date(list[idx].time*1000);
    let label=period==='intraday'?date.toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'}):date.toLocaleDateString('zh-CN',{year:'2-digit',month:'2-digit',day:period==='day'?'2-digit':undefined});
    ctx.fillText(label,p.l+idx*cw+cw/2,h-8);
  }
}
function updateOhlc(i){
  if(!candles.length)return;
  let idx=Math.max(0,Math.min(candles.length-1,candles.length-start-visible+i)),c=candles[idx];if(!c)return;
  let date=new Date(c.time*1000).toLocaleString('zh-CN',{hour12:false});
  if(period==='intraday'){$('ohlc').innerHTML=`<span>${date}</span><span>现价 <b>${priceFormat(c.close,quotes[selected])}</b></span><span>量 <b>${compact(c.volume,'')}</b></span>`;return}
  $('ohlc').innerHTML=`<span>${date}</span><span>开 <b>${priceFormat(c.open,quotes[selected])}</b></span><span>高 <b>${priceFormat(c.high,quotes[selected])}</b></span><span>低 <b>${priceFormat(c.low,quotes[selected])}</b></span><span>收 <b>${priceFormat(c.close,quotes[selected])}</b></span><span>量 <b>${compact(c.volume,'')}</b></span>`+MA_LINES.map(ma=>{let v=movingAverage(idx,ma.n);return `<span style="color:${ma.color}">MA${ma.n} <b style="color:${ma.color}">${v==null?'—':priceFormat(v,quotes[selected])}</b></span>`}).join('');
}
wrap.addEventListener('pointerdown',e=>{if(!candles.length)return;wrap.setPointerCapture(e.pointerId);drag={x:e.clientX,start};wrap.classList.add('dragging')});wrap.addEventListener('pointermove',e=>{if(drag){let dx=e.clientX-drag.x,cw=layout().plotW/visible;start=Math.max(0,Math.min(candles.length-visible,drag.start+Math.round(dx/cw)));render()}else if(candles.length){let box=wrap.getBoundingClientRect(),idx=Math.floor((e.clientX-box.left-layout().p.l)/(layout().plotW/visible));updateOhlc(idx);let lab=$('crosshairLabel');lab.style.display='block';let date=new Date(candles[Math.max(0,Math.min(candles.length-1,candles.length-start-visible+idx))]?.time*1000);lab.textContent=Number.isNaN(+date)?'':date.toLocaleString('zh-CN',{hour12:false})}});wrap.addEventListener('pointerup',()=>{drag=null;wrap.classList.remove('dragging')});wrap.addEventListener('pointerleave',()=>{if(!drag)$('crosshairLabel').style.display='none'});wrap.addEventListener('wheel',e=>{if(!candles.length)return;e.preventDefault();let factor=e.deltaY>0?1.15:.87,old=visible;visible=Math.max(15,Math.min(candles.length,Math.round(visible*factor)));let box=wrap.getBoundingClientRect(),ratio=(e.clientX-box.left-layout().p.l)/layout().plotW;let anchor=candles.length-start-old+Math.round(ratio*old);start=Math.max(0,Math.min(candles.length-visible,candles.length-anchor+Math.round(ratio*visible)));render()},{passive:false});
document.querySelectorAll('.ticker-card').forEach(el=>el.addEventListener('click',()=>{document.querySelector('.ticker-card.selected')?.classList.remove('selected');el.classList.add('selected');selected=el.dataset.symbol;renderSummary();loadCandles()}));document.querySelectorAll('.periods button').forEach(el=>el.addEventListener('click',()=>{document.querySelector('.periods .active')?.classList.remove('active');el.classList.add('active');period=el.dataset.period;loadCandles()}));$('resetView').addEventListener('click',()=>{start=0;visible=period==='intraday'?candles.length:Math.min(70,candles.length);render()});$('refresh').addEventListener('click',()=>{loadQuotes();loadCandles()});window.addEventListener('resize',resize);resize();loadQuotes();loadCandles();setInterval(()=>{loadQuotes();if(period==='intraday')loadCandles(true)},30000);setInterval(()=>{$('clock').textContent=new Date().toLocaleTimeString('zh-CN',{hour12:false})},1000);
