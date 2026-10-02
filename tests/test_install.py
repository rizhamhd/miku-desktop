import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from miku.config import load, DEFAULTS
from miku.install import install, uninstall, autostart_block, remove_block
from miku.bridge import transform, install_midnight, remove_midnight

CONTENT='''Item {
    readonly property int padding: 10
    Item { id: list }
    component NotifWrapper: Item {
        required property NotifData modelData
        readonly property alias nonAnimHeight: notif.nonAnimHeight
    }
}'''
WRAPPER='''import QtQuick
Item {
    id: root
    Content { id: content }
}'''

class TemporaryUser(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        env={f'XDG_{kind}_HOME':str(self.root/kind.lower()) for kind in ('CONFIG','DATA','STATE')}
        self.env=patch.dict(os.environ,env); self.env.start()
        self.home=patch('pathlib.Path.home',return_value=self.root/'home'); self.home.start()
    def tearDown(self):
        self.home.stop(); self.env.stop(); self.tmp.cleanup()

class ConfigTests(TemporaryUser):
    def test_defaults_and_reject_bad_types(self):
        self.assertTrue(load()['autoNotificationHop'])
        path=self.root/'config/miku-desktop/config.json'; path.parent.mkdir(parents=True)
        path.write_text('{"pollIntervalMs":true}')
        with self.assertRaises(ValueError): load()
        path.write_text('{"notificationBridgeCommand":"sh -c bad"}')
        with self.assertRaises(ValueError): load()

class BridgeTests(TemporaryUser):
    def test_transform_idempotent(self):
        transformed=transform(CONTENT,WRAPPER)
        self.assertEqual(transform(*transformed),transformed)
        self.assertIn('miku-notifications-',transformed[1])
    def test_incompatible_leaves_files_alone(self):
        with self.assertRaises(RuntimeError): transform('Unknown layout',WRAPPER)
    def test_install_restore_and_protect_later_edits(self):
        local=self.root/'config/quickshell/caelestia/modules/notifications'; local.mkdir(parents=True)
        (local/'Content.qml').write_text(CONTENT); (local/'Wrapper.qml').write_text(WRAPPER)
        install_midnight()
        new=(local/'Wrapper.qml').read_text()
        (local/'Wrapper.qml').write_text(new+'\n// user change')
        with self.assertRaises(RuntimeError): remove_midnight()
        self.assertTrue((local/'Wrapper.qml').read_text().endswith('// user change'))
        (local/'Wrapper.qml').write_text(new)
        remove_midnight()
        self.assertEqual((local/'Wrapper.qml').read_text(),WRAPPER)
        self.assertEqual((local/'Content.qml').read_text(),CONTENT)

class InstallTests(TemporaryUser):
    def test_autostart_lua_and_classic(self):
        binary=Path('/path with space/miku')
        for name in ('hyprland.lua','hyprland.conf'):
            block=autostart_block(Path(name),binary)
            text='existing\n'+block+'later edit\n'
            self.assertEqual(remove_block(text,block),'existing\nlater edit\n')
            self.assertIn("'/path with space/miku'",block)
    @patch('miku.install.os.geteuid',return_value=1000)
    @patch('miku.cli.require_session',return_value=[])
    @patch('miku.install.assets.install')
    @patch('miku.install.subprocess.run')
    @patch('miku.install.time.sleep')
    def test_install_update_uninstall_preserves_user_changes(self,*mocks):
        hypr=self.root/'config/hypr/hyprland.conf'; hypr.parent.mkdir(parents=True)
        hypr.write_text('monitor = ,preferred,auto,1\n')
        install(no_start=True,no_midnight_bridge=True)
        install(no_start=True,no_midnight_bridge=True)
        self.assertEqual(hypr.read_text().count('BEGIN MIKU DESKTOP'),1)
        with hypr.open('a') as f: f.write('# later user setting\n')
        uninstall()
        self.assertEqual(hypr.read_text(),'monitor = ,preferred,auto,1\n# later user setting\n')
        self.assertFalse((self.root/'data/miku-desktop').exists())
        self.assertTrue((self.root/'config/miku-desktop/config.json').exists())
    @patch('miku.install.os.geteuid',return_value=1000)
    @patch('miku.cli.require_session',return_value=[])
    def test_refuses_unmanaged_install(self,*mocks):
        target=self.root/'data/miku-desktop'; target.mkdir(parents=True)
        (target/'mine').write_text('keep')
        with self.assertRaises(RuntimeError): install(no_start=True,no_autostart=True)
        self.assertEqual((target/'mine').read_text(),'keep')
    @patch('miku.install.os.geteuid',return_value=1000)
    @patch('miku.cli.require_session',return_value=[])
    @patch('miku.install.assets.install')
    @patch('miku.install.subprocess.run')
    def test_failed_start_restores_config_and_removes_partial_install(self,run,*mocks):
        import subprocess
        hypr=self.root/'config/hypr/hyprland.lua'; hypr.parent.mkdir(parents=True)
        original='-- my config\n'; hypr.write_text(original)
        def execute(cmd,**kw):
            if cmd[-1]=='start': raise subprocess.CalledProcessError(1,cmd)
        run.side_effect=execute
        with self.assertRaises(subprocess.CalledProcessError): install(no_midnight_bridge=True)
        self.assertEqual(hypr.read_text(),original)
        self.assertFalse((self.root/'data/miku-desktop').exists())
        self.assertFalse((self.root/'home/.local/bin/miku-desktop').is_symlink())
    @patch('miku.install.os.geteuid',return_value=1000)
    @patch('miku.cli.require_session',return_value=[])
    @patch('miku.install.assets.install')
    def test_unknown_autostart_fails_before_download_or_install(self,download,*mocks):
        hypr=self.root/'config/hypr/hyprland.conf'; hypr.parent.mkdir(parents=True)
        hypr.write_text('# BEGIN MIKU DESKTOP (managed)\nunknown\n')
        with self.assertRaises(RuntimeError): install(no_start=True,no_midnight_bridge=True)
        download.assert_not_called()
        self.assertFalse((self.root/'data/miku-desktop').exists())
