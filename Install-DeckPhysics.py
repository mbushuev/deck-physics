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

from PatchDialog import choose_launch_options
from PatchPackages import checksum as digest


HERE = Path(__file__).resolve().parent
USER_DIR = Path.home()
STEAM = USER_DIR / '.local/share/Steam'
STATE = USER_DIR / '.local/share/amd-physx/deck-proton11'
RUNTIME_DIR = Path('deck-runtime/chkuendig-proton-ab')
VERSION = '1791559474 proton-11.0-2e-x86_64'
WINE_HASH = 'e67b173fbb06ed42a15de73c50024403c2a825e0b044b737005940b87ff5ef9e'
GAMES = {
    '35140': ('Batman: Arkham Asylum GOTY', 'Binaries/ShippingPC-BmGame.exe'),
    '19680': ('Alice: Madness Returns', 'Binaries/Win32/AliceMadnessReturns.exe'),
}
LAUNCH_OPTIONS = {
    'skip_startup_movies': (True, 'Skip intro videos', 'Skip videos before the main menu.'),
    'show_fps': (True, 'Show FPS counter', 'Show FPS and frame time with MangoHud.'),
}
PHYSX_NAME = 'PhysX_9.23.1019_SystemSoftware.exe'
PHYSX_URL = 'https://us.download.nvidia.com/Windows/9.23.1019/' + PHYSX_NAME
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
    paths = re.findall(r'^\s*"path"\s+"([^"]+)"', settings.read_text(), re.M)
    return list(dict.fromkeys((steam / 'steamapps', *(Path(p) / 'steamapps' for p in paths))))


def discover(steam):
    apps = libraries(steam)
    games = {}
    for app_id, (name, exe_path) in GAMES.items():
        for app_dir in apps:
            manifest = app_dir / f'appmanifest_{app_id}.acf'
            if not manifest.is_file():
                continue
            match = re.search(r'^\s*"installdir"\s+"([^"]+)"', manifest.read_text(), re.M)
            if not match:
                continue
            exe = app_dir / 'common' / match[1] / exe_path
            if exe.is_file():
                games[app_id] = {'name': name, 'exe': str(exe.resolve()),
                                 'prefix': str((app_dir / 'compatdata' / app_id).resolve())}
                break
    if not games:
        raise RuntimeError('Steam could not find an installed copy of Batman or Alice.')

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
    return apps, {'steam': str(steam.resolve()), 'proton': str(proton.resolve()),
                  'runtime': str(runtime.resolve()), 'games': games}


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


def confirm_physx(game, requirement):
    message = (f'{game} requires {requirement}.\n\n'
               'The installer will reuse a verified local copy of NVIDIA PhysX 9.23.1019 '
               'or download it from NVIDIA (about 29 MB) if needed.\n\n'
               f'If you skip this step, Deck Physics cannot launch {game}.')
    result = subprocess.run(['kdialog', '--title', f'PhysX for {game}',
                             '--yes-label', f'Set Up {game}', '--no-label', f'Skip {game}',
                             '--yesno', message], check=False)
    if result.returncode == 1:
        return False
    result.check_returncode()
    return True


def download_physx(destination):
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
            output.close()
            if pending.stat().st_size != PHYSX_SIZE or not matches(pending, PHYSX_HASH):
                raise RuntimeError('The NVIDIA download does not match the verified package.')
            os.replace(pending, destination)
        finally:
            pending.unlink(missing_ok=True)


def acquire_physx(state):
    cache = USER_DIR / '.cache/winetricks/physx' / PHYSX_NAME
    local = state / PHYSX_NAME
    for candidate in (local, cache):
        if matches(candidate, PHYSX_HASH):
            return candidate
    subprocess.run(['kdialog', '--passivepopup', 'Downloading PhysX 9.23.1019 from NVIDIA…', '5'])
    download_physx(local)
    return local


def accept_nvidia_terms(archive, state):
    receipt = state / 'accepted-nvidia-license'
    if receipt.is_file() and receipt.read_text().strip() == PHYSX_HASH:
        return True
    terms = subprocess.check_output(['7z', 'x', '-so', str(archive), 'EULA.txt'])
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=state) as document:
        document.write(terms.decode('cp1252', errors='replace'))
        document.flush()
        result = subprocess.run([
            'zenity', '--text-info', '--title=NVIDIA PhysX 9.23.1019',
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
    env.update(STEAM_COMPAT_CLIENT_INSTALL_PATH=layout['steam'], STEAM_COMPAT_DATA_PATH=str(prefix),
               STEAM_COMPAT_TOOL_PATHS=f'{proton}:{runtime.parent}', SteamAppId='35140',
               SteamGameId='35140', PROTON_USE_WOW64='1', WINEDEBUG='-all')
    command = [str(runtime), '--verb=waitforexitandrun', '--', str(proton / 'proton'),
               'waitforexitandrun', str(archive), '/s']
    log_path = state / 'batman-physx-install.log'
    with log_path.open('w') as log:
        result = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180)
    if result.returncode or not batman_has_physx(prefix):
        raise RuntimeError(f'PhysX installation failed in the Batman Proton prefix. See {log_path}')


def prepare_physx(apps, layout, state, temporary):
    games = layout['games']
    alice = find_alice_files(apps, state) if '19680' in games else None
    batman = Path(games['35140']['prefix']) if '35140' in games else None
    need_batman = batman is not None and not batman_has_physx(batman)
    setup_alice = ('19680' in games and alice is None
                   and confirm_physx('Alice', 'the NVIDIA PhysX 2.8.4.11 files'))
    setup_batman = (need_batman
                    and confirm_physx('Batman', 'a registered PhysX 2.8.1 runtime in its Proton prefix'))
    if setup_alice or setup_batman:
        archive = acquire_physx(state)
        if accept_nvidia_terms(archive, state):
            if setup_alice:
                alice = extract_alice_files(archive, temporary)
            if setup_batman:
                install_batman_physx(archive, layout, batman, state)
        else:
            setup_batman = False
    if alice is None:
        games.pop('19680', None)
    if need_batman and not setup_batman:
        games.pop('35140')
    return alice


def check_payload(bundle):
    manifest = json.loads((bundle / 'SHA256.json').read_text())
    for relative, expected in manifest.items():
        if not matches(bundle / relative, expected):
            raise RuntimeError('Installer file failed verification: ' + relative)
    return manifest


def install_release(bundle, state, layout, alice, manifest, patches):
    games = layout['games']
    patches = [patch for patch in patches if patch.app_id in games]
    for patch in patches:
        games[patch.app_id].setdefault('patches', []).append(patch.launch_settings())
    encoded = json.dumps(layout, sort_keys=True)
    identifier = hashlib.sha256((encoded + json.dumps(manifest, sort_keys=True)).encode()).hexdigest()
    release = state / ('release-' + identifier[:16])
    if not release.exists():
        with tempfile.TemporaryDirectory(dir=state) as work:
            stage = Path(work) / 'release'
            shutil.copytree(bundle / 'runtime', stage / RUNTIME_DIR, symlinks=True)
            (stage / RUNTIME_DIR / 'steam-layout.json').write_text(encoded)
            shutil.copy2(bundle / 'run', stage / 'run')
            if alice:
                for relative, file in alice.items():
                    target = stage / 'deck-runtime/input' / relative
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
    manifest = check_payload(HERE)
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (STATE / 'install.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        games = layout['games']
        processes = [Path(g['exe']).name[:15] for g in games.values()]
        if '35140' in games:
            processes.extend(('BmLauncher.exe', 'BmStartApp.exe'))
        if subprocess.run(['pgrep', '-x', '|'.join(re.escape(p) for p in processes)],
                          stdout=subprocess.DEVNULL).returncode == 0:
            raise RuntimeError('Close Batman and Alice before running the installer.')
        previous = STATE / 'current' / RUNTIME_DIR / 'steam-layout.json'
        choices = choose_launch_options(previous, games, HERE / 'patches', LAUNCH_OPTIONS)
        if choices is None:
            return
        game_options, selected_patches = choices
        for app_id, options in game_options.items():
            games[app_id]['launch_options'] = options
        detected = tuple(games)
        with tempfile.TemporaryDirectory(dir=STATE) as temp:
            alice = prepare_physx(apps, layout, STATE, Path(temp))
            skipped = '\n'.join(f'Deck Physics cannot launch {GAMES[app_id][0]} until its PhysX setup is complete.'
                                for app_id in detected if app_id not in games)
            if not games:
                subprocess.run(['kdialog', '--title', 'PhysX for Steam Deck', '--msgbox',
                                'No games were configured.\n\n' + skipped], check=False)
                return
            launch = install_release(HERE, STATE, layout, alice, manifest, selected_patches)

    names = ', '.join(game['name'] for game in layout['games'].values())
    option = shlex.quote(str(launch)) + ' %command%'
    patch_count = sum(len(game.get('patches', ())) for game in layout['games'].values())
    instructions = (f'Installed for {names}.\n'
                    f'Enabled game patches: {patch_count}.\n\n'
                    'Select Proton 11.0 in the Steam properties for each game.\n'
                    'Copy the line below into each game’s Launch Options.\n'
                    'Set PhysX to High in the game settings.')
    if skipped:
        instructions += '\n\n' + skipped
    subprocess.run(['kdialog', '--title', 'PhysX for Steam Deck', '--inputbox', instructions, option],
                   stdout=subprocess.DEVNULL, check=False)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, BadZipFile, subprocess.SubprocessError) as error:
        print(error, file=sys.stderr)
        if shutil.which('kdialog'):
            subprocess.run(['kdialog', '--error', str(error)], check=False)
        raise SystemExit(1)
