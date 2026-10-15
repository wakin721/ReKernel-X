ReKernel-X 1.6 / LineageOS Xiaomi 12S 分阶段初始化诊断版

旧版在部分开机中导致 SystemUI 启动超时。此版本仍需实机诊断验证。
早期开机只提供 Netlink 接口，让 NoActive 能发现并连接；此时 Hook 尚未工作。
必须在开机后 10 分钟内首次解锁。系统界面和锁屏服务稳定 10 秒后才启用 Hook。
启用后再观察 60 秒；界面异常、激活失败或就绪超时会禁用下一次自动加载。
失败标记不会因单纯 sys.boot_completed=1 而清除。
Netlink 连接正常并不单独证明 Hook 已启用，请检查 load.log 的 stage=hooks active。

支持已收录的 mayfly 内核：5.10.260-gki-gef362912d37b、5.10.269-gki-g490755fcc6cc、
5.10.269-gki-geff4b40407a1（LineageOS 24）。首次使用仍需实机运行验证。
同一个模块可在兼容内核之间复用；保留 CFI 和模块 CRC 校验。
原始 ReKernel-X 功能源码未修改。构建信息见 build-info.json，源码见 source。

通过 KernelSU/Magisk 的模块安装功能安装本 ZIP，重启后检查 NoActive。
已收录内核且实际 CONFIG 选项匹配其档案时自动复用；版本注释变化不会触发禁用。
LineageOS 24 的四项工具链差异已按精确值审查，完整配置摘要仍按内核分别检查。
未知内核需先验证并更新兼容列表，兼容时只重新打包、不编译模块。
ABI 真正变化时才需适配或重编，禁止强制加载或移除 CRC。
启动时发现未验证内核、配置变化、模块损坏或加载失败会禁用模块。
模块会等待系统开机完成后再观察 60 秒；若在此期间重启，下一次启动会禁用模块。
此保护不能保证覆盖所有运行时故障；首次安装后请先确认手机操作正常。

手动回退：在 Root 管理器中禁用 ReKernel-X 后重启。
ADB Root 回退：touch /data/adb/modules/rekernel_x/disable，然后重启。
日志：/data/adb/modules/rekernel_x/load.log
