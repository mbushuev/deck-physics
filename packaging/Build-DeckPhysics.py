#!/usr/bin/env python3
"""Assemble the Deck installer from a pinned Proton-ZLUDA release."""

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
import tempfile
from urllib.request import urlopen
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


PACKAGING = Path(__file__).resolve().parent
SOURCE = PACKAGING.parent
PACKAGE = 'DeckPhysics-Proton11'
UPSTREAM_NOTICE_DIRS = {'HiGHS', 'lld', 'llvm', 'zluda-cargo'}


def sha256(path):
    result = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def collect(stream, files, stage):
    pending = {record['member']: (path, record['sha256']) for path, record in files.items()}
    notice_dirs = set()
    with tarfile.open(fileobj=stream, mode='r|gz') as archive:
        for member in archive:
            name = member.name.removeprefix('./')
            parts = PurePosixPath(name).parts
            if name in pending:
                relative, expected = pending.pop(name)
            elif (member.isfile() and len(parts) >= 3 and parts[0] == 'licenses'
                  and parts[1] in UPSTREAM_NOTICE_DIRS):
                if '..' in parts or '\\' in name or ':' in name:
                    raise ValueError(f'Invalid notice path: {name}')
                relative, expected = name, None
                notice_dirs.add(parts[1])
            else:
                continue
            if not member.isfile():
                raise ValueError(f'Expected a regular file for {name}')
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as source, target.open('wb') as output:
                shutil.copyfileobj(source, output)
            if expected is not None and sha256(target) != expected:
                raise ValueError(f'Unexpected SHA-256 for {name}')
    if pending:
        raise ValueError('Missing upstream files: ' + ', '.join(sorted(pending)))
    if missing := UPSTREAM_NOTICE_DIRS - notice_dirs:
        raise ValueError('Missing upstream notices: ' + ', '.join(sorted(missing)))


def bundle(stage, links, output):
    root = stage.name

    def reproducible(info):
        info.uid = info.gid = info.mtime = 0
        info.uname = info.gname = ''
        info.mode = 0o755 if info.name in (f'{root}/installer/run', f'{root}/Install.sh') else 0o644
        return info

    with output.open('wb') as file, gzip.GzipFile(filename='', fileobj=file, mode='wb',
                                                compresslevel=6, mtime=0) as stream:
        with tarfile.open(fileobj=stream, mode='w|') as archive:
            for path in sorted(stage.rglob('*')):
                if path.is_file():
                    archive.add(path, arcname=f'{root}/{path.relative_to(stage).as_posix()}',
                                filter=reproducible)
            for name, target in sorted(links.items()):
                link = tarfile.TarInfo(f'{root}/{name}')
                link.type = tarfile.SYMTYPE
                link.linkname = target
                archive.addfile(reproducible(link))


def build_bundled_patches(stage, work):
    library = work / 'hip-wait-startup.so'
    source = PACKAGING / 'native/hip-wait-startup.c'
    source_copy = stage / source.relative_to(SOURCE)
    source_copy.parent.mkdir(parents=True)
    shutil.copy2(source, source_copy)
    subprocess.run(['cc', '-O2', '-fPIC', '-shared', '-pthread', '-Wl,--build-id=none',
                    '-o', str(library), str(source), '-ldl'], check=True)
    binary = library.read_bytes()

    for manifest in sorted((PACKAGING / 'bundled-patches').glob('*/*.json')):
        data = manifest.read_bytes()
        settings = json.loads(data)
        source_copy = stage / manifest.relative_to(SOURCE)
        source_copy.parent.mkdir(parents=True, exist_ok=True)
        source_copy.write_bytes(data)
        target = stage / 'patches' / manifest.parent.name / f'{manifest.stem}.deckphysx.zip'
        target.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(target, 'w') as archive:
            archive.writestr(ZipInfo('patch.json'), data, compress_type=ZIP_DEFLATED)
            if preload := settings.get('preload'):
                if preload != library.name:
                    raise ValueError(f'Unknown bundled patch library: {preload}')
                archive.writestr(ZipInfo(f'files/{library.name}'), binary,
                                 compress_type=ZIP_DEFLATED)


def build(proton, output):
    pins = json.loads((PACKAGING / 'upstream.json').read_text())
    with tempfile.TemporaryDirectory(dir=output.parent) as work:
        if proton is None:
            proton = Path(work) / 'Proton-ZLUDA.tar.gz'
            with urlopen(pins['archive']['url'], timeout=60) as source, proton.open('wb') as archive:
                shutil.copyfileobj(source, archive)
        if sha256(proton) != pins['archive']['sha256']:
            raise ValueError('Proton-ZLUDA archive did not match the pinned SHA-256')

        stage = Path(work) / PACKAGE
        stage.mkdir()
        for name in ('Install.sh', 'README.md', 'VERSION'):
            shutil.copy2(SOURCE / name, stage / name)
        for name in ('installer', 'docs', 'licenses', 'runtime'):
            shutil.copytree(SOURCE / name, stage / name, ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(PACKAGING / 'upstream-patches', stage / 'packaging/upstream-patches')
        for name in ('Build-DeckPhysics.py', 'upstream.json'):
            shutil.copy2(PACKAGING / name, stage / 'packaging' / name)

        with proton.open('rb') as stream:
            collect(stream, pins['files'], stage)
        build_bundled_patches(stage, Path(work))

        runtime = stage / 'runtime'
        manifest = {path.relative_to(stage).as_posix(): sha256(path)
                    for path in sorted(runtime.rglob('*')) if path.is_file()}
        for relative, target in pins['links'].items():
            manifest[relative] = manifest[Path(relative).with_name(target).as_posix()]
        manifest['installer/run'] = sha256(stage / 'installer/run')
        manifest['VERSION'] = sha256(stage / 'VERSION')
        (stage / 'installer/SHA256.json').write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
        pending = Path(work) / output.name
        bundle(stage, pins['links'], pending)
        os.replace(pending, output)


def build_sources(output):
    pins = json.loads((PACKAGING / 'upstream.json').read_text())
    with tempfile.TemporaryDirectory(dir=output.parent) as work:
        stage = Path(work) / f'{PACKAGE}-sources'
        stage.mkdir()
        shutil.copy2(SOURCE / 'licenses/SOURCES.md', stage / 'SOURCES.md')
        for name, record in pins['corresponding_sources'].items():
            target = stage / name
            with urlopen(record['url'], timeout=60) as source, target.open('wb') as archive:
                shutil.copyfileobj(source, archive)
            if sha256(target) != record['sha256']:
                raise ValueError(f'Unexpected SHA-256 for {name}')
        pending = Path(work) / output.name
        bundle(stage, {}, pending)
        os.replace(pending, output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proton', type=Path, help='Use a local copy of the pinned release archive')
    parser.add_argument('--sources-only', action='store_true',
                        help='Build the corresponding source archive for the release')
    parser.add_argument('--output', type=Path, help='Override the versioned output filename')
    options = parser.parse_args()
    if options.sources_only and options.proton is not None:
        parser.error('--proton applies to the installer build')
    try:
        version = (SOURCE / 'VERSION').read_text(encoding='ascii').strip()
        if not re.fullmatch(r'(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*)){2}', version):
            raise ValueError('VERSION must contain a version in MAJOR.MINOR.PATCH format')
        if options.sources_only:
            output = options.output or Path(f'{PACKAGE}-{version}-sources.tar.gz')
            build_sources(output)
        else:
            output = options.output or Path(f'{PACKAGE}-{version}.tar.gz')
            build(options.proton, output)
    except (OSError, ValueError, tarfile.TarError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'{error}\n')
    print(output)
