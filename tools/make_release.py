#!/usr/bin/env python3
"""Tags the current commit with Bastion's version and pushes the tag, which
starts the GitHub build and publishes a Release when it finishes.

Use it after you change Bastion itself (patches, config, branding):
  1. bump [release] revision in config/bastion.toml, commit and push to main
  2. python tools/make_release.py

(Chromium updates don't need this; the upstream-watch workflow tags them.)
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bastion_common  # noqa: E402


def main():
    version = bastion_common.bastion_version()
    status = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True,
                            check=True, cwd=bastion_common.REPO_ROOT).stdout
    if status.strip():
        raise SystemExit('You have uncommitted changes. Commit and push them first.')
    existing = subprocess.run(['git', 'tag', '--list', version], capture_output=True, text=True,
                              check=True, cwd=bastion_common.REPO_ROOT).stdout
    if existing.strip():
        raise SystemExit(f'Tag {version} already exists. Bump [release] revision in '
                         'config/bastion.toml first.')
    subprocess.run(['git', 'tag', version], check=True, cwd=bastion_common.REPO_ROOT)
    subprocess.run(['git', 'push', 'origin', version], check=True, cwd=bastion_common.REPO_ROOT)
    print(f'Pushed tag {version}. Watch the build in the Actions tab on GitHub.')


if __name__ == '__main__':
    main()
