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
                entry = fetch_json(f"https://web.ifzq.gtimg.cn/appstock/app/minute/query?code={cfg['tencent']}")['data'][cfg['tencent']]
                q = entry['qt'][cfg['tencent']]
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
            candles = self.tencent_candles(key, period)
            self.send_json({'candles': candles, 'currency': cfg['currency'], 'symbol': cfg['symbol'], 'period': period, 'name': cfg['name']})
        except Exception as exc:
            self.send_json({'error': f'获取K线失败：{exc}'}, 502)

    def tencent_candles(self, key, period):
        """Fetch all chart history from Tencent's domestic market data endpoints."""
        code = SYMBOLS[key]['tencent']
        if period == 'intraday':
            endpoint = 'UsMinute' if key == 'ndx' else 'minute'
            minute_result = fetch_json(f'https://web.ifzq.gtimg.cn/appstock/app/{endpoint}/query?code={code}')['data'][code]
            minute = minute_result['data']
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
