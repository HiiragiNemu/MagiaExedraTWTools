# 日服 Exedra 3.18.0：电脑、MuMu 与 Android 手机安装

本页使用包名 `com.aniplex.magia.exedra.jp` 的原版三 split XAPK。下载和安装走 GitHub Release，不需要把 Google Play 切换到日本区；游戏内登录、服务可用性仍由游戏服务端决定。

## 下载与校验

- [下载 JP 3.18.0 XAPK](https://github.com/HiiragiNemu/MagiaExedraTWTools/releases/download/jp-v3.18.0/com.aniplex.magia.exedra.jp-3.18.0.xapk)
- 大小：`923195400` bytes
- SHA-256：`43cd6eca5a8af7e8bf017fd922e4b0a9260e63933051f5eff3ae21c89a89a514`
- split 校验值：[`mobile/SHA256SUMS-jp-3.18.0.txt`](../mobile/SHA256SUMS-jp-3.18.0.txt)
- XAPK 内应包含 `com.aniplex.magia.exedra.jp.apk`、`base_assets.apk`、`config.arm64_v8a.apk` 三个 APK 及 `manifest.json`。

Windows 校验：

```text
certutil -hashfile com.aniplex.magia.exedra.jp-3.18.0.xapk SHA256
```

## MuMu / 电脑 ADB

1. 启动 64 位 MuMu，打开开发者选项和 ADB 调试；在 MuMu 设置中记录该实例的 ADB 地址。
2. 用 7-Zip 解压 XAPK（它是 ZIP），得到三个 APK。不要只安装 base APK。
3. 在 Platform Tools 目录执行：

```text
adb connect HOST:ADB_PORT
adb -s HOST:ADB_PORT install-multiple -r -i com.android.vending `
  com.aniplex.magia.exedra.jp.apk base_assets.apk config.arm64_v8a.apk
```

`-r` 用于原位升级并保留资料；遇到签名不匹配时停止，不要先卸载或清除数据。完成后可用 `adb shell am force-stop com.aniplex.magia.exedra.jp` 保持游戏停止，再手动启动。

## Android 手机

Android 11+ 可使用无线调试配对后，通过电脑执行同一组 `adb install-multiple`；也可使用支持 Shizuku 的 split 安装器，一次选择三个 APK，保持签名校验开启。Android 10 及以下使用电脑 ADB 路线。

## 常见问题

- **跳转 Google Play**：不要点击商店更新按钮；从本页 Release 直接下载完整 XAPK，再按上面步骤安装。
- **更新提示**：先校验新 XAPK，再原位升级；版本与包名必须一致。
- **登录失败**：保留错误文字和版本信息，分别检查网络、账号绑定与服务状态；安装成功不代表登录验收。

