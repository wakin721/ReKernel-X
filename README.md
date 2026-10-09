# ReKernel-X

## LineageOS 小米 12S 定制构建

此 fork 的默认分支 `lineage-mayfly` 基于上游 **1.6**，用于已经实机验证的
`mayfly / 5.10.260-gki-gef362912d37b`。内核功能源码保持该版本，通过匹配的
内核源码、真实配置、符号 CRC 和 Clang 工具链完成适配。

**下载与构建：** 打开 [专用 GitHub Actions](https://github.com/wakin721/ReKernel-X/actions/workflows/lineage-mayfly.yml)，
选择成功的运行，在 Artifacts 下载 `ReKernel-X-LineageOS-mayfly-…`。
解压 artifact，取出里面的 **`ReKernel-X-1.6-LineageOS-mayfly-5.10.260.zip`**，
在 KernelSU / Magisk 中安装这个内层 ZIP 后重启。不要直接安装整个 artifact。

在 Actions 中点击 **Run workflow** 可以手动构建；推送到 `lineage-mayfly`
且修改模块源码、适配配置或构建脚本时也会自动构建。流程不需要个人令牌或额外 Secrets。
每个 artifact 包含模块、安装 ZIP、SHA256、构建日志及 ABI 校验结果，保存 30 天。
本分支的专用流程不会自动发布 Release。

安装和启动均检查内核版本及配置摘要。保留 CFI、栈保护和 MODVERSIONS；
若加载失败或上次启动未通过开机后 60 秒观察期，下一次启动会禁用模块。
不提供上游通用版本的自动更新入口。启动保护不能覆盖所有运行时故障，
首次使用新的构建仍需确认 NoActive 连接及实际操作正常。

**升级系统或更换内核后必须重新适配。** 不能仅改版本字符串或选择另一个
androidXX-5.10 预编译模块强行加载。源头及校验说明见
[内核配置档案](profiles/lineage-mayfly/README.md)。`main` 保留上游分支。

本地构建使用 x86_64 Ubuntu 24.04：安装工作流列出的 apt 依赖，创建 Python venv，
执行 `pip install -r ci/mayfly/requirements.txt`，再运行 `bash ci/mayfly/build.sh`。
工具链和内核源码会按固定提交下载，产物写入 `dist/`。建议至少预留 10 GB 磁盘空间。
`BUILD_ROOT`、`DOWNLOAD_CACHE`、`JOBS` 可配置构建目录、下载缓存和并行数。
源码及配置包含在安装 ZIP 中，仓库提交记录写入 `build-info.json`。

以下为上游项目说明；当前设备请使用上面的专用流程和 ZIP。

[![C](https://img.shields.io/badge/language-C-%23f34b7d.svg?style=plastic)](https://en.wikipedia.org/wiki/C_(programming_language))
[![Android](https://img.shields.io/badge/platform-Android-0078d7.svg?style=plastic)](https://en.wikipedia.org/wiki/Android_(operating_system))
[![AArch64](https://img.shields.io/badge/arch-AArch64-red.svg?style=plastic)](https://en.wikipedia.org/wiki/AArch64)

为墓碑模块提供内核支持

基于 [Re:Kernel](https://github.com/Sakion-Team/Re-Kernel) v9.2 二次开发

## 作用

进程被冻结后，无法正常响应，ReKernel-X 在内核监听并提供如下事件

| 类型 | 触发条件 | 适用场景 |
|---|---|---|
| Binder | 冻结进程收到 Binder 调用 | 系统服务或其他应用访问冻结进程 |
| Signal | 冻结进程收到 SIGKILL 等关键信号 | 感知杀进程等行为 |
| Network | 被监控 UID 收到入站网络包 | 消息类应用接收推送 |

## 依赖环境

- 内核 ≥ 5.10
- [KernelSU](https://kernelsu.org/zh_CN/guide/installation.html)
  或 [Magisk](https://topjohnwu.github.io/Magisk/install.html)
  或 [APatch](https://github.com/bmax121/APatch)

## 安装

从 [GitHub Releases](https://github.com/myflavor/ReKernel-X/releases) 下载模块并刷入，重启后自动加载

## 开发接入

用户态通过 Generic Netlink 接收内核事件，仓库提供现成的 AAR 客户端

- 接入方式见 [Develop](Develop)
- 内核源码与编译说明见 [LKM-Source](LKM-Source)

## 许可

本项目使用 [GPL](LICENSE)，修改或二次分发请保持开源
