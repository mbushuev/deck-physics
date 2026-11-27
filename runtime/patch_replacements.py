"""Resolve and verify files temporarily replaced by an installed game patch."""

from hashlib import file_digest
from pathlib import Path
import re


SHA256 = re.compile(r'[0-9a-f]{64}')


def checksum(path):
    with path.open('rb') as source:
        return file_digest(source, 'sha256').hexdigest()


def has_relative_components(path):
    return (isinstance(path, str) and path.isprintable() and '\\' not in path
            and ':' not in path and all(part not in ('', '.', '..') for part in path.split('/')))


def validate_replacements(entries):
    if not isinstance(entries, list):
        raise ValueError('Expected a list of patch replacements')
    for entry in entries:
        if (not isinstance(entry, dict)
                or entry.keys() != {'root', 'target', 'source', 'original_sha256'}
                or entry['root'] not in ('game', 'prefix')
                or not all(has_relative_components(entry[key]) for key in ('target', 'source'))
                or not isinstance(entry['original_sha256'], str)
                or not SHA256.fullmatch(entry['original_sha256'])):
            raise ValueError('Invalid patch replacement')
    targets = {(entry['root'], entry['target'].casefold()) for entry in entries}
    if len(targets) != len(entries):
        raise ValueError('Duplicate patch replacement target')
    return entries


def existing_file(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f'Expected an existing file inside the selected directory: {relative}')
    return path


def original_file(entry, game):
    root = Path(game['exe']).resolve().parent if entry['root'] == 'game' else Path(game['prefix']).resolve()
    target = existing_file(root, entry['target'])
    if checksum(target) != entry['original_sha256']:
        raise ValueError(f'Patch does not support this version of {entry["target"]}. Review the selected patches.')
    return target


def replacement_file(entry, patch_dir):
    return existing_file(patch_dir.resolve(), entry['source'])
