#!/usr/bin/env python3
"""Quick check that every patch Bastion applies still applies, and that the
branding step still works, without doing a full Windows build.

Runs on Linux (GitHub Actions or locally) in ~10-20 minutes:
  1. prepares the work directory exactly like build.py does,
  2. downloads and unpacks the official Chromium source tarball
     (or uses --source if you already have one unpacked),
  3. applies ungoogled-chromium's patches, the Windows patches and Bastion's,
  4. runs the branding step.

Usage:
  python tools/check_patches.py                    # download + check
  python tools/check_patches.py --source /path/src # reuse an unpacked tree (it gets modified!)
"""

import argparse
import configparser
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bastion_common  # noqa: E402

sys.path.insert(0, str(bastion_common.REPO_ROOT / 'branding'))
import apply as branding  # noqa: E402


def _windows_download_dirs(workdir):
    """Folders filled by Windows-only downloads (not in the source tarball)."""
    parser = configparser.ConfigParser()
    parser.read(workdir / 'downloads.ini', encoding='utf-8')
    return [parser[s]['output_path'].strip().rstrip('/') + '/'
            for s in parser.sections() if 'output_path' in parser[s]]


def _patch_targets(patch_path):
    targets = []
    for line in patch_path.read_text(encoding='utf-8', errors='replace').splitlines():
        if line.startswith('+++ '):
            target = line[4:].split('\t')[0].strip()
            if target.startswith('b/'):
                targets.append(target[2:])
    return targets


def _download_source(workdir, cache, dest):
    utils = workdir / 'ungoogled-chromium' / 'utils'
    sys.path.insert(0, str(utils))
    import downloads  # pylint: disable=import-outside-toplevel
    info = downloads.DownloadInfo([workdir / 'ungoogled-chromium' / 'downloads.ini'])
    cache.mkdir(parents=True, exist_ok=True)
    downloads.retrieve_downloads(info, cache, None, False, False)
    downloads.check_downloads(info, cache, None)
    dest.mkdir(parents=True, exist_ok=True)
    downloads.unpack_downloads(info, cache, None, dest)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--workdir', type=Path, default=bastion_common.REPO_ROOT / 'work-check')
    parser.add_argument('--source', type=Path, help='Existing unpacked Chromium source tree')
    parser.add_argument('--cache', type=Path, default=bastion_common.REPO_ROOT / 'download-cache')
    args = parser.parse_args()

    workdir = args.workdir.resolve()
    try:
        bastion_common.prepare_workdir(workdir)
    except bastion_common.ConfigError as exc:
        bastion_common.fail(str(exc))
    version = bastion_common.chromium_version()
    print(f'Checking Bastion patches against Chromium {version}')

    if args.source:
        src = args.source.resolve()
    else:
        src = workdir / 'build' / 'src'
        if src.exists():
            shutil.rmtree(src)
        _download_source(workdir, args.cache.resolve(), src)

    skip_dirs = _windows_download_dirs(workdir)
    failures, skipped, applied = [], [], 0
    for patch in bastion_common.patch_files_in_order(workdir):
        targets = _patch_targets(patch)
        if targets and all(any(t.startswith(d) for d in skip_dirs) for t in targets):
            skipped.append(patch)
            continue
        result = subprocess.run(
            ['patch', '-p1', '--ignore-whitespace', '--forward', '--no-backup-if-mismatch',
             '-i', str(patch), '-d', str(src)],
            capture_output=True, text=True, check=False)
        if result.returncode != 0:
            failures.append((patch, result.stdout + result.stderr))
        else:
            applied += 1

    print(f'Applied {applied} patches; skipped {len(skipped)} that only touch '
          f'Windows-only downloads.')
    for patch in skipped:
        print(f'  skipped: {patch.relative_to(workdir)}')
    if failures:
        print(f'\n{len(failures)} PATCH(ES) FAILED:')
        for patch, output in failures:
            print(f'\n--- {patch.relative_to(workdir)}\n{output.strip()}')
        return 1

    branding.apply(src)
    print('\nAll patches apply and branding works.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
