"""Command line lifecycle and setup entry points."""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from . import __version__
from .config import ROOT, load, write_default
from . import assets


def require_session():
    from .backend import query
    for binary in ('hyprctl','qs'):
        if not shutil.which(binary): raise RuntimeError(f'Missing {binary}; run ./install.sh')
    if not os.environ.get('HYPRLAND_INSTANCE_SIGNATURE') or not os.environ.get('WAYLAND_DISPLAY'):
        raise RuntimeError('Run Miku from a terminal inside your Hyprland session')
    version=subprocess.check_output(['qs','--version'],text=True)
    match=re.search(r'(\d+)\.(\d+)\.(\d+)',version)
    if not match or tuple(map(int,match.groups())) < (0,3,1):
        raise RuntimeError('Quickshell 0.3.1+ is required; update quickshell or quickshell-git')
    monitors=query(['hyprctl','-j','monitors'])
    if not monitors: raise RuntimeError('Hyprland has no active monitors')
    return monitors


def ipc(method, screen=None, args=()):
    monitors=require_session()
    screens=[m['name'] for m in monitors if screen is None or m['name']==screen]
    if not screens: raise RuntimeError('Monitor not found')
    for name in screens:
        cmd=['qs','ipc','-p',str(ROOT/'app'),'call','pet-'+name,method,*map(str,args)]
        subprocess.run(cmd,check=True)


def main(argv=None):
    parser=argparse.ArgumentParser(prog='miku-desktop',description='Desktop companion for Hyprland, independent of your shell')
    parser.add_argument('--version',action='version',version=__version__)
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ('start','run','stop','doctor','stream','status','fetch-sprites'):
        sub.add_parser(name)
    sub.add_parser('uninstall').add_argument('--keep-autostart',action='store_true')
    for name in ('perch','home'):
        sub.add_parser(name).add_argument('--screen')
    bridge=sub.add_parser('bridge')
    bridge.add_argument('kind',choices=['midnight'])
    bridge.add_argument('action',choices=['install','remove'])
    args=parser.parse_args(argv)
    try:
        if args.command=='stream':
            from .backend import stream
            stream()
        elif args.command=='fetch-sprites': print(assets.install())
        elif args.command in ('start','run'):
            monitors=require_session(); write_default(); cfg=load()
            try: assets.validate(cfg['spritePath'])
            except FileNotFoundError:
                if cfg['spritePath'].rstrip('/')!=str(assets.sprite_path()): raise
                assets.install()
            command=['qs','-p',str(ROOT/'app'),'-n']
            env=dict(os.environ,MIKU_DESKTOP_COMMAND=str(ROOT/'bin/miku-desktop'))
            if args.command=='run': os.execvpe(command[0],command,env)
            subprocess.run(command+['-d'],env=env,check=True)
            deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                result=subprocess.run(['qs','ipc','-p',str(ROOT/'app'),'call','pet-'+monitors[0]['name'],'status'],env=env,capture_output=True,text=True)
                if result.returncode==0: break
                time.sleep(.1)
            else: raise RuntimeError('Pet did not start; use miku-desktop run to inspect QML errors')
        elif args.command=='stop':
            subprocess.run(['qs','kill','-p',str(ROOT/'app')],check=True)
        elif args.command in ('status','perch','home'): ipc(args.command,getattr(args,'screen',None))
        elif args.command=='doctor':
            monitors=require_session(); cfg=load(); assets.validate(cfg['spritePath'])
            from .backend import NotificationSource, query
            source=NotificationSource(); layers=query(['hyprctl','-j','layers'])
            print(f'Miku Desktop {__version__}: Hyprland connection and sprites OK')
            for m in monitors:
                rects,adapter=source.rects(m,layers,cfg)
                print(f"{m['name']}: {adapter}; {len(rects)} notification surface(s)")
            print('Window perching works with any shell. Notification support depends on popup geometry; see docs/notifications.md.')
        elif args.command=='bridge':
            from .bridge import install_midnight, remove_midnight
            print(install_midnight() if args.action=='install' else remove_midnight())
            print('Restart Midnight Shell to apply the bridge change.')
        elif args.command=='uninstall':
            from .install import uninstall
            uninstall(keep_autostart=args.keep_autostart)
        return 0
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
        print(f'miku-desktop: {error}',file=sys.stderr)
        return 1
