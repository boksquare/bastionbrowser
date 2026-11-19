#!/usr/bin/env python3
"""Builds Bastion for Windows x64.

What this does:
  1. Prepares a work directory: a copy of ungoogled-chromium-windows (pinned
     in upstream/) with Bastion's patch exclusions, extra patches and GN flags.
  2. Runs upstream's build.py from there, with one hook: right after all
     patches are applied (where upstream would run domain substitution),
     Bastion's branding is applied to the source tree.

Usage (on Windows, from a "x64 Native Tools" or normal prompt):
  python build.py                 # full local build
  python build.py --ci            # resumable build used by GitHub Actions
  python build.py --prepare-only  # only create the work directory

See docs/BUILDING.md for prerequisites.
"""

import argparse
import importlib.util
import os
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'tools'))
import bastion_common  # noqa: E402

sys.path.insert(0, str(bastion_common.REPO_ROOT / 'branding'))
import apply as branding  # noqa: E402

BUILD_TIMEOUT_EXIT_CODE = 124


def _extra_gn_flags():
    """GN flags that come from the environment instead of the repo."""
    flags = []
    # Optional Google API key (enables Translate / Safe Browsing). Supplied as a
    # GitHub Actions secret; never commit it. See docs/MAINTAINING.md.
    api_key = os.environ.get('BASTION_GOOGLE_API_KEY', '').strip()
    if api_key:
        if '"' in api_key or '\\' in api_key:
            bastion_common.fail('BASTION_GOOGLE_API_KEY contains invalid characters')
        flags.append(f'google_api_key="{api_key}"')
    return flags


def _load_upstream_build(workdir):
    spec = importlib.util.spec_from_file_location('upstream_build', workdir / 'build.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--workdir', type=Path, default=bastion_common.REPO_ROOT / 'work',
                        help='Where the patched build scripts and the Chromium tree live '
                             '(default: %(default)s). Keep this path short on Windows.')
    parser.add_argument('--prepare-only', action='store_true',
                        help='Only prepare the work directory, then stop.')
    args, upstream_args = parser.parse_known_args()

    workdir = args.workdir.resolve()
    try:
        config = bastion_common.prepare_workdir(workdir, _extra_gn_flags())
    except bastion_common.ConfigError as exc:
        bastion_common.fail(str(exc))
    print(f'Bastion {bastion_common.bastion_version(config)}: work directory ready at {workdir}')
    if args.prepare_only:
        return 0

    upstream = _load_upstream_build(workdir)

    # Hook: upstream calls domain_substitution.apply_substitution(...) exactly
    # once, right after applying every patch. Bastion runs its branding there,
    # and only runs the real substitution if the config asks for it.
    real_substitution = upstream.domain_substitution

    def post_patch_hook(regex_path, files_path, source_tree, *rest):
        branding.apply(Path(source_tree))
        if config['upstream']['domain_substitution']:
            real_substitution.apply_substitution(regex_path, files_path, source_tree, *rest)

    upstream.domain_substitution = types.SimpleNamespace(apply_substitution=post_patch_hook)

    sys.argv = [str(workdir / 'build.py')] + upstream_args
    try:
        upstream.main()
    except upstream._BuildTimeout:  # pylint: disable=protected-access
        return BUILD_TIMEOUT_EXIT_CODE
    return 0


if __name__ == '__main__':
    sys.exit(main())
