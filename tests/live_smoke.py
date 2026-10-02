#!/usr/bin/env python3
"""Opt-in test: opens a temporary window/popup and stops its own pet on exit."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parent.parent

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--sprites',required=True)
    args=parser.parse_args()
    mon=next(m for m in json.loads(subprocess.check_output(['hyprctl','-j','monitors'],text=True)) if m.get('focused'))
    with tempfile.TemporaryDirectory(prefix='miku-smoke-') as tmp:
        folder=Path(tmp)
        cfg=folder/'config/miku-desktop'; cfg.mkdir(parents=True)
        (cfg/'config.json').write_text(json.dumps({'spritePath':str(Path(args.sprites).resolve()),'midnightBridge':False}))
        env=dict(os.environ,XDG_CONFIG_HOME=str(folder/'config'))
        command=ROOT/'bin/miku-desktop'
        def ipc(method,*values):
            return subprocess.check_output(['qs','ipc','-p',str(ROOT/'app'),'call','pet-'+mon['name'],method,*map(str,values)],text=True,env=env)
        def state(): return json.loads(ipc('status'))
        def until(predicate,seconds=8):
            deadline=time.monotonic()+seconds
            last=None
            while time.monotonic()<deadline:
                try:
                    last=state()
                    if predicate(last): return last
                except (subprocess.CalledProcessError,json.JSONDecodeError): pass
                time.sleep(.1)
            raise AssertionError(last)
        popup=None; dialog=None
        try:
            subprocess.run([str(command),'start'],check=True,env=env)
            until(lambda s:s['visible'] and s['layer']=='desktop')
            print('PASS: standalone pet starts behind apps, with Midnight integration disabled',flush=True)
            # A real, isolated Wayland notification-shaped layer surface.
            popup=folder/'popup'; popup.mkdir()
            (popup/'shell.qml').write_text('''import Quickshell
import Quickshell.Wayland
import QtQuick
PanelWindow {
    implicitWidth: 400; implicitHeight: 110
    anchors { bottom: true; right: true }
    margins { bottom: 80; right: 25 }
    color: "#243848"
    WlrLayershell.namespace: "notifications"
    WlrLayershell.layer: WlrLayer.Top
    WlrLayershell.exclusionMode: ExclusionMode.Ignore
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
    mask: Region {}
    Text { anchors.centerIn: parent; text: "Miku standalone notification test"; color: "white" }
}''')
            subprocess.run(['qs','-p',str(popup),'-d'],check=True,env=env)
            until(lambda s:s['body']['grounded'] and s['body']['support'].startswith('notification:layer:') and s['layer']=='overlay')
            print('PASS: automatic notification hop using native Hyprland layer geometry',flush=True)
            subprocess.run(['qs','kill','-p',str(popup)],check=True,env=env); popup=None
            until(lambda s:s['layer']=='desktop')
            print('PASS: goes behind apps after notification dismissal',flush=True)
            dialog=subprocess.Popen(['zenity','--info','--title=Miku standalone window test','--text=Temporary Miku window perch test','--width=500','--height=250'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            s=until(lambda s:any(p['id'].startswith('window:') for p in s['platforms']))
            p=next(p for p in s['platforms'] if p['id'].startswith('window:'))
            ipc('drop',(p['left']+p['right'])/2-64,max(0,p['top']-240))
            until(lambda s:s['body']['support']==p['id'] and s['layer']=='overlay')
            print('PASS: standalone window landing',flush=True)
            dialog.terminate(); dialog.wait(timeout=3); dialog=None
            # Return home explicitly if some unrelated window remains underneath.
            ipc('home'); until(lambda s:s['layer']=='desktop')
        finally:
            if dialog: dialog.terminate(); dialog.wait(timeout=3)
            if popup: subprocess.run(['qs','kill','-p',str(popup)],env=env)
            subprocess.run([str(command),'stop'],env=env)

if __name__=='__main__': main()
