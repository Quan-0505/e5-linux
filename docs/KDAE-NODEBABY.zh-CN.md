# E5 OpenWrt：Rust daed 与节点小宝

Actions → Build and publish OpenWrt 使用本 fork 的 E5 固定子模块、E5 6.18 内核和 OpenWrt 25.12.6，构建并校验完整通用 ZIP/TAR 刷入包。Rust daed 3.2.2 从 `openwrt/network-addons/lock.json` 固定的公开提交构建，包含 DaedNext 页面、Geosite/GeoIP 和 ARM64 引擎。
MU300 clean-tf-7.2 只作为构建校验参考，不使用它的 boot、设备树或模组适配。

LuCI → 服务 → daed / 节点小宝 自动打开当前设备的 2023 / 9118 管理界面。Rust daed 使用上游 Rust 引擎与固定的 DaedNext 管理界面；E5 服务显式使用 `NETNS_LINK=veth`。针对 E5 核验过的 Go `wing.db`，首启时用 Rust 内置 `state migrate` 命令创建独立的 `/etc/daed/daed.db` 副本，原 `wing.db` 不修改，以便回退。节点小宝使用官方公开 ARM64 4.3.5-734，并校验 SHA256。

首次空白安装请自行设置管理账号、添加订阅，并为节点小宝绑定自己的设备。镜像不带账号、数据库、JWT、订阅、节点、SSH 密钥或节点小宝身份。Rust 状态保存在 `/etc/daed/daed.db`；设备更新时保留本机 Go 数据库与 Rust 数据库，通用固件包不包含其中任何一个。服务等待网络的工作由 procd 子进程执行，不阻塞系统启动。

内核显式启用 NETKIT、VETH、BPF/JIT/BTF、流量分类和入口 qdisc；最终内核配置与 ELF、文件清单在发布前校验。Rust release 含 F50 SIPA RAWIP IPv4 出口兼容补丁；E5/F50 的实际流量通过前仍属于候选构建。订阅更新和 Geodata 更新由 Rust 服务自身管理。

更新器保留设备本地数据库与节点小宝身份，不用旧软件覆盖新软件；SQLite 使用在线备份读取已提交 WAL。更新器通过新镜像自带的 Python/SQLite 运行，不依赖旧系统 Python 模块。Go KDAE 的 `/etc/daed/wing.db` 或 `/etc/daed-kdae/wing.db` 只作为迁移源；Rust 首启时创建新的 `daed.db`。迁移失败会阻止新服务启动并留下原 Go 数据库，不能强行删除或覆盖源库。通用发布包始终没有这些设备状态。

固定的信息屏 09b7ec8 的 USB 调度器有未知操作先查询硬件导致错误返回不一致的问题。tools/prepare-screen-compat.py 校验原始 SHA 后加入参数拒绝，保留原 USB 测试并记录补丁在本仓库。

节点小宝默认仅提供本机服务与自行授权的隧道路由，不预置个人异地网段或放开隧道防火墙。需要下游转发时按自己的网段配置防火墙和回程。

仅编译不代表硬件实测通过；刷入使用 E5 原有安装器，校准与 vendor 数据从接收设备自身提取。不要使用 MU300 固件或其他设备的身份备份。
