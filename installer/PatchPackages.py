"""Discover and install optional per-game patch archives."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from zipfile import BadZipFile, ZipFile


PATCH_NAME = '*.deckphysx.zip'
PATCH_ID = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')
ENV_NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
PATH_PART = re.compile(r'[A-Za-z0-9_.-]+')


def checksum(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def relative_path(value):
    return isinstance(value, str) and all(
        PATH_PART.fullmatch(part) and part not in ('.', '..') for part in value.split('/'))


def archive_files(archive):
    seen = set()
    files = set()
    for member in archive.infolist():
        path = member.filename.removesuffix('/')
        expected_type = stat.S_IFDIR if member.is_dir() else stat.S_IFREG
        if (path in seen or not relative_path(path) or member.flag_bits & 1
                or (path != 'patch.json' and path != 'files' and not path.startswith('files/'))
                or stat.S_IFMT(member.external_attr >> 16) not in (0, expected_type)):
            raise ValueError('Invalid archive path or file type')
        seen.add(path)
        if not member.is_dir():
            files.add(path)
    if 'patch.json' not in files or 'files' in files:
        raise ValueError('Expected patch.json and optional files/ payload')
    return files


@dataclass(frozen=True)
class Patch:
    path: Path
    sha256: str
    app_id: str
    id: str
    title: str
    description: str
    details: str
    requires: tuple
    environment: dict
    file_environment: dict
    preload: str | None
    prepare: str | None
    requires_nvidia_physx: bool

    @property
    def key(self):
        return f'{self.app_id}:{self.id}'

    def launch_settings(self):
        return {'id': self.id, 'sha256': self.sha256, 'environment': self.environment,
                'file_environment': self.file_environment, 'preload': self.preload}

    def install(self, target, game):
        with tempfile.TemporaryDirectory(dir=target.parent) as work:
            snapshot = Path(work) / 'patch.zip'
            shutil.copyfile(self.path, snapshot)
            if checksum(snapshot) != self.sha256:
                raise ValueError(f'{self.title} changed after selection. Run the installer again.')
            with ZipFile(snapshot) as archive:
                target.mkdir()
                for name in sorted(archive_files(archive) - {'patch.json'}):
                    output = target / name.removeprefix('files/')
                    output.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(name) as source, output.open('xb') as dest:
                        shutil.copyfileobj(source, dest)
        if self.prepare:
            try:
                subprocess.run([sys.executable, '-B', str(target / self.prepare),
                                game['prefix'], game['exe']], cwd=target, check=True)
            except subprocess.CalledProcessError as error:
                raise RuntimeError(f'Could not prepare {self.title}. See the setup output.') from error
        required = list(self.file_environment.values())
        if self.preload:
            required.append(self.preload)
        if missing := next((name for name in required if not (target / name).is_file()), None):
            raise ValueError(f'{self.title} did not provide {missing}')


def read_patch(path):
    with path.open('rb') as source:
        with ZipFile(source) as archive:
            files = archive_files(archive)
            manifest = archive.getinfo('patch.json')
            if manifest.file_size > 16 * 1024:
                raise ValueError('Patch manifest is too large')
            info = json.loads(archive.read(manifest))
        source.seek(0)
        sha256 = hashlib.file_digest(source, 'sha256').hexdigest()
    required = {'format', 'id', 'app_id', 'title', 'description'}
    optional = {'details', 'requires', 'environment', 'file_environment', 'preload', 'prepare',
                'requires_nvidia_physx'}
    if (not isinstance(info, dict) or not required <= info.keys() <= required | optional
            or type(info['format']) is not int or info['format'] != 1):
        raise ValueError('Unsupported patch manifest')
    if any(not isinstance(info[key], str) or not info[key].strip() or not info[key].isprintable()
           for key in ('id', 'app_id', 'title', 'description')):
        raise ValueError('Invalid patch title, description or ID')
    if not PATCH_ID.fullmatch(info['id']) or not re.fullmatch(r'[1-9][0-9]*', info['app_id']):
        raise ValueError('Invalid patch or Steam App ID')
    details = info.get('details', '')
    if not isinstance(details, str) or any(c != '\n' and not c.isprintable() for c in details):
        raise ValueError('Invalid patch details')
    requires = info.get('requires', [])
    if not isinstance(requires, list) or any(
            not isinstance(key, str) or not PATCH_ID.fullmatch(key) or key == info['id'] for key in requires):
        raise ValueError('Invalid patch dependencies')
    environment = info.get('environment', {})
    file_environment = info.get('file_environment', {})
    if (not isinstance(environment, dict) or not isinstance(file_environment, dict)
            or environment.keys() & file_environment.keys()
            or any(not ENV_NAME.fullmatch(key) for key in environment.keys() | file_environment.keys())
            or any(not isinstance(value, str) or '\0' in value for value in environment.values())
            or not all(map(relative_path, file_environment.values()))):
        raise ValueError('Invalid launch environment')
    preload = info.get('preload')
    prepare = info.get('prepare')
    if preload is not None and not relative_path(preload):
        raise ValueError('Invalid preload path')
    if prepare is not None and (not relative_path(prepare) or not prepare.endswith('.py')
                                or 'files/' + prepare not in files):
        raise ValueError('Missing or invalid preparation script')
    # Existing Batman preparation scripts used the verified prefix runtime.
    requires_nvidia_physx = info.get('requires_nvidia_physx', info['app_id'] == '35140' and prepare is not None)
    if type(requires_nvidia_physx) is not bool or (requires_nvidia_physx and info['app_id'] != '35140'):
        raise ValueError('Invalid NVIDIA PhysX patch requirement')
    return Patch(path, sha256, info['app_id'], info['id'], info['title'], info['description'],
                 details.strip(), tuple(requires), environment, file_environment, preload, prepare,
                 requires_nvidia_physx)


def discover_patches(folder, games):
    patches = {}
    duplicates = set()
    issues = []
    for path in sorted(folder.glob(f'*/{PATCH_NAME}')):
        try:
            patch = read_patch(path)
        except (OSError, ValueError, BadZipFile, NotImplementedError) as error:
            issues.append(f'{path.parent.name}/{path.name}: {error}')
            continue
        if patch.app_id not in games:
            continue
        if patch.key in patches or patch.key in duplicates:
            duplicates.add(patch.key)
            patches.pop(patch.key, None)
            issues.append(f'{patch.title}: duplicate patch ID for the same game.')
        else:
            patches[patch.key] = patch
    return patches, issues


def validate_selection(patches, selected):
    variables = set()
    for key, patch in patches.items():
        if key not in selected:
            continue
        for required in patch.requires:
            dependency_key = f'{patch.app_id}:{required}'
            if dependency_key not in selected:
                dependency = patches.get(dependency_key)
                name = dependency.title if dependency else required
                raise ValueError(f'{patch.title} requires {name}.')
        for name in patch.environment.keys() | patch.file_environment.keys():
            if (patch.app_id, name) in variables:
                raise ValueError(f'{patch.title} conflicts with another selected patch for this game.')
            variables.add((patch.app_id, name))


def without_missing_dependencies(patches):
    remaining = {patch.key: patch for patch in patches}
    while missing := [key for key, patch in remaining.items()
                      if any(f'{patch.app_id}:{dependency}' not in remaining for dependency in patch.requires)]:
        for key in missing:
            del remaining[key]
    return list(remaining.values())
