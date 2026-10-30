// Browser-side market data: loads Tencent / Sina / Eastmoney endpoints via <script> tags (no CORS, no local server needed).
const SYMBOLS={
  nvda:{tencent:'us.NVDA',currency:'USD',market:'NASDAQ'},
  aapl:{tencent:'us.AAPL',currency:'USD',market:'NASDAQ'},
  mu:{tencent:'us.MU',currency:'USD',market:'NASDAQ'},
  meta:{tencent:'us.META',currency:'USD',market:'NASDAQ'},
  googl:{tencent:'us.GOOGL',currency:'USD',market:'NASDAQ'},
  goog:{tencent:'us.GOOG',currency:'USD',market:'NASDAQ'},
  ndx:{tencent:'us.NDX',currency:'USD',market:'NASDAQ-100',isIndex:true},
  nq:{sina:'NQ',currency:'USD',market:'CME 期货',isIndex:true},
  hstech:{tencent:'hkHSTECH',currency:'HKD',market:'恒生科技指数',isIndex:true},
  shcomp:{tencent:'sh000001',currency:'CNY',market:'上交所',isIndex:true},
  chinext:{tencent:'sz399006',secid:'0.399006',currency:'CNY',market:'深交所',isIndex:true},
  momenta:{tencent:'hk06880',secid:'116.06880',currency:'HKD',market:'港交所'},
  unitree:{tencent:'sh688836',secid:'1.688836',currency:'CNY',market:'上交所科创板'},
};
let scriptSeq=0;
function loadScript(url,charset){
  return new Promise((ok,fail)=>{
    const s=document.createElement('script'),timer=setTimeout(()=>{s.remove();fail(Error('请求超时'))},15000);
    if(charset)s.charset=charset;
    s.referrerPolicy='no-referrer';
    s.src=url;
    s.onload=()=>{clearTimeout(timer);s.remove();ok()};
    s.onerror=()=>{clearTimeout(timer);s.remove();fail(Error('行情源连接失败：'+new URL(url).hostname))};
    document.head.appendChild(s);
  });
}
// Endpoints that assign their result to a global variable whose name we choose.
async function loadVar(build){
  const name='__mkt'+(++scriptSeq);
  await loadScript(build(name));
  const value=window[name];window[name]=undefined;
  if(value==null)throw Error('行情源无返回');
  return value;
}
// Eastmoney JSONP callback style.
function loadJsonp(url){
  return new Promise((ok,fail)=>{
    const name='__cb'+(++scriptSeq);let received=false;
    window[name]=d=>{received=true;ok(d)};
    loadScript(url+'&cb='+name).then(()=>{
      delete window[name];
      if(!received)fail(Error('估值接口未返回数据'));
    },e=>{delete window[name];fail(e)});
  });
}
async function tencentQuote(code){
  // The minute/query endpoint is blocked by Tencent WAF. This quote feed
  // assigns a fixed global variable and uses GBK rather than UTF-8.
  code=code.replace(/^us\./,'us');
  const variable='v_'+code;
  await loadScript('https://qt.gtimg.cn/q='+encodeURIComponent(code),'gbk');
  const raw=window[variable];
  if(typeof raw!=='string'||!raw.includes('~'))throw Error('腾讯未返回该标的报价');
  const q=raw.split('~');
  if(q.length<33||!(+q[3]>0))throw Error('该标的暂无有效报价');
  return q;
}
const tencent=(path,name)=>`https://web.ifzq.gtimg.cn/appstock/app/${path}&_var=${name}`;
const sina=(method,code,name)=>`https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20${name}=/GlobalFuturesService.${method}?symbol=${code}`;
const parseStamp=t=>Math.floor(new Date(t.replace(' ','T')).getTime()/1000);

async function sinaMinutes(cfg){
  const rows=(await loadVar(n=>sina('getGlobalFuturesMinLine',cfg.sina,n))).minLine_1d||[];
  if(!rows.length)throw Error('新浪行情源没有返回分时数据');
  // The first row carries extra header fields (date, previous settlement, exchange...).
  return {prevSettle:+rows[0][1],points:rows.map(r=>({time:parseStamp(r[r.length-1]),price:+(r.length>6?r[5]:r[1])}))};
}

async function quoteFor(key){
  const cfg=SYMBOLS[key],base={currency:cfg.currency,market:cfg.market,name:names[key],isIndex:!!cfg.isIndex};
  if(cfg.sina){
    const {prevSettle,points}=await sinaMinutes(cfg),last=points[points.length-1],change=last.price-prevSettle;
    return {...base,price:last.price,change,changePercent:prevSettle?change/prevSettle*100:0,turnover:null,turnoverRate:null,pe:null,volume:0,
      asOf:new Date(last.time*1000).toLocaleString('zh-CN',{hour12:false})};
  }
  const code=cfg.tencent,q=await tencentQuote(code);
  const isUS=code.startsWith('us.'),isHK=code.startsWith('hk');
  const positive=v=>Number.isFinite(+v)&&+v>0?+v:null;
  // 腾讯总市值字段45以亿计；美股/港股成交额为原币，A股为万元。
  let marketCap=cfg.isIndex?null:positive(q[45])===null?null:+q[45]*1e8;
  let turnover=key==='ndx'||key==='hstech'?null:positive(q[37])===null?null:+q[37]*(isUS||isHK?1:10000);
  let pe=cfg.isIndex?null:positive(q[39]);
  const turnoverRate=q.length>38&&!['','0','0.00'].includes(q[38])?+q[38]:null;
  // Eastmoney adds valuation fields where available; prices stay on the same Tencent feed as the chart.
  if(cfg.secid){
    try{
      const m=(await loadJsonp(`https://push2.eastmoney.com/api/qt/stock/get?secid=${cfg.secid}&fields=f162,f48,f116`)).data||{};
      if(Number.isFinite(+m.f162)&&+m.f162>0)pe=m.f162/100;
      if(!cfg.isIndex&&Number.isFinite(+m.f116)&&+m.f116>0)marketCap=+m.f116;
      if(m.f48!=null)turnover=m.f48;
    }catch(e){}
  }
  return {...base,price:+q[3],change:+q[31],changePercent:+q[32],turnover,turnoverRate,pe,marketCap,volume:+q[6],asOf:q[30]};
}

async function fetchQuotes(){
  const keys=Object.keys(SYMBOLS),results=await Promise.allSettled(keys.map(quoteFor)),quotes={};
  keys.forEach((k,i)=>{const r=results[i];quotes[k]=r.status==='fulfilled'?r.value:{error:r.reason?.message||'获取失败',currency:SYMBOLS[k].currency,market:SYMBOLS[k].market,isIndex:!!SYMBOLS[k].isIndex}});
  return {quotes,updatedAt:new Date().toISOString()};
}

function groupCandles(candles,period){
  const bucketOf=d=>{
    if(period==='week'){const t=new Date(d);t.setDate(t.getDate()-((t.getDay()+6)%7));return t.toDateString()}
    if(period==='month')return d.getFullYear()+'-'+d.getMonth();
    if(period==='quarter')return d.getFullYear()+'-Q'+Math.floor(d.getMonth()/3);
    return String(d.getFullYear());
  };
  const out=[];let lastBucket=null;
  for(const c of candles){
    const b=bucketOf(new Date(c.time*1000));
    if(b!==lastBucket){out.push({...c});lastBucket=b;continue}
    const agg=out[out.length-1];
    agg.high=Math.max(agg.high,c.high);agg.low=Math.min(agg.low,c.low);agg.close=c.close;agg.volume+=c.volume;
  }
  return out;
}
const dayStamp=s=>{const [y,m,d]=s.split('-').map(Number);return Math.floor(new Date(y,m-1,d).getTime()/1000)};

async function sinaCandles(cfg,period){
  if(period==='intraday')return (await sinaMinutes(cfg)).points.map(p=>({time:p.time,open:p.price,close:p.price,high:p.price,low:p.price,volume:0}));
  const rows=await loadVar(n=>sina('getGlobalFuturesDailyKLine',cfg.sina,n));
  const candles=rows.filter(r=>+r.open>0&&+r.close>0).map(r=>({time:dayStamp(r.date),open:+r.open,close:+r.close,high:+r.high,low:+r.low,volume:+r.volume||0}));
  return (period==='day'?candles:groupCandles(candles,period)).slice(-240);
}

async function tencentCandles(key,period){
  const code=SYMBOLS[key].tencent;
  if(period==='intraday'){
    const endpoint=code.startsWith('us.')?'UsMinute':code.startsWith('hk')?'hkMinute':'day';
    const payload=await loadVar(n=>tencent(`${endpoint}/query?code=${code}`,n));
    const result=payload.data?.[code];
    if(!result)throw Error('腾讯未返回该标的分时数据');
    const minute=Array.isArray(result.data)?result.data[result.data.length-1]:result.data;
    const rows=minute?.data||[];
    if(!rows.length)throw Error('腾讯行情源没有返回分时数据');
    let dateText=String(minute.date||'');
    if(!dateText){const qd=result.qt?.[code]||[];dateText=qd.length>30?String(qd[30]).slice(0,10):''}
    dateText=dateText.replace(/[-\/]/g,'');
    if(dateText.length!==8){const n=new Date();dateText=''+n.getFullYear()+String(n.getMonth()+1).padStart(2,'0')+String(n.getDate()).padStart(2,'0')}
    const y=+dateText.slice(0,4),mo=+dateText.slice(4,6)-1,d=+dateText.slice(6,8),out=[];let prevVol=0;
    for(const row of rows){
      const parts=row.split(' ');if(parts.length<2)continue;
      const clock=parts[0].padStart(4,'0'),price=+parts[1],cumulative=parts.length>2?+parts[2]:prevVol;
      out.push({time:Math.floor(new Date(y,mo,d,+clock.slice(0,2),+clock.slice(2)).getTime()/1000),open:price,close:price,high:price,low:price,volume:Math.max(0,cumulative-prevVol)});
      prevVol=cumulative;
    }
    return out;
  }
  const [interval,count]={day:['day',240],week:['week',180],month:['month',180],quarter:['month',240],year:['month',240]}[period]||['day',240];
  const response=(await loadVar(n=>tencent(`${code.startsWith('us.')?'usfqkline':'fqkline'}/get?param=${code},${interval},,,${count},qfq`,n))).data[code];
  const rows=response[interval]||response['qfq'+interval]||[],candles=[];
  for(const r of rows){
    // Tencent rows are [date, open, close, high, low, volume]; drop corrupt records occasionally returned for global indices.
    // Also drop rows far from the previous close (e.g. a bogus ~11 point bar for the live US session).
    const prev=candles[candles.length-1];
    if(r.length<6||+r[1]<=0||+r[2]<=0||Math.abs(r[2]/r[1]-1)>.5||(SYMBOLS[key].isIndex&&prev&&Math.abs(r[2]/prev.close-1)>.5))continue;
    candles.push({time:dayStamp(r[0]),open:+r[1],close:+r[2],high:+r[3],low:+r[4],volume:+r[5]||0});
  }
  return period==='quarter'||period==='year'?groupCandles(candles,period):candles;
}

async function fetchCandles(key,period){
  const cfg=SYMBOLS[key];
  if(!cfg)throw Error('无效标的');
  try{return cfg.sina?await sinaCandles(cfg,period):await tencentCandles(key,period)}
  catch(e){throw Error('获取K线失败：'+e.message)}
}
