import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / 'installer'), str(REPO / 'runtime')]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, REPO / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


INSTALLER = load('game_setup', 'installer/Install-DeckPhysics.py')
RUNTIME = load('game_runtime', 'runtime/Run-DeckPhysics.py')

from PatchDialog import PatchDialog
import proton_compatibility as COMPAT


class GameProfilesTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()

    def test_catalog_is_visible_without_games_or_proton(self):
        apps, layout = INSTALLER.discover(self.root / 'Steam')
        self.assertEqual(set(layout['games']), {'35140', '19680', '50130'})
        self.assertTrue(all(set(game) == {'name'} for game in layout['games'].values()))
        self.assertEqual(INSTALLER.discover_runtime(apps), {'proton': None, 'runtime': None})

    def test_discovers_steam_mafia_classic(self):
        steam = self.root / 'Steam'
        apps = steam / 'steamapps'
        exe = apps / 'common/Mafia II/pc/mafia2.exe'
        exe.parent.mkdir(parents=True)
        exe.touch()
        (apps / 'appmanifest_50130.acf').write_text('  "installdir"  "Mafia II"\n')
        _, layout = INSTALLER.discover(steam)
        self.assertEqual(layout['games']['50130']['exe'], str(exe))
        self.assertEqual(layout['games']['50130']['prefix'], str(apps / 'compatdata/50130'))

    def test_compatible_depot_is_selected_without_a_version_label(self):
        steam = self.root / 'Steam'
        selected = steam / 'steamapps/common/Proton 11.0'
        cached = steam / 'steamrt64/steamapps/content/app_4628710/depot_4628711'
        relative = 'x86_64-unix/ntdll.so'
        for tool, binary in ((selected, b'new Wine'), (cached, b'compatible Wine')):
            wine = tool / 'files/lib/wine' / relative
            wine.parent.mkdir(parents=True)
            wine.write_bytes(binary)
            (tool / 'proton').touch()
        abi = {relative: hashlib.sha256(b'compatible Wine').hexdigest()}
        with patch.object(COMPAT, 'WINE_ABI', abi):
            self.assertEqual(COMPAT.select_bridge_proton(selected, steam), cached)
            self.assertEqual(COMPAT.select_bridge_proton(cached, steam), cached)
            (cached / 'files/lib/wine' / relative).write_bytes(b'updated Wine')
            self.assertIsNone(COMPAT.select_bridge_proton(selected, steam))

    def test_incompatible_tool_starts_original_command_without_bridge(self):
        app_id = '50130'
        exe = self.root / 'games/Mafia II/pc/mafia2.exe'
        entry = self.root / COMPAT.RUNTIME
        proton = self.root / 'Proton 12.0' / 'proton'
        command = [str(entry), str(proton), 'waitforexitandrun', str(exe)]
        prefix = self.root / 'compatdata' / app_id
        layout = {'games': {app_id: {'exe': str(exe), 'prefix': str(prefix)}}}
        with (patch.object(RUNTIME, 'select_bridge_proton', return_value=None),
              patch.object(RUNTIME, 'RELEASE', self.root),
              patch.object(RUNTIME, 'patch_null_host_free') as patch_bridge,
              patch.object(RUNTIME.subprocess, 'call', return_value=0) as run,
              patch.dict(RUNTIME.os.environ, {'STEAM_COMPAT_DATA_PATH': str(prefix)}, clear=True)):
            self.assertEqual(RUNTIME.launch(command, self.root, app_id, layout), 0)
        patch_bridge.assert_not_called()
        self.assertEqual(run.call_args.args[0], command)
        self.assertNotIn('PROTON_ENABLE_ZLUDA', run.call_args.kwargs['env'])
        self.assertIn('standard settings', (self.root / f'launch-{app_id}.log').read_text())

    def test_mafia_intro_skip_preserves_other_movies(self):
        exe = self.root / 'Mafia II/pc/mafia2.exe'
        videos = exe.parent / 'sds/video'
        videos.mkdir(parents=True)
        for movie in ('Logos.bik', 'NVidia_logo.bik', 'fmv0000.bik'):
            (videos / movie).touch()
        mount = []
        RUNTIME.hide_mafia_intro_movies(mount, exe)
        cutscene = str(videos / 'fmv0000.bik')
        self.assertEqual(mount, ['--tmpfs', str(videos), '--ro-bind', cutscene, cutscene])
        self.assertTrue((videos / 'Logos.bik').exists())

    def test_manual_choice_uses_a_stable_separate_prefix_and_rejects_duplicates(self):
        _, layout = INSTALLER.discover(self.root / 'Steam')
        catalog = layout['games']
        executable = self.root / 'Manual copy.EXE'
        executable.touch()
        state = self.root / 'state'
        choices = {'35140': {'manual_exe': str(executable), 'launch_options': {'show_fps': True}}}
        game = INSTALLER.configure_games(catalog, choices, state)['35140']
        self.assertEqual(game['source'], 'manual')
        self.assertEqual(game['exe'], str(executable))
        self.assertEqual(Path(game['prefix']).parent, state / 'manual-prefixes')
        self.assertEqual(INSTALLER.configure_games(catalog, choices, state)['35140'], game)
        self.assertNotIn('exe', catalog['35140'])
        choices['19680'] = choices['35140']
        with self.assertRaisesRegex(ValueError, 'different executable'):
            INSTALLER.configure_games(catalog, choices, state)

    def test_setup_submits_only_the_active_game_and_its_patches(self):
        alice = self.root / 'Alice.exe'
        alice.touch()
        setup = PatchDialog.__new__(PatchDialog)
        setup.games = {'35140': {'name': 'Batman'}, '19680': {'name': 'Alice'}}
        setup.active_game = '19680'
        setup.manual_paths = {'35140': '/missing.exe', '19680': str(alice)}
        setup.game_options = {'35140': {'show_fps': True},
                              '19680': {'show_fps': True, 'frame_rate': 'default'}}
        setup.options = {'show_fps': Mock(**{'get_active.return_value': False})}
        setup.frame_rate = Mock(**{'get_active_id.return_value': '90'})
        setup.patches = {
            '35140:unused': SimpleNamespace(app_id='35140'),
            '19680:chosen': SimpleNamespace(app_id='19680'),
        }
        setup.selected = set(setup.patches)
        setup.gtk = SimpleNamespace(ResponseType=SimpleNamespace(OK=1))
        setup.dialog = Mock(**{'run.return_value': 1})
        setup.error = Mock()
        setup.continue_button = Mock()

        with patch('PatchDialog.validate_selection') as validate:
            choices, patches = setup.run()
        validate.assert_called_once_with(setup.patches, {'19680:chosen'})
        self.assertEqual(choices, {'19680': {'launch_options': {'show_fps': False, 'frame_rate': '90'},
                                           'manual_exe': str(alice)}})
        self.assertEqual(patches, [setup.patches['19680:chosen']])

    def test_non_steam_shortcut_matches_only_a_manually_selected_executable(self):
        manual = self.root / 'manual.exe'
        library = self.root / 'library.exe'
        games = {'35140': {'exe': str(library)}, '19680': {'source': 'manual', 'exe': str(manual)}}
        command = ['runtime', 'proton', 'waitforexitandrun', str(manual)]
        self.assertEqual(RUNTIME.select_game(command, '3200000000', games), '19680')
        self.assertEqual(RUNTIME.select_game(['proton', str(library)], '35140', games), '35140')
        with self.assertRaisesRegex(ValueError, 'not configured'):
            RUNTIME.select_game(['proton', str(library)], '3200000000', games)
        with self.assertRaisesRegex(ValueError, 'Non-Steam shortcut'):
            RUNTIME.select_game(command, '19680', games)

    def test_selecting_the_detected_executable_keeps_the_steam_prefix(self):
        executable = self.root / 'Alice.exe'
        executable.touch()
        game = {'name': 'Alice', 'exe': str(executable), 'source': 'steam', 'prefix': str(self.root / 'steam')}
        choices = {'19680': {'manual_exe': str(executable), 'launch_options': {}}}
        configured = INSTALLER.configure_games({'19680': game}, choices, self.root / 'state')
        self.assertEqual(configured['19680'], dict(game, launch_options={}))

    def test_manual_launch_uses_the_prepared_prefix(self):
        release = self.root / 'release'
        release.mkdir()
        work = release / 'work'
        work.mkdir()
        prefix = self.root / 'manual-prefix'
        shortcut_prefix = self.root / 'steam-shortcut-prefix'
        proton = self.root / 'Proton 11.0'
        runtime = self.root / COMPAT.RUNTIME
        executable = self.root / 'games/Batman/Binaries/manual.exe'
        layout = {'proton': str(proton), 'runtime': str(runtime), 'games': {
            '35140': {'source': 'manual', 'prefix': str(prefix), 'exe': str(executable)}}}
        command = [str(runtime), str(proton / 'proton'), 'waitforexitandrun', str(executable)]

        with (patch.object(RUNTIME, 'select_bridge_proton', return_value=proton),
              patch.object(RUNTIME, 'RELEASE', release), patch.object(RUNTIME, 'patch_null_host_free'),
              patch.object(RUNTIME.subprocess, 'call', return_value=0) as run,
              patch.dict(RUNTIME.os.environ, {'STEAM_COMPAT_DATA_PATH': str(shortcut_prefix)})):
            self.assertEqual(RUNTIME.launch(command, work, '35140', layout), 0)
        self.assertTrue(prefix.is_dir())
        self.assertFalse(shortcut_prefix.exists())
        self.assertEqual(run.call_args.kwargs['env']['STEAM_COMPAT_DATA_PATH'], str(prefix))
        self.assertIn(str(executable), run.call_args.args[0])
        self.assertNotIn('-NoFPSCap', run.call_args.args[0])

    def test_game_and_prefix_replacements_are_read_only_and_check_updates(self):
        exe = self.root / 'Game/pc/game.exe'
        prefix = self.root / 'prefix'
        engine = prefix / 'Program Files (x86)/Engine/engine.dll'
        patch_dir = self.root / 'runtime/patches/50130/performance'
        for path in (exe, engine, patch_dir / 'new.exe', patch_dir / 'new.dll'):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'original' if path in (exe, engine) else b'replacement')
        digest = hashlib.sha256(b'original').hexdigest()
        replacements = [
            {'root': 'game', 'target': 'game.exe', 'source': 'new.exe', 'original_sha256': digest},
            {'root': 'prefix', 'target': 'Program Files (x86)/Engine/engine.dll',
             'source': 'new.dll', 'original_sha256': digest},
        ]
        layout = {'games': {'50130': {'exe': str(exe), 'prefix': str(prefix), 'patches': [
            {'id': 'performance', 'file_environment': {}, 'preload': None, 'environment': {},
             'replacements': replacements},
        ]}}}
        proton = self.root / 'Proton 11.0'
        argv = [str(self.root / COMPAT.RUNTIME), str(proton / 'proton'), 'waitforexitandrun', str(exe)]
        with (patch.object(RUNTIME, 'BASE', self.root / 'runtime'),
              patch.object(RUNTIME, 'RELEASE', self.root),
              patch.object(RUNTIME, 'select_bridge_proton', return_value=proton),
              patch.object(RUNTIME, 'patch_null_host_free'),
              patch.object(RUNTIME.subprocess, 'call', return_value=0) as run,
              patch.dict(RUNTIME.os.environ, {'STEAM_COMPAT_DATA_PATH': str(prefix)})):
            self.assertEqual(RUNTIME.launch(argv.copy(), self.root, '50130', layout), 0)
            command = run.call_args.args[0]
            for original, name in ((exe, 'new.exe'), (engine, 'new.dll')):
                position = command.index(str(patch_dir / name))
                self.assertEqual(command[position - 1:position + 2],
                                 ['--ro-bind', str(patch_dir / name), str(original)])
                self.assertEqual(original.read_bytes(), b'original')
            run.reset_mock()
            engine.write_bytes(b'updated')
            with self.assertRaisesRegex(ValueError, 'does not support'):
                RUNTIME.launch(argv.copy(), self.root, '50130', layout)
            run.assert_not_called()

    def test_alice_frame_rate_option_applies_the_game_flag_and_optional_dxvk_limit(self):
        release = self.root / 'release'
        runtime = self.root / COMPAT.RUNTIME
        proton = self.root / 'Proton 11.0'
        executable = self.root / 'Alice.exe'
        game = {'source': 'manual', 'prefix': str(self.root / 'prefix'), 'exe': str(executable)}
        layout = {'proton': str(proton), 'runtime': str(runtime), 'games': {'19680': game}}
        config = 'd3d9.presentInterval = 0'
        cases = (
            ({'frame_rate': 'default'}, [], [], config),
            ({'frame_rate': '60'}, [], ['-NoFPSCap'], config + ';d3d9.maxFrameRate = 60'),
            ({'frame_rate': '90'}, ['-nofpscap'], ['-nofpscap'], config + ';d3d9.maxFrameRate = 90'),
            ({'frame_rate': 'uncapped'}, [], ['-NoFPSCap'], config),
            ({'unlock_fps': True}, [], ['-NoFPSCap'], config),
            ({'frame_rate': 'default', 'unlock_fps': True}, [], [], config),
        )
        for options, existing, expected, expected_config in cases:
            with self.subTest(options=options, existing=existing):
                game['launch_options'] = {'show_fps': False, **options}
                command = [str(runtime), str(proton / 'proton'), 'waitforexitandrun',
                           str(executable), *existing]
                with (patch.object(RUNTIME, 'select_bridge_proton', return_value=proton),
                      patch.object(RUNTIME, 'RELEASE', release), patch.object(RUNTIME, 'patch_null_host_free'),
                      patch.dict(RUNTIME.os.environ, {'DXVK_CONFIG': config}, clear=True),
                      patch.object(RUNTIME.os, 'link'), patch.object(RUNTIME.subprocess, 'call') as run):
                    release.mkdir(exist_ok=True)
                    with tempfile.TemporaryDirectory(dir=release) as work:
                        RUNTIME.launch(command, Path(work), '19680', layout)
                self.assertEqual([arg for arg in run.call_args.args[0] if arg.lower() == '-nofpscap'],
                                 expected)
                self.assertEqual(run.call_args.kwargs['env']['DXVK_CONFIG'], expected_config)
                self.assertNotIn('MANGOHUD', run.call_args.kwargs['env'])
