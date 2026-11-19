#!/usr/bin/env python3
"""Moves Bastion to a newer ungoogled-chromium-windows release.

  python tools/bump_upstream.py --check     # print the newest upstream tag if newer than ours
  python tools/bump_upstream.py --to TAG    # move the upstream/ submodule to TAG
  python tools/bump_upstream.py --latest    # same, with the newest tag

After --to/--latest, run tools/check_patches.py, then commit and tag.
The upstream-watch GitHub workflow does all of this automatically every day.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bastion_common  # noqa: E402

UPSTREAM_URL = 'https://github.com/ungoogled-software/ungoogled-chromium-windows'
_TAG_RE = re.compile(r'^(\d+)\.(\d+)\.(\d+)\.(\d+)-(\d+)\.(\d+)$')


def _git(*args, cwd=None):
    return subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True,
                          text=True).stdout.strip()


def _tag_key(tag):
    match = _TAG_RE.match(tag)
    return tuple(int(x) for x in match.groups()) if match else None


def current_tag():
    return _git('describe', '--tags', '--exact-match', cwd=bastion_common.UPSTREAM_DIR)


def latest_tag():
    out = _git('ls-remote', '--tags', '--refs', UPSTREAM_URL)
    tags = [line.split('refs/tags/')[1] for line in out.splitlines() if 'refs/tags/' in line]
    tags = [t for t in tags if _tag_key(t)]
    return max(tags, key=_tag_key)


def _set_revision(value):
    path = bastion_common.CONFIG_PATH
    text = path.read_text(encoding='utf-8')
    new_text, count = re.subn(r'(?m)^revision = \d+$', f'revision = {value}', text)
    if count != 1:
        raise SystemExit('Could not find "revision = N" in config/bastion.toml')
    path.write_text(new_text, encoding='utf-8')


def _sdk_line(action_path):
    text = action_path.read_text(encoding='utf-8-sig')
    match = re.search(r'Install Windows SDK ([\d.]+)', text)
    return match.group(1) if match else None


def move_to(tag):
    up = bastion_common.UPSTREAM_DIR
    old_version = bastion_common.chromium_version()
    old_revision = bastion_common.load_config()['release']['revision']
    _git('fetch', '--depth', '1', 'origin', 'tag', tag, cwd=up)
    _git('checkout', '-q', tag, cwd=up)
    _git('submodule', 'update', '--init', '--depth', '1', cwd=up)
    new_version = bastion_common.chromium_version()
    # Same Chromium version (upstream packaging fix only) -> next Bastion revision.
    _set_revision(old_revision + 1 if new_version == old_version else 1)

    notes = []
    ours = _sdk_line(bastion_common.REPO_ROOT / '.github' / 'actions' / 'prepare' / 'action.yml')
    theirs = _sdk_line(up / '.github' / 'actions' / 'prepare' / 'action.yml')
    if ours != theirs:
        notes.append(f'Upstream now installs Windows SDK {theirs} (Bastion installs {ours}). '
                     'Copy the SDK step from upstream/ungoogled-chromium-windows/.github/'
                     'actions/prepare/action.yml into .github/actions/prepare/action.yml.')
    print(f'Moved upstream to {tag} (Chromium {old_version} -> {new_version}); '
          f'Bastion version is now {bastion_common.bastion_version()}')
    for note in notes:
        print('NOTE:', note)
    return notes


def _github_output(**values):
    path = os.environ.get('GITHUB_OUTPUT')
    if path:
        with open(path, 'a', encoding='utf-8') as f:
            for key, value in values.items():
                f.write(f'{key}={value}\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true')
    group.add_argument('--latest', action='store_true')
    group.add_argument('--to', metavar='TAG')
    args = parser.parse_args()

    current = current_tag()
    if args.check:
        newest = latest_tag()
        is_newer = _tag_key(newest) > _tag_key(current)
        print(f'current: {current}\nnewest:  {newest}\nupdate available: {is_newer}')
        _github_output(current=current, newest=newest, update=str(is_newer).lower())
        return 0

    tag = latest_tag() if args.latest else args.to
    if not _tag_key(tag):
        raise SystemExit(f'Not an ungoogled-chromium-windows release tag: {tag}')
    notes = move_to(tag)
    _github_output(version=bastion_common.bastion_version(), notes=' '.join(notes))
    return 0


if __name__ == '__main__':
    sys.exit(main())
