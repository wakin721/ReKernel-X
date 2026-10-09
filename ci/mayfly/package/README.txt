ReKernel-X 1.6 / LineageOS Xiaomi 12S 定制构建

仅适用于 5.10.260-gki-gef362912d37b 和构建时记录的内核配置。
源码、配置和工具链对应手机当前版本；保留 CFI 和模块 CRC 校验。
原始 ReKernel-X 功能源码未修改。构建信息见 build-info.json，源码见 source。

通过 KernelSU/Magisk 的模块安装功能安装本 ZIP，重启后检查 NoActive。
升级系统或更换内核后需要重新适配，禁止强制加载或绕过版本检查。
启动时发现版本/配置变化或加载失败会禁用模块。
模块会等待系统开机完成后再观察 60 秒；若在此期间重启，下一次启动会禁用模块。
此保护不能保证覆盖所有运行时故障；首次安装后请先确认手机操作正常。

手动回退：在 Root 管理器中禁用 ReKernel-X 后重启。
ADB Root 回退：touch /data/adb/modules/rekernel_x/disable，然后重启。
日志：/data/adb/modules/rekernel_x/load.log
