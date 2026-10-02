#!/usr/bin/env python3
"""Opt-in real install/update/uninstall into temporary XDG directories."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from miku.install import install, uninstall

parser=argparse.ArgumentParser()
parser.add_argument('--archive',required=True)
args=parser.parse_args()
with tempfile.TemporaryDirectory(prefix='miku-install-check-') as tmp:
    root=Path(tmp)
    env={f'XDG_{kind}_HOME':str(root/kind.lower()) for kind in ('CONFIG','DATA','STATE')}
    with patch.dict(os.environ,env),patch('pathlib.Path.home',return_value=root/'home'):
        hypr=root/'config/hypr/hyprland.conf'; hypr.parent.mkdir(parents=True)
        hypr.write_text('# temporary integration-test config\n')
        try:
            install(archive=args.archive,no_midnight_bridge=True)
            binary=root/'home/.local/bin/miku-desktop'
            subprocess.run([str(binary),'doctor'],check=True)
            subprocess.run([str(binary),'status'],check=True)
            install(archive=args.archive,no_midnight_bridge=True)
            assert hypr.read_text().count('BEGIN MIKU DESKTOP')==1
            print('PASS: actual install, startup, doctor, status and in-place update')
        finally:
            if (root/'state/miku-desktop/installation.json').exists(): uninstall()
        assert hypr.read_text()=='# temporary integration-test config\n'
        assert not (root/'data/miku-desktop').exists()
        assert not (root/'home/.local/bin/miku-desktop').is_symlink()
        print('PASS: actual uninstall removed the pet and restored autostart')
