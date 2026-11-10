#!/usr/bin/env python3
"""Launch the Steam-selected Valve Proton with the pinned GPU PhysX bridge."""

import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from alice_bridge_patch import patch_null_host_free


BASE = Path(__file__).resolve().parent
RELEASE = BASE.parent.parent
WINE_HASH = 'e67b173fbb06ed42a15de73c50024403c2a825e0b044b737005940b87ff5ef9e'
VERSION = '1791559474 proton-11.0-2e-x86_64'


def bind_file(mount, source, target):
    mount.extend(('--ro-bind', str(source), str(target)))


def launch(command, work, app_id, layout):
    game = layout['games'][app_id]
    batman = app_id == '35140'
    executable = Path(game['exe'])
    proton = Path(layout['proton'])
    runtime = Path(layout['runtime'])
    allowed = {executable}
    if batman:
        allowed.update(executable.with_name(name) for name in ('BmLauncher.exe', 'BmStartApp.exe'))
    runtime_indices = [i for i, arg in enumerate(command) if Path(arg).name == runtime.name]
    proton_indices = [i for i, arg in enumerate(command) if Path(arg).name == 'proton']
    game_indices = [i for i, arg in enumerate(command) if Path(arg).suffix.lower() == '.exe'
                    and Path(arg).resolve() in allowed]
    if not len(runtime_indices) == len(proton_indices) == len(game_indices) == 1:
        raise ValueError('Expected a Steam launch with Valve Proton 11.0 selected.')
    ri, pi, gi = runtime_indices[0], proton_indices[0], game_indices[0]
    if (not ri < pi < gi or Path(command[ri]).resolve() != runtime
            or Path(command[pi]).resolve() != (proton / 'proton').resolve()):
        raise ValueError('Expected a Steam launch with the supported Valve Proton runtime.')
    if Path(os.environ.get('STEAM_COMPAT_DATA_PATH', '')).resolve() != Path(game['prefix']):
        raise ValueError('Expected the installed game’s Steam prefix.')
    wine = proton / 'files/lib/wine'
    if ((proton / 'version').read_text().strip() != VERSION
            or hashlib.sha256((wine / 'x86_64-unix/ntdll.so').read_bytes()).hexdigest() != WINE_HASH):
        raise ValueError('Valve Proton changed. This release requires Proton 11.0-2e.')

    command[gi] = str(executable)
    if '-nostartupmovies' not in (arg.lower() for arg in command[gi+1:]):
        command.append('-nostartupmovies')
    game_dir = executable.parents[1 if batman else 2]
    mount = ['bwrap', '--dev-bind', '/', '/']
    bind_file(mount, game_dir, game_dir)
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
    mount += ['--overlay-src', str(bridge / unix.name), '--overlay-src', str(unix),
              '--ro-overlay', str(unix)]
    bind_file(mount, direct / 'wine/x86_64-unix/ntdll.so', unix / 'ntdll.so')

    env = {key: value for key, value in os.environ.items()
           if not key.startswith(('ARKHAM_', 'BATMA_', 'ALICE_', 'ZLUDA', 'PROTON_LOG'))}
    backend_dir = direct.with_name('lib64')
    env.update(PROTON_USE_WOW64='1', PROTON_ENABLE_ZLUDA='1', PROTON_ENABLE_NVAPI='1',
               PROTON_FORCE_NVAPI='1', DXVK_ENABLE_NVAPI='1', DXVK_NVAPI_ALLOW_OTHER_DRIVERS='1',
               WINEDLLOVERRIDES='nvcuda=b', HSA_OVERRIDE_GFX_VERSION='10.3.0', WINEDEBUG='-all',
               AMD_CU_MASK='0x3f', MANGOHUD='1',
               ZLUDA_WINE_BACKEND_PATH=str(backend_dir / 'libcuda.so.1'))
    env.pop('PROTON_DISABLE_NVAPI', None)
    env.pop('CUDA_FAKE_LUID', None)
    env.setdefault('MANGOHUD_CONFIG', 'fps,frametime')
    if not batman:
        physx = BASE.parent / 'input'
        overlay = work / 'game-dll'
        overlay.mkdir()
        for name in ('physx-runtime/alice2/PhysXCore.dll', 'PhysXDevice.dll',
                     'physx-runtime/common/cudart32_65.dll'):
            dll = physx / name
            os.link(dll, overlay / dll.name)
        mount += ['--overlay-src', str(executable.parent), '--overlay-src', str(overlay),
                  '--ro-overlay', str(executable.parent)]

    proton_lib = proton / 'files/lib/i386-linux-gnu'
    env['LD_LIBRARY_PATH'] = str(proton_lib) + ':' + env.get('LD_LIBRARY_PATH', '')
    libs = f'{backend_dir}:{BASE / "valve11-addon/lib"}'
    command[pi:pi] = [
        '/bin/sh', '-c',
        'export LD_LIBRARY_PATH="$1${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"; '
        'export LD_PRELOAD="$2${LD_PRELOAD:+:$LD_PRELOAD}"; shift 2; exec "$@"',
        'deck-physx-runtime', libs, str(BASE / 'hip-wait-startup.so'),
    ]
    with (RELEASE / f'launch-{app_id}.log').open('w') as log:
        return subprocess.call(mount + ['--'] + command, env=env, stdout=log, stderr=subprocess.STDOUT)


def main(command):
    app_id = os.environ.get('SteamAppId')
    layout = json.loads((BASE / 'steam-layout.json').read_text())
    if app_id not in layout['games']:
        raise ValueError('This Steam game is not configured. Run the installer first.')
    with (RELEASE / f'launch-{app_id}.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with tempfile.TemporaryDirectory(prefix=f'play-{app_id}-', dir=RELEASE) as directory:
            return launch(command, Path(directory), app_id, layout)


if __name__ == '__main__':
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, ValueError) as error:
        print(f'Deck PhysX: {error}', file=sys.stderr)
        raise SystemExit(1)
