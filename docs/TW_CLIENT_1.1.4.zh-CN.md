# 台服 Android 1.1.4 更新（2026-10-20）

> **原包已公开（2026-10-20）**：固定 GitHub 下载已匿名读回，文件长度及服务器 SHA-256 与本地原版包一致，分段内容一致；三个 APK 原始签名通过。新版设备安装与登录尚未测试。

包名 `tw.sonet.magiaexedra`；版本 `1.1.4`；versionCode `26091812`；arm64-v8a，最低 Android 9。

- [固定原版 XAPK 下载](https://github.com/HiiragiNemu/MagiaExedraTWTools/releases/download/v1.1.4/tw.sonet.magiaexedra-1.1.4-26091812.xapk)
- [TW/JP 工具 v1.4.2](https://github.com/HiiragiNemu/MagiaExedraTWTools/releases/download/tw-jp-tools-v1.4.2/MagiaExedraTWJPTools-v1.4.2.zip)
- [完整包及三 split 校验值](../mobile/SHA256SUMS-tw-1.1.4.txt)
- [本版验证记录](TW_CLIENT_1.1.4_VERIFICATION.json)
- [Windows / MuMu](TW_MUMU_ORIGINAL_INSTALL.zh-CN.md) · [Android 手机](TW_ANDROID_PHONE_INSTALL.zh-CN.md)

完整包 `769647949` bytes；SHA-256 `4cc19af8dbb8091f93e0252738b59e794b1ba8aa14aba15ee5a7cab93ec90e6a`。
三个 APK 均通过 apksigner，发行方证书 SHA-256 为 `5cc7d069ae980bcc92129f1238d2e4377bb31f881b1a51635afe9bb1c4db57c9`，与旧原版证书一致。

下载及 split 安装不要求把 Google Play 账号切换到台区。游戏登录、服务端可用性及账号继承仍需各自验收。

## 当前测试与历史证据

本版完成真实包/三 split 静态核验与既有安装器离线校验；设备安装、首次启动、登录与游戏操作尚未测试。
旧 [1.1.3 版本记录](TW_CLIENT_1.1.3_VERIFICATION.json) 中的三个 MuMu 原位升级结果仅属于 1.1.3，未继承为 1.1.4 通过。

电脑继续使用 `install_tw.py`；手机的 `mobile/install_tw_termux.sh` 已同步为本版整包及三个 split 的固定哈希。请同步更新工具 ZIP，不关闭哈希检查。

已有客户端请原位升级，不要先卸载或清除资料。电脑安装器先备份旧 APK，默认不启动游戏；手机脚本不备份账号、存档或旧 APK。旧版本可能受服务器最低版本规则限制。
