#!/usr/bin/env python3
"""Local quote proxy for the market dashboard. Uses only Python's standard library."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
SYMBOLS = {
    'ndx': {'name': '纳斯达克100指数', 'symbol': '^NDX', 'secid': '100.NDX', 'tencent': 'us.NDX', 'currency': 'USD', 'market': 'NASDAQ-100'},
    'nq': {'name': '纳斯达克100期货', 'symbol': 'NQ', 'secid': '', 'sina': 'NQ', 'currency': 'USD', 'market': 'CME 期货'},
    'hstech': {'name': '恒生科技指数', 'symbol': 'HSTECH.HK', 'secid': '100.HSTECH', 'tencent': 'hkHSTECH', 'currency': 'HKD', 'market': '恒生科技指数'},
    'shcomp': {'name': '上证指数', 'symbol': '000001.SS', 'secid': '1.000001', 'tencent': 'sh000001', 'currency': 'CNY', 'market': '上交所'},
    'chinext': {'name': '创业板指数', 'symbol': '399006.SZ', 'secid': '0.399006', 'tencent': 'sz399006', 'currency': 'CNY', 'market': '深交所'},
    'momenta': {'name': '魔门塔', 'symbol': '6880.HK', 'secid': '116.06880', 'tencent': 'hk06880', 'currency': 'HKD', 'market': '港交所'},
    'unitree': {'name': '宇树科技', 'symbol': '688836.SS', 'secid': '1.688836', 'tencent': 'sh688836', 'currency': 'CNY', 'market': '上交所科创板'},
}

def fetch_json(url):
    referer = 'https://quote.eastmoney.com/' if 'eastmoney.com' in url else 'https://gu.qq.com/'
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36', 'Referer': referer, 'Accept': '*/*'})
    with urlopen(req, timeout=18) as response:
        return json.loads(response.read().decode('utf-8'))

def fetch_sina(url):
    """Fetch a Sina JSONP/var response and return the raw text (GBK encoded)."""
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36', 'Referer': 'https://finance.sina.com.cn/', 'Accept': '*/*'})
    with urlopen(req, timeout=18) as response:
        return response.read().decode('gbk', errors='replace')

def sina_jsonp(url):
    text = fetch_sina(url)
    return json.loads(text[text.index('(') + 1:text.rindex(')')])

def sina_future_quote(cfg):
    text = fetch_sina(f"https://hq.sinajs.cn/list=hf_{cfg['sina']}")
    q = text.split('"')[1].split(',')
    price, prev = float(q[0]), float(q[7])
    change = price - prev
    return {
        'price': price, 'change': change, 'changePercent': change / prev * 100 if prev else 0,
        'turnover': None, 'turnoverRate': None, 'pe': None, 'volume': float(q[9] or 0),
        'currency': cfg['currency'], 'market': cfg['market'], 'name': cfg['name'],
        'asOf': f'{q[12]} {q[6]}', 'isIndex': True,
    }

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/quotes':
            self.quotes()
            return
        if parsed.path == '/api/candles':
            self.candles(parse_qs(parsed.query))
            return
        if parsed.path.startswith('/api/'):
            self.send_json({'error': '未知接口'}, 404)
            return
        super().do_GET()

    def quotes(self):
        results = {}
        for key, cfg in SYMBOLS.items():
            try:
                if 'sina' in cfg:
                    results[key] = sina_future_quote(cfg)
                    continue
                raw = fetch_sina(f"https://qt.gtimg.cn/q={cfg['tencent']}")
                q = raw.split('"')[1].split('~')
                if len(q) < 33 or float(q[3]) <= 0:
                    raise ValueError('该标的暂无有效报价')
                price, change, pct = float(q[3]), float(q[31]), float(q[32])
                currency = {'ndx': 'USD', 'hstech': 'HKD', 'shcomp': 'CNY', 'chinext': 'CNY', 'momenta': 'HKD', 'unitree': 'CNY'}[key]
                turnover = None if key in ('ndx', 'hstech') else float(q[37]) * (1 if key == 'momenta' else 10000)
                turnover_rate = float(q[38]) if len(q) > 38 and q[38] not in ('', '0', '0.00') else None
                pe = None
                # Eastmoney adds valuation fields where available; prices stay on the same Tencent feed as the chart.
                if key not in ('ndx', 'hstech', 'shcomp'):
                    try:
                        url = 'https://push2.eastmoney.com/api/qt/stock/get?secid=' + cfg['secid'] + '&fields=f162,f48'
                        market_data = fetch_json(url).get('data') or {}
                        pe = market_data.get('f162', 0) / 100 if market_data.get('f162') else None
                        if market_data.get('f48') is not None:
                            turnover = market_data['f48']
                    except Exception:
                        pass
                results[key] = {
                    'price': price, 'change': change, 'changePercent': pct,
                    'turnover': turnover, 'turnoverRate': turnover_rate, 'pe': pe, 'volume': float(q[6]),
                    'currency': currency, 'market': 'NASDAQ-100' if key == 'ndx' else cfg['market'],
                    'name': cfg['name'], 'asOf': q[30],
                    'isIndex': key in ('ndx', 'hstech', 'chinext', 'shcomp'),
                }
            except Exception as exc:
                results[key] = {'error': str(exc), 'name': cfg['name'], 'currency': cfg['currency'], 'market': cfg['market']}
        self.send_json({'quotes': results, 'updatedAt': __import__('datetime').datetime.now().astimezone().isoformat()})

    def candles(self, query):
        key = (query.get('symbol') or ['ndx'])[0]
        if key not in SYMBOLS:
            self.send_json({'error': '无效标的'}, 400)
            return
        period = (query.get('period') or ['day'])[0]
        cfg = SYMBOLS[key]
        try:
            candles = self.sina_candles(key, period) if 'sina' in cfg else self.tencent_candles(key, period)
            self.send_json({'candles': candles, 'currency': cfg['currency'], 'symbol': cfg['symbol'], 'period': period, 'name': cfg['name']})
        except Exception as exc:
            self.send_json({'error': f'获取K线失败：{exc}'}, 502)

    def sina_candles(self, key, period):
        """Fetch futures history from Sina's global futures endpoints."""
        code = SYMBOLS[key]['sina']
        dt = __import__('datetime').datetime
        base = 'https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_x=/GlobalFuturesService.'
        if period == 'intraday':
            rows = sina_jsonp(f'{base}getGlobalFuturesMinLine?symbol={code}')['minLine_1d']
            output = []
            for row in rows:
                # The first row carries extra header fields; every row ends with a full timestamp.
                price = float(row[5] if len(row) > 6 else row[1])
                stamp = int(dt.strptime(row[-1], '%Y-%m-%d %H:%M:%S').timestamp())
                output.append({'time': stamp, 'open': price, 'close': price, 'high': price, 'low': price, 'volume': 0})
            if not output:
                raise ValueError('新浪行情源没有返回分时数据')
            return output
        rows = sina_jsonp(f'{base}getGlobalFuturesDailyKLine?symbol={code}')
        candles = []
        for row in rows:
            if float(row['open']) <= 0 or float(row['close']) <= 0:
                continue
            candles.append({'time': int(dt.strptime(row['date'], '%Y-%m-%d').timestamp()), 'open': float(row['open']), 'close': float(row['close']), 'high': float(row['high']), 'low': float(row['low']), 'volume': float(row['volume'] or 0)})
        if period != 'day':
            def bucket_of(date):
                if period == 'week':
                    return date.isocalendar()[:2]
                if period == 'month':
                    return (date.year, date.month)
                if period == 'quarter':
                    return (date.year, (date.month - 1) // 3)
                return date.year
            grouped = {}
            for candle in candles:
                bucket = bucket_of(dt.fromtimestamp(candle['time']))
                if bucket not in grouped:
                    grouped[bucket] = dict(candle)
                else:
                    agg = grouped[bucket]
                    agg['high'] = max(agg['high'], candle['high'])
                    agg['low'] = min(agg['low'], candle['low'])
                    agg['close'] = candle['close']
                    agg['volume'] += candle['volume']
            candles = [grouped[bucket] for bucket in sorted(grouped)]
        return candles[-240:]

    def tencent_candles(self, key, period):
        """Fetch all chart history from Tencent's domestic market data endpoints."""
        code = SYMBOLS[key]['tencent']
        if period == 'intraday':
            endpoint = 'UsMinute' if code.startswith('us.') else 'hkMinute' if code.startswith('hk') else 'day'
            minute_result = fetch_json(f'https://web.ifzq.gtimg.cn/appstock/app/{endpoint}/query?code={code}')['data'][code]
            minute = minute_result['data']
            if isinstance(minute, list):
                minute = minute[-1] if minute else {}
            rows = minute.get('data', [])
            if not rows:
                raise ValueError('腾讯行情源没有返回分时数据')
            date_text = str(minute.get('date') or '')
            if not date_text:
                quote_data = minute_result.get('qt', {}).get(code, [])
                date_text = str(quote_data[30])[:10] if len(quote_data) > 30 else ''
            date_text = date_text.replace('-', '').replace('/', '')
            if len(date_text) != 8:
                date_text = __import__('datetime').datetime.now().strftime('%Y%m%d')
            dt = __import__('datetime').datetime
            output, previous_volume = [], 0
            for row in rows:
                parts = row.split()
                if len(parts) < 2:
                    continue
                clock = parts[0].zfill(4)
                price = float(parts[1])
                stamp = int(dt.strptime(date_text + clock, '%Y%m%d%H%M').timestamp())
                cumulative = float(parts[2]) if len(parts) > 2 else previous_volume
                output.append({'time': stamp, 'open': price, 'close': price, 'high': price, 'low': price, 'volume': max(0, cumulative - previous_volume)})
                previous_volume = cumulative
            return output
        interval, count = {'day': ('day', 240), 'week': ('week', 180), 'month': ('month', 180), 'quarter': ('month', 240), 'year': ('month', 240)}.get(period, ('day', 240))
        url = f'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},{interval},,,{count},qfq'
        response = fetch_json(url)['data'][code]
        rows = response.get(interval) or response.get('qfq' + interval) or []
        candles = []
        for row in rows:
            # Tencent rows are [date, open, close, high, low, volume].
            # Drop corrupt monthly records occasionally returned for global indices.
            if len(row) < 6 or float(row[1]) <= 0 or float(row[2]) <= 0:
                continue
            if abs(float(row[2]) / float(row[1]) - 1) > 0.5:
                continue
            date = __import__('datetime').datetime.strptime(row[0], '%Y-%m-%d')
            candles.append({'time': int(date.timestamp()), 'open': float(row[1]), 'close': float(row[2]), 'high': float(row[3]), 'low': float(row[4]), 'volume': float(row[5] or 0)})
        if period in ('quarter', 'year'):
            grouped = {}
            for candle in candles:
                date = __import__('datetime').datetime.fromtimestamp(candle['time'])
                bucket = (date.year, (date.month - 1) // 3) if period == 'quarter' else date.year
                if bucket not in grouped:
                    grouped[bucket] = dict(candle)
                else:
                    agg = grouped[bucket]
                    agg['high'] = max(agg['high'], candle['high'])
                    agg['low'] = min(agg['low'], candle['low'])
                    agg['close'] = candle['close']
                    agg['volume'] += candle['volume']
            candles = [grouped[bucket] for bucket in sorted(grouped)]
        return candles

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8765'))
    print(f'行情看板已启动：http://127.0.0.1:{port}')
    ThreadingHTTPServer(('127.0.0.1', port), Handler).serve_forever()
