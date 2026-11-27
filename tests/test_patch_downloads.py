import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'installer'))
from PatchDownloads import download_patches
from PatchPackages import discover_patches


def archive(app_id, patch_id):
    stream = io.BytesIO()
    with ZipFile(stream, 'w') as package:
        package.writestr('patch.json', json.dumps({
            'format': 1, 'app_id': app_id, 'id': patch_id, 'title': patch_id, 'description': 'Test patch',
        }))
    return stream.getvalue()


class PatchDownloadsTest(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        root = Path(work.name)
        self.folder = root / 'patches'
        self.cache = root / 'downloads'
        self.payloads = {}
        self.entries = {}
        self.fetch = self.enterContext(patch('PatchDownloads.fetch', side_effect=self.response))

    def publish(self, app_id, patch_id, content):
        path = f'patches/game-{app_id}/{patch_id}.deckphysx.zip'
        self.entries.setdefault(app_id, []).append({
            'path': path, 'size': len(content), 'sha256': hashlib.sha256(content).hexdigest(),
        })
        self.payloads[path] = content
        return path

    def response(self, path, _limit):
        if path == 'catalog.json':
            return json.dumps({'format': 1, 'games': self.entries}).encode()
        return self.payloads[path]

    def test_download_scopes_to_selected_game_and_appears_in_patch_list(self):
        self.publish('50130', 'gpu-clothing', archive('50130', 'gpu-clothing'))
        self.publish('19680', 'other', archive('19680', 'other'))

        self.assertEqual(download_patches(self.cache, '50130'), 1)
        self.assertEqual(self.fetch.call_count, 2)
        self.assertFalse((self.cache / '19680').exists())

        patches, issues = discover_patches(self.folder, ['50130', '19680'], self.cache)
        self.assertEqual(issues, [])
        self.assertEqual(set(patches), {'50130:gpu-clothing'})

    def test_failed_verification_leaves_previous_set_active(self):
        path = self.publish('50130', 'gpu-clothing', archive('50130', 'gpu-clothing'))
        download_patches(self.cache, '50130')
        current = self.cache / '50130/current'
        old = current.resolve()
        self.payloads[path] = archive('19680', 'gpu-clothing')

        with self.assertRaisesRegex(ValueError, 'did not match the patch catalog'):
            download_patches(self.cache, '50130')
        self.assertEqual(current.resolve(), old)

    def test_valid_archive_for_another_game_is_rejected(self):
        self.publish('50130', 'gpu-clothing', archive('19680', 'gpu-clothing'))
        with self.assertRaisesRegex(ValueError, 'does not match the selected game'):
            download_patches(self.cache, '50130')
        self.assertFalse((self.cache / '50130/current').exists())

    def test_catalog_rejects_path_traversal(self):
        self.publish('50130', 'gpu-clothing', archive('50130', 'gpu-clothing'))
        self.entries['50130'][0]['path'] = 'patches/../gpu-clothing.deckphysx.zip'
        with self.assertRaisesRegex(ValueError, 'Invalid patch in the catalog'):
            download_patches(self.cache, '50130')
        self.assertEqual(self.fetch.call_count, 1)
