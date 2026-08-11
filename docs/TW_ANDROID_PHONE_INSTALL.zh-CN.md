# Android 11+ 单手机安装原版台服 XAPK

本页提供两条不使用电脑、模拟器或台湾区 Google 账号的路线。两条路线都安装
同一套未修改、未重签名的台服 1.1.2 三 split XAPK，并把 Android 的 installer
package name 设为 `com.android.vending`。

- **首选 GUI**：Shizuku + 开源 Install with Options，适合普通用户；
- **强校验脚本**：Termux + Wireless debugging + `android-tools`，适合需要自动
  SHA-256、版本、split 和安装来源验收的用户。

Android 11/API 30 或更新版本才具有本页使用的系统内置无线调试本机启动方式。
Android 10 及以下请使用电脑 ADB 或仓库中的 Windows/MuMu 向导。

## 下载与固定校验值

原版 XAPK：

<https://github.com/HiiragiNemu/MagiaExedraTWTools/releases/download/v1.1.2/tw.sonet.magiaexedra-1.1.2-26072717.xapk>

```text
大小：769197299 bytes
SHA-256：664dfbc307c5f6b640d01b1fc661de02fa30fc382a68426530abc657dc9e2d14
```

三个 split 的固定值在
[`mobile/SHA256SUMS-tw-1.1.2.txt`](../mobile/SHA256SUMS-tw-1.1.2.txt)。
未来新版本必须先发布新的完整 XAPK 与每个 split 固定值；不要把本脚本的 1.1.2
常量用于其他版本。

建议至少保留约 2.5 GiB 可用存储，供 XAPK、解压文件及系统安装暂存使用。升级
使用 `-r` 保留应用数据；手机脚本不备份旧 APK，也不是应用数据备份工具。

## 路线 A：Shizuku + Install with Options（GUI 首选）

1. 从 [Shizuku 官方下载页](https://shizuku.rikka.app/download/) 安装 Shizuku。
2. 从开源项目
   [zacharee/InstallWithOptions](https://github.com/zacharee/InstallWithOptions)
   的官方 Release 安装 Install with Options。
3. 打开开发者选项和“无线调试”。在 Shizuku 中选择“通过无线调试启动”，按
   系统提示完成配对。每次手机重启后通常需要重新启动 Shizuku。
4. **先校验 XAPK**。GUI 安装器本身不会强制本仓库的 SHA-256。可使用 Termux：

   ```text
   sha256sum ~/storage/downloads/tw.sonet.magiaexedra-1.1.2-26072717.xapk
   ```

   输出必须与上方完整值完全一致。也可使用可信的本地 SHA-256 工具。
5. 把 `.xapk` 当作 ZIP 解压。确认其中恰好有三个 `.apk`；可再对三个文件运行
   `sha256sum`，其结果必须分别匹配仓库清单中的三个值。外层文件名可能与清单
   使用的标准角色名不同，以哈希为准。
6. 打开 Install with Options，允许 Shizuku 权限，一次选择上述**三个 APK**，
   使用 split APK 安装。
7. 将 **Installer package name** 填为：

   ```text
   com.android.vending
   ```

8. 保持“Disable Verification”“Allow Downgrade”“Bypass Low Target SDK”等无关
   选项关闭。本客户端不需要关闭签名验证；不同签名的更新本来也不能靠该选项
   解决。
9. 点击安装。完成后不要点击 Open；从应用信息页确认游戏保持停止，再由用户
   人工启动。

Install with Options 使用 Shizuku 的 shell 权限并支持 split APK。Android 14+
限制 shell 设置 originating package，但仍允许 installer package 字段；本方案
只依赖后者。

## 路线 B：Termux 固定哈希自动验收

### 1. 准备官方 Termux

从 [Termux 官网](https://termux.dev/en/) 链接的官方渠道安装 Termux，不要使用
不明二次打包版本。执行：

```text
pkg update
pkg install android-tools coreutils unzip
termux-setup-storage
```

授权共享存储访问后，下载并解压本仓库最新工具 Release，进入含有 `mobile/`
目录的工具根目录。

### 2. 本机无线 ADB 配对

打开：开发者选项 → 无线调试 → 使用配对码配对设备。配对地址与连接地址使用
不同的临时端口，以系统页面显示为准：

```text
adb pair PHONE_IP:PAIR_PORT
adb connect PHONE_IP:DEBUG_PORT
adb devices
```

输入系统显示的一次性配对码。推荐分屏显示设置和 Termux。`adb devices` 应只
出现当前手机的一个 `HOST:PORT device`；若有多个连接，脚本要求显式选择。

### 3. 执行安装

```text
bash mobile/install_tw_termux.sh ~/storage/downloads/tw.sonet.magiaexedra-1.1.2-26072717.xapk
```

脚本会自动：

1. 验证完整 XAPK 的 769197299-byte 大小及固定 SHA-256；
2. 只提取三个 APK，并按各自固定 SHA-256 识别 base、assets 和 arm64 split；
3. 自动选择唯一已连接的本机 Wireless ADB endpoint；
4. 确认目标为 Android 11/API 30 或更新版本；
5. 执行：

   ```text
   adb install-multiple -r -i com.android.vending BASE ASSETS ARM64
   ```

6. 验证版本 `1.1.2 (26072717)`、三个安装路径及 installer package；
7. 执行 `am force-stop`，保持游戏停止，绝不自动启动。

若连接了多个无线目标：

```text
bash mobile/install_tw_termux.sh --serial PHONE_IP:DEBUG_PORT /path/to/original.xapk
```

也可设置 `TW_ADB_SERIAL`。

## 常见问题

- **没有 Wireless debugging**：系统低于 Android 11，或厂商关闭了该功能；改用
  电脑 ADB／MuMu 路线。
- **配对成功但 devices 为空**：配对端口不是连接端口；返回无线调试主页面，
  使用“IP 地址和端口”显示的连接端口运行 `adb connect`。
- **INSTALL_FAILED_USER_RESTRICTED**：部分系统还要求开启“通过 USB 安装”或
  “USB 调试（安全设置）”，并禁止访客／工作资料安装。
- **INSTALL_FAILED_UPDATE_INCOMPATIBLE**：当前已安装应用签名不同。不要为了
  尝试而卸载重要资料；先确认旧客户端是否也是同一官方签名。
- **校验失败**：停止操作，重新下载完整 Release XAPK；不要混用不同版本 split。
- **安装成功但网络错误**：DNS、代理、出口、服务器和账号流程与安装来源无关。

本流程不会生成 Google Play 购买记录，不修改 APK、签名、游戏代码或许可响应。
