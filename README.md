# Magia Exedra Taiwan Tools

Public, reproducible Python tools for the original Taiwan Android client and for
future Taiwan resource, scenario, and video-data integration.

The Git source tree contains no APKs, account credentials, UUIDs, JWTs,
sessions, cookies, or private captures. A hash-pinned copy of the original
1.1.2 XAPK is provided as a GitHub Release asset so the wizard does not depend
on a Taiwan-region Google Play account or a third-party download page.

## Original XAPK install/update on MuMu

Requirements:

- Python 3.10 or newer;
- Android Platform Tools (`adb`);
- a running 64-bit MuMu instance with ADB debugging enabled.

### Easiest path: double-click the Python wizard

Double-click [`install_tw.py`](install_tw.py), or run it without arguments:

```text
python install_tw.py
```

The bilingual wizard finds `adb` from PATH, Android SDK, common MuMu install
locations, or `TW_ADB`; discovers ready MuMu/ADB devices; and lists original
XAPKs placed beside the tool, in the current directory, Downloads, Desktop, or
the root of a Windows drive. It safely asks which device to use when more than
one is connected. If no device is visible, it offers a manual MuMu ADB address.

Choose the verified latest download or a discovered local XAPK, review the
summary, and confirm once. The default always preserves app data, backs up the
currently installed split APKs, and **keeps the game stopped**. Missing ADB,
offline/unauthorized devices, invalid files, cancellation, and Ctrl+C are
reported without silently selecting a different device. The window pauses at
the end so a double-click user can read the result.

The CLI accepts either a local original XAPK or downloads the release selected
by [`manifests/known-releases.json`](manifests/known-releases.json). It validates
the whole XAPK plus the exact original `base`, `base_assets`, and
`config.arm64_v8a` split set, preserves the current package state, installs or
updates atomically, verifies the result, and creates JSON evidence plus a
package-level rollback.

It has been verified to start the original game Activity without changing a
Google account to the Taiwan region. No APK patch, re-signing, Activity skip, or
license-response interception is used. The tool **does not launch by default**;
pass `--launch` explicitly when desired.

- [中文使用说明](docs/TW_MUMU_ORIGINAL_INSTALL.zh-CN.md)
- [English guide](docs/TW_MUMU_ORIGINAL_INSTALL.en.md)
- [MIT license](LICENSE)
- CLI: [`tools/tw_original_installer.py`](tools/tw_original_installer.py)
- Double-click wizard: [`install_tw.py`](install_tw.py)
- Release trust manifest: [`manifests/known-releases.json`](manifests/known-releases.json)

Download, verify, install/update, and keep the game stopped:

```text
python tools/tw_original_installer.py --download-latest --serial HOST:ADB_PORT
```

Use an optional HTTP proxy only for the XAPK download:

```text
python tools/tw_original_installer.py --download-latest --proxy http://PROXY_HOST:PROXY_PORT --serial HOST:ADB_PORT
```

Install/update from a local known XAPK:

```text
python tools/tw_original_installer.py --xapk ORIGINAL_CLIENT.xapk --serial HOST:ADB_PORT
```

Validate without ADB:

```text
python tools/tw_original_installer.py --xapk ORIGINAL_CLIENT.xapk --validate-only
```

Launch only after all installation checks pass:

```text
python tools/tw_original_installer.py --xapk ORIGINAL_CLIENT.xapk --serial HOST:ADB_PORT --launch
```

### Release trust model

`latestVersion` in the release manifest is the sole selector for
`--download-latest`. Its endpoint, whole-XAPK length/SHA-256, and all three
split lengths/SHA-256 values are mandatory. A local XAPK whose version is in
the manifest is automatically checked against every pin; a command-line hash
cannot replace those pins.

An unlisted local version is accepted only with a separately trusted
`--expected-xapk-sha256`. Adding a future official release requires updating
only `manifests/known-releases.json`, including `latestVersion` when that release
becomes current. No Python source edit is needed.

Downloads use a resumable `.part` file, a strong ETag or Last-Modified
validator, strict Range checks, a four-GiB streaming ceiling, trusted length and
SHA-256 verification, and atomic completion.

### Installation and rollback

Fresh install and old-version update use the same command. The package operation
is always:

```text
adb install-multiple -r -i com.android.vending BASE ASSET_SPLIT ABI_SPLIT
```

When adbd initially runs as root, the tool temporarily switches it to shell
mode and restores the original root state afterward. It changes no emulator
proxy or network setting and reads no game-account data.

Existing splits are backed up before an update. The reported state directory
contains `input.json`, `before.json`, `previous-apks.json`,
`adb-operations.jsonl`, `journal.json`, `verification.json`, and—when complete
rollback material exists—`rollback.py`. Rollback verifies version drift and
backup hashes before changing the package. It is an APK-level rollback, not an
application-data snapshot.

## Taiwan data-pipeline status

The installed game's initial on-demand cache is not a complete corpus. The
companion research pipeline now obtains data from the authoritative Resource
catalog instead of treating the initial approximately 2 GB cache as complete.
The current TW 1.1.2 verification recovered 6,268 Resource records and 14,386
AssetBundle records, downloaded all 6,268 Resource files, and parsed all 2,780
official `zh_TW` scenario JSON files with zero missing or failed entries. The
remaining work is to turn the private-session bootstrap into a documented CI
secret interface and publish the reusable downloader in the companion research
repository.

Pipeline stages:

1. fetch and version the complete Taiwan Resource catalog (verified);
2. resolve every entry through the selected GCS or legacy transport (verified
   for the current legacy route);
3. resume downloads and verify count, missing count, failure count, size, and
   SHA-256;
4. decode the complete official `zh_TW` story/scenario JSON set for reader
   integration (verified for TW 1.1.2);
5. expose a stable scenario index and provenance report without private
   account/session material;
6. add optional Taiwan video-manifest and media download support; and
7. provide deterministic exports for the Exedra reader and wiki-compatible
   tooling.

## Repository rules

- Never commit credentials, handover codes, identifiers, tokens, sessions,
  cookies, or authenticated traffic.
- Never commit APK/XAPK/APKS packages or downloaded publisher resources.
- Keep generated state and rollback copies outside Git.
- Tests run offline; optional live verification must be explicit.

## Tests

```text
python -m unittest discover -s tests -v
python -m compileall -q install_tw.py tools tests
```

The suite covers the no-argument wizard with a fake ADB device, multi-device
selection, missing ADB, fresh install, update, default no-launch behavior,
rollback, manifest-driven latest selection, known/unknown release trust,
strict XAPK identity, and bounded resumable downloads using loopback-only
fixtures. Tests never operate a real emulator.
