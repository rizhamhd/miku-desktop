import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from miku import assets

class AssetTests(unittest.TestCase):
    def test_checksum_and_selected_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            # Minimal PNG header fixture; runtime only checks dimensions after pinned hashes.
            png=b'\x89PNG\r\n\x1a\n'+b'\x00\x00\x00\rIHDR'+(128).to_bytes(4,'big')*2
            stream=io.BytesIO()
            with zipfile.ZipFile(stream,'w') as z:
                for name in assets.REQUIRED: z.writestr('pack/miku/'+name,png)
                z.writestr('pack/LICENSE','Test license')
                z.writestr('../../outside','must not be extracted')
            data=stream.getvalue(); archive=root/'pack.zip'; archive.write_bytes(data)
            spec=dict(url='unused',sha256=hashlib.sha256(data).hexdigest(),prefix='pack/miku/',licensePath='pack/LICENSE',files={n:hashlib.sha256(png).hexdigest() for n in assets.REQUIRED})
            (root/'assets.json').write_text(json.dumps(spec))
            target=root/'sprites/miku'
            with patch('miku.assets.ROOT',root),patch('miku.assets.sprite_path',return_value=target):
                assets.install(archive)
                self.assertEqual(len(list(target.glob('*.png'))),46)
                self.assertFalse((root/'outside').exists())
                self.assertEqual(assets.install(archive),target)
            spec['sha256']='bad'; (root/'assets.json').write_text(json.dumps(spec))
            with patch('miku.assets.ROOT',root),patch('miku.assets.sprite_path',return_value=root/'other'):
                with self.assertRaises(ValueError): assets.install(archive)
                self.assertFalse((root/'other').exists())
