# Bastion plan

## Goals (acceptance criteria)

1. **Fast and light**: lower RAM use than Chrome and Firefox on the same
   workload, measured, not assumed.
2. **All the normal browser features**: password saving, autofill, passkeys,
   incognito, profiles, history, bookmarks, downloads, PDF viewer.
3. **Very strong built-in ad blocking**, including YouTube and Twitch ads.
4. **Very strong pop-up blocking**, including invisible click-hijacking
   overlays on videos and images that open ad tabs.
5. **Works on practically every site**, like Chrome.
6. Chrome Web Store extensions: preferred, not required.

## Decisions so far

| Topic | Decision |
|---|---|
| Use | Personal |
| Platform | Windows x64 only |
| Engine | Chromium, starting from ungoogled-chromium (Option A) |
| Builds | Public GitHub repo + free GitHub Actions runners (chained stages, ~1 day per full build) |
| Sync | None for now; Chromium's sync code stays in (disabled) so a self-hosted sync server can be added later |
| DRM (Netflix, Spotify, Prime, Disney+) | Not required. Non-DRM video (YouTube, Twitch, Kick, Vimeo, ...) must work, so H.264/AAC are enabled |
| Maintenance | Automated; the owner handles exceptions with docs/MAINTAINING.md |
| Name | Bastion (teal shield and tower logo) |
| Default search | Google (changeable in settings) |

### Google services

| Service | Plan |
|---|---|
| Translate | **Keep.** Chromium only offers translation when the build has a Google API key (`google_apis::HasAPIKeyConfigured()`). Phase 1 adds one via a GitHub secret (`BASTION_GOOGLE_API_KEY`), or falls back to on-device translation if Google won't issue a usable key. |
| Safe Browsing | **Keep** (malware and phishing warnings). ungoogled-chromium removes it, so Phase 1 restores it. It also needs the API key. |
| Certificate revocation updates, basic spell check | Keep |
| Push notifications (Google's push service), Cast | Phase 1 decision; both depend on Google services that may not accept third-party builds |
| Usage stats, crash upload, remote experiments (Finch), on-device AI models, Privacy Sandbox ad APIs, Google sign-in, Google Pay autofill, Lens, password leak check | Removed (ungoogled-chromium already does this) |

## Phases

### Phase 0: Foundation (current)
- [x] Repo layout: upstream pinned as a submodule, Bastion's changes layered on top
- [x] Skip the ungoogled patches that break Bastion's goals: default prefs
      (they turn off password saving and autofill), Web Store blocking, "no search" engine,
      always asking where to save downloads
- [x] Branding: name, logo, icons, own install folder, registry names and Windows IDs
      (no clashes with Chrome or other Chromium browsers); product strings renamed in all 81 languages
- [x] Cloud build pipeline (chained stages) and GitHub Releases
- [x] Fast Linux patch check
- [x] Daily automatic Chromium updates: patch check → tag → build → release, or an issue if a human is needed
- [ ] First successful Windows build, installed and smoke-tested

### Phase 1: Chrome-equivalent basics
- Confirm the Chrome Web Store "Add to Chrome" button and extension auto-updates work
- Restore Safe Browsing; add the Google API key; make Translate work
- Bastion default preferences (passwords and autofill on, background mode off, sensible privacy)
- Own new tab page; first-run page
- Decide on push notifications and Cast

### Phase 2: Built-in ad blocker
- Brave's open-source `adblock-rust` engine wired into Chromium's network
  layer (blocks requests before they leave the browser; not limited by Manifest V3)
- Cosmetic filtering (hides leftover ad boxes) and scriptlet injection
  (needed for YouTube ads and anti-adblock walls)
- Filter lists: EasyList, EasyPrivacy, uBlock Origin's lists (including Quick
  Fixes for YouTube), AdGuard. Updated in the browser every few hours, no rebuild needed
- Twitch: strip or replace ad segments in the video stream. Best effort;
  Twitch inserts ads server-side and no blocker catches all of them
- Per-site on/off switch, element picker
- Prototype and test here first (scripts against a real Chromium), then port into the browser

### Phase 3: Pop-up and overlay guard
Layered on top of Chromium's normal blocker, which misses overlay ads because the click is real:
- `$popup` filter rules applied to new windows and tabs
- Overlay-click detection: if the clicked element is an invisible or
  near-full-screen top layer (or a cross-site ad frame) and the click opens a
  new cross-site tab, block it and send the click to the real content underneath
- Tab-under blocking (opener tab redirected right after a pop-up), pop-unders,
  `window.open` from ad iframes without a click inside them, notification-permission spam, redirect chains
- "Blocked" badge with allow once / always allow
- Test pages that reproduce each trick

### Phase 4: Memory and speed
- Tab freezing and discarding tuned for low RAM; fewer helper processes,
  without weakening site isolation
- Remove remaining background services
- Benchmark script: same tab set in Bastion vs Chrome, Edge, Brave and Firefox
  (memory), plus Speedometer 3 (speed)

### Phase 5: Testing
- Top-500-sites compatibility run, ad-block test suites, the pop-up test pages,
  manual YouTube and Twitch checks

### Phase 6: Polish
- In-browser auto-update from GitHub Releases
- Optional: code signing, Widevine (DRM), sync server

## Known limits (honest)
- The executable is still named `chrome.exe` (shortcuts, window titles and
  installer say Bastion). Renaming it touches many build files; maybe later.
- Twitch ad blocking will be best effort (see Phase 2).
- RAM: same engine as Chrome, so the savings come from blocking, tab
  management and removed services. Phase 4 measures it.
