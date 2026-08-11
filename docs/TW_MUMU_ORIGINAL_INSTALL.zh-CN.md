# MuMu 原版台服 XAPK 安装与升级

本工具使用 Python 3.10 及以上版本和 Android Platform Tools。它安装未修改的
原版 XAPK，不修改 APK、签名、许可返回或游戏代码，也不读取、记录游戏账号
资料。

已验证效果：无需把 Google 账号切换到台湾区，原始游戏 Activity 可以启动，
而不会跳转 Google Play。游戏服务器、网络出口、访客账号和资料继承仍是
彼此独立的步骤。

## 准备

1. 安装 Python 3.10 或更新版本。
2. 安装 `adb`，启动 64 位 MuMu 并启用 ADB 调试。
3. 准备原版 XAPK，或让向导下载信任清单指定的最新版。

## 最简单：双击 Python 一键向导

直接双击仓库根目录的 `install_tw.py`。也可在任意终端中运行：

```text
python install_tw.py
```

无需填写长命令。向导会自动：

1. 从环境变量、PATH、Android SDK 和常见 MuMu 安装目录寻找 `adb`；
2. 列出已就绪的 MuMu/ADB 设备，只有一个时自动选中，多个时要求按编号选择；
3. 在工具旁、当前目录、下载目录、桌面和 Windows 各磁盘根目录寻找 `.xapk`；
4. 让你选择“下载已校验最新版”或一个本地原版 XAPK；
5. 最后显示设备、来源、保留数据、备份和不启动游戏的摘要，再确认一次。

如果没有发现设备，向导会提示输入 MuMu 的 ADB 地址，例如
`127.0.0.1:16384`。设备离线、未授权、ADB 缺失或同时连接多台设备时都会给出
明确提示，不会静默选错设备。取消、关闭输入或按 Ctrl+C 时会保留已经完成的
检查点。双击运行时，结束后窗口会等待按 Enter，便于阅读结果。

默认行为始终是：使用 `-r` 保留游戏数据、升级前备份原 APK、安装完成后执行
`am force-stop`，并通过 `pidof` 验证游戏进程不存在。需要启动时仍应使用下面的
高级命令并显式添加 `--launch`；它只会在安装包、版本、split 和来源全部验证后
启动。

下载默认**直连**。代理提示留空会传入 `None`，并禁用操作系统及环境变量中
继承的代理；只有明确填写代理 URL 或使用 `--proxy` 时才经过该代理。

如果自动查找不到 `adb.exe`，可设置 `TW_ADB` 指向它；如果 XAPK 不在常用
位置，可在向导中选择 `P` 后粘贴完整路径。

## 高级命令行方式

## 下载最新版并安装/升级

```text
python tools/tw_original_installer.py --download-latest --serial HOST:ADB_PORT
```

可选代理只用于 XAPK 下载，不会修改 MuMu Wi-Fi、系统代理或 ADB reverse。
省略 `--proxy` 即直连；需要时替换下面的端口占位符：

```text
python tools/tw_original_installer.py --download-latest --proxy http://127.0.0.1:<YOUR_PROXY_PORT> --serial HOST:ADB_PORT
```

只使用一台 Android 11+ 手机、无需电脑的 Shizuku 图形流程和 Termux 强校验
流程参见 [Android 手机单机安装说明](TW_ANDROID_PHONE_INSTALL.zh-CN.md)。

下载使用 `.part`、HTTP Range、强 ETag/Last-Modified、严格区间和长度检查、
四 GiB 流式上限、SHA-256 及原子改名。中断后重新执行同一命令即可续传。

## 使用本地原版 XAPK

安装或从旧版原位升级：

```text
python tools/tw_original_installer.py --xapk ORIGINAL_CLIENT.xapk --serial HOST:ADB_PORT
```

只检查文件，不查找 ADB、不连接模拟器：

```text
python tools/tw_original_installer.py --xapk ORIGINAL_CLIENT.xapk --validate-only
```

默认**不会启动游戏**。只有显式添加 `--launch` 才会在全部验证通过后启动：

```text
python tools/tw_original_installer.py --xapk ORIGINAL_CLIENT.xapk --serial HOST:ADB_PORT --launch
```

## 版本信任清单

`manifests/known-releases.json` 是已知版本的唯一信任源：

- `latestVersion` 决定 `--download-latest` 选择哪个版本；
- `latestEndpoint` 提供下载入口；
- 每个版本必须固定完整 XAPK 的长度和 SHA-256；
- 同时必须固定 `base`、`base_assets`、`config.arm64_v8a` 三个 split 的
  长度和 SHA-256。

本地 XAPK 的版本若已在清单中，工具自动强制执行完整 XAPK 和每个 split 的
全部固定值，命令行哈希不能覆盖清单。未列出的版本必须提供从独立可信渠道
获得的 `--expected-xapk-sha256`。

将来发布新版本时，只需核验并增加一条 release；需要设为最新版时同步更新
`latestVersion`。无需修改 Python 源码。

## 安装过程

工具逐个解析 AndroidManifest，并只接受：

```text
package: tw.sonet.magiaexedra
splits: base + base_assets + config.arm64_v8a
```

它拒绝缺失、重复、额外 split、错误 package、混合版本、异常压缩和加密 APK。
首次安装和旧版升级都通过
`adb install-multiple -r -i com.android.vending` 原子执行；`-r` 保留应用数据。
默认不启动时，工具随后显式 `force-stop` 并以 `pidof` 验证游戏进程不存在；
显式 `--launch` 则先完成安装验收，再启动游戏。若 adbd 原先为 root，工具安装前
临时 `unroot`，结束后恢复原状态。

## 证据与回滚

默认状态目录位于当前用户的本地应用数据区，包含：

- `input.json`：XAPK、信任来源、版本及每个 split 的长度/SHA-256；
- `before.json`：原版本、安装来源、split 路径和 adbd 状态；
- `previous-apks/` 与 `previous-apks.json`：升级前完整 APK 备份；
- `adb-operations.jsonl`：不含游戏账号资料的 ADB 证据；
- `journal.json`：操作阶段；
- `verification.json`：最终版本、安装来源、split，以及默认停止验收或显式启动结果；
- `rollback.py`：回滚材料完整时生成。

在状态目录运行：

```text
python rollback.py --serial HOST:ADB_PORT
```

回滚会确认当前包仍是本次目标版本、核对旧 split 哈希，再用 `-r -d` 恢复。
它只回滚 APK，不回滚应用数据；新版若迁移过数据，旧客户端未必能够读取。
检测到版本漂移时会停止。需要回滚能力时不要使用
`--skip-current-apk-backup`。

## 常见问题

- **找不到 ADB**：安装 Android Platform Tools，或让 `TW_ADB` 指向
  `adb.exe` 后重新打开向导。
- **设备离线**：重启 MuMu 的 ADB 调试；没有自动发现时，在向导中输入
  `HOST:ADB_PORT`。
- **多台设备**：向导显示 serial 和型号并要求按编号选择，不会默认选择第一台。
- **文件校验失败**：不要混用版本或架构；重新取得清单对应的完整 XAPK。
- **清单显示旧版**：核验新发行物后更新 release 和 `latestVersion`。
- **安装正确但网络异常**：代理、DNS 和出口地区与安装来源是独立问题。
- **游戏要求登录**：账号流程不属于安装器；工具不接触密码、UUID、JWT、
  Session 或 Cookie。

## 边界

工具只复现完整原版 split 安装和 Android 安装来源。它不会生成购买记录、
改包、重签名、跳过 Activity 或拦截许可结果。发行方改变客户端或服务器规则
后，应以新的原版 XAPK 重新验证。
