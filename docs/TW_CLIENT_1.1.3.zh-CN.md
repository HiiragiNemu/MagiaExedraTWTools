# 台服 Android 1.1.3 更新（2026-09-12）

## 下载

- [完整原版 XAPK](https://github.com/HiiragiNemu/MagiaExedraTWTools/releases/download/v1.1.3/tw.sonet.magiaexedra-1.1.3-26082020.xapk)
- [工具 v1.3.1 ZIP](https://github.com/HiiragiNemu/MagiaExedraTWTools/releases/download/tw-installer-v1.3.1/MagiaExedraTWTools-v1.3.1.zip)
- [每个文件的固定校验值](../mobile/SHA256SUMS-tw-1.1.3.txt)
- [机器可读验证记录](TW_CLIENT_1.1.3_VERIFICATION.json)

包名 `tw.sonet.magiaexedra`；版本 `1.1.3`；versionCode `26082020`；架构 `arm64-v8a`。
Google Play 当前条目显示 1.1.3、更新日 2026-08-27；APKPure 版本页显示 2026-09-03。
两者日期含义不同，版本以原 APK 内的 AndroidManifest 为准。

XAPK 大小：`769647949` bytes。SHA-256：

```text
e99d80c95c746c80258ec5682231861f0ca1dbbb9390b6d764c398ff1c4f5d95
```

## 原版与升级连续性

外层 XAPK 原样镜像，三个 APK 未修改、未重签名。Android SDK `apksigner verify --verbose --print-certs`
验证三个 split 均通过，并与已知 1.1.2 的发布者签名一致：

```text
5cc7d069ae980bcc92129f1238d2e4377bb31f881b1a51635afe9bb1c4db57c9
```

三个 split 为 `base`、`base_assets`、`config.arm64_v8a`，版本一致。安装仍使用
`adb install-multiple -r -i com.android.vending`；所有 APK 一起安装，默认不启动游戏。
Windows 工具升级前备份原 APK并生成回滚脚本。手机脚本没有 APK 备份能力。
请先确认游戏账号的继承/绑定状态，但不要向工具或 GitHub 提交任何账号资料。
不要先卸载或清数据；Android 若拒绝不同签名的升级，应停止并检查来源。

## 非台区 Google 账号与验证状态

公开 XAPK 与工具下载均不要求 GitHub 登录，安装步骤不要求 Google Play 改区。
该流程只安装发布者签名的完整原包并设置 Android 安装来源，不改包或修改许可响应。
已完成真实 1.1.3 包/签名校验，以及模拟 ADB 的首次安装、1.1.2→1.1.3 升级、回滚回归。
另已在三个 MuMu 实例（SM_S9280、ABR_AL80、SM_S9110）实际完成 1.1.2→1.1.3 原位升级：全部 split、版本与安装来源核对通过，旧 APK 分别备份，未卸载／清除数据，游戏保持停止。
模拟 ADB 与实机安装均不是账号登录验收：1.1.3 的非台区账号首次启动、登录与进入游戏仍需确认。
若安装后依然出现商店或许可错误，请保留错误文字、Android 版本和游戏版本；不要清除资料试错。

## 公开入口修复

维护仓库为 PUBLIC，同时以匿名请求核对 main 清单、工具 ZIP 与 XAPK。
之前收藏的 1.1.2 链接仍是历史包，不会自动变成 1.1.3。
Python v1.3.0 具备在线清单刷新，更新后的 main 可提供 1.1.3；推荐下载 v1.3.1，以免离线回退仍选旧版。
手机用户必须更新脚本，因为手机脚本的校验值是固定的。

## 上游

- [台服官方 Google Play 条目](https://play.google.com/store/apps/details?id=tw.sonet.magiaexedra&hl=en_US&gl=TW)
- [台服官方网站](https://mme.so-net.tw/)
- [APKPure 原版 1.1.3 来源页](https://apkpure.net/%E9%AD%94%E6%B3%95%E5%B0%91%E5%A5%B3%E5%B0%8F%E5%9C%93-magia-exedra/tw.sonet.magiaexedra/download/1.1.3)
