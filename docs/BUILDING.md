# Building Bastion

## In the cloud (the normal way)

Builds run on GitHub's free Windows runners (free because the repo is public).

- **Automatic:** the `upstream-watch` workflow builds and releases each new
  Chromium version by itself. See [MAINTAINING.md](MAINTAINING.md).
- **Release your own change:** bump `revision` in `config/bastion.toml`,
  commit, push, then run `python tools/make_release.py` (it tags the commit;
  the tag starts the `build` workflow, which publishes a Release when done).
- **Test build without a release:** GitHub → **Actions** → **build** →
  **Run workflow** on `main`. The installer appears as a downloadable
  artifact (`bastion-x64`) on the run page, kept for 4 days.

### Why it takes about a day
A GitHub runner has 4 CPU cores and 16 GB RAM, and a job may run at most 6
hours. Chromium needs far more than that, so `.github/workflows/build.yml`
is a chain of up to 16 stages: each builds for about 3.5 hours, zips the
half-built tree, and the next stage continues from it. Before any of that, a
fast Linux job (`check-patches`, ~15 min) makes sure every patch still
applies, so a broken patch fails in minutes instead of hours.

## Checking patches locally (Linux or WSL, ~15 min)

```bash
git clone --recurse-submodules https://github.com/boksquare/bastionbrowser
```

```bash
cd bastionbrowser && python3 tools/check_patches.py
```

It downloads the official Chromium source (~2 GB), applies every patch and
runs the branding step. Needs Python 3.11+, `patch`, and ~15 GB free disk.

## Building on your own Windows PC (optional)

Only worth it on a strong machine: 8+ cores, 32 GB RAM, 200 GB free on an SSD.
Expect 3–10 hours for the first build.

1. Install **Visual Studio 2022** (Community is fine) with the
   *Desktop development with C++* workload, plus the **Windows 11 SDK
   10.0.28000.0** (the version is in `.github/actions/prepare/action.yml`).
2. Install **Python 3.12**, **Git for Windows** and **7-Zip**, then run:
   ```powershell
   python -m pip install httplib2==0.22.0 clang==21.1.7
   ```
3. Clone to a short path (long paths break the Chromium build):
   ```powershell
   git clone --recurse-submodules https://github.com/boksquare/bastionbrowser C:\bastion
   ```
4. Build (resumable mode, the same one the cloud uses):
   ```powershell
   cd C:\bastion; python build.py --ci
   ```
   This mode stops itself after 3.5 hours of compiling (exit code 124). Run
   the same command again to continue where it stopped. When it finishes it
   packages the installer and zip into `C:\bastion\work\build\`.

To start over, for example after changing patches, delete
`C:\bastion\work\build\src` first. Otherwise the existing, already-patched
Chromium tree is reused.
