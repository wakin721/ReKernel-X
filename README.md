# ReKernel-X

## LineageOS 小米 12S 兼容复用

此 fork 的默认分支 `lineage-mayfly` 基于上游 **1.6**。同一个原始定制模块
可用于 `mayfly` 的以下内核：

| 内核 | LineageOS 参考构建 |
|---|---|
| `5.10.260-gki-gef362912d37b` | `23.2-20260925-NIGHTLY-mayfly` |
| `5.10.269-gki-g490755fcc6cc` | `23.2-20261009-NIGHTLY-mayfly` |
| `5.10.269-gki-geff4b40407a1` | `24.0-20261012-NIGHTLY-mayfly` |

功能源码和 `.ko` 保持原始验证版本，三个内核的 66 项导入 CRC 均匹配。
配置检查只比较实际 CONFIG 选项，忽略顶部内核版本注释。
LineageOS 24 的内核使用 Clang 22，旧模块仍使用原始 Clang 21 构建。
四项工具链配置差异的精确值已单独记录并审查；安装和启动仍匹配每个内核自己的
完整配置摘要，不会忽略编译器变化。静态验证不能替代首次实机 CFI/运行验证。

2026-10-14 已在上述 LineageOS 24 构建实机验证
[兼容包 92a79ed](https://github.com/wakin721/ReKernel-X/actions/runs/38545355287)：
18 项 CI 测试通过，原始 `.ko` 未重编；正常 insmod 成功，Netlink/Hook 初始化成功，
NoActive 日志显示“ReKernel-X通知正常”，开机后 60 秒观察期通过。
用户确认已连接、应用切换操作正常，本次启动未观察到 CFI 故障。
这是一次启动和操作验证，不代表所有运行路径或后续内核都已验证。

**下载：** 打开 [无编译复用打包 Actions](https://github.com/wakin721/ReKernel-X/actions/workflows/reuse-mayfly.yml)，
选择成功的运行，在 Artifacts 下载 `ReKernel-X-mayfly-compatible-…`。
解压 artifact，取出里面的 **`ReKernel-X-1.6-LineageOS-mayfly-compatible.zip`**，
在 KernelSU / Magisk 中安装这个内层 ZIP 后重启。不要直接安装整个 artifact。

在 Actions 中点击 **Run workflow** 可以手动打包；更新兼容档案或加载脚本后
会自动运行。流程校验仓库内固定的旧模块及所有已收录内核的 CRC，运行加载策略测试，
再生成 ZIP，**不下载 Clang、不编译模块**。无需个人令牌或额外 Secrets。
每个 artifact 包含模块、安装 ZIP、SHA256、复用日志及 ABI 校验结果，保存 30 天。
原来的 [编译流程](https://github.com/wakin721/ReKernel-X/actions/workflows/lineage-mayfly.yml)
保留，供功能源码或 ABI 实际变化时使用；本分支不自动发布 Release。

安装和启动均检查已验证内核列表、实际配置摘要及模块完整性。保留 CFI、栈保护和 MODVERSIONS；
若加载失败或上次启动未通过开机后 60 秒观察期，下一次启动会禁用模块。
不提供上游通用版本的自动更新入口。启动保护不能覆盖所有运行时故障，
首次使用新的构建仍需确认 NoActive 连接及实际操作正常。

**已收录且配置匹配该内核档案的更新会直接复用模块。** 未收录内核会禁用模块，
需要检查其配置、导出 CRC、Binder 内部结构/函数和 Hook 声明后补充兼容列表；
检查通过即可重新打包，只有真正不兼容时才需适配或重编。
不根据 `5.10.*` 通配符推定兼容，不改 vermagic，不移除 CRC，也不强制加载。
源头及校验说明见 [原始内核档案](profiles/lineage-mayfly/README.md)、
[5.10.269 兼容档案](profiles/lineage-mayfly-5.10.269/README.md)、
[LineageOS 24 兼容档案](profiles/lineage-mayfly-5.10.269-los24/README.md)及
[旧模块来源](prebuilt/mayfly/README.md)。`main` 保留上游分支。

本地复用打包：创建 Python venv，执行 `pip install -r ci/mayfly/requirements.txt`，
然后运行 `python ci/mayfly/reuse.py`；只做验证可用 `--verify-only`。
测试：`python -m unittest discover -s ci/mayfly -p 'test_*.py' -v`。
模块功能源码改变时复用流程会拒绝旧二进制，需要重新构建并更新固定模块及来源记录。

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
