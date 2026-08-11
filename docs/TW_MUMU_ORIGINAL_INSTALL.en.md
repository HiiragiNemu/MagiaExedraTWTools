# Install or update the original Taiwan XAPK on MuMu

This tool requires Python 3.10 or newer plus Android Platform Tools. It installs
the unmodified original XAPK. It does not patch the APK, signature, license
response, or game code, and it never reads or records game-account data.

Verified result: the original game Activity can start without changing a Google
account to the Taiwan region, instead of redirecting to Google Play. Server
availability, network routing, guest login, and data handover remain separate
steps.

## Prerequisites

1. Install Python 3.10 or newer.
2. Install `adb`, start a 64-bit MuMu instance, and enable ADB debugging.
3. Have the original XAPK available, or let the wizard download the release
   selected by the trust manifest.

## Easiest method: double-click the Python wizard

Double-click `install_tw.py` in the repository root, or run:

```text
python install_tw.py
```

No long command is required. The wizard automatically:

1. finds `adb` through environment variables, PATH, Android SDK, and common
   MuMu install locations;
2. detects ready MuMu/ADB devices, auto-selects a sole device, and requires a
   numbered choice when several are connected;
3. finds `.xapk` files beside the tool, in the current directory, Downloads,
   Desktop, and Windows drive roots;
4. offers the verified latest download or a discovered local original XAPK;
5. displays the device, source, data-preservation, backup, and no-launch choices
   before one final confirmation.

If no device is visible, enter the MuMu ADB address, for example
`127.0.0.1:16384`. Missing ADB, offline/unauthorized devices, and multiple
devices are reported explicitly; the wizard never silently chooses a different
target. Cancellation, closed input, and Ctrl+C preserve completed checkpoints.
After a double-click run, the window waits for Enter so the result remains
readable.

Defaults are always: preserve game data with `-r`, back up the installed APK
set before updating, explicitly run `am force-stop`, and use `pidof` to verify
that no game process remains. Use the advanced command below with an explicit
`--launch` only when you want it started; launch then occurs after the package,
version, split, and installer checks pass.

Downloads are **direct by default**. An empty proxy prompt becomes `None` and
disables inherited operating-system and environment proxies. A proxy is used
only when you enter one explicitly or pass `--proxy`.

If automatic discovery misses `adb.exe`, set `TW_ADB` to its full path. If the
XAPK is elsewhere, choose `P` in the wizard and paste its full path.

## Advanced command-line use

## Download the latest release and install/update

```text
python tools/tw_original_installer.py --download-latest --serial HOST:ADB_PORT
```

An optional explicit proxy applies only to the XAPK download. It does not
change MuMu Wi-Fi, the system proxy, or ADB reverse rules. Omitting `--proxy`
is direct; replace the port placeholder below when needed:

```text
python tools/tw_original_installer.py --download-latest --proxy http://127.0.0.1:<YOUR_PROXY_PORT> --serial HOST:ADB_PORT
```

For Android 11+ installation entirely on one phone, without a computer, see
the [Android phone-only guide](TW_ANDROID_PHONE_INSTALL.en.md). It documents
both the Shizuku GUI route and the hash-enforcing Termux route.

Downloads use a `.part` file, HTTP Range, a strong ETag or Last-Modified
validator, strict range and length checks, a four-GiB streaming ceiling,
SHA-256, and atomic completion. Run the same command again to resume.

## Use a local original XAPK

Fresh install or in-place update:

```text
python tools/tw_original_installer.py --xapk ORIGINAL_CLIENT.xapk --serial HOST:ADB_PORT
```

Validate files without looking for ADB or connecting to an emulator:

```text
python tools/tw_original_installer.py --xapk ORIGINAL_CLIENT.xapk --validate-only
```

The default is **no launch**. Launch occurs only when `--launch` is explicitly
added after all checks pass:

```text
python tools/tw_original_installer.py --xapk ORIGINAL_CLIENT.xapk --serial HOST:ADB_PORT --launch
```

## Release trust manifest

`manifests/known-releases.json` is the sole trust source for listed releases:

- `latestVersion` selects the release used by `--download-latest`;
- `latestEndpoint` supplies its download endpoint;
- every release pins the complete XAPK length and SHA-256; and
- it also pins lengths and SHA-256 values for `base`, `base_assets`, and
  `config.arm64_v8a`.

If a local XAPK version is listed, the tool automatically enforces every whole
and per-split pin. A command-line hash cannot override the manifest. An unlisted
version requires `--expected-xapk-sha256` obtained through a separately trusted
channel.

For a future official release, verify it and add one release record. Update
`latestVersion` when it becomes current. No Python source change is required.

## Installation behavior

The tool parses every AndroidManifest and accepts only:

```text
package: tw.sonet.magiaexedra
splits: base + base_assets + config.arm64_v8a
```

It rejects missing, duplicate, or extra splits, the wrong package, mixed
versions, suspicious compression, and encrypted APK entries. Fresh install and
old-version update both use atomic
`adb install-multiple -r -i com.android.vending`; `-r` preserves app data. If
launch was not requested, the tool then force-stops the package and verifies
with `pidof` that no game process remains. With explicit `--launch`, it validates
the installed package first and starts the game afterward. If adbd initially
runs as root, it is temporarily unrooted and its prior state is restored
afterward.

## Evidence and rollback

The default state directory is below the current user's local application-data
area and contains:

- `input.json`: XAPK trust, version, and per-split lengths/SHA-256;
- `before.json`: previous version, install source, split paths, and adbd state;
- `previous-apks/` plus `previous-apks.json`: complete pre-update APK backup;
- `adb-operations.jsonl`: ADB evidence without game-account material;
- `journal.json`: operation stage;
- `verification.json`: final version, installer, splits, and either verified
  stopped state or explicit-launch result;
- `rollback.py`: generated when complete rollback material exists.

Run from that state directory:

```text
python rollback.py --serial HOST:ADB_PORT
```

Rollback confirms that the current package still matches this operation's
target, verifies old split hashes, and restores them with `-r -d`. It rolls back
APKs, not application data; a newer client may migrate data an older client
cannot read. It stops on version drift. Do not use
`--skip-current-apk-backup` when rollback is required.

## Troubleshooting

- **ADB not found:** install Android Platform Tools or point `TW_ADB` to
  `adb.exe`, then reopen the wizard.
- **Device offline:** restart MuMu ADB debugging; if discovery stays empty,
  enter `HOST:ADB_PORT` in the wizard.
- **Several devices:** the wizard lists serials and models and requires a
  numbered choice; it does not default to the first one.
- **File validation fails:** do not mix versions or architectures; obtain the
  complete XAPK corresponding to the trust manifest.
- **Manifest still selects an older release:** verify the new artifacts, add the
  release, and update `latestVersion`.
- **Install succeeds but networking fails:** proxy, DNS, and exit region are
  independent from install-source attribution.
- **The game asks for login:** account flows are outside this installer. It does
  not touch passwords, UUIDs, JWTs, sessions, or cookies.

## Scope

This tool reproduces a complete original split installation and Android
install-source attribution. It does not invent a purchase record, modify or
re-sign the APK, skip an Activity, or intercept a license result. Revalidate a
new original XAPK when publisher client or server rules change.
