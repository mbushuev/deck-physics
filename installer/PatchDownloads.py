"""Download the selected game's patch set from the Deck Physics patch catalog."""

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from urllib.request import urlopen

from PatchPackages import read_patch


CATALOG_BASE = 'https://raw.githubusercontent.com/mbushuev/deck-physics-patches/main/'
PATCH_FILE = re.compile(r'patches/[a-z0-9-]+/([a-z0-9-]+\.deckphysx\.zip)')
SHA256 = re.compile(r'[0-9a-f]{64}')
MAX_CATALOG = 512 * 1024
MAX_PATCH = 64 * 1024 * 1024


def fetch(relative, limit):
    with urlopen(CATALOG_BASE + relative, timeout=20) as source:
        if not source.geturl().startswith(CATALOG_BASE):
            raise ValueError('Unexpected patch download location.')
        content = source.read(limit + 1)
        if len(content) > limit:
            raise ValueError('The patch download exceeded its expected size.')
        return content


def catalog_entries(app_id):
    catalog = json.loads(fetch('catalog.json', MAX_CATALOG))
    if not isinstance(catalog, dict) or catalog.get('format') != 1 or not isinstance(catalog.get('games'), dict):
        raise ValueError('The patch catalog format is unsupported.')
    entries = catalog['games'].get(app_id, [])
    if not isinstance(entries, list):
        raise ValueError('Invalid patch list for the selected game.')
    names = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError('Invalid patch in the catalog.')
        path, size, digest = (entry.get(key) for key in ('path', 'size', 'sha256'))
        match = PATCH_FILE.fullmatch(path) if isinstance(path, str) else None
        if (not match or match[1] in names or type(size) is not int or not 0 < size <= MAX_PATCH
                or not isinstance(digest, str) or not SHA256.fullmatch(digest)):
            raise ValueError('Invalid patch in the catalog.')
        names.add(match[1])
    return entries


def download_patches(cache, app_id):
    if not re.fullmatch(r'[1-9][0-9]*', app_id):
        raise ValueError('Invalid Steam App ID.')
    entries = catalog_entries(app_id)
    game = cache / app_id
    game.mkdir(parents=True, exist_ok=True)
    current = game / 'current'
    previous = current.resolve() if current.is_symlink() else None
    if entries:
        # Keep the previous set visible until all new archives pass verification.
        with tempfile.TemporaryDirectory(dir=game, prefix='download-') as scratch:
            stage = Path(scratch) / 'patches'
            stage.mkdir()
            patch_ids = set()
            for entry in entries:
                relative, size, digest = (entry[key] for key in ('path', 'size', 'sha256'))
                filename = Path(relative).name
                content = fetch(relative, size)
                if len(content) != size or hashlib.sha256(content).hexdigest() != digest:
                    raise ValueError(f'{filename} did not match the patch catalog.')
                target = stage / filename
                target.write_bytes(content)
                patch = read_patch(target)
                if patch.app_id != app_id or patch.id in patch_ids:
                    raise ValueError(f'{filename} does not match the selected game or duplicates another patch.')
                patch_ids.add(patch.id)
            saved = Path(tempfile.mkdtemp(dir=game, prefix='set-'))
            try:
                os.replace(stage, saved)
                pointer = Path(scratch) / 'current'
                pointer.symlink_to(saved.name)
                os.replace(pointer, current)
            except OSError:
                shutil.rmtree(saved, ignore_errors=True)
                raise
    else:
        current.unlink(missing_ok=True)
    if previous and previous.parent == game.resolve() and previous.name.startswith('set-'):
        shutil.rmtree(previous, ignore_errors=True)
    return len(entries)
