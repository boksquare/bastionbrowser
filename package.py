#!/usr/bin/env python3
"""Packages a finished Bastion build into an installer and a portable zip.

build.py copies this file into the work directory, where upstream's build
script runs it after a successful build. Outputs (in <workdir>/build/):
  bastion_<version>_installer_x64.exe   - per-user installer (mini_installer)
  bastion_<version>_windows_x64.zip     - portable copy, no install needed
"""

import argparse
import sys
from pathlib import Path
import shutil

_WORKDIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_WORKDIR / 'ungoogled-chromium' / 'utils'))
import filescfg  # noqa: E402  pylint: disable=wrong-import-position
sys.path.pop(0)


def _target_cpu(build_outputs):
    args_gn = (build_outputs / 'args.gn').read_text(encoding='utf-8')
    for cpu in ('x64', 'x86', 'arm64'):
        if f'target_cpu="{cpu}"' in args_gn:
            return cpu
    raise RuntimeError('Could not read target_cpu from args.gn')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cpu-arch', default='64bit', choices=('64bit', '32bit', 'arm'),
                        help='The "arch" key used to filter FILES.cfg (default: %(default)s)')
    args = parser.parse_args()

    version = (_WORKDIR / 'bastion_version.txt').read_text(encoding='utf-8').strip()
    src = _WORKDIR / 'build' / 'src'
    build_outputs = src / 'out' / 'Default'
    cpu = _target_cpu(build_outputs)
    out_dir = _WORKDIR / 'build'

    installer = out_dir / f'bastion_{version}_installer_{cpu}.exe'
    shutil.copyfile(build_outputs / 'mini_installer.exe', installer)

    timestamp = None
    committime = src / 'build' / 'util' / 'LASTCHANGE.committime'
    if committime.exists():
        timestamp = int(committime.read_text().strip())

    archive = out_dir / f'bastion_{version}_windows_{cpu}.zip'
    excluded = {Path('mini_installer.exe'), Path('mini_installer_exe_version.rc'),
                Path('setup.exe'), Path('chrome.packed.7z')}
    files = filescfg.filescfg_generator(src / 'chrome' / 'tools' / 'build' / 'win' / 'FILES.cfg',
                                        build_outputs, args.cpu_arch, excluded)
    filescfg.create_archive(files, tuple(), build_outputs, archive, timestamp)
    print(f'Packaged {installer.name} and {archive.name}')


if __name__ == '__main__':
    main()
