# Magia Exedra TW Original XAPK Installer

Public, reproducible tools for installing or upgrading the **original, unmodified
Taiwan Android client** without switching a Google Play account to the Taiwan
region.

This repository is intentionally limited to XAPK installation, update, integrity
verification, backup, and rollback.

## Supported routes

### Windows / MuMu

Requirements:

- Python 3.10 or newer;
- Android Platform Tools (`adb`);
- a 64-bit MuMu instance with ADB debugging enabled.

Run:

```text
py -3 install_tw.py
```

The wizard detects ADB devices, offers the pinned original XAPK or a local XAPK,
validates the complete three-split package, shows a summary, and installs only
after confirmation. Downloads are direct by default. An optional proxy is used
only when the operator explicitly enters one; no machine-specific proxy is
embedded in the tool.

The install operation is equivalent to:

```text
adb install-multiple -r -i com.android.vending BASE ASSET_SPLIT ABI_SPLIT
```

`-r` preserves application data. By default the installer explicitly force-stops
the package and verifies that no game process remains; it launches only when
`--launch` is requested. For an upgrade it first stores and hashes the currently
installed split APKs and writes a runnable `rollback.py` beside the backup.

Guides:

- [Windows / MuMu guide (中文)](docs/TW_MUMU_ORIGINAL_INSTALL.zh-CN.md)
- [Windows / MuMu guide (English)](docs/TW_MUMU_ORIGINAL_INSTALL.en.md)

### Android 11+ phone only

No computer or emulator is required. Two documented routes are available:

1. Shizuku plus a split-APK installer that exposes the installer-package field;
2. Termux, Android Wireless debugging, `android-tools`, and the repository's
   hash-enforcing shell script.

Guides:

- [Android phone-only guide (中文)](docs/TW_ANDROID_PHONE_INSTALL.zh-CN.md)
- [Android phone-only guide (English)](docs/TW_ANDROID_PHONE_INSTALL.en.md)

Android 10 and older should use the Windows/ADB route because they do not provide
the same built-in on-device Wireless debugging flow.

## Integrity and release selection

The trusted original-client metadata is stored in
[`manifests/known-releases.json`](manifests/known-releases.json). The installer
checks the XAPK hash, package name, version, required split names, per-split
hashes, and supported ABI before installation.

Current pinned original client:

- package: `tw.sonet.magiaexedra`
- version: `1.1.2` (`26072717`)
- XAPK SHA-256:
  `664dfbc307c5f6b640d01b1fc661de02fa30fc382a68426530abc657dc9e2d14`

## Update safety and rollback

- Fresh install: rollback removes only the installed package.
- Upgrade: rollback verifies both version drift and backup hashes before
  restoring the previous split set.
- The tool never backs up or reads game-account credentials.
- The tool does not write Windows system proxy, WinHTTP, DNS, routes, firewall,
  VPN, or TUN configuration.
- The game remains stopped after installation so the operator controls first
  launch.

## Development verification

```text
py -3 -m pytest -q
```

The test suite uses temporary fixtures and fake ADB runners. It does not modify a
real emulator or phone.

## License

[MIT](LICENSE)
