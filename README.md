# Bastion

A fast, private Chromium-based browser for Windows with strong built-in ad and
pop-up blocking. Chrome Web Store extensions work.

> **Status: Phase 0 (foundation).** The build pipeline, branding and
> auto-update automation are in place; the first builds are a de-Googled,
> Bastion-branded Chromium. The built-in ad blocker, pop-up/overlay guard and
> memory work come in the next phases. See [docs/PLAN.md](docs/PLAN.md).

## Get Bastion

Download the latest `bastion_*_installer_x64.exe` from
[Releases](https://github.com/boksquare/bastionbrowser/releases) and run it.
It installs for your Windows user only (no admin prompt), into
`%LOCALAPPDATA%\Bastion`. A portable `.zip` is published too.

The builds aren't code-signed yet, so Windows SmartScreen will warn the
first time: click **More info → Run anyway**.

## How it's built

Bastion is Chromium plus a small, focused set of changes:

```
Chromium (Google, open source)
  └─ ungoogled-chromium            removes Google tracking and background services
       └─ ungoogled-chromium-windows   Windows build fixes and toolchain
            └─ Bastion                  this repo: keeps the useful Google bits,
                                        branding, ad/pop-up blocking (coming), tuning
```

Upstream is pinned as a git submodule in `upstream/`; Bastion never edits
it. `build.py` copies it to a work directory and layers Bastion's changes on
top (see `tools/bastion_common.py`). That keeps monthly Chromium updates
mostly automatic.

| Path | What it is |
|---|---|
| `config/bastion.toml` | Which upstream patches Bastion skips, version revision |
| `config/flags.bastion.gn` | Extra Chromium build flags |
| `patches/` | Bastion's own Chromium patches (`patches/series` lists them in order) |
| `branding/` | Logo source, rendered icons, and the script that rebrands the source |
| `build.py` | Builds Bastion (runs upstream's build with Bastion's changes) |
| `package.py` | Turns a finished build into the installer and zip |
| `tools/` | Patch checker, upstream updater, release helper |
| `.github/workflows/` | Cloud builds, daily upstream check, patch checks |

## Docs

* [docs/PLAN.md](docs/PLAN.md): goals, phases, decisions
* [docs/BUILDING.md](docs/BUILDING.md): how builds work, and building on your own PC
* [docs/MAINTAINING.md](docs/MAINTAINING.md): keeping Bastion up to date, step by step

## License

Bastion's own scripts and patches: BSD 3-Clause (see [LICENSE](LICENSE)).
Chromium, ungoogled-chromium and ungoogled-chromium-windows keep their own
licenses (BSD-style); see their repositories.
