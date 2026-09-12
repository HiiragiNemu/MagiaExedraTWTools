# 中文下载站维护

公开站点：<https://magia-exedra-tw-tools.pages.dev/>

网站只包含下载链接、中文教程、校验值和验证记录，不接收账号资料。XAPK 托管于 GitHub Releases，不上传到 Cloudflare Pages 的静态资源目录。

## 构建与检查

需要 Python 3.10+；站点构建本身无第三方 Python / Node 依赖。

```text
py -3 scripts/build_site.py
py -3 -m pytest -q
py -3 -m http.server 8769 --bind 127.0.0.1 --directory dist/site
```

浏览器访问 `http://127.0.0.1:8769/`，检查桌面和手机布局、教程标签页、键盘操作、复制按钮与下载链接。测试所需 pytest 见仓库原测试说明。

## Cloudflare Pages

此项目使用 Direct Upload，不是 Git 自动构建。使用已有 Cloudflare 登录和 Wrangler CLI；不得把 token 放进仓库。
首次创建项目（只做一次）：

```text
npx wrangler@4.130.0 pages project create magia-exedra-tw-tools --production-branch main --force
```

发布前先将已通过测试的源码合并到本仓库 `main`，并公开对应的 GitHub Release 文件，再部署同一源码构建产物：

```text
py -3 scripts/build_site.py
npx wrangler@4.130.0 pages deploy dist/site --project-name magia-exedra-tw-tools --branch main
```

## 每次客户端更新

1. 下载完整原版 XAPK，核对实际包名、版本、三个 split 和发布者签名连续性。
2. 更新 `manifests/known-releases.json`、手机脚本固定校验值及该版本的验证记录；保留旧版条目。
3. 更新教程版本与 `scripts/build_site.py` 中的工具发布版本。网站主要版本号、大小和哈希来自清单。
4. 运行测试，确认安装／升级／回滚行为。使用匿名下载核对公开 Release 文件。
5. 构建并发布，检查正式域名实际内容、手机布局及所有主下载。

网站回退：从之前已发布的源码提交在独立目录重新构建，通过相同 Pages 命令重新部署。游戏升级回滚与站点回退分开；游戏设备的回滚应使用该次安装备份生成的脚本，不要卸载或清除资料。
