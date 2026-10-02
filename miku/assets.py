"""Download a pinned sprite archive and verify every installed image."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import urllib.request
import zipfile
import shutil
from .config import ROOT, sprite_path

REQUIRED = [f"shime{i}.png" for i in range(1,47)]

def validate(path):
    path=Path(path)
    for name in REQUIRED:
        data=(path/name).read_bytes()
        if data[:8] != b'\x89PNG\r\n\x1a\n' or len(data)<24:
            raise ValueError(f"Invalid PNG: {name}")
        if int.from_bytes(data[16:20],'big') != 128 or int.from_bytes(data[20:24],'big') != 128:
            raise ValueError(f"{name} must be 128×128 pixels")

def install(archive=None):
    spec=json.loads((ROOT/'assets.json').read_text())
    target=sprite_path()
    if target.exists():
        validate(target)
        return target
    if archive:
        data=Path(archive).read_bytes()
    else:
        with urllib.request.urlopen(spec['url'],timeout=60) as response:
            data=response.read(20*1024*1024+1)
    if hashlib.sha256(data).hexdigest()!=spec['sha256']:
        raise ValueError('Sprite archive checksum mismatch; no assets installed')
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.sprites-',dir=target.parent) as tmp:
        staged=Path(tmp)/'hatsune-miku'
        staged.mkdir()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            # Never extract arbitrary archive paths.
            for name, expected in spec['files'].items():
                payload=z.read(spec['prefix']+name)
                if hashlib.sha256(payload).hexdigest()!=expected:
                    raise ValueError(f'Sprite checksum mismatch: {name}')
                (staged/name).write_bytes(payload)
            (staged/'UPSTREAM-LICENSE').write_bytes(z.read(spec['licensePath']))
        validate(staged)
        (staged/'SOURCE.json').write_text(json.dumps(spec,indent=2)+'\n')
        staged.rename(target)
    return target
