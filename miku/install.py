"""Per-user install, managed autostart, and reversible uninstall."""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import time
from .config import ROOT, xdg, write_default
from . import assets
from .bridge import atomic_text

COPY=('app','bin','miku','integrations','docs','assets.json','LICENSE','NOTICE.md','README.md')
BEGIN='# BEGIN MIKU DESKTOP (managed)'
END='# END MIKU DESKTOP (managed)'


def autostart_block(path, binary):
    command=shlex.join([str(binary),'start'])
    if path.suffix=='.lua':
        return '\n'+BEGIN.replace('#','--',1)+'\nhl.on("hyprland.start", function()\n    hl.exec_cmd('+json.dumps(command,ensure_ascii=False)+')\nend)\n'+END.replace('#','--',1)+'\n'
    return '\n'+BEGIN+'\nexec-once = '+command+'\n'+END+'\n'


def remove_block(text,block):
    # Remove only the exact stanza we wrote, preserving unrelated user edits.
    return text.replace(block,'',1)


def install(no_start=False,no_autostart=False,hyprland_config=None,no_midnight_bridge=False,archive=None):
    if os.geteuid()==0: raise RuntimeError('Install as your normal desktop user, not with sudo')
    from .cli import require_session
    from .config import load
    require_session(); load()
    destination=xdg('data')/'miku-desktop'
    state=xdg('state')/'miku-desktop/installation.json'
    binary=Path.home()/'.local/bin/miku-desktop'
    if destination.resolve()==ROOT.resolve(): raise RuntimeError('Run the installer from a fresh repository checkout')
    if destination.exists() and not (destination/'.miku-managed').exists():
        raise RuntimeError(f'{destination} exists and is not managed by this installer')
    if (binary.exists() or binary.is_symlink()) and (not binary.is_symlink() or binary.resolve()!=destination/'bin/miku-desktop'):
        raise RuntimeError(f'Refusing to replace unrelated executable: {binary}')
    previous_text=state.read_text() if state.exists() else None
    previous=json.loads(previous_text) if previous_text else {}
    path=None
    if not no_autostart:
        if hyprland_config: path=Path(hyprland_config).expanduser().resolve()
        else:
            folder=xdg('config')/'hypr'
            path=next((folder/n for n in ('hyprland.lua','hyprland.conf') if (folder/n).is_file()),None)
        if not path or not path.is_file():
            raise RuntimeError('Cannot locate Hyprland config. Pass --hyprland-config PATH or --no-autostart')
    # Prepare all configuration edits before downloading or replacing anything.
    before={}; after={}
    if previous.get('autostart'):
        oldpath=Path(previous['autostart']['path'])
        if oldpath.exists():
            before[oldpath]=oldpath.read_text()
            after[oldpath]=remove_block(before[oldpath],previous['autostart']['block'])
    record=dict(destination=str(destination),binary=str(binary))
    if path:
        before.setdefault(path,path.read_text())
        text=after.get(path,before[path])
        if 'BEGIN MIKU DESKTOP (managed)' in text:
            raise RuntimeError('Found an unrecognized Miku autostart stanza; remove it before reinstalling')
        block=autostart_block(path,binary)
        after[path]=text+block
        record['autostart']=dict(path=str(path),block=block)
    assets.install(archive)
    write_default()
    destination.parent.mkdir(parents=True,exist_ok=True)
    state.parent.mkdir(parents=True,exist_ok=True)
    if path and not previous:
        shutil.copy2(path,state.parent/('hyprland-before-miku-'+str(time.time_ns())+path.suffix))
    old_link=os.readlink(binary) if binary.is_symlink() else None
    with tempfile.TemporaryDirectory(prefix='.miku-install-',dir=destination.parent) as tmp:
        staged=Path(tmp)/'app'; staged.mkdir()
        for name in COPY:
            source=ROOT/name
            if source.is_dir(): shutil.copytree(source,staged/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            else: shutil.copy2(source,staged/name)
        (staged/'.miku-managed').write_text('Miku Desktop user installation\n')
        saved=None
        if destination.exists():
            subprocess.run(['qs','kill','-p',str(destination/'app')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            time.sleep(1)
            saved=Path(tmp)/'previous'; destination.rename(saved)
        try:
            staged.rename(destination)
            binary.parent.mkdir(parents=True,exist_ok=True)
            if binary.is_symlink(): binary.unlink()
            binary.symlink_to(destination/'bin/miku-desktop')
            for file,text in after.items(): atomic_text(file,text)
            atomic_text(state,json.dumps(record,indent=2)+'\n')
            if not no_start: subprocess.run([str(binary),'start'],check=True)
        except Exception:
            subprocess.run(['qs','kill','-p',str(destination/'app')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            if destination.exists(): shutil.rmtree(destination)
            if saved: saved.rename(destination)
            if binary.is_symlink(): binary.unlink()
            if old_link: binary.symlink_to(old_link)
            for file,text in before.items(): atomic_text(file,text)
            if previous_text: atomic_text(state,previous_text)
            elif state.exists(): state.unlink()
            if saved and not no_start: subprocess.run([str(binary),'start'],check=False)
            raise
    if not no_midnight_bridge:
        from .bridge import install_midnight
        local=xdg('config')/'quickshell/caelestia'
        system=Path('/etc/xdg/quickshell/caelestia')
        if (local/'modules/notifications/Content.qml').exists() or (system/'modules/notifications/Content.qml').exists():
            try:
                print(install_midnight())
                print('Restart Midnight Shell once if its notification bridge is not already running.')
            except (OSError,RuntimeError) as error:
                print(f'Midnight bridge not installed: {error}. Desktop/window behavior is available.')
    print(f'Installed {binary}')


def uninstall(keep_autostart=False):
    state=xdg('state')/'miku-desktop/installation.json'
    if not state.exists(): raise RuntimeError('No per-user installation found; remove the Arch package with pacman if applicable')
    record=json.loads(state.read_text()); destination=Path(record['destination']); binary=Path(record['binary'])
    if not (destination/'.miku-managed').exists(): raise RuntimeError('Installation marker missing; refusing to delete files')
    from .bridge import remove_midnight
    print(remove_midnight())
    subprocess.run(['qs','kill','-p',str(destination/'app')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if not keep_autostart and 'autostart' in record:
        path=Path(record['autostart']['path'])
        if path.exists(): atomic_text(path,remove_block(path.read_text(),record['autostart']['block']))
    if binary.is_symlink() and binary.resolve()==destination/'bin/miku-desktop': binary.unlink()
    shutil.rmtree(destination)
    state.unlink()
    print('Uninstalled Miku Desktop. Your settings, sprites, and backups were kept.')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--no-start',action='store_true')
    parser.add_argument('--no-autostart',action='store_true')
    parser.add_argument('--no-midnight-bridge',action='store_true')
    parser.add_argument('--hyprland-config')
    parser.add_argument('--archive',help='Use a previously downloaded, checksum-verified sprite archive')
    args=parser.parse_args()
    try: install(**vars(args))
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
        parser.exit(1,f'Install failed: {error}\n')

if __name__=='__main__': main()
