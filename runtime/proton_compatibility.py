"""Select the installed Wine build that can host the packaged CUDA bridge."""

from hashlib import file_digest
from itertools import chain
from pathlib import Path
import re


WINE_ABI = {
    'x86_64-unix/ntdll.so': 'e67b173fbb06ed42a15de73c50024403c2a825e0b044b737005940b87ff5ef9e',
    'x86_64-windows/ntdll.dll': '4909f3ce552d0954a249633c0caca7e648e0138a0b03165e441445b406fd5e26',
    'i386-windows/ntdll.dll': '0c1264277f68615084232fb144701ab2c76e53d6ceeac5c29c70471d0e29e4e6',
}
RUNTIME = Path('SteamLinuxRuntime_4/_v2-entry-point')
STEAM = Path.home() / '.local/share/Steam'


def libraries(steam):
    settings = steam / 'steamapps/libraryfolders.vdf'
    try:
        contents = settings.read_text()
    except FileNotFoundError:
        contents = ''
    paths = re.findall(r'^\s*"path"\s+"([^"]+)"', contents, re.M)
    return list(dict.fromkeys((steam / 'steamapps', *(Path(p) / 'steamapps' for p in paths))))


def installed_protons(apps):
    for app_dir in apps:
        common = app_dir / 'common'
        candidates = sorted(common.glob('Proton*'), key=lambda path: (path.name != 'Proton 11.0', path))
        for directory in candidates:
            if (directory / 'proton').is_file():
                yield directory.resolve()


def bridge_compatible(proton):
    if not (proton / 'proton').is_file():
        return False
    try:
        for relative, expected in WINE_ABI.items():
            with (proton / 'files/lib/wine' / relative).open('rb') as file:
                if file_digest(file, 'sha256').hexdigest() != expected:
                    return False
    except OSError:
        return False
    return True


def select_bridge_proton(selected, steam, installed=None):
    if bridge_compatible(selected):
        return selected

    apps = libraries(steam)
    caches = [steam / 'steamrt64/steamapps/content', *(app_dir / 'content' for app_dir in apps)]
    depots = (directory for cache in caches for directory in sorted(cache.glob('app_*/depot_*')))
    saved = (Path(installed),) if installed else ()
    checked = {selected}
    for candidate in chain(installed_protons(apps), saved, depots):
        candidate = candidate.resolve()
        if candidate in checked:
            continue
        checked.add(candidate)
        if bridge_compatible(candidate):
            return candidate
    return None
