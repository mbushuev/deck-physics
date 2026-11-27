#!/usr/bin/env python3
"""Launch Steam games with the GPU PhysX bridge when compatible Wine is available."""

import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from alice_bridge_patch import patch_null_host_free
from patch_replacements import original_file, replacement_file, validate_replacements
from proton_compatibility import RUNTIME, STEAM, select_bridge_proton


BASE = Path(__file__).resolve().parent
RELEASE = BASE.parent.parent


def bind_file(mount, source, target):
    mount.extend(('--ro-bind', str(source), str(target)))


def hide_mafia_intro_movies(mount, executable):
    videos = executable.parent / 'sds/video'
    if not videos.is_dir():
        return
    mount.extend(('--tmpfs', str(videos)))
    for entry in sorted(videos.iterdir()):
        if entry.name.lower() not in ('logos.bik', 'nvidia_logo.bik'):
            bind_file(mount, entry, entry)


def select_game(command, steam_id, games):
    if steam_id in games:
        if games[steam_id].get('source', 'steam') == 'steam':
            return steam_id
        raise ValueError('Launch the selected executable from its Non-Steam shortcut.')

    proton = next((i for i, arg in enumerate(command) if Path(arg).name == 'proton'), len(command))
    executables = {Path(arg).resolve() for arg in command[proton + 1:] if Path(arg).suffix.lower() == '.exe'}
    matching = [app_id for app_id, game in games.items()
                if game.get('source') == 'manual' and Path(game['exe']) in executables]
    if len(matching) == 1:
        return matching[0]
    raise ValueError('This Steam game or Non-Steam shortcut is not configured. Run the installer first.')


def launch(command, work, app_id, layout):
    game = layout['games'][app_id]
    options = game.get('launch_options', layout.get('launch_options', {}))
    batman = app_id == '35140'
    manual = game.get('source') == 'manual'
    executable = Path(game['exe'])
    allowed = {executable}
    if batman and not manual:
        allowed.update(executable.with_name(name) for name in ('BmLauncher.exe', 'BmStartApp.exe'))
    runtime_indices = [i for i, arg in enumerate(command) if Path(arg).name == RUNTIME.name]
    proton_indices = [i for i, arg in enumerate(command) if Path(arg).name == 'proton']
    game_indices = [i for i, arg in enumerate(command) if Path(arg).suffix.lower() == '.exe'
                    and Path(arg).resolve() in allowed]
    if len(game_indices) != 1:
        raise ValueError('Expected a Steam launch of the configured game.')
    gi = game_indices[0]
    steam_prefix = os.environ.get('STEAM_COMPAT_DATA_PATH')
    prefix = Path(game['prefix'])
    if not manual and (not steam_prefix or Path(steam_prefix).resolve() != prefix):
        raise ValueError('Expected the installed game’s Steam prefix.')
    launch_env = os.environ.copy()
    if manual:
        prefix.mkdir(parents=True, exist_ok=True)
        launch_env['STEAM_COMPAT_DATA_PATH'] = str(prefix)

    log_path = RELEASE / f'launch-{app_id}.log'
    selected = None
    proton = None
    if (len(runtime_indices) == len(proton_indices) == 1
            and runtime_indices[0] < proton_indices[0] < gi
            and Path(command[runtime_indices[0]]).resolve().parent.name == RUNTIME.parent.name):
        pi = proton_indices[0]
        selected = Path(command[pi]).resolve().parent
        proton = select_bridge_proton(selected, Path(layout.get('steam', STEAM)), layout.get('proton'))
    if proton is None:
        message = ('Deck Physics found no Wine build matching the GPU bridge for this Steam launch. '
                   'Starting with Steam’s selected tool and the game’s standard settings.')
        print(message, file=sys.stderr)
        with log_path.open('w') as log:
            print(message, file=log, flush=True)
            return subprocess.call(command, env=launch_env, stdout=log, stderr=subprocess.STDOUT)

    command[gi] = str(executable)
    skip_movies = options.get('skip_startup_movies', True)
    if app_id != '50130' and skip_movies and not any(
            arg.lower() == '-nostartupmovies' for arg in command[gi + 1:]):
        command.append('-nostartupmovies')
    frame_rate = 'default'
    if app_id == '19680':
        legacy = 'uncapped' if options.get('unlock_fps') is True else 'default'
        frame_rate = options.get('frame_rate', legacy)
        if frame_rate in ('60', '90', 'uncapped') and not any(
                arg.lower() == '-nofpscap' for arg in command[gi + 1:]):
            command.append('-NoFPSCap')
    mount = ['bwrap', '--dev-bind', '/', '/']
    if proton != selected:
        # Keep Steam's argv and tool paths intact inside this launch's namespace.
        mount.extend(('--bind', str(proton), str(selected)))
    wine = selected / 'files/lib/wine'
    game_dir = executable if manual else executable.parents[1 if app_id in ('35140', '50130') else 2]
    bind_file(mount, game_dir, game_dir)
    if app_id == '50130' and skip_movies:
        hide_mafia_intro_movies(mount, executable)
    direct = BASE / 'valve11-legacy/files/lib'
    bridge = direct / 'wine-cuda/zluda'
    win32 = work / 'nvcuda.dll'
    patch_null_host_free(bridge / 'i386-windows/nvcuda.dll', win32)
    bind_file(mount, win32, wine / 'i386-windows/nvcuda.dll')
    bind_file(mount, bridge / 'x86_64-windows/nvcuda.dll', wine / 'x86_64-windows/nvcuda.dll')
    for arch, dll in (('i386-windows', 'nvapi.dll'), ('x86_64-windows', 'nvapi64.dll')):
        relative = Path('nvapi') / arch / dll
        bind_file(mount, direct / 'wine' / relative, wine / relative)
    unix = wine / 'x86_64-unix'
    mount += ['--overlay-src', str(bridge / unix.name),
              '--overlay-src', str(proton / 'files/lib/wine' / unix.name),
              '--ro-overlay', str(unix)]
    bind_file(mount, direct / 'wine/x86_64-unix/ntdll.so', unix / 'ntdll.so')

    env = {key: value for key, value in launch_env.items()
           if not key.startswith(('ARKHAM_', 'BATMA_', 'ALICE_', 'ZLUDA', 'PROTON_LOG'))}
    backend_dir = direct.with_name('lib64')
    env.update(PROTON_USE_WOW64='1', PROTON_ENABLE_ZLUDA='1', PROTON_ENABLE_NVAPI='1',
               PROTON_FORCE_NVAPI='1', DXVK_ENABLE_NVAPI='1', DXVK_NVAPI_ALLOW_OTHER_DRIVERS='1',
               WINEDLLOVERRIDES='nvcuda=b', HSA_OVERRIDE_GFX_VERSION='10.3.0', WINEDEBUG='-all',
               ZLUDA_WINE_BACKEND_PATH=str(backend_dir / 'libcuda.so.1'))
    env.pop('PROTON_DISABLE_NVAPI', None)
    env.pop('CUDA_FAKE_LUID', None)
    if options.get('show_fps', True):
        env['MANGOHUD'] = '1'
        env.setdefault('MANGOHUD_CONFIG', 'fps,frametime')
    preloads = []
    replacements = {}
    for patch in game.get('patches', ()):
        root = BASE / 'patches' / app_id / patch['id']
        files = {key: root / name for key, name in patch['file_environment'].items()}
        required = list(files.values())
        if patch['preload']:
            preload = root / patch['preload']
            required.append(preload)
            preloads.append(str(preload))
        if any(not path.is_file() for path in required):
            raise ValueError(f'Files for {patch["id"]} are missing. Re-run the installer.')
        for entry in validate_replacements(patch.get('replacements', [])):
            target = original_file(entry, game)
            if target in replacements:
                raise ValueError(f'Multiple patches replace {entry["target"]}. Review the selected patches.')
            replacements[target] = replacement_file(entry, root)
        env.update(patch['environment'])
        env.update({key: str(path) for key, path in files.items()})
    if app_id == '19680':
        physx = BASE.parent / 'input'
        overlay = work / 'game-dll'
        overlay.mkdir()
        for name in ('physx-runtime/alice2/PhysXCore.dll', 'PhysXDevice.dll',
                     'physx-runtime/common/cudart32_65.dll'):
            dll = physx / name
            os.link(dll, overlay / dll.name)
        mount += ['--overlay-src', str(executable.parent), '--overlay-src', str(overlay),
                  '--ro-overlay', str(executable.parent)]
    for target, source in replacements.items():
        bind_file(mount, source, target)

    if frame_rate in ('60', '90'):
        config = env.get('DXVK_CONFIG')
        limit = f'd3d9.maxFrameRate = {frame_rate}'
        env['DXVK_CONFIG'] = f'{config};{limit}' if config else limit

    proton_lib = selected / 'files/lib/i386-linux-gnu'
    env['LD_LIBRARY_PATH'] = str(proton_lib) + ':' + env.get('LD_LIBRARY_PATH', '')
    libs = f'{backend_dir}:{BASE / "valve11-addon/lib"}'
    command[pi:pi] = [
        '/bin/sh', '-c',
        'export LD_LIBRARY_PATH="$1${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"; '
        'if [ -n "$2" ]; then export LD_PRELOAD="$2${LD_PRELOAD:+:$LD_PRELOAD}"; fi; '
        'shift 2; exec "$@"',
        'deck-physics-runtime', libs, ':'.join(preloads),
    ]
    with log_path.open('w') as log:
        if proton != selected:
            print(f'Deck Physics is using compatible Proton from {proton}', file=log, flush=True)
        return subprocess.call(mount + ['--'] + command, env=env, stdout=log, stderr=subprocess.STDOUT)


def main(command):
    layout = json.loads((BASE / 'steam-layout.json').read_text())
    app_id = select_game(command, os.environ.get('SteamAppId'), layout['games'])
    with (RELEASE / f'launch-{app_id}.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with tempfile.TemporaryDirectory(prefix=f'play-{app_id}-', dir=RELEASE) as directory:
            return launch(command, Path(directory), app_id, layout)


if __name__ == '__main__':
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, ValueError) as error:
        print(f'Deck Physics: {error}', file=sys.stderr)
        raise SystemExit(1)
