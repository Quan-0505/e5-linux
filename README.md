<div align="center">

# 老头乐 E5 · OpenWrt

**把 E5 变成随身 5G 路由器 · 内置存储安装 · Rust daed · 节点小宝 · GitHub Actions 构建**

[![Build](https://img.shields.io/github/actions/workflow/status/Quan-0505/e5-linux/e5-kdae-release.yml?branch=codex%2Fe5-internal-kdae&label=Build&style=flat-square)](https://github.com/Quan-0505/e5-linux/actions/workflows/e5-kdae-release.yml)
[![Release](https://img.shields.io/github/v/release/Quan-0505/e5-linux?style=flat-square&label=Release)](https://github.com/Quan-0505/e5-linux/releases/latest)
[![OpenWrt](https://img.shields.io/badge/OpenWrt-25.12.5-00b5e2?style=flat-square)](https://openwrt.org/)
[![Kernel](https://img.shields.io/badge/Linux-6.18_LTS-orange?style=flat-square)](https://github.com/sprd-linux-devs/linux/tree/e5-6.18)
[![Rust daed](https://img.shields.io/badge/Rust_daed-3.2.1-805ad5?style=flat-square)](https://github.com/Quan-0505/rust-daed)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

**面向老头乐 E5（Unisoc UMS9621 / ARM64）的 OpenWrt 定制构建**

[📦 固件下载](#download) · [✨ 功能介绍](#features) · [🚀 安装与升级](#install) · [🔧 自行编译](#build) · [❤️ 开源致谢](#credits)

</div>

---

在 E5 原生 Linux 适配的基础上，整合 **OpenWrt、daed 管理控制台和节点小宝**，保留蜂窝上网、Wi-Fi 热点、USB 网络、信息屏以及短信等设备功能。

本仓库维护内置 eMMC 的独立 e5root 安装与更新。本次公开 Rust 固件从 codex/e5-rust-daed-20261018 构建；原 codex/e5-internal-kdae 分支保留为 Go 版本维护线。

<a id="features"></a>
## ✨ 功能介绍

| 功能 | 说明 |
| --- | --- |
| **内置 OpenWrt** | OpenWrt 25.12.5，安装到独立 `e5root` 分区；已有内置安装通过更新入口升级 |
| **E5 原生内核** | Linux 6.18 LTS，保留 E5 充电、触屏、背光、音频和蜂窝硬件适配 |
| **daed 管理界面** | Rust daed 3.2.1，提供订阅、节点、群组、DNS、路由、实时日志及热重载管理 |
| **eBPF 数据面** | 构建时核对 BTF、BPF、veth、TC/clsact 等能力及匹配的内核模块 |
| **节点小宝** | 预装官方 ARM64 4.3.5-734 客户端，提供 LuCI 服务入口，使用者自行登录绑定 |
| **蜂窝与热点** | ModemManager Unisoc 适配，提供 SIM/APN、蜂窝数据、Wi-Fi 热点和 USB 网络管理 |
| **屏幕与短信** | 信息屏内置 daed 管理入口、未读短信提示、双卡短信、VoLTE/VoNR 设置及锁屏唤醒修正 |
| **升级保留设置** | 保留本机代理数据库及关联文件、CA 和节点小宝绑定状态；首次启动以非破坏性副本迁移保留 Go 账号和配置 |
| **公开构建** | GitHub Actions 构建，Release 提供固件安装包及切换模块 |

KDAE 的 DNS、直连/代理策略和节点小宝的转发/回程路由需要按自己的网络配置。软件预装不代表已配置订阅或已获得第三方服务权限；跨站点 UDP 单播也不等同于广播或 mDNS 自动发现。

<a id="download"></a>
## 📦 固件下载

前往 **[Releases](https://github.com/Quan-0505/e5-linux/releases)** 下载完整 E5 安装包，解压后先看 **`START-HERE.md`**；当前发布文件的 SHA-256 摘要见对应发布说明。

| 文件 | 用途 |
| --- | --- |
| `e5-openwrt-flash-*.zip` | 完整安装包，包含电脑安装器、系统镜像、工具及详细指南 |
| `e5-linux-switch-*.zip` | 已安装系统的 Android → Linux 切换模块，不是完整固件 |

**当前发布（2026-10-18）**：build-20261018-080713-a616610（https://github.com/Quan-0505/e5-linux/releases/tag/build-20261018-080713-a616610），OpenWrt 25.12.5、E5 Linux 6.18.54、Rust daed 3.2.1、节点小宝 4.3.5-734。源码来自 codex/e5-rust-daed-20261018（https://github.com/Quan-0505/e5-linux/tree/codex/e5-rust-daed-20261018），提交 a6166106d22406255de9b449095f7d17e9be14d8；Rust daed 锁定提交 7b1d18772789be988c933dc5e18fdb5411a00857。

本版修复内置更新时误将旧 Go 服务启动脚本覆盖 Rust 服务脚本的问题。Actions 全量构建、包哈希、目标 E5 的既有 e5root 保数据升级及升级后服务验收均通过；GPT 与分区布局保持不变。实机确认 Rust daed 数据库迁移和控制台可用，原账号、DNS、路由与有效群组策略保留，订阅刷新成功，节点小宝服务可达。个别外部 HTTPS/UDP DNS 探测超时，详见 docs/RELEASE-20261018.zh-CN.md，这些探测不作为所有网络环境的保证。

本次 Release 仅提供完整固件 ZIP 与 Android/Linux 切换 ZIP；不附带重复 tar.gz、build.json 或 SHA256SUMS。Windows 图形安装器包的源文件指纹与本次候选源码不匹配，因此未发布。已安装系统请使用“更新 OpenWrt”入口；不要把首次安装、重装或缩容入口当作普通升级。


固件不包含个人订阅、节点、密码、JWT、数据库、SSH 私钥或节点小宝组网身份。Wi-Fi、基带等设备运行文件由安装器从接收设备自身提取，不使用他人的 NV、校准或整机备份。

<a id="install"></a>
## 🚀 安装与升级

### 首次安装

1. 核对设备确为老头乐 E5，准备可恢复的原机备份、稳定供电及可靠数据线。
2. Android 侧准备好包内指南要求的 Root、ADB 和启动条件；Shell 超级用户请求需要在本机允许。
3. 解压完整 E5 安装包，Windows 打开 `OpenWrt-Installer.exe`；也可在具备依赖的电脑运行 `python3 OpenWrt-Installer.py`。
4. 按安装器选择存储位置、容量与热点设置，以该包的 `START-HERE.md` 为操作依据。

| 方式 | 对存储的影响 |
| --- | --- |
| **内置独立分区** | 缩小 `userdata` 并创建 `e5root`；是否能保留 Android 用户数据取决于加密和文件系统检查结果 |
| **TF 卡** | 写入所选 TF 卡并清除安装目标上的原数据；使用包内对应入口 |
| **旧 userdata 镜像** | 兼容入口，受 data 加密及文件系统状态限制，按安装器检查结果操作 |

**安装到内置存储不等于删除全部 Android 分区。** 当前安装流程保留必要启动链及 Android 回退路径，不提供“一键擦除 Android 并回收全部空间”的承诺。加密 data 的内置安装可能要求恢复出厂；不要把首次安装、重装或缩容入口当作普通升级。

### 已有 OpenWrt 更新

设备运行 OpenWrt 时，通过 USB 网络连接电脑，打开新包安装器，选择 **更新 OpenWrt**（当前主入口菜单第 6 项）。

- 电脑通过 SSH 主动上传，检查机型、现有布局、容量和载荷哈希。
- 重启进入 initramfs，将校验后的载荷复制到内存，卸载系统分区后更新内核与系统。
- 保持原分区容量，恢复设备自己的配置及运行文件；本定制分支额外保留 KDAE 与节点小宝数据。
- 已有独立分区更新不重新缩容、不修改 GPT；自行安装的其他软件包和未列入保留清单的文件需要另外备份。

单根内置系统更新没有 TF 双系统分区的自动回退能力，写入期间应保持供电。详见 [SSH 与内置更新说明](https://github.com/Quan-0505/e5-linux/blob/codex/e5-internal-kdae/docs/UPDATE-SSH-PART-20261013.zh-CN.md) 和 [插件保留说明](https://github.com/Quan-0505/e5-linux/blob/codex/e5-internal-kdae/docs/KDAE-NODEBABY.zh-CN.md)。

### 登录与系统切换

| 入口 | 默认地址 / 使用方式 |
| --- | --- |
| LuCI | `http://192.168.9.1/`，使用自己的设备管理账号 |
| daed（Rust 候选） | `http://192.168.9.1:2023/`；首次创建管理员、导入自己的订阅 |
| 节点小宝 | `http://192.168.9.1:9118/`；使用自己的账号登录绑定 |
| LuCI 快捷入口 | **服务 → daed / 节点小宝**，随设备当前管理地址打开 |

上表为默认 LAN 地址，修改过网段后使用实际地址。固件不预置本人的账号、管理密码或无线密码。

Linux 中可通过屏幕的系统切换入口，或 `e5-next-boot android && reboot` 返回 Android。Android 切回已安装的 OpenWrt，可使用电脑安装器的系统切换入口或独立切换模块；**不要反复刷完整固件来切换系统**。试启动失败回到 Android 时，应先检查启动日志。

<a id="build"></a>
## 🔧 自行编译

本次 Rust 固件由 **Actions → Build and publish OpenWrt** 从 codex/e5-rust-daed-20261018 构建。要复现本次发布，请检出对应源码提交；其他分支的引擎版本可能不同。Fork 后请核对工作流中的依赖与权限。

```sh
git clone --recurse-submodules --branch codex/e5-rust-daed-20261018 https://github.com/Quan-0505/e5-linux.git
cd e5-linux
```

工作流构建 E5 内核、匹配模块、原生 ModemManager、信息屏、Rust daed、DaedNext 页面、公开 Geodata、节点小宝和完整安装包；校验软件来源、镜像元数据、模块能力及最终包哈希。Rust daed 与节点小宝来源见 [软件锁定清单](openwrt/network-addons/lock.json)。Go `wing.db` 由设备本地首次启动迁移到新的 Rust 数据库，源库不覆盖；配置迁移必须在设备上验收。

CI 成功表示构建及所列检查通过，不能代替特定设备上的蜂窝、通话、充电、Wi-Fi、代理或断电重启测试。发布说明应分别记录源码变化、打包结果和实机验证范围。

## 📚 更多资料

- [内置分区原理与安装流程](https://github.com/Quan-0505/e5-linux/blob/codex/e5-internal-kdae/docs/INTERNAL-PARTITION-SYSTEM-20261012.zh-CN.md)
- [2026-10-18 固件发布与验证范围](docs/RELEASE-20261018.zh-CN.md)
- [2026-10-15 上游同步记录](https://github.com/Quan-0505/e5-linux/blob/codex/e5-internal-kdae/docs/UPSTREAM-20261015.zh-CN.md)
- [KDAE 与节点小宝集成](https://github.com/Quan-0505/e5-linux/blob/codex/e5-internal-kdae/docs/KDAE-NODEBABY.zh-CN.md)
- [上游技术说明（中文）](README.upstream.zh-CN.md) / [English](README.upstream.en.md)

<a id="credits"></a>
## ❤️ 开源致谢

感谢以下项目和作者提供的基础工作，让老头乐 E5 从 Android 设备走到可使用的 Linux / OpenWrt：

- **[sprd-linux-devs / Enceka](https://github.com/sprd-linux-devs/e5-linux)**：E5 Linux 基础适配、启动流程、内核与用户空间支持，以及持续的硬件研究。
- **[kanoqwq/e5-linux](https://github.com/kanoqwq/e5-linux)**：安装器、共享设备服务、信息屏、蜂窝与存储等改进；感谢作者长期维护和分享。
- **[dikeckaan/mu300-linux](https://github.com/dikeckaan/mu300-linux)**：随身 Wi-Fi Linux 项目及可复用的安装、管理和修复思路。
- **[OpenWrt](https://openwrt.org/)**、**[Linux](https://www.kernel.org/)**、**[ModemManager](https://modemmanager.org/)**：路由系统、内核和蜂窝连接管理基础。
- **[Enceka/infoscreen](https://github.com/Enceka/infoscreen)** 与 **[infoscreen-plugins](https://github.com/Enceka/infoscreen-plugins)**：设备信息屏和应用框架。
- **[daeuniverse](https://github.com/daeuniverse)**、**[ksong008/DaeNext](https://github.com/ksong008/DaeNext)**、**[ksong008/DaedNext](https://github.com/ksong008/DaedNext)**：eBPF 透明代理引擎和管理界面的基础工作；本仓库通过 [rust-daed](https://github.com/Quan-0505/rust-daed) 集成。
- 所有提交修复、文档、测试结果及问题反馈的贡献者。

本仓库脚本沿用 [MIT 许可](LICENSE)；Linux、KDAE 及其他组件分别遵循各自原有许可，版权与致谢均予以保留。节点小宝采用[官方软件](https://iepose.com/)，按其官方授权与服务条款使用，不将其列为本仓库的开源组件。
