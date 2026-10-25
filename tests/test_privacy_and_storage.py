import base64
import hashlib
import hmac
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
from storage import clean_media

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

init_config=module('init_config',ROOT/'scripts/init_config.py')
privacy_check=module('privacy_check',ROOT/'scripts/privacy_check.py')


class StorageTests(unittest.TestCase):
    def test_cleanup_removes_media_and_partial_files_but_not_open_databases(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve()
            for name in ('clip.mp4','frame.jpg','speech.wav','unfinished.part','runtime.db','runtime.db-wal'):
                (root/name).write_bytes(b'fictional')
            clean_media(root)
            self.assertEqual({path.name for path in root.iterdir()},{'runtime.db','runtime.db-wal'})

    def test_private_configuration_is_valid_and_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            init_config.initialize(directory)
            private=Path(directory)/'private'
            token=(private/'token.txt').read_text().strip()
            payload,signature=token.split('.')
            decode=lambda value:base64.urlsafe_b64decode(value+'='*(-len(value)%4))
            expected=hmac.new((private/'auth_secret.key').read_bytes(),decode(payload),hashlib.sha256).digest()
            self.assertTrue(hmac.compare_digest(expected,decode(signature)))
            settings=json.loads((private/'settings.json').read_text())
            self.assertEqual(settings['cookie'],'')
            self.assertFalse(settings['record_data'])
            self.assertFalse(settings['download_record'])
            with self.assertRaises(SystemExit):init_config.initialize(directory)

    def test_privacy_checker_flags_private_files_without_echoing_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            (path/'private').mkdir()
            (path/'note.txt').write_text('fictional-sensitive-marker',encoding='utf-8')
            findings=privacy_check.inspect(path,['fictional-sensitive-marker'])
            self.assertIn(('note.txt','private deny-list match'),findings)
            self.assertIn(('private','private/generated directory'),findings)
            self.assertNotIn('fictional-sensitive-marker',repr(findings))


if __name__=='__main__':unittest.main()
