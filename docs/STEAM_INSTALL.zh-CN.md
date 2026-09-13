# Steam Windows 安装与网络准备

本页说明如何从 Steam 客户端安装 SAMPLE（AppID `2987800`），并让游戏流量遵循本机已有的 Clash Verge 或 WireGuard 路由。它不修改 Steam 账号区域、授权或商店策略；安装与游玩仍需要该账号拥有 SAMPLE 授权。

## 一键打开安装页

在已登录 Steam 的 Windows 上运行：

```text
Start-Process 'steam://install/2987800'
```

确认 Steam 显示安装磁盘与授权状态后继续。也可以在 Steam 客户端搜索 AppID 对应页面安装。脚本不会写入证书、系统代理、DNS、路由或 VPN 配置。

## Clash Verge / WireGuard 双兼容

1. 先启动你自己的 Clash Verge（系统代理或 TUN）或 WireGuard 隧道。
2. 在 Clash 规则中将 Steam/游戏域名按你的节点策略转发；WireGuard 则由隧道 AllowedIPs 决定路由。
3. 只启用一个 TUN/全局路由，避免两个客户端同时接管默认路由。
4. 用 `curl.exe https://api.steampowered.com` 检查基础连通性，再启动游戏；游戏内 CDN 资源更新仍由服务端决定。

Steam 客户端和游戏进程继承 Windows 网络栈，因此无需向游戏目录写入代理 DLL 或证书。若出现地区或授权提示，先在 Steam 客户端确认账号许可与商店可见性；网络节点本身不会产生账号授权。

## 验证与回滚

- 安装完成后在 Steam“属性 → 已安装文件”执行文件完整性验证。
- 卸载只通过 Steam 客户端进行；游戏存档是否云同步由 Steam 设置决定。
- 本仓库的 TW/JP Android 工具不会读取 Steam 凭据，也不会触碰 Steam 安装目录。

## 与 TW/JP 移动版的关系

TW/JP XAPK 可直接从本仓库 Releases 下载并通过 MuMu/ADB 安装，不需要切换 Google Play 区域。Steam 版是独立发行渠道，版本、账号许可和网络策略不能与 Android 包互换。

