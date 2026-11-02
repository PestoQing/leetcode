"""本机教学服务：静态网页 + 串行、可暂停的真实参数更新 API。

只接受本机、同源 JSON 写请求，不执行网页提供的任意命令或文件路径。
所有训练在同一CPU/内存受限服务内的单个后台线程运行，GET请求不训练。
"""
import json
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from live_engine import Experiment

ROOT=Path(__file__).resolve().parent
LOCK=threading.RLock()
POOL=ThreadPoolExecutor(max_workers=1)
STOP=threading.Event()
EXPERIMENT=None
STATE=dict(busy=False,error=None,operation='idle',finished=0,requested=0)


def status():
    with LOCK:
        result=dict(STATE)
        result['available']=True
        if EXPERIMENT is not None:
            e=EXPERIMENT
            result.update(session=e.name,algo=e.algo,seed=e.seed,lr=e.lr,round=e.history[-1]['round'],
                folder=str(e.folder),history=[dict(round=x['round'],return_=x['evaluation']['return_'],actor_hash=x['actor_hash']) for x in e.history])
        return result


def work(action,config):
    global EXPERIMENT
    try:
        if action=='create':
            new=Experiment(config['algo'],config['seed'],config['lr'])
            with LOCK:
                if EXPERIMENT is not None:EXPERIMENT.close()
                EXPERIMENT=new
                STATE['finished']=1
        else:
            for _ in range(config['count']):
                if STOP.is_set():break
                # update包含真梯度计算、Adam、真实200步仿真和落盘，不能跳过中间轮。
                EXPERIMENT.update()
                with LOCK:STATE['finished']+=1
    except Exception as exc:
        with LOCK:STATE['error']=str(exc)
        traceback.print_exc()
    finally:
        with LOCK:
            STATE['busy']=False
            STATE['operation']='paused' if STOP.is_set() else 'idle'


class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)

    def json_reply(self,data,code=200):
        encoded=json.dumps(data,ensure_ascii=False,allow_nan=False).encode()
        self.send_response(code)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(encoded)))
        self.end_headers();self.wfile.write(encoded)

    def do_GET(self):
        path=urlparse(self.path)
        if path.path=='/api/live/status':return self.json_reply(status())
        if path.path=='/api/live/round':
            try:
                query=parse_qs(path.query);index=int(query['index'][0])
                with LOCK:
                    if EXPERIMENT is None or not 0<=index<len(EXPERIMENT.history):raise ValueError('该轮尚未完成')
                    record=EXPERIMENT.history[index]
                return self.json_reply(record)
            except (ValueError,KeyError) as exc:return self.json_reply(dict(error=str(exc)),404)
        # 目录含虚拟环境、历史记录等，禁用目录列表及隐藏文件请求。
        from urllib.parse import unquote
        if any(part.startswith('.') for part in unquote(path.path).split('/') if part):return self.send_error(403)
        return super().do_GET()

    def list_directory(self,path):
        self.send_error(403,'Directory listing disabled')

    def do_POST(self):
        if self.path not in ['/api/live/create','/api/live/update','/api/live/stop']:
            return self.json_reply(dict(error='接口不存在'),404)
        host=self.headers.get('Host','')
        origin=self.headers.get('Origin')
        allowed=['127.0.0.1:8765','localhost:8765']
        if host not in allowed or (origin is not None and origin not in ['http://'+h for h in allowed]):
            return self.json_reply(dict(error='仅支持本机同源请求'),403)
        if not self.headers.get('Content-Type','').startswith('application/json'):
            return self.json_reply(dict(error='需要JSON请求'),415)
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<4096:raise ValueError('请求体大小不正确')
            data=json.loads(self.rfile.read(length))
            if not isinstance(data,dict):raise ValueError('需要JSON对象')
            action=self.path.rsplit('/',1)[1]
            with LOCK:
                if action=='stop':
                    STOP.set()
                    return self.json_reply(dict(message='将在当前完整更新和仿真落盘后暂停'))
                if STATE['busy']:return self.json_reply(dict(error='已有操作正在运行，请等待或暂停'),409)
                if action=='create':
                    algo=data['algo'];seed=data['seed'];lr=data['lr']
                    if algo not in ['bc','ppo','sac','iql']:raise ValueError('算法不支持')
                    if type(seed) is not int or not 0<=seed<2**31:raise ValueError('种子应为非负整数')
                    if type(lr) not in [int,float] or not .00001<=lr<=.02:raise ValueError('学习率范围为1e-5到0.02')
                    config=dict(algo=algo,seed=seed,lr=lr)
                else:
                    if EXPERIMENT is None:raise ValueError('请先创建实验')
                    if STATE['error']:raise ValueError('上次操作异常，请创建新实验后继续')
                    count=data['count']
                    if type(count) is not int or not 1<=count<=10:raise ValueError('单次更新轮数应为1到10')
                    if EXPERIMENT.round+count>50:raise ValueError('本次会话最多50轮，请减少轮数或新建实验')
                    config=dict(count=count)
                STOP.clear()
                STATE.update(busy=True,error=None,operation=action,finished=0,requested=1 if action=='create' else config['count'])
                POOL.submit(work,action,config)
            return self.json_reply(dict(accepted=True),202)
        except (ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:
            return self.json_reply(dict(error=str(exc)),400)


if __name__=='__main__':
    print('教学服务：http://127.0.0.1:8765/（逐轮更新任务严格串行）',flush=True)
    server=ThreadingHTTPServer(('127.0.0.1',8765),Handler)
    try:server.serve_forever()
    finally:
        STOP.set();POOL.shutdown(wait=True);server.server_close()
