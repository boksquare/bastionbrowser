#!/usr/bin/env python3
"""Applies Bastion branding to a patched Chromium source tree.

Run automatically by build.py after all patches are applied. Can also be run
by hand:  python branding/apply.py <path to chromium src>

It does three things:
  * replaces the Chromium logo files with Bastion's (branding/generated/),
  * rewrites chrome/app/theme/chromium/BRANDING (product/company names),
  * renames "Chromium" to "Bastion" in the user-visible product strings,
    while keeping credit to the Chromium project ("The Chromium Authors",
    "the Chromium open source project").

The install folder, registry names and Windows IDs are changed by
patches/bastion/branding/install-modes.patch instead.
"""

import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GEN = HERE / 'generated'
SOURCE = HERE / 'source'

# Destination (relative to the Chromium src dir) -> file in branding/.
ICON_MAP = {
    'chrome/app/theme/chromium/win/chromium.ico': GEN / 'bastion.ico',
    'chrome/app/theme/chromium/win/tiles/Logo.png': GEN / 'logo_600.png',
    'chrome/app/theme/chromium/win/tiles/SmallLogo.png': GEN / 'logo_176.png',
    'chrome/app/theme/chromium/product_logo_16.png': GEN / 'logo_16.png',
    'chrome/app/theme/chromium/product_logo_24.png': GEN / 'logo_24.png',
    'chrome/app/theme/chromium/product_logo_48.png': GEN / 'logo_48.png',
    'chrome/app/theme/chromium/product_logo_64.png': GEN / 'logo_64.png',
    'chrome/app/theme/chromium/product_logo_128.png': GEN / 'logo_128.png',
    'chrome/app/theme/chromium/product_logo_256.png': GEN / 'logo_256.png',
    'chrome/app/theme/chromium/product_logo.svg': SOURCE / 'logo.svg',
    'chrome/app/theme/chromium/product_logo_animation.svg': SOURCE / 'logo.svg',
    'chrome/app/theme/default_100_percent/chromium/product_logo_16.png': GEN / 'logo_16.png',
    'chrome/app/theme/default_100_percent/chromium/product_logo_32.png': GEN / 'logo_32.png',
    'chrome/app/theme/default_200_percent/chromium/product_logo_16.png': GEN / 'logo_32.png',
    'chrome/app/theme/default_200_percent/chromium/product_logo_32.png': GEN / 'logo_64.png',
    'chrome/app/theme/default_100_percent/chromium/product_logo_name_22.png':
        GEN / 'product_logo_name_22.png',
    'chrome/app/theme/default_100_percent/chromium/product_logo_name_22_white.png':
        GEN / 'product_logo_name_22_white.png',
    'chrome/app/theme/default_200_percent/chromium/product_logo_name_22.png':
        GEN / 'product_logo_name_22@2x.png',
    'chrome/app/theme/default_200_percent/chromium/product_logo_name_22_white.png':
        GEN / 'product_logo_name_22_white@2x.png',
}

BRANDING_FILE = 'chrome/app/theme/chromium/BRANDING'
BRANDING_VALUES = {
    'COMPANY_FULLNAME': 'Bastion',
    'COMPANY_SHORTNAME': 'Bastion',
    'PRODUCT_FULLNAME': 'Bastion',
    'PRODUCT_SHORTNAME': 'Bastion',
    'PRODUCT_INSTALLER_FULLNAME': 'Bastion Installer',
    'PRODUCT_INSTALLER_SHORTNAME': 'Bastion Installer',
    'COPYRIGHT': 'Copyright @LASTCHANGE_YEAR@ The Chromium Authors and Bastion contributors. '
                 'All rights reserved.',
}

# String files that name the product: (English .grd, glob of its translations).
# Paths are relative to src.
STRING_FILES = [
    ('chrome/app/chromium_strings.grd', 'chrome/app/resources/chromium_strings_*.xtb'),
    ('components/components_chromium_strings.grd',
     'components/strings/components_chromium_strings_*.xtb'),
]

# "Chromium" as a whole word, except where it credits the Chromium project.
_PRODUCT_NAME_RE = re.compile(
    r'\bChromium\b(?!\s+(?:Authors|open[ -]source|project|OS)\b)(?!OS\b)')
# Text inside these attributes/elements is metadata, not shown to users;
# rewriting it is harmless, but URLs must never change.
_URL_RE = re.compile(r'https?://[^\s"<>]+')


def _rename_product(text):
    # Protect URLs, rename, restore.
    urls = []

    def stash(match):
        urls.append(match.group(0))
        return f'\x00{len(urls) - 1}\x00'

    text = _URL_RE.sub(stash, text)
    text = _PRODUCT_NAME_RE.sub('Bastion', text)
    return re.sub(r'\x00(\d+)\x00', lambda m: urls[int(m.group(1))], text)


def _message_ids(src, grd_path):
    """Grit message IDs of every <message> in grd_path, in document order.

    A translation (.xtb) is matched to its English message by an ID computed
    from the English text, so renaming the product in the English text changes
    the ID. We compute IDs before and after renaming and re-point the
    translations, which keeps every language translated.
    """
    grit_dir = str(src / 'tools' / 'grit')
    if grit_dir not in sys.path:
        sys.path.insert(0, grit_dir)
    from grit import grd_reader  # pylint: disable=import-outside-toplevel
    from grit.node import message  # pylint: disable=import-outside-toplevel
    root = grd_reader.Parse(str(grd_path), debug=False, skip_validation_checks=True)
    return [node.GetCliques()[0].GetId() for node in root.Preorder()
            if isinstance(node, message.MessageNode)]


_PART_RE = re.compile(r'<part\s+file="([^"]+)"')


def _grd_with_parts(grd_path):
    """grd_path plus every .grdp file it pulls in with <part file="...">.

    Parts can include further parts; each path is relative to the file that
    names it. E.g. chromium_strings.grd keeps ~140 settings strings
    ("About Chromium", ...) in settings_chromium_strings.grdp.
    """
    files, queue = [], [grd_path]
    while queue:
        path = queue.pop(0)
        if path in files:
            continue
        if not path.exists():
            raise SystemExit(f'Branding: missing string file {path}')
        files.append(path)
        queue.extend(path.parent / rel for rel in
                     _PART_RE.findall(path.read_text(encoding='utf-8')))
    return files


def _rebrand_strings(src, grd_rel, xtb_glob):
    grd_path = src / grd_rel
    xtb_paths = sorted(src.glob(xtb_glob))
    if not grd_path.exists() or not xtb_paths:
        raise SystemExit(f'Branding: missing {grd_rel} or its translations ({xtb_glob})')

    old_ids = _message_ids(src, grd_path)
    for path in _grd_with_parts(grd_path):
        path.write_text(_rename_product(path.read_text(encoding='utf-8')), encoding='utf-8')
    new_ids = _message_ids(src, grd_path)
    if len(old_ids) != len(new_ids):
        raise SystemExit(f'Branding: message count changed while rebranding {grd_rel}')
    id_map = {old: new for old, new in zip(old_ids, new_ids) if old != new}

    id_re = re.compile(r'(<translation id=")(\d+)(")')
    for path in xtb_paths:
        text = path.read_text(encoding='utf-8')
        text = id_re.sub(lambda m: m.group(1) + id_map.get(m.group(2), m.group(2)) + m.group(3),
                         text)
        path.write_text(_rename_product(text), encoding='utf-8')
    return len(id_map), len(xtb_paths)


def apply(src):
    src = Path(src)
    if not (src / 'chrome').is_dir():
        raise SystemExit(f'Not a Chromium source tree: {src}')

    for dest_rel, origin in ICON_MAP.items():
        dest = src / dest_rel
        if not dest.exists():
            raise SystemExit(f'Branding: expected Chromium file is missing: {dest_rel}')
        shutil.copyfile(origin, dest)

    branding_path = src / BRANDING_FILE
    lines = branding_path.read_text(encoding='utf-8').splitlines()
    out = []
    for line in lines:
        key = line.split('=', 1)[0]
        out.append(f'{key}={BRANDING_VALUES[key]}' if key in BRANDING_VALUES else line)
    branding_path.write_text('\n'.join(out) + '\n', encoding='utf-8')

    summary = []
    for grd_rel, xtb_glob in STRING_FILES:
        renamed, languages = _rebrand_strings(src, grd_rel, xtb_glob)
        summary.append(f'{grd_rel}: {renamed} messages renamed across {languages} languages')
    print(f'Branding applied: {len(ICON_MAP)} images, BRANDING file.')
    for line in summary:
        print('  ' + line)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    apply(sys.argv[1])
