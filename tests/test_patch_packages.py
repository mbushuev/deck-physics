import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

REPO = Path(__file__).resolve().parents[1]
INSTALLER_DIR = REPO / 'installer'
sys.path.insert(0, str(INSTALLER_DIR))

from PatchPackages import discover_patches, validate_selection


SPEC = importlib.util.spec_from_file_location('installer', INSTALLER_DIR / 'Install-DeckPhysics.py')
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)


class PatchPackagesTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.folder = self.root / 'patches'
        self.games = {'35140': {'exe': 'game.exe', 'prefix': 'game-prefix'},
                      '19680': {'exe': 'other.exe', 'prefix': 'other-prefix'}}

    def make_patch(self, folder, app_id, patch_id, files=None, **settings):
        path = self.folder / folder / f'{patch_id}.deckphysx.zip'
        path.parent.mkdir(parents=True, exist_ok=True)
        manifest = dict(format=1, app_id=app_id, id=patch_id, title=patch_id,
                        description='Test patch', **settings)
        with ZipFile(path, 'w') as archive:
            archive.writestr('patch.json', json.dumps(manifest))
            for name, content in (files or {}).items():
                archive.writestr(name, content)
        return path

    def test_only_selected_patches_are_installed_for_each_game(self):
        self.make_patch('alice', '19680', 'example', environment={'EXAMPLE': 'alice'},
                        details='First line.\nSecond line.')
        self.make_patch('renamed-batman-folder', '35140', 'example', {
            'files/prepare.py': 'from pathlib import Path\nimport sys\n'
                                'Path("generated").write_text(sys.argv[1])\n',
        }, prepare='prepare.py', file_environment={'EXAMPLE': 'generated'})
        patches, issues = discover_patches(self.folder, self.games)
        self.assertEqual(issues, [])
        self.assertEqual(set(patches), {'35140:example', '19680:example'})
        self.assertEqual(patches['19680:example'].details, 'First line.\nSecond line.')
        self.assertEqual(patches['35140:example'].details, '')

        state = self.root / 'state'
        state.mkdir()
        bundle = self.root / 'bundle'
        (bundle / 'runtime').mkdir(parents=True)
        (bundle / 'installer').mkdir()
        launcher = bundle / 'installer/run'
        launcher.write_bytes((INSTALLER_DIR / 'run').read_bytes())
        for selected in ([], [patches['35140:example']], []):
            layout = {'games': {app_id: dict(game) for app_id, game in self.games.items()}}
            launch = INSTALLER.install_release(bundle, state, layout, None, {}, selected)
            self.assertEqual(launch, state / 'current/run')
            self.assertEqual(launch.read_bytes(), launcher.read_bytes())
            runtime = state / 'current' / INSTALLER.RUNTIME_DIR
            installed = json.loads((runtime / 'steam-layout.json').read_text())['games']
            generated = runtime / 'patches/35140/example/generated'
            self.assertEqual(generated.is_file(), bool(selected))
            self.assertEqual(bool(installed['35140'].get('patches')), bool(selected))
            self.assertNotIn('patches', installed['19680'])
            if selected:
                self.assertEqual(generated.read_text(), 'game-prefix')

    def test_missing_dependency_and_conflicting_variables_are_rejected(self):
        self.make_patch('batman', '35140', 'base', environment={'SETTING': '1'})
        self.make_patch('batman', '35140', 'child', requires=['base'])
        self.make_patch('batman', '35140', 'conflict', environment={'SETTING': '2'})
        patches, issues = discover_patches(self.folder, self.games)
        self.assertEqual(issues, [])
        with self.assertRaisesRegex(ValueError, 'requires base'):
            validate_selection(patches, {'35140:child'})
        with self.assertRaisesRegex(ValueError, 'conflicts'):
            validate_selection(patches, {'35140:base', '35140:conflict'})
        validate_selection(patches, {'35140:base', '35140:child'})

    def test_batman_package_check_only_applies_to_selected_patches_that_need_it(self):
        self.make_patch('batman', '35140', 'legacy', {'files/prepare.py': ''}, prepare='prepare.py')
        self.make_patch('batman', '35140', 'standalone', {'files/prepare.py': ''},
                        prepare='prepare.py', requires_nvidia_physx=False)
        layout = {'games': {'35140': self.games['35140']}}
        patches, issues = discover_patches(self.folder, layout['games'])
        self.assertFalse(issues)
        self.assertTrue(patches['35140:legacy'].requires_nvidia_physx)
        selected = [patches['35140:standalone']]
        with patch.object(INSTALLER, 'batman_has_physx') as check:
            self.assertEqual(INSTALLER.prepare_physx([], layout, self.root, self.root, selected),
                             (None, selected, False))
        check.assert_not_called()

    def test_skipping_shared_package_keeps_batman_and_its_independent_patches(self):
        self.make_patch('batman', '35140', 'base', requires_nvidia_physx=True)
        self.make_patch('batman', '35140', 'dependent', requires=['base'])
        self.make_patch('batman', '35140', 'indirect', requires=['dependent'])
        self.make_patch('batman', '35140', 'standalone')
        patches, issues = discover_patches(self.folder, self.games)
        self.assertFalse(issues)
        layout = {'games': self.games.copy()}
        with patch.object(INSTALLER, 'find_physx_package', return_value=None) as find:
            alice, selected, skipped = INSTALLER.prepare_physx(
                [], layout, self.root, self.root, list(patches.values()))
        find.assert_called_once_with(self.root)
        self.assertIsNone(alice)
        self.assertTrue(skipped)
        self.assertEqual(selected, [patches['35140:standalone']])
        self.assertEqual(set(layout['games']), {'35140'})

    def test_one_package_sets_up_both_games_when_needed(self):
        self.make_patch('batman', '35140', 'package', requires_nvidia_physx=True)
        patches, issues = discover_patches(self.folder, self.games)
        self.assertFalse(issues)
        selected = list(patches.values())
        layout = {'games': self.games.copy()}
        archive = self.root / 'nvidia.exe'
        alice = {'example.dll': self.root / 'example.dll'}
        with (patch.object(INSTALLER, 'find_physx_package', return_value=archive) as find,
              patch.object(INSTALLER, 'accept_nvidia_terms', return_value=True) as terms,
              patch.object(INSTALLER, 'extract_alice_files', return_value=alice) as extract,
              patch.object(INSTALLER, 'install_batman_physx') as install):
            self.assertEqual(INSTALLER.prepare_physx([], layout, self.root, self.root, selected),
                             (alice, selected, False))
        find.assert_called_once_with(self.root)
        terms.assert_called_once_with(archive, self.root)
        extract.assert_called_once_with(archive, self.root)
        install.assert_called_once_with(archive, layout, Path('game-prefix'), self.root)
        self.assertEqual(set(layout['games']), {'35140', '19680'})

    def test_package_step_downloads_once_and_reuses_verified_archive(self):
        archive = self.root / INSTALLER.PHYSX_NAME
        data = b'test NVIDIA package'
        archive.write_bytes(b'corrupt cached package')
        with (patch.object(INSTALLER, 'PHYSX_HASH', hashlib.sha256(data).hexdigest()),
              patch.object(INSTALLER, 'USER_DIR', self.root),
              patch.object(INSTALLER, 'confirm_physx_download', return_value=True) as confirm,
              patch.object(INSTALLER, 'download_physx_with_progress',
                           side_effect=lambda file: file.write_bytes(data)) as download):
            self.assertIsNone(INSTALLER.find_physx_package(self.root))
            INSTALLER.prepare_physx_package(self.root)
            INSTALLER.prepare_physx_package(self.root)
            self.assertEqual(INSTALLER.find_physx_package(self.root), archive)
        confirm.assert_called_once_with()
        download.assert_called_once_with(archive)

    def test_download_reaches_100_only_after_package_verification(self):
        archive = self.root / INSTALLER.PHYSX_NAME
        data = b'test NVIDIA package'
        with (patch.object(INSTALLER, 'PHYSX_SIZE', len(data)),
              patch.object(INSTALLER, 'PHYSX_HASH', hashlib.sha256(data).hexdigest()),
              patch.object(INSTALLER, 'urlopen') as open_url):
            for payload in (b'x' * len(data), data):
                response = io.BytesIO(payload)
                response.geturl = lambda: INSTALLER.PHYSX_URL
                open_url.return_value = response
                updates = []

                def progress(percent, _message):
                    updates.append((percent, archive.is_file()))

                if payload != data:
                    with self.assertRaisesRegex(RuntimeError, 'does not match'):
                        INSTALLER.download_physx(archive, progress)
                    self.assertEqual(updates, [(95, False), (97, False)])
                    self.assertFalse(list(self.root.iterdir()))
                else:
                    INSTALLER.download_physx(archive, progress)
                    self.assertEqual(updates, [(95, False), (97, False), (100, True)])
                    self.assertEqual(archive.read_bytes(), data)

    def test_unsafe_or_replaced_archives_cannot_be_extracted(self):
        self.make_patch('batman', '35140', 'invalid', {'files/../escape': 'payload'})
        self.make_patch('batman', '35140', 'valid')
        patches, issues = discover_patches(self.folder, self.games)
        self.assertEqual(set(patches), {'35140:valid'})
        self.assertEqual(len(issues), 1)
        self.make_patch('batman', '35140', 'valid', environment={'CHANGED': '1'})
        target = self.root / 'installed'
        with self.assertRaisesRegex(ValueError, 'changed after selection'):
            patches['35140:valid'].install(target, self.games['35140'])
        self.assertFalse(target.exists())
