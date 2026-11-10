import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from PatchPackages import discover_patches, validate_selection


REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('installer', REPO / 'Install-DeckPhysics.py')
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
        (bundle / 'run').touch()
        for selected in ([], [patches['35140:example']], []):
            layout = {'games': {app_id: dict(game) for app_id, game in self.games.items()}}
            INSTALLER.install_release(bundle, state, layout, None, {}, selected)
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
