# Magia Exedra TW / JP Original XAPK Installer

Public, reproducible tools for installing or upgrading the **original, unmodified
Taiwan Android client** without switching a Google Play account to the Taiwan
region.

This repository is intentionally limited to XAPK installation, update, integrity
verification, backup, and rollback.

## 中文下载网站

**[打开 Exedra TW / JP 下载站](https://magia-exedra-tw-tools.pages.dev/)** — 直接下载文件，阅读电脑 / MuMu 与手机中文教程。

日服同步入口： [JP 3.18.0 原版 XAPK](https://github.com/HiiragiNemu/MagiaExedraTWTools/releases/download/jp-v3.18.0/com.aniplex.magia.exedra.jp-3.18.0.xapk) · [日服安装教程](docs/JP_ANDROID_INSTALL.zh-CN.md)。下载和 split 安装不依赖 Google Play 区域切换。

## 最新下载 / 非台区 Google 账号用户

**2026-09-12 更新：台服 Android 1.1.3（26082020）。** 本仓库与下列 Release 下载公开，无需 GitHub 账号。

- [下载原版台服 1.1.3 XAPK](https://github.com/HiiragiNemu/MagiaExedraTWTools/releases/download/v1.1.3/tw.sonet.magiaexedra-1.1.3-26082020.xapk)
- [下载 TW/JP 安装工具 v1.4.0 ZIP（电脑和手机教程均包含）](https://github.com/HiiragiNemu/MagiaExedraTWTools/releases/download/tw-jp-tools-v1.4.0/MagiaExedraTWJPTools-v1.4.0.zip)
- [本次版本、签名与兼容性说明](docs/TW_CLIENT_1.1.3.zh-CN.md)
- [Windows / MuMu 安装教程](docs/TW_MUMU_ORIGINAL_INSTALL.zh-CN.md) · [Android 手机教程](docs/TW_ANDROID_PHONE_INSTALL.zh-CN.md)

电脑用户：下载并解压**工具 ZIP**，运行 `install_tw.py`，选择下载已校验最新版；已有游戏请直接原位升级，保留游戏资料，**不要先卸载或清除数据**。
手机用户：请使用更新后的 1.1.3 手机教程及脚本，旧手机脚本固定为 1.1.2，需一并更新。

这些下载与安装步骤不要求把 Google Play 账号切换至台区。实际游戏登录、服务器可用性和账号继承由游戏服务决定；安装成功不等于登录成功。1.1.3 的完整包、三 split、签名连续性与离线安装/升级/回滚已核验；三个 MuMu 实例已完成 1.1.2→1.1.3 原位升级，未卸载或清除数据；本次尚无新版非台区账号的实机登录验收记录。

若旧教程的 GitHub 链接曾显示 404，请使用上述公开地址重新下载。遇到截图所示“应用程序已推出新版本”时应升级 **XAPK 客户端**，不是重新下载游戏内资源。不要把第三方旧版缓存页面或安装器版本号当作最新游戏版本。

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

Before downloading the pinned client, the wizard refreshes the release manifest
from this repository's `main` branch. If GitHub is temporarily unreachable it
uses the bundled hash-pinned manifest, so an existing installer archive remains
usable offline. Neither route changes Windows, emulator, VPN, DNS, WinHTTP, or
WinINET proxy settings.

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
- [Steam Windows 安装与网络准备（中文）](docs/STEAM_INSTALL.zh-CN.md)

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
- version: `1.1.3` (`26082020`)
- XAPK SHA-256:
  `e99d80c95c746c80258ec5682231861f0ca1dbbb9390b6d764c398ff1c4f5d95`

Check the online release manifest without ADB or an XAPK download:

```text
py -3 tools/tw_original_installer.py --check-release
```

Download, verify, and install the selected release non-interactively:

```text
py -3 tools/tw_original_installer.py --download-latest --serial YOUR_ADB_SERIAL
```

Use `--no-refresh-release-manifest` only when deliberately operating from the
bundled manifest. In-game asset downloads shown after launch are separate from
the Android XAPK version and do not by themselves mean the installer is stale.

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

## Download website

The dependency-free Chinese download site is built from the same pinned release manifest.
See [Cloudflare build and deployment](docs/CLOUDFLARE_SITE.zh-CN.md).
