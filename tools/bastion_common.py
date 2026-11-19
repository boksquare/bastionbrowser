"""Shared helpers for Bastion's build scripts.

Bastion does not fork ungoogled-chromium-windows' build scripts. Instead it
copies that project (pinned in upstream/) into a working directory and makes a
few precise changes there before running its build:

  1. drops the ungoogled-chromium patches listed in config/bastion.toml,
  2. appends Bastion's own patches (patches/series) to the Windows series,
  3. appends Bastion's GN flags,
  4. swaps in Bastion's package.py so outputs are named bastion_*.

That keeps upstream untouched, so a Chromium update is mostly "move the
submodule to the new tag" (see docs/MAINTAINING.md).
"""

import shutil
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
UPSTREAM_DIR = REPO_ROOT / 'upstream' / 'ungoogled-chromium-windows'
CONFIG_PATH = REPO_ROOT / 'config' / 'bastion.toml'
PATCHES_DIR = REPO_ROOT / 'patches'

# Files and folders of the upstream checkout that are never copied into the
# work directory (build/ holds the multi-GB Chromium tree and is preserved).
_SKIP_COPY = {'.git', '.github', 'build', '__pycache__'}


class ConfigError(RuntimeError):
    """Raised when config/bastion.toml no longer matches upstream."""


def load_config():
    with open(CONFIG_PATH, 'rb') as f:
        return tomllib.load(f)


def chromium_version():
    return (UPSTREAM_DIR / 'ungoogled-chromium' / 'chromium_version.txt').read_text().strip()


def bastion_version(config=None):
    """Version string used in file names and release tags, e.g. 157.0.8103.78-1."""
    config = config or load_config()
    return f"{chromium_version()}-{config['release']['revision']}"


def _read_series(path):
    return [line.strip() for line in path.read_text(encoding='utf-8').splitlines()]


def _copy_upstream(workdir):
    """Copies upstream/ungoogled-chromium-windows into workdir, keeping workdir/build."""
    workdir.mkdir(parents=True, exist_ok=True)
    for item in UPSTREAM_DIR.iterdir():
        if item.name in _SKIP_COPY:
            continue
        dest = workdir / item.name
        if dest.is_dir():
            shutil.rmtree(dest)
        elif dest.exists():
            dest.unlink()
        if item.is_dir():
            shutil.copytree(item, dest, ignore=shutil.ignore_patterns('.git', '__pycache__'))
        else:
            shutil.copy2(item, dest)


def _apply_patch_exclusions(workdir, excluded):
    series_path = workdir / 'ungoogled-chromium' / 'patches' / 'series'
    lines = _read_series(series_path)
    missing = [p for p in excluded if p not in lines]
    if missing:
        raise ConfigError(
            'These patches are listed in config/bastion.toml exclude_patches but are no '
            'longer in the ungoogled-chromium series (renamed or removed upstream). '
            'Check what replaced them, then update the config:\n  ' + '\n  '.join(missing))
    kept = [line for line in lines if line not in excluded]
    series_path.write_text('\n'.join(kept) + '\n', encoding='utf-8')


def bastion_patch_series():
    """Bastion's own patches, in order, relative to patches/."""
    return [line for line in _read_series(PATCHES_DIR / 'series')
            if line and not line.startswith('#')]


def _add_bastion_patches(workdir):
    series = bastion_patch_series()
    for rel in series:
        if not rel.startswith('bastion/'):
            raise ConfigError(f'patches/series: {rel} must live under patches/bastion/')
        if not (PATCHES_DIR / rel).is_file():
            raise ConfigError(f'patches/series lists {rel}, but patches/{rel} does not exist')
    # Copied next to upstream's Windows patches (workdir/patches/bastion/...).
    dest_root = workdir / 'patches' / 'bastion'
    if dest_root.exists():
        shutil.rmtree(dest_root)
    for rel in series:
        dest = workdir / 'patches' / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PATCHES_DIR / rel, dest)
    win_series = workdir / 'patches' / 'series'
    lines = [line for line in _read_series(win_series) if line]
    lines += series
    win_series.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def _add_gn_flags(workdir, config, extra_flags=()):
    flags_path = workdir / 'flags.windows.gn'
    text = flags_path.read_text(encoding='utf-8').rstrip('\n') + '\n'
    text += '\n# ---- Bastion (config/flags.bastion.gn) ----\n'
    text += (REPO_ROOT / config['gn']['flags_file']).read_text(encoding='utf-8')
    for flag in extra_flags:
        text += flag + '\n'
    flags_path.write_text(text, encoding='utf-8')


def prepare_workdir(workdir, extra_gn_flags=()):
    """Builds the patched copy of the upstream build scripts in workdir."""
    if not (UPSTREAM_DIR / 'build.py').exists():
        raise ConfigError(
            'upstream/ungoogled-chromium-windows is empty. Run:\n'
            '  git submodule update --init --recursive')
    config = load_config()
    workdir = Path(workdir)
    _copy_upstream(workdir)
    _apply_patch_exclusions(workdir, config['upstream']['exclude_patches'])
    _add_bastion_patches(workdir)
    _add_gn_flags(workdir, config, extra_gn_flags)
    shutil.copy2(REPO_ROOT / 'package.py', workdir / 'package.py')
    (workdir / 'bastion_version.txt').write_text(bastion_version(config) + '\n', encoding='utf-8')
    return config


def patch_files_in_order(workdir):
    """Every patch file the build applies, in order (ungoogled core, then Windows + Bastion)."""
    workdir = Path(workdir)
    result = []
    for patches_root in (workdir / 'ungoogled-chromium' / 'patches', workdir / 'patches'):
        for line in _read_series(patches_root / 'series'):
            if line and not line.startswith('#'):
                result.append(patches_root / line)
    return result


def fail(message):
    print(f'ERROR: {message}', file=sys.stderr)
    sys.exit(1)
