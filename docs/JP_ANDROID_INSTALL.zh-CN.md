# 日服 Exedra 3.21.2：免 Google 日区账号安装与更新

> **原包已公开（2026-10-22）**：JP 3.21.2 固定 GitHub 下载已匿名读回，文件长度及服务器 SHA-256 与本地原版包一致，分段内容一致；三个 APK 原始签名通过。新版设备安装与登录尚未测试。

2026-10-22 核验版本：**3.21.2（26102016）**。原版 Android 三 split，最低 Android 9、arm64；APK 未修改、未重签名。安装工具版本为 **v1.4.3**，与游戏版本分别管理。

## 本次更新

固定原版包从 3.21.1 更新为 3.21.2，原安装与回滚机制保持不变；旧版清单与测试记录继续保留。新版三 split 的版本和发行方证书已逐个核验。

## 下载

- [原版 JP 3.21.2 XAPK](https://github.com/HiiragiNemu/MagiaExedraTWTools/releases/download/jp-v3.21.2/com.aniplex.magia.exedra.jp-3.21.2-26102016.xapk)
- [TW/JP 安装工具 v1.4.3](https://github.com/HiiragiNemu/MagiaExedraTWTools/releases/download/tw-jp-tools-v1.4.3/MagiaExedraTWJPTools-v1.4.3.zip)
- [完整包与三个 split 的校验表](../mobile/SHA256SUMS-jp-3.21.2.txt)
- [版本与测试记录](JP_CLIENT_3.21.2_VERIFICATION.json)

大小：`958742220` bytes。SHA-256：

```text
6bbae00ab7e95b5e6f391ecf48c9d7a628599615a96cf0d0953ec1e08bef0a45
```

下载不要求 GitHub 账号，安装不要求 Google Play 改区。游戏账号继承与网络仍按游戏原有流程处理；本工具不索取账号、密码或引继码。

## Windows / MuMu（推荐工具方式）

1. 安装 Python 3.10+ 和 Android Platform Tools，打开目标设备 ADB 调试。
2. 解压工具 ZIP，连接目标设备；多实例时明确选中自己的地址。
3. 在工具目录执行，`HOST:ADB_PORT` 替换成自己的设备地址：

```text
adb connect HOST:ADB_PORT
python install_jp.py --download-latest --serial HOST:ADB_PORT
```

已有下载文件时：

```text
python install_jp.py --xapk com.aniplex.magia.exedra.jp-3.21.2-26102016.xapk --serial HOST:ADB_PORT
```

也可双击 `install_jp.py` 使用向导。工具核验整包与三个 split、原位安装、验证版本/安装来源并保存旧 APK 与回退脚本。默认安装后保持游戏停止，再由你启动。

**已有游戏不要先卸载或清除数据。** `-r` 原位升级保留资料；请先自行确认账号的继承/绑定方式。签名不同或安装失败时停止，不通过卸载试错。APK 回退不等于存档回退，Android 也可能拒绝降级。

## 手动 ADB

把 XAPK 当作 ZIP 解压；三个文件必须一起安装，不要只装 base。以下为单行命令，Windows 终端 / Termux 均可使用：

```text
adb -s HOST:ADB_PORT install-multiple -r -i com.android.vending com.aniplex.magia.exedra.jp.apk base_assets.apk config.arm64_v8a.apk
```

`-i com.android.vending` 是 Android 安装来源字段，不会登录 Google、创建购买记录或修改游戏许可响应。完整 split 和安装来源两项都要保留。

## Android 手机

- 有电脑：USB ADB 或 Android 11+ 无线调试配对后，用同一套 Python 工具/ADB 命令。Android 9/10 使用 USB。
- 无电脑、Android 11+：从 [Termux 官方渠道](https://termux.dev/) 安装 Termux，运行 `pkg install python android-tools`，按系统无线调试页面分别执行 `adb pair PHONE_IP:PAIR_PORT`、`adb connect PHONE_IP:DEBUG_PORT`。解压工具 ZIP 到 Termux 可读目录，再执行 `python install_jp.py --download-latest --serial PHONE_IP:DEBUG_PORT`。配对端口与连接端口不是同一个。
- 图形方式：支持 Shizuku 的 split 安装器需一次选择三个 APK，Installer package name 填 `com.android.vending`；保持签名验证开启，不启用跳过验证/强制降级。先用上面的 SHA-256 校验完整 XAPK。

这些手机步骤没有本次实体手机验收，已验证的设备范围见测试记录；不要把模拟器结果描述为所有手机均已实测。

## 当前版本验证与历史实测

**3.21.2 本次验证范围**：完整 XAPK、三 split、包名、版本与原始签名；既有安装器的离线 `--validate-only` 验证。新版设备安装、启动、登录、战斗与实体手机验收尚未执行。

**历史 3.21.0，非本版验收**：MuMu Android 15 独立空白实例曾在零 Google 账号状态完成安装、原生登录、开场影片、3D 移动及教程战斗。保留原始 [3.21.0 记录](JP_CLIENT_3.21.0_VERIFICATION.json)，不将这些结果迁移到 3.21.2。

已有 Google 组件的设备请保持原状，不要为此卸载系统组件。

## 网络与登录排查

免 Google 日区账号不等于免日服网络条件。安装包下载成功，也不代表游戏登录/API/资源下载线路都可达。

- **提示客户端版本更新**：更新本页完整 XAPK，保留游戏数据。
- **提示网络错误或登录重试**：先确认日服服务可达；历史 3.21.0 测试默认线路收到访问拒绝，日本出口线路才进入后续资源下载。不同出口质量不同，单次打开标题页不足以判断线路稳定。最终已通过可达线路进入教程战斗。
- 更换线路后关闭游戏进程再打开，避免继续使用旧连接；不必卸载游戏、清除存档或更换 Google 账号。
- 下载失败时先检查游戏资源 CDN 的连通性；不要因此清除账号或反复卸载。开场的向上滑动提示需要实际滑动，静置不会继续教程。
- 如需游戏加速器/日本网络出口，由使用者自行配置。安装工具只安装原版包，不修改系统代理、DNS、VPN，不包含共享账号或代理配置。
- 首次启动还会下载游戏内资源；历史 3.21.0 新设备显示约 **2.4 GB**，这与约 959 MB 的 XAPK 是两个步骤。

## 遇到更新提示

客户端强制更新应更新完整 XAPK，不是删除游戏内资源缓存。旧工具可在线读取新发布清单；离线使用请更新工具 ZIP。`--download-latest` 指本仓库最近核验的版本，不自动承诺永远等于商店最新。

维护者发布前运行 `python scripts/check_jp_release.py`，检查匿名下载端点、文件长度与 GitHub 资产 SHA-256。每次客户端更新仍须重新核验签名和实际启动。

旧 [3.21.1 验证记录](JP_CLIENT_3.21.1_VERIFICATION.json)与清单继续保留。

官方版本来源：[Google Play 日服条目](https://play.google.com/store/apps/details?id=com.aniplex.magia.exedra.jp&hl=ja&gl=jp)。原包获取来源：[APKPure 原包下载端点](https://d.apkpure.net/b/XAPK/com.aniplex.magia.exedra.jp?version=latest)；公开使用上方固定版本镜像，避免可变 latest 与固定哈希不一致。

