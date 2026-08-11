# MuMu 原版台服安装演示视频脚本

本脚本用于演示：不切换台湾区 Google 账号，使用公开工具把完整、未修改的
台服 XAPK 安装或原位升级到 64 位 MuMu，并在人工确认后启动游戏。

## 演示前准备

1. 安装 Python 3.10 或更新版本与 Android Platform Tools。
2. 启动 64 位 MuMu，开启 ADB 调试，暂时关闭游戏。
3. 从 [最新工具 Release](https://github.com/HiiragiNemu/MagiaExedraTWTools/releases/latest)
   下载并解压 `MagiaExedraTWTools-v*.zip`（版本号会随发布更新）。
4. 可让向导在线下载已固定哈希的 XAPK；为缩短录制，也可提前下载同一
   Release 中的原版 XAPK，放在工具目录旁。
5. 隐藏 Google 邮箱、玩家 ID、引继码、密码、代理订阅与个人目录用户名。

公开入口：

- 仓库：<https://github.com/HiiragiNemu/MagiaExedraTWTools>
- 最新工具 Release：<https://github.com/HiiragiNemu/MagiaExedraTWTools/releases/latest>
- 原版 XAPK Release：<https://github.com/HiiragiNemu/MagiaExedraTWTools/releases/tag/v1.1.2>
- 中文完整说明：<TW_MUMU_ORIGINAL_INSTALL.zh-CN.md>

## 推荐成片结构

### 1. 开场与结论（约 20 秒）

画面展示仓库和 Release。建议旁白：

> 这个方案使用发行方的完整原版 XAPK，不改 APK、不重签名，也不修改游戏
> 代码。它通过完整安装三个 split，并把 Android 安装来源记录为 Google Play，
> 因此不需要把自己的 Google 账号切换到台湾区。

说明安装来源、游戏联网、账号登录是三个独立环节；本视频只演示安装和升级。

### 2. 公开文件与哈希（约 30 秒）

展示 Release 中的工具 ZIP 和原版 XAPK，然后运行：

```text
certutil -hashfile MagiaExedraTWTools-v当前版本.zip SHA256
certutil -hashfile tw.sonet.magiaexedra-1.1.2-26072717.xapk SHA256
```

把结果与 Release 的 SHA-256 对照。强调向导还会独立验证 XAPK 内的
`base.apk`、`split_base_assets.apk` 与 `split_config.arm64_v8a.apk`。

### 3. MuMu 准备（约 20 秒）

展示：

- MuMu 为 64 位实例；
- ADB 调试已开启；
- 游戏窗口已经关闭；
- `adb devices -l` 能看到设备。

不需要打开 Google Play，也不需要展示 Google 账号地区。

### 4. 一键安装或升级（约 2 至 4 分钟）

双击 `install_tw.py`，或者在工具目录运行：

```text
py -3 install_tw.py
```

完整录下：

1. 向导自动找到 `adb` 和 MuMu；
2. 只有一个设备时自动选择，多设备时按编号选择；
3. 首次使用按 Enter 选择 `D` 下载固定版本，或选择已经发现的本地 XAPK；
4. 默认留空并直连；如 GitHub 确实需要本机代理，只在下载提示处填写
   `http://127.0.0.1:<YOUR_PROXY_PORT>`，将 `<YOUR_PROXY_PORT>` 替换为自己
   电脑上的真实监听端口；这不会修改 MuMu 代理；
5. 摘要显示保留应用数据、备份旧 APK、安装后显式停止并校验进程；
6. 输入 `y`；
7. 展示完整 XAPK、三个 split、版本与安装来源全部验证通过；
8. 展示 `verification.json` 中 `forcedStopped=true`、`stoppedVerified=true`
   和 `processAlive=false`，证明工具没有自动启动游戏且停止状态已验收。

为缩短成片可使用已下载 XAPK，但旁白应说明普通用户可选 `D` 自动下载。

### 5. 安装结果验证（约 40 秒）

把示例 serial 换成自己在 `adb devices -l` 中看到的值：

```text
adb -s emulator-5554 shell pm path tw.sonet.magiaexedra
adb -s emulator-5554 shell dumpsys package tw.sonet.magiaexedra
```

当前固定版本预期显示：

```text
versionName=1.1.2
versionCode=26072717
installerPackageName=com.android.vending
base.apk
split_base_assets.apk
split_config.arm64_v8a.apk
```

再展示状态目录中的 `verification.json`；其中不含游戏账号或会话材料。

### 6. 人工启动（约 1 分钟）

此时才手动点击 MuMu 中的游戏图标。展示游戏不再跳转 Google Play，并进入
标题、登录或主菜单。若画面出现玩家 ID、引继码或其他账号资料，后期必须打码。

建议旁白：

> 安装来源问题已经解决。若此处出现网络错误，应另行检查代理、DNS 和出口；
> 那些设置不属于安装器，也不应通过反复重装解决。

### 7. 后续升级与回滚（约 30 秒）

以后发行新版本时，从同一仓库取得新增的、已固定哈希的 Release，再运行同一个
向导并选择 `D`。不要先卸载旧客户端；工具使用 `-r` 原位升级并保留数据。

展示状态目录：

```text
%LOCALAPPDATA%\MagiaExedraTWTools\install-state\时间-PID\
```

其中包含安装前 APK 备份、验证记录和材料完整时生成的 `rollback.py`。说明回滚
只恢复 APK 版本，不是应用数据快照。

## 建议视频标题与简介

标题：

```text
无需台湾区 Google 账号：用原版 XAPK 在 MuMu 安装/升级 Magia Exedra 台服
```

简介：

```text
本演示使用公开、带 SHA-256 固定值的原版台服 XAPK 和 Python 向导，完整安装
base、base_assets、arm64 三个 split，并记录 Android 安装来源为 Google Play。
客户端没有修改或重签名。工具默认保留数据、备份旧 APK，并在验证完成后保持
游戏停止，由用户人工启动。游戏服务器连通、代理和账号登录属于独立步骤。
```

## 不应在演示中声称的内容

- 不要称为修改版、破解包或许可绕过；实际方案没有修改客户端。
- 不要声称工具会创建 Google 购买记录或改变账号地区。
- 不要承诺任意未来版本永久有效；新版本必须先加入哈希信任清单。
- 不要把安装成功等同于服务器、代理或账号流程必然成功。
