#!/usr/bin/env python3
"""Assemble the Deck installer from a pinned Proton-ZLUDA release."""

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
from urllib.request import urlopen


SOURCE = Path(__file__).resolve().parent
PACKAGE = 'DeckPhysX-Proton11'


def sha256(path):
    result = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def collect(stream, files, stage):
    pending = {record['member']: (path, record['sha256']) for path, record in files.items()}
    with tarfile.open(fileobj=stream, mode='r|gz') as archive:
        for member in archive:
            name = member.name.removeprefix('./')
            if name not in pending:
                continue
            relative, expected = pending.pop(name)
            if not member.isfile():
                raise ValueError(f'Expected a regular file for {name}')
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as source, target.open('wb') as output:
                shutil.copyfileobj(source, output)
            if sha256(target) != expected:
                raise ValueError(f'Unexpected SHA-256 for {name}')
            if not pending:
                return
    raise ValueError('Missing upstream files: ' + ', '.join(sorted(pending)))


def bundle(stage, links, output):
    def reproducible(info):
        info.uid = info.gid = info.mtime = 0
        info.uname = info.gname = ''
        info.mode = 0o755 if info.name in (f'{PACKAGE}/run', f'{PACKAGE}/Install.sh') else 0o644
        return info

    with output.open('wb') as file, gzip.GzipFile(filename='', fileobj=file, mode='wb',
                                                compresslevel=6, mtime=0) as stream:
        with tarfile.open(fileobj=stream, mode='w|') as archive:
            for path in sorted(stage.rglob('*')):
                if path.is_file():
                    archive.add(path, arcname=f'{PACKAGE}/{path.relative_to(stage).as_posix()}',
                                filter=reproducible)
            for name, target in sorted(links.items()):
                link = tarfile.TarInfo(f'{PACKAGE}/{name}')
                link.type = tarfile.SYMTYPE
                link.linkname = target
                archive.addfile(reproducible(link))


def build(proton, output):
    pins = json.loads((SOURCE / 'upstream.json').read_text())
    with tempfile.TemporaryDirectory(dir=output.parent) as work:
        if proton is None:
            proton = Path(work) / 'Proton-ZLUDA.tar.gz'
            with urlopen(pins['archive']['url'], timeout=60) as source, proton.open('wb') as archive:
                shutil.copyfileobj(source, archive)
        if sha256(proton) != pins['archive']['sha256']:
            raise ValueError('Proton-ZLUDA archive did not match the pinned SHA-256')

        stage = Path(work) / PACKAGE
        stage.mkdir()
        for name in ('Install.sh', 'Install-DeckPhysX.py', 'Build-DeckPhysX.py', 'run', 'README.md',
                     'BUILD.md', 'VERSION', 'upstream.json', 'alice-pe32-null-host-free.patch'):
            shutil.copy2(SOURCE / name, stage / name)
        shutil.copytree(SOURCE / 'docs', stage / 'docs')
        shutil.copytree(SOURCE / 'licenses', stage / 'licenses')
        shutil.copytree(SOURCE / 'native', stage / 'native')
        shutil.copytree(SOURCE / 'runtime', stage / 'runtime', ignore=shutil.ignore_patterns('__pycache__'))

        with proton.open('rb') as stream:
            collect(stream, pins['files'], stage)

        runtime = stage / 'runtime'
        flags = ['cc', '-O2', '-fPIC', '-shared', '-pthread', '-Wl,--build-id=none']
        subprocess.run(flags + ['-o', str(runtime / 'hip-wait-startup.so'),
                                str(SOURCE / 'native/hip-wait-startup.c'), '-ldl'], check=True)

        manifest = {path.relative_to(stage).as_posix(): sha256(path)
                    for path in sorted((stage / 'runtime').rglob('*')) if path.is_file()}
        for relative, target in pins['links'].items():
            manifest[relative] = manifest[Path(relative).with_name(target).as_posix()]
        manifest['run'] = sha256(stage / 'run')
        manifest['VERSION'] = sha256(stage / 'VERSION')
        (stage / 'SHA256.json').write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
        pending = Path(work) / output.name
        bundle(stage, pins['links'], pending)
        os.replace(pending, output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proton', type=Path, help='Use a local copy of the pinned release archive')
    parser.add_argument('--output', type=Path, help='Override the versioned installer filename')
    options = parser.parse_args()
    try:
        version = (SOURCE / 'VERSION').read_text(encoding='ascii').strip()
        if not re.fullmatch(r'(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*)){2}', version):
            raise ValueError('VERSION must contain a version in MAJOR.MINOR.PATCH format')
        output = options.output or Path(f'{PACKAGE}-{version}.tar.gz')
        build(options.proton, output)
    except (OSError, ValueError, tarfile.TarError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'{error}\n')
    print(output)
