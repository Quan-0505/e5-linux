# 公共热点关闭 U-APSD（2026-10-19）

按用户要求，E5 仓库所有机型和 MU300 仓库所有机型的 OpenWrt 热点统一关闭
U-APSD advertisement。这是明确的配置策略选择，不代表已证实 U-APSD 是
所有延迟尖峰的根因，也不宣称它在所有终端上没有用途。

- 公共 `patch-hostapd-sae.py` 同时处理 shell、ucode 两条 AP 配置生成路径，
  输出 `uapsd_advertisement_enabled=0`，包括恢复的旧开启配置。
- 新装热点写入 `option uapsd '0'`；升级后 `95-disable-ap-uapsd` 一次性迁移
  所有既有 AP，包括匿名 section，不改 station/client 接口。
- 保留 WMM、DTIM、beacon、信道、带宽、密码和其他省电机制；没有新增服务、
  轮询或保活流量，也没有修改无线驱动、SAE 密钥处理及 AT 流程。
- 使用现有 wifi-scripts 包构建入口；补丁脚本本身已纳入构建哈希，因此旧
  APK 缓存不会被误当作包含本次修改。不需要新增另一套打包路径。

离线验证：使用实际运行版 OpenWrt 生成脚本应用补丁两次，检查幂等和 shell
语法；在现有 OpenWrt 容器执行修改后的 ucode AP setup，覆盖旧值 1、0、缺省，
确认输出 U-APSD 0、WMM 1、DTIM 2。另用真实 UCI 执行迁移，验证具名/匿名 AP、
STA 不变、SSID/带宽/DTIM 不变，以及重复执行不改配置文件。

两仓库均通过上述检查，未编译打包。后续仅对 MU300 仓库对应的 U30 Air 实机
执行公共配置迁移并确认 hostapd 配置 advertisement 0、WMM 1、DTIM 2；E5
系列及其他实机尚未部署。未部署新的 wifi-scripts APK。

后续 U30 Air 核查发现：驱动收到的 WMM IE 的 U-APSD 位确为 0，但电脑只读
获取的最新 BSS IE 仍为 QoS Info 0x80，即固件实际广播仍宣告 U-APSD。
所以本次完成的是公共配置策略，**尚不能保证固件已关闭 U-APSD**，亦不能把
修改后仍有高 ping 当作排除该方向的依据。固件控制入口仍需原厂对照核验；
未盲改能力掩码、关闭 WMM 或加入常驻保活。

## 与 MU300 低延迟修改的适用边界

2026-10-19 再次核对：E5、T551M、M8、T512N 使用这里的公共热点配置，
不需要为每个机型重复添加 U-APSD 策略。源码修改尚不等于这些实机已更新。

MU300 的 WCN PCIe RX-push 游标修复属于 PCIe EDMA 接收路径；本仓库这些
机型运行 SDIO 通路，不能把该缺陷直接认定为相同的 SDIO 故障。

U30 Air 原厂 `init.md.rc` 的 CPU0 lowlatency 设置已有实际固件证据，
并按用户要求用于 MU300 全部机型。本轮从本仓库已保存的原厂镜像仅提取
`/etc/init`，核对 E5 的 80 个 rc 和 T551M 的 99 个 rc，未发现
`lowlatency`、`cpuidle` 或 `state[012]/disable` 设置。输入分别为忽略目录
`work/e5-audit-20261016/vendor_a.img` 和
`work/power-model-audit-20261016/stock/t551m/vendor_a.img`；提取结果位于
`work/lowlatency-stock-20261019/`，未再次复制整套固件到 WSL。

这只说明检查过的 vendor init 脚本没有该设置，不能证明原厂 PowerHAL、
其他分区或运行时不会调整 idle；M8/T512N 本轮没有完成对应原厂核验。
因此此次未将禁用 CPU0 idle 加入 E5 公共启动路径，也没有把 U30 Air 的
延迟测量或功耗判断当作 E5 系列实机验证。E5 系列是否需要调整 idle，
仍应以对应设备的原厂运行状态和受控延迟对照为依据。
