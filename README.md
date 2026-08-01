# Magia Exedra Taiwan Tools

Public, reproducible Python tools for the original Taiwan Android client and for
future Taiwan resource, scenario, and video-data integration.

This repository contains no APKs, account credentials, UUIDs, JWTs, sessions,
cookies, private captures, or publisher assets.

## Original XAPK install/update on MuMu

Requirements:

- Python 3.10 or newer;
- Android Platform Tools (`adb`);
- a running 64-bit MuMu instance with ADB debugging enabled.

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

## Planned Taiwan data pipeline

The installed game's initial on-demand cache is not a complete corpus. The
planned public pipeline will obtain data from the authoritative Resource
catalog instead of treating the initial approximately 2 GB cache as complete.

Planned stages:

1. fetch and version the complete Taiwan Resource catalog;
2. resolve every entry through the selected GCS or legacy transport;
3. resume downloads and verify count, missing count, failure count, size, and
   SHA-256;
4. decode the complete official `zh_TW` story/scenario JSON set for reader
   integration;
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
python -m compileall -q tools tests
```

The suite covers fresh install, update, default no-launch behavior, rollback,
manifest-driven latest selection, known/unknown release trust, strict XAPK
identity, and bounded resumable downloads using loopback-only fixtures.
