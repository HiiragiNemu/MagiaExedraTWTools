# Magia Exedra TW / JP Original XAPK Installer

Public, reproducible tools for installing or upgrading the **original, unmodified
Taiwan and Japan Android clients** without switching the Google Play account
region for XAPK download and split installation. TW uses the installer wizard
below; JP has a separate [ADB/phone guide](docs/JP_ANDROID_INSTALL.zh-CN.md).
The repository name is retained for existing links; it covers both regions.

This repository is intentionally limited to XAPK installation, update, integrity
verification, backup, and rollback.

## 中文下载网站

**[打开 Exedra TW / JP 下载站](https://hiiraginemu.github.io/madeinmagius-site/#exedra)** — 直接下载文件，阅读电脑 / MuMu 与手机中文教程。

## 2026-10-22 更新：JP 3.21.2 / TW 1.1.4 / 工具 v1.4.3

> **原包已公开（2026-10-22）**：JP 3.21.2 固定 GitHub 下载已匿名读回，文件长度及服务器 SHA-256 与本地原版包一致，分段内容一致；三个 APK 原始签名通过。新版设备安装与登录尚未测试。 台服 1.1.4 保留 2026-10-20 已公开的原包与验证记录。

- JP：**3.21.2（26102016）**，[固定原包下载](https://github.com/HiiragiNemu/MagiaExedraTWTools/releases/download/jp-v3.21.2/com.aniplex.magia.exedra.jp-3.21.2-26102016.xapk) · [安装教程](docs/JP_ANDROID_INSTALL.zh-CN.md)。
- TW：**1.1.4（26091812）**，[固定原包下载](https://github.com/HiiragiNemu/MagiaExedraTWTools/releases/download/v1.1.4/tw.sonet.magiaexedra-1.1.4-26091812.xapk) · [本版说明](docs/TW_CLIENT_1.1.4.zh-CN.md)。
- [TW/JP 工具 v1.4.3](https://github.com/HiiragiNemu/MagiaExedraTWTools/releases/download/tw-jp-tools-v1.4.3/MagiaExedraTWJPTools-v1.4.3.zip)；更新 JP 离线清单与教程，安装器和 TW Termux 脚本保持不变。

下载与完整 split 安装不依赖 Google Play 区域切换。账号继承和游戏登录仍按原流程处理。已有游戏请原位升级，**不要先卸载或清除数据**。

新版真实原包、三 split、版本号与原始签名已校验；离线安装器回归与设备安装/游戏验收分开。旧 JP 3.21.0 MuMu 战斗证据及 TW 1.1.3 三实例升级证据保留，但不是 JP 3.21.2 或 TW 1.1.4 的运行通过。

### 保留的历史公开版本

- [JP 3.21.1](https://github.com/HiiragiNemu/MagiaExedraTWTools/releases/download/jp-v3.21.1/com.aniplex.magia.exedra.jp-3.21.1-26101610.xapk) · [其原始验证记录](docs/JP_CLIENT_3.21.1_VERIFICATION.json)。
- [工具 v1.4.2](https://github.com/HiiragiNemu/MagiaExedraTWTools/releases/download/tw-jp-tools-v1.4.2/MagiaExedraTWJPTools-v1.4.2.zip)。
- [JP 3.21.0](https://github.com/HiiragiNemu/MagiaExedraTWTools/releases/download/jp-v3.21.0/com.aniplex.magia.exedra.jp-3.21.0.xapk) · [其原始验证记录](docs/JP_CLIENT_3.21.0_VERIFICATION.json)。
- [TW 1.1.3](https://github.com/HiiragiNemu/MagiaExedraTWTools/releases/download/v1.1.3/tw.sonet.magiaexedra-1.1.3-26082020.xapk) · [其版本说明](docs/TW_CLIENT_1.1.3.zh-CN.md)。
- [工具 v1.4.1](https://github.com/HiiragiNemu/MagiaExedraTWTools/releases/download/tw-jp-tools-v1.4.1/MagiaExedraTWJPTools-v1.4.1.zip)。
- 更早 JP 3.18.0、TW 1.1.2/1.0.5 的原清单条目保持不变；历史条目不保证下载端点仍可用或仍满足服务器最低客户端版本。

`--download-latest` 选择本仓库清单中的固定版本，不自动证明商店最新。JP 3.21.2 固定原包 URL 已公开并匿名读回；TW 1.1.4 保留已公开固定地址。离线验证使用本地原包和 `--no-refresh-release-manifest`。

## Supported routes

### TW: Windows / MuMu

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

### TW: Android 11+ phone only

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

Pinned TW original client (JP package and hashes are in the separate guide):

- package: `tw.sonet.magiaexedra`
- version: `1.1.4` (`26091812`)
- XAPK SHA-256:
  `4cc19af8dbb8091f93e0252738b59e794b1ba8aa14aba15ee5a7cab93ec90e6a`

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
