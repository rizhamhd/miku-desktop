"""Read Hyprland geometry; no notification service ownership or message content."""
import concurrent.futures
import json
import math
import subprocess
import sys
import time
from .config import load


def query(argv, timeout=1.5):
    result=subprocess.run(argv,capture_output=True,text=True,timeout=timeout)
    if result.returncode: raise RuntimeError(result.stderr.strip() or 'Command failed')
    return json.loads(result.stdout)


def logical_size(monitor):
    w,h=monitor['width'],monitor['height']
    if monitor.get('transform',0) % 2: w,h=h,w
    scale=monitor.get('scale',1) or 1
    return w/scale,h/scale


def normalize_rects(rects, width, height):
    result=[]
    if not isinstance(rects,list): return result
    for r in rects:
        if not isinstance(r,dict) or not isinstance(r.get('id'),(str,int)): continue
        try:
            values=[float(r[k]) for k in ('left','right','top','bottom')]
        except (KeyError,TypeError,ValueError): continue
        if not all(math.isfinite(x) for x in values): continue
        left,right,top,bottom=values
        left,right=max(0,left),min(width,right)
        if right-left<40 or top<0 or top>=height or bottom<=top: continue
        key=str(r['id'])
        result.append(dict(id=key if key.startswith('notification:') else 'notification:'+key,
            left=left,right=right,top=top,bottom=min(height,bottom),rank=1000000+len(result)))
    return result


def layer_rects(layers, monitor, namespaces):
    """Hyprland layer positions are monitor-local logical pixels."""
    width,height=logical_size(monitor)
    result=[]
    levels=layers.get(monitor['name'],{}).get('levels',{})
    for group in levels.values():
        for item in group:
            if item.get('namespace') not in namespaces or item.get('alpha',1)<=0: continue
            x,y,w,h=(item.get(k,0) for k in ('x','y','w','h'))
            # Full-screen surfaces do not describe the popup inside them.
            if w>=width*.8 or h>=height*.8: continue
            result.append(dict(id='notification:layer:'+str(item.get('address')),
                left=x,right=x+w,top=y,bottom=y+h))
    return normalize_rects(result,width,height)


class NotificationSource:
    def __init__(self):
        self.commands={}
        self.retry_at={}

    def rects(self, monitor, layers, cfg):
        name=monitor['name']
        width,height=logical_size(monitor)
        custom=cfg['notificationBridgeCommand']
        if custom:
            try:
                payload=query([arg.replace('{monitor}',name) for arg in custom],.4)
                return normalize_rects(payload,width,height), 'custom-bridge'
            except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired):
                return [],'custom-bridge-unavailable'
        # Cache a working command; probe absent shells at most every 10 seconds.
        if cfg['midnightBridge'] and time.monotonic()>=self.retry_at.get(name,0):
            commands=[self.commands[name]] if name in self.commands else [
                ['qs','ipc','-c','caelestia','call','miku-notifications-'+name,'snapshot'],
                ['qs','ipc','-c','caelestia','call','miku-'+name,'status'],
            ]
            for command in commands:
                try:
                    payload=query(command,.4)
                    if isinstance(payload,dict):
                        payload=[dict(p,bottom=p['top']+1) for p in payload.get('platforms',[]) if p.get('id','').startswith('notification:')]
                    if not isinstance(payload,list): raise ValueError('Bridge did not return rectangles')
                    self.commands[name]=command
                    return normalize_rects(payload,width,height),'midnight-bridge'
                except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired): pass
            self.commands.pop(name,None)
            self.retry_at[name]=time.monotonic()+10
        return layer_rects(layers,monitor,cfg['notificationNamespaces']),'hyprland-layers'


def snapshot(cfg, source, executor):
    futures={key:executor.submit(query,['hyprctl','-j',key]) for key in ('clients','monitors','layers')}
    values={key:future.result() for key,future in futures.items()}
    notifications={}; adapters={}
    for mon in values['monitors']:
        notifications[mon['name']],adapters[mon['name']]=source.rects(mon,values['layers'],cfg)
    # Window titles and notification contents are never sent to the UI or logged.
    client_keys=('address','mapped','hidden','visible','monitor','workspace','at','size','floating','focusHistoryID','pinned','fullscreen')
    clients=[{k:c[k] for k in client_keys if k in c} for c in values['clients']]
    return dict(clients=clients,monitors=values['monitors'],notifications=notifications,
                adapters=adapters,config=cfg,connected=True)


def stream():
    cfg=load(); source=NotificationSource()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        while True:
            start=time.monotonic()
            try: data=snapshot(cfg,source,executor)
            except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired):
                data=dict(clients=[],monitors=[],notifications={},adapters={},config=cfg,connected=False)
            try: print(json.dumps(data,separators=(',',':')),flush=True)
            except BrokenPipeError: return
            time.sleep(max(.01,cfg['pollIntervalMs']/1000-(time.monotonic()-start)))
