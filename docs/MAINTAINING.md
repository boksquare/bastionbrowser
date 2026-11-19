# Maintaining Bastion

A browser has to stay current: Chromium ships security fixes every few weeks,
and an outdated browser is exposed to publicly known attacks. Bastion
automates almost all of it. This guide covers the parts that need you.

## What happens automatically

Every day at 09:17 UTC, the **upstream-watch** workflow:

1. checks whether [ungoogled-chromium-windows](https://github.com/ungoogled-software/ungoogled-chromium-windows/releases)
   has a newer release (they usually follow a new Chrome version within days),
2. moves Bastion to it and applies every patch to the real Chromium source (~15 min),
3. if everything applies: commits, tags (e.g. `158.0.1234.56-1`) and starts the
   Windows **build**, which publishes a new
   [Release](https://github.com/boksquare/bastionbrowser/releases) about a day later,
4. if not: opens a GitHub **issue** titled *"Automatic update to … needs attention"*.

## One-time setup: get notified

On the repo page click **Watch → Custom**, tick **Issues** and **Releases**,
then **Apply**. GitHub will then email you when a new Bastion version is out
or when an update needs a hand.

## Installing a new version

Download the new `bastion_*_installer_x64.exe` from Releases and run it.
It updates Bastion in place; bookmarks, passwords, extensions and settings
stay. (A built-in updater is planned for Phase 6.)

## When the automatic update fails

Open the issue. It links to the run log and shows the last lines of the patch
check. The easiest fix is to open a Claude Code session on this repo and paste
the issue link. Otherwise, find your case below:

### "These patches are listed in config/bastion.toml exclude_patches but are no longer in the … series"
Upstream renamed or removed a patch Bastion skips. Look at
`upstream/ungoogled-chromium-windows/ungoogled-chromium/patches/series`
(and its git history) to see what it became, then update `exclude_patches`
in `config/bastion.toml`, or just delete the line if the patch is gone.

### "PATCH(ES) FAILED" and the failed file is under `patches/bastion/…`
One of Bastion's own patches no longer fits the new Chromium code. Refresh it:

1. On Linux/WSL, prepare a tree at the new version (the bump is not committed
   yet, so do it locally):
   ```bash
   python3 tools/bump_upstream.py --latest
   ```
   ```bash
   python3 tools/check_patches.py --workdir /tmp/bw
   ```
2. The checker leaves the source at `/tmp/bw/build/src` with all patches
   applied except the parts of the failing one that no longer fit. Those
   are saved as `.rej` files next to the affected source files. Apply the
   rejected changes by hand, then produce a new patch with `diff -u`
   against the original files (or `git diff` if you `git init` the tree
   before patching) for just the files that patch touches.
3. Replace the file under `patches/bastion/`, re-run `tools/check_patches.py`
   until it passes, then commit both the patch and the bump:
   ```bash
   git add -A && git commit -m "Update to upstream <tag>" && git push
   ```
   ```bash
   python3 tools/make_release.py
   ```

### "PATCH(ES) FAILED" and the failed file is an ungoogled-chromium patch
That's upstream's problem, not Bastion's, and very rare in a published
release. Close the issue and wait for upstream's next release; the
watcher will try again.

### "Upstream now installs Windows SDK …"
Copy the *Install Windows SDK* step from
`upstream/ungoogled-chromium-windows/.github/actions/prepare/action.yml`
into `.github/actions/prepare/action.yml`, commit, push, then run
**Actions → upstream-watch → Run workflow**.

## When a Windows build stage fails

Open the failed run in **Actions**:

- **One stage failed for a flaky reason** (network error, artifact upload,
  runner lost): click **Re-run failed jobs**. Each stage resumes from the
  previous stage's saved progress (kept 4 days).
- **A compile error**: the log says which file. Usually a Bastion patch
  conflicts with new code in a way that still applies but doesn't compile.
  Fix the patch as above.

## Releasing your own changes

1. Change what you need (patches, config, branding), and make sure
   `python3 tools/check_patches.py` passes.
2. Increase `revision` in `config/bastion.toml` (e.g. `1` → `2`), commit, push.
3. Run `python3 tools/make_release.py`. It tags the commit; the tag starts
   the build, and the Release appears when the build finishes.

## Moving to a specific upstream version by hand

```bash
python3 tools/bump_upstream.py --to 157.0.8103.78-1.1
```

Then run the patch check, commit, push and `make_release.py` as above.

## Secrets

| Secret | Used for | Status |
|---|---|---|
| `BASTION_GOOGLE_API_KEY` | Translate and Safe Browsing | Phase 1. Optional; builds work without it |

Add secrets under **Settings → Secrets and variables → Actions → New
repository secret**. Never commit keys to the repo; it is public.
