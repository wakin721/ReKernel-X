# ReKernel-X

## 分阶段初始化诊断版

`diagnostic/staged-boot` 正在验证开机卡在“手机正在启动中”的问题。
2026-10-15 的一次失败启动出现 12 个进程启动超时，SystemUI 被杀死后
KeyguardService 为 DEAD、用户保持锁定；只禁用 ReKernel-X 的对照启动恢复正常。
旧模块在解锁后加载成功，但 NoActive 没有重新连接，故简单延迟 insmod 不够。
这些证据不能单独证明某个 Hook、CFI 或内核 ABI 是根因。

本诊断版修改初始化流程，并**重新编译一次模块**：

1. 开机早期只初始化规则表和原有 Netlink 接口，让 NoActive 按原时机发现模块。
   此时 Binder、signal、netfilter 和 kprobe Hook 均未启用。
2. 用户 0 在开机 10 分钟内首次解锁，且当前 SystemUI 进程的 SystemUIService/
   KeyguardService 正常、前台不是 FallbackHome，连续稳定 10 秒后启用 Hook。
3. 用 root 专用、只能单向开启的 `hooks_enabled` 参数激活 Hook。
   激活失败回滚 Hook，保留传输层供诊断。不要手动修改参数来绕过就绪检查。
4. 激活后继续观察 UI 60 秒。超时、激活失败或 UI 异常会禁用下一次自动加载，
   并保留失败启动标记；不再只依赖 `sys.boot_completed=1` 判断成功。

保留设备、内核、完整 CONFIG 指纹、模块 SHA256、内核原生 CRC/CFI/栈保护。
新模块 68 项版本条目已静态匹配三个已收录内核；原始模块是 66 项。
内核端生命周期和 shell 启动策略均有可执行回归测试。
**2026-10-15 实机对照未解决卡死，请勿当作稳定版本安装。**
内核记录早期只有 Netlink 就绪，`hooks_enabled=N` 全程未开启，仍然出现
12 个进程启动超时、SystemUI 被杀死、KeyguardService DEAD 和 FallbackHome。
这排除了“必须先开启本模块 Binder/kprobe Hook 才发生故障”的解释；
随后经明确授权，只暂停 NoActive user0 注入、保留其他模块作了对照。
该轮却在更早的 LineageOS HealthInterfaceService 初始化阶段，等待
ChargingControlController 的 `waitForDeclaredService`，触发 65 秒主线程 Watchdog。
同样的充电 HAL 等待在 10:20 的历史启动也出现过，因而没有得到可用于归责
NoActive/LSPosed 的干净对照。不要把 Binder 延迟或某个模块启用直接等同于根因。
测试后 NoActive 与全部 Xposed 启用状态均已恢复原值，ReKernel-X 保持禁用以恢复手机。
新保护正确保留失败标记，没有把 `boot_completed=1` 误当作 UI 正常。
源码/ABI/35 项测试通过仅证明相应静态和策略行为，不能证明实机开机稳定。

日志在 `/data/adb/modules/rekernel_x/load.log`：
`stage=transport` 只表示连接接口就绪；只有 `stage=hooks active` 才表示 Hook 工作，
`stage=healthy` 表示 UI 与后续观察均通过。仅 NoActive 显示连接不足以证明功能全部启用。
开机后 10 分钟未解锁也会保守地禁用下一次加载，需要手动重新启用。
回退：在 Root 管理器禁用本模块后重启，保留现有应用数据。

Actions 可选择本分支手动运行 `Package compatible mayfly module (no compilation)`，
它验证固定的诊断二进制并打包，不再次编译；修改 C 功能后仍必须重新构建和更新来源记录。
安装内层 `ReKernel-X-1.6-LineageOS-mayfly-staged-diagnostic.zip`，不要安装 artifact 外层 ZIP。

## 历史兼容包说明

以下说明属于旧版兼容包，其一次正常开机验证不能代表后续每次开机均稳定。

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
