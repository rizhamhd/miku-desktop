"""Optional Midnight adapter. Only notification geometry is exposed."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import time
from .config import ROOT, xdg

FILES=('modules/notifications/Content.qml','modules/notifications/Wrapper.qml')

def transform(content,wrapper):
    if 'function perchRects()' not in content:
        for token in ('id: list','component NotifWrapper: Item','required property NotifData modelData'):
            if token not in content: raise RuntimeError('Unsupported Midnight notification layout; left unchanged')
        anchor='    readonly property int padding:'
        alias='        readonly property alias nonAnimHeight: notif.nonAnimHeight'
        if content.count(anchor)!=1 or content.count(alias)!=1:
            raise RuntimeError('Unsupported Midnight notification layout; left unchanged')
        content=content.replace(anchor,(ROOT/'integrations/midnight/perch-function.qmlpart').read_text()+anchor,1)
        content=content.replace(alias,alias+'\n        readonly property alias perchItem: notif',1)
    if 'miku-notifications-' not in wrapper:
        if 'id: root' not in wrapper or 'id: content' not in wrapper:
            raise RuntimeError('Unsupported Midnight wrapper; left unchanged')
        for line in ('import Quickshell','import Quickshell.Io'):
            if line not in wrapper.splitlines(): wrapper=line+'\n'+wrapper
        pos=wrapper.rfind('}')
        if pos<0: raise RuntimeError('Unsupported Midnight wrapper')
        wrapper=wrapper[:pos]+'''    // Miku Desktop optional bridge: screen-local rectangles, no message content.
    IpcHandler {
        target: "miku-notifications-" + (root.QsWindow.window?.screen?.name ?? "")
        function snapshot(): string {
            return JSON.stringify(root.visible ? content.perchRects() : []);
        }
    }
'''+wrapper[pos:]
    return content,wrapper


def atomic_text(path,text):
    path=Path(path)
    with tempfile.NamedTemporaryFile(mode='w',dir=path.parent,delete=False) as f:
        f.write(text); temp=Path(f.name)
    temp.chmod(0o644); temp.replace(path)


def install_midnight(system=Path('/etc/xdg/quickshell/caelestia')):
    local=xdg('config')/'quickshell/caelestia'
    state=xdg('state')/'miku-desktop/midnight-bridge.json'
    if state.exists(): return 'Midnight bridge already installed'
    source=local if local.exists() else Path(system)
    if not all((source/name).is_file() for name in FILES):
        raise RuntimeError('Midnight Shell not found; use a layer-based adapter or a custom bridge')
    old=[(source/name).read_text() for name in FILES]
    new=transform(*old) # Validate both files before touching anything.
    if tuple(old)==new: return 'Compatible Midnight bridge already present'
    created=not local.exists()
    backup=state.parent/('midnight-backup-'+str(time.time_ns()))
    backup.mkdir(parents=True)
    if created:
        local.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(source,local,symlinks=True)
    record=dict(local=str(local),created=created,backup=str(backup),files={})
    try:
        for name,before,after in zip(FILES,old,new):
            dst=backup/name; dst.parent.mkdir(parents=True,exist_ok=True); dst.write_text(before)
            atomic_text(local/name,after)
            record['files'][name]=hashlib.sha256(after.encode()).hexdigest()
        atomic_text(state,json.dumps(record,indent=2)+'\n')
    except Exception:
        for name,before in zip(FILES,old): atomic_text(local/name,before)
        raise
    return 'Installed Midnight notification bridge (original files backed up)'


def remove_midnight():
    state=xdg('state')/'miku-desktop/midnight-bridge.json'
    if not state.exists(): return 'No managed Midnight bridge installed'
    record=json.loads(state.read_text()); local=Path(record['local']); backup=Path(record['backup'])
    for name,expected in record['files'].items():
        if hashlib.sha256((local/name).read_bytes()).hexdigest()!=expected:
            raise RuntimeError(f'{name} changed since bridge installation. Restore manually from {backup}; no files overwritten')
    for name in record['files']: atomic_text(local/name,(backup/name).read_text())
    if record['created']:
        # Preserve any later user customizations instead of deleting the override.
        archived=state.parent/('midnight-override-disabled-'+str(time.time_ns()))
        shutil.move(local,archived)
    state.unlink()
    return 'Removed Midnight bridge; original notification files restored'
