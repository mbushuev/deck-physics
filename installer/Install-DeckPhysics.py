#!/usr/bin/env python3
"""Install the two Steam Deck profiles from a local bridge bundle."""

import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit
from urllib.request import urlopen
from zipfile import BadZipFile

from PatchDialog import choose_launch_options, manual_executable
from PatchPackages import checksum as digest
from PatchPackages import without_missing_dependencies


BUNDLE = Path(__file__).resolve().parents[1]
USER_DIR = Path.home()
STEAM = USER_DIR / '.local/share/Steam'
STATE = USER_DIR / '.local/share/amd-physx/deck-proton11'
RUNTIME_DIR = Path('deck-runtime/chkuendig-proton-ab')
VERSION = '1791559474 proton-11.0-2e-x86_64'
WINE_HASH = 'e67b173fbb06ed42a15de73c50024403c2a825e0b044b737005940b87ff5ef9e'
GAMES = {
    '35140': ('Batman: Arkham Asylum GOTY Edition', 'Binaries/ShippingPC-BmGame.exe'),
    '19680': ('Alice: Madness Returns', 'Binaries/Win32/AliceMadnessReturns.exe'),
}
LAUNCH_OPTIONS = {
    'skip_startup_movies': (True, 'Skip intro videos', 'Skip videos before the main menu.'),
    'show_fps': (True, 'Show FPS counter', 'Show FPS and frame time with MangoHud.'),
}
PHYSX_VERSION = '9.23.1019'
PHYSX_NAME = f'PhysX_{PHYSX_VERSION}_SystemSoftware.exe'
PHYSX_URL = f'https://us.download.nvidia.com/Windows/{PHYSX_VERSION}/{PHYSX_NAME}'
PHYSX_SIZE = 29_417_888
PHYSX_HASH = '9b42b84e881769d681e09f62a1b51532616b2e6a2d5d99d0ccae6eb5fbbc208c'
PHYSX_ROOT = Path('pfx/drive_c/Program Files (x86)/NVIDIA Corporation/PhysX')
ALICE_FILES = {
    'Engine/5182B3C9EFEC/PhysXCore.dll': (
        'physx-runtime/alice2/PhysXCore.dll',
        '3824e4825f75d0467043dd07451b5d1bfd9283f32be295af5c84b472c7ace6b5'),
    'Common/PhysXDevice.dll': (
        'PhysXDevice.dll',
        '163a6af59d0235a79b45c6ec9180211f8fa29cf47fc6d53cf9561b9f4f8d5600'),
    'Common/cudart32_65.dll': (
        'physx-runtime/common/cudart32_65.dll',
        'd24f627027c5881b43e43967a96ad2742e22f3a008e58bcde35bd228c4233d8a'),
}
BATMAN_FILES = {
    'Engine/v2.8.1/PhysXCore.dll':
        'df8d6bf07d024b8dce846a4bfcc5fdf4c42afc5e67acd43afb66cf28bfffff88',
    'Engine/v2.8.1/PhysXCooking.dll':
        'c6fd154743ff39427a22aef0c41592ee2b555c046aa32121eeb5fc9e24bc2494',
    'Common/PhysXLoader.dll':
        'eb7dac7ba3520fc57ad34f9c7da893055e44bdb1753ad824525a0114b0e1c211',
}


def matches(path, expected):
    return path.is_file() and digest(path) == expected


def libraries(steam):
    settings = steam / 'steamapps/libraryfolders.vdf'
    contents = settings.read_text() if settings.is_file() else ''
    paths = re.findall(r'^\s*"path"\s+"([^"]+)"', contents, re.M)
    return list(dict.fromkeys((steam / 'steamapps', *(Path(p) / 'steamapps' for p in paths))))


def discover(steam):
    apps = libraries(steam)
    games = {app_id: {'name': name} for app_id, (name, _) in GAMES.items()}
    for app_id, (name, exe_path) in GAMES.items():
        for app_dir in apps:
            manifest = app_dir / f'appmanifest_{app_id}.acf'
            if not manifest.is_file():
                continue
            contents = manifest.read_text()
            match = re.search(r'^\s*"installdir"\s+"([^"]+)"', contents, re.M)
            if not match:
                continue
            exe = app_dir / 'common' / match[1] / exe_path
            if exe.is_file():
                title = re.search(r'^\s*"name"\s+"([^"\r\n]+)"', contents, re.M)
                games[app_id] = {'name': title[1] if title else name, 'exe': str(exe.resolve()),
                                 'prefix': str((app_dir / 'compatdata' / app_id).resolve()), 'source': 'steam'}
                break
    return apps, {'steam': str(steam.resolve()), 'games': games}


def discover_runtime(apps):
    for app_dir in apps:
        proton = app_dir / 'common/Proton 11.0'
        version = proton / 'version'
        if version.is_file() and version.read_text().strip() == VERSION and matches(
                proton / 'files/lib/wine/x86_64-unix/ntdll.so', WINE_HASH):
            break
    else:
        raise RuntimeError('This build requires Valve Proton 11.0-2e. Select Proton 11.0 '
                           'in the game’s Steam properties and let Steam download it.')
    runtime = next((entry for app_dir in apps
                    if (entry := app_dir / 'common/SteamLinuxRuntime_4/_v2-entry-point').is_file()), None)
    if runtime is None:
        raise RuntimeError('Steam Linux Runtime 4 is missing. Let Steam finish installing it.')
    return {'proton': str(proton.resolve()), 'runtime': str(runtime.resolve())}


def configure_games(catalog, choices, state):
    games = {}
    executables = set()
    for app_id, choice in choices.items():
        game = dict(catalog[app_id])
        if path := choice.get('manual_exe'):
            exe = manual_executable(path)
            if str(exe) != game.get('exe'):
                identifier = hashlib.sha256(os.fsencode(exe)).hexdigest()[:16]
                game.update(exe=str(exe), source='manual',
                            prefix=str(state / 'manual-prefixes' / f'{app_id}-{identifier}'))
        if 'exe' not in game or not Path(game['exe']).is_file():
            raise ValueError(f'Choose an executable for {game["name"]}.')
        if game['exe'] in executables:
            raise ValueError('Choose a different executable for each configured game.')
        executables.add(game['exe'])
        game['launch_options'] = choice['launch_options']
        games[app_id] = game
    return games


def find_alice_files(apps, state):
    for library in apps:
        for root in (library / 'compatdata').glob(f'*/{PHYSX_ROOT}'):
            if all(matches(root / source, expected)
                   for source, (_, expected) in ALICE_FILES.items()):
                return {target: root / source for source, (target, _) in ALICE_FILES.items()}
    root = state / 'current/deck-runtime/input'
    if all(matches(root / target, expected) for target, expected in ALICE_FILES.values()):
        return {target: root / target for target, _ in ALICE_FILES.values()}
    return None


def batman_has_physx(prefix):
    registry = prefix / 'pfx/system.reg'
    if not registry.is_file():
        return False
    registered = (r'"PhysXCore Path"="C:\\Program Files (x86)\\NVIDIA Corporation\\PhysX\\Engine"'
                  in registry.read_text(errors='replace'))
    return registered and all(matches(prefix / PHYSX_ROOT / relative, expected)
                              for relative, expected in BATMAN_FILES.items())


def confirm_physx_download(destination):
    message = (f'Download the official NVIDIA PhysX {PHYSX_VERSION} package (about 29 MB). '
               'It provides the runtime files that games and their patches need to work correctly. '
               f'Setup reuses the download across games.\n\nDownload location\n{destination}')
    result = subprocess.run(['kdialog', '--title', f'NVIDIA PhysX {PHYSX_VERSION}',
                             '--yes-label', 'Download Package', '--no-label', 'Skip Package',
                             '--yesno', message], check=False)
    if result.returncode == 1:
        return False
    result.check_returncode()
    return True


def download_physx(destination, progress):
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as output:
        pending = Path(output.name)
        try:
            with urlopen(PHYSX_URL, timeout=25) as response:
                server = urlsplit(response.geturl())
                if server.scheme != 'https' or server.hostname != 'us.download.nvidia.com':
                    raise RuntimeError('The NVIDIA download was redirected to another server.')
                for chunk in iter(lambda: response.read(1024 * 1024), b''):
                    if output.tell() + len(chunk) > PHYSX_SIZE:
                        raise RuntimeError('The NVIDIA download exceeds the expected size.')
                    output.write(chunk)
                    progress(95 * output.tell() // PHYSX_SIZE, 'Downloading from NVIDIA…')
            output.close()
            progress(97, 'Checking SHA-256…')
            if pending.stat().st_size != PHYSX_SIZE or not matches(pending, PHYSX_HASH):
                raise RuntimeError('The NVIDIA download does not match the verified package.')
            os.replace(pending, destination)
            progress(100, 'Package verified.')
        finally:
            pending.unlink(missing_ok=True)


def find_physx_package(state):
    cache = USER_DIR / '.cache/winetricks/physx' / PHYSX_NAME
    local = state / PHYSX_NAME
    return next((candidate for candidate in (local, cache) if matches(candidate, PHYSX_HASH)), None)


def download_physx_with_progress(destination):
    command = ['zenity', '--progress', f'--title=NVIDIA PhysX {PHYSX_VERSION}',
               '--text=Connecting to NVIDIA…', '--percentage=0', '--width=440',
               '--auto-close', '--no-cancel']
    with subprocess.Popen(command, stdin=subprocess.PIPE, bufsize=0) as dialog:
        def update(percent, message):
            try:
                dialog.stdin.write(f'#{message}\n{percent}\n'.encode())
            except BrokenPipeError:
                pass

        try:
            download_physx(destination, update)
        except BaseException:
            if dialog.poll() is None:
                dialog.terminate()
            raise


def prepare_physx_package(state):
    destination = state / PHYSX_NAME
    if find_physx_package(state) is None and confirm_physx_download(destination):
        download_physx_with_progress(destination)


def accept_nvidia_terms(archive, state):
    receipt = state / 'accepted-nvidia-license'
    if receipt.is_file() and receipt.read_text().strip() == PHYSX_HASH:
        return True
    terms = subprocess.check_output(['7z', 'x', '-so', str(archive), 'EULA.txt'])
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=state) as document:
        document.write(terms.decode('cp1252', errors='replace'))
        document.flush()
        result = subprocess.run([
            'zenity', '--text-info', f'--title=NVIDIA PhysX {PHYSX_VERSION}',
            '--width=820', '--height=620', '--filename=' + document.name,
            '--checkbox=I have read and accept the NVIDIA license terms',
        ], check=False)
    if result.returncode == 1:
        return False
    result.check_returncode()
    receipt.write_text(PHYSX_HASH + '\n')
    return True


def extract_alice_files(archive, directory):
    members = {source: 'PhysX/files/' + source for source in ALICE_FILES}
    subprocess.run(['7z', 'x', '-y', '-o' + str(directory), str(archive), *members.values()],
                   check=True, stdout=subprocess.DEVNULL)
    selected = {}
    for source, (target, expected) in ALICE_FILES.items():
        file = directory / members[source]
        if not matches(file, expected):
            raise RuntimeError('Unexpected file in the NVIDIA package: ' + source)
        selected[target] = file
    return selected


def install_batman_physx(archive, layout, prefix, state):
    proton = Path(layout['proton'])
    runtime = Path(layout['runtime'])
    prefix.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    steam_id = '0' if layout['games']['35140'].get('source') == 'manual' else '35140'
    env.update(STEAM_COMPAT_CLIENT_INSTALL_PATH=layout['steam'], STEAM_COMPAT_DATA_PATH=str(prefix),
               STEAM_COMPAT_TOOL_PATHS=f'{proton}:{runtime.parent}', SteamAppId=steam_id,
               SteamGameId=steam_id, PROTON_USE_WOW64='1', WINEDEBUG='-all')
    command = [str(runtime), '--verb=waitforexitandrun', '--', str(proton / 'proton'),
               'waitforexitandrun', str(archive), '/s']
    log_path = state / 'batman-physx-install.log'
    with log_path.open('w') as log:
        result = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180)
    if result.returncode or not batman_has_physx(prefix):
        name = layout['games']['35140']['name']
        raise RuntimeError(f'PhysX installation failed for {name}. See {log_path}')


def prepare_physx(apps, layout, state, temporary, patches):
    games = layout['games']
    alice = find_alice_files(apps, state) if '19680' in games else None
    need_alice = '19680' in games and alice is None
    batman = Path(games['35140']['prefix']) if '35140' in games else None
    need_batman = (batman is not None and any(patch.requires_nvidia_physx for patch in patches)
                   and not batman_has_physx(batman))
    if need_alice or need_batman:
        archive = find_physx_package(state)
        if archive is not None and accept_nvidia_terms(archive, state):
            if need_alice:
                alice = extract_alice_files(archive, temporary)
            if need_batman:
                install_batman_physx(archive, layout, batman, state)
                need_batman = False
    if alice is None:
        games.pop('19680', None)
    if need_batman:
        patches = without_missing_dependencies(patch for patch in patches if not patch.requires_nvidia_physx)
    return alice, patches, need_batman


def check_payload(bundle):
    manifest = json.loads((bundle / 'installer/SHA256.json').read_text())
    for relative, expected in manifest.items():
        if not matches(bundle / relative, expected):
            raise RuntimeError('Installer file failed verification: ' + relative)
    return manifest


def read_installed_layout(release):
    try:
        return json.loads((release / RUNTIME_DIR / 'steam-layout.json').read_text())
    except FileNotFoundError:
        return {}


def install_release(bundle, state, layout, alice, manifest, patches):
    previous = (state / 'current').resolve()
    saved = read_installed_layout(previous)
    games = {app_id: dict(game) for app_id, game in layout['games'].items()}
    kept = {app_id: dict(game) for app_id, game in saved.get('games', {}).items() if app_id not in games}
    for game in kept.values():
        if 'launch_options' in saved:
            game.setdefault('launch_options', saved['launch_options'])
    merged = {**kept, **games}
    if len({game['exe'] for game in merged.values()}) != len(merged):
        raise ValueError('Choose a different executable for each configured game.')
    patches = [patch for patch in patches if patch.app_id in games]
    for patch in patches:
        games[patch.app_id].setdefault('patches', []).append(patch.launch_settings())
    encoded = json.dumps({**layout, 'games': merged}, sort_keys=True)
    identifier = hashlib.sha256((encoded + json.dumps(manifest, sort_keys=True)).encode()).hexdigest()
    release = state / ('release-' + identifier[:16])
    if not release.exists():
        with tempfile.TemporaryDirectory(dir=state) as work:
            stage = Path(work) / 'release'
            shutil.copytree(bundle / 'runtime', stage / RUNTIME_DIR, symlinks=True)
            (stage / RUNTIME_DIR / 'steam-layout.json').write_text(encoded)
            shutil.copy2(bundle / 'installer/run', stage / 'run')
            for app_id in kept:
                relative = RUNTIME_DIR / 'patches' / app_id
                if (previous / relative).is_dir():
                    shutil.copytree(previous / relative, stage / relative, symlinks=True)
            alice_input = Path('deck-runtime/input')
            if '19680' in kept and (previous / alice_input).is_dir():
                shutil.copytree(previous / alice_input, stage / alice_input, symlinks=True)
            if alice:
                for relative, file in alice.items():
                    target = stage / alice_input / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file, target)
            for patch in patches:
                root = stage / RUNTIME_DIR / 'patches' / patch.app_id
                root.mkdir(parents=True, exist_ok=True)
                patch.install(root / patch.id, games[patch.app_id])
            os.replace(stage, release)
    with tempfile.TemporaryDirectory(dir=state) as work:
        pointer = Path(work) / 'current'
        pointer.symlink_to(release.name)
        os.replace(pointer, state / 'current')
    return state / 'current/run'


def main():
    missing = [name for name in ('bwrap', '7z', 'kdialog', 'zenity') if not shutil.which(name)]
    if missing:
        raise RuntimeError('Missing SteamOS tools: ' + ', '.join(missing))
    apps, layout = discover(STEAM)
    manifest = check_payload(BUNDLE)
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (STATE / 'install.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        catalog = layout['games']
        prepare_physx_package(STATE)
        saved = read_installed_layout(STATE / 'current')
        choices = choose_launch_options(saved, catalog, BUNDLE / 'patches', LAUNCH_OPTIONS,
                                        PHYSX_VERSION, lambda: find_physx_package(STATE),
                                        lambda: prepare_physx_package(STATE))
        if choices is None:
            return
        game_choices, selected_patches = choices
        games = configure_games(catalog, game_choices, STATE)
        if not games:
            return
        layout.update(discover_runtime(apps), games=games)
        processes = [Path(game['exe']).name[:15] for game in games.values()]
        if '35140' in games and games['35140']['source'] == 'steam':
            processes.extend(('BmLauncher.exe', 'BmStartApp.exe'))
        if subprocess.run(['pgrep', '-x', '|'.join(re.escape(p) for p in processes)],
                          stdout=subprocess.DEVNULL).returncode == 0:
            name = next(iter(games.values()))['name']
            raise RuntimeError(f'Close {name} before running setup.')
        detected = {app_id: game['name'] for app_id, game in games.items()}
        with tempfile.TemporaryDirectory(dir=STATE) as temp:
            alice, selected_patches, skipped_batman_patches = prepare_physx(
                apps, layout, STATE, Path(temp), selected_patches)
            skipped = [f'Deck Physics cannot launch {name} until its PhysX setup is complete.'
                       for app_id, name in detected.items() if app_id not in games]
            if skipped_batman_patches:
                skipped.append(f'Patches for {detected["35140"]} that require the NVIDIA package were skipped.')
            if not games:
                subprocess.run(['kdialog', '--title', 'PhysX for Steam Deck', '--msgbox',
                                'No games were configured.\n\n' + '\n'.join(skipped)], check=False)
                return
            launch = install_release(BUNDLE, STATE, layout, alice, manifest, selected_patches)

    option = shlex.quote(str(launch)) + ' %command%'
    game = next(iter(games.values()))
    patch_count = len(selected_patches)
    instructions = (f'Configured game\n{game["name"]}\n\nEnabled patches ({patch_count})\n\n'
                    'In Steam, select Proton 11.0 and paste the command below into Launch Options.\n'
                    'Set PhysX to High in the game settings.')
    if game['source'] == 'manual':
        instructions += '\n\nUse the Non-Steam shortcut for the executable you selected.'
    if skipped:
        instructions += '\n\n' + '\n'.join(skipped)
    subprocess.run(['kdialog', '--title', 'Deck Physics Setup Complete', '--inputbox', instructions, option],
                   stdout=subprocess.DEVNULL, check=False)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, BadZipFile, subprocess.SubprocessError) as error:
        print(error, file=sys.stderr)
        if shutil.which('kdialog'):
            subprocess.run(['kdialog', '--error', str(error)], check=False)
        raise SystemExit(1)
