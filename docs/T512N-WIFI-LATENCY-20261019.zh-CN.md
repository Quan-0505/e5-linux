# T512N Wi-Fi 内网延迟静态分析（2026-10-19）

## 范围与结论

本轮按用户要求仅静态分析，使用已保存的本机 Android 模块、固件与原始日志，
以及当前 T512N 构建源码。没有重新采集、修改设备、连接电脑到热点或更改省电参数。

**已确认一个固件加载适配缺口：原厂按 XPE eFuse 选择拼接固件的后半段，
当前 OpenWrt 的 request_firmware 下载路径没有执行该选择。**
本机此前 Android 与 OpenWrt 的实际固件版本字符串相互印证这一差异。

这是需要优先修复的确定偏差，但**尚未证明它是约 26 ms 内网 ping 的根因**；
本轮没有修复前后同客户端、同方向、同负载的延迟对照。

## 本机证据

原厂设备为 T512N/PB8，Android 13、512NCA05。
只读留存于 `dumps/t512n-stock-20261018/`，模块摘要来自已校验的
`reference/manifest.json`：

| 文件 | SHA-256 |
| --- | --- |
| 原厂 wcn_bsp.ko | `c752df3f0ab6d2138a049c99335c45cc1e914ea9edb978f6d34bddff580ca748` |
| 原厂 sprd_wlan_combo.ko | `d7a271f5aa046df30bee2896d24275bc7241c2fd8ef2d43e87d2625c87e803df` |
| 本机 wcnmodem.bin，3145728 字节 | `741cfe747974f93d8be6f3d23670d8fef571d1c36a8d1154c8b5b0fdcc66e3c3` |

同一份 WCN 文件包含两个固件变体：

| 起点 | 版本字符串 |
| --- | --- |
| `0` | `MARLIN3_20A_RLS2_W23.37.1 / sc2355_marlin3_lite / 09-11-2023 16:32:47` |
| `0x180000` | `MARLIN3_20A_RLS2_W23.37.1 / sc2355_marlin3_lite_abX / 09-11-2023 16:39:06` |

- 原厂 `dmesg.txt`，uptime 34.033753 起返回 **lite_abX**。
- 此前 OpenWrt `out/t512n/ram1/wifi-kernel.log`，uptime 80.730535 起返回 **lite**。
- 原厂日志明确记录原文件为 3 MiB，选择后仅下载 29 个最多 32768 字节的块。
  不能把“复制的是本机同一文件”当作“运行了同一固件”的证明。

该 OpenWrt 日志来自之前的 RAM 试运行，**不是本轮连接设备的当前读数**。
当前源码仍缺少同一选段逻辑；不能据此声称已读到设备今天实际加载的版本。

## 原厂驱动反汇编

使用本机原厂 `wcn_bsp.ko` 的 AArch64 带重定位反汇编，不以相似型号源码代替：

- `pre_btwifi_download_sdio` 位于 `0x13084`，内联了 firmware 下载逻辑。
- `0x132ac..0x132b0` 建立大小比较值 `0xe7400`。
- 大文件路径 `0x132f0` 调用 `marlin_get_wcn_xpe_efuse_data`。
- `0x132f4` 与 `1` 比较；命中后，`0x13300` 将数据指针增加 `0x180000`。
- `0x1330c` 设置长度 `0xe7400 - 0x50 = 0xe73b0 = 947120` 字节，
  与原厂日志的 29 次分块传输一致。
- XPE getter 位于 `0xf08c`：经过寄存器准备，读取 `0x40859030`，
  `0xf178` 提取第 29–30 位，缓存读取结果。
  这是运行时硬件选择条件，不能仅因 chip ID 是 AB 就把所有设备视为 XPE。

反汇编保存在忽略目录 `work/t512n-wifi-static-20261019/`：
`stock-pre-download.asm`、`stock-xpe-efuse.asm`、`stock-efuse-read.asm`。
其中 `sprdwcn_bus_reg_read` 存在编译器生成的同名局部函数，分析依据实际重定位目标，
不是只按函数名字猜测调用参数。

当前构建源码的 `drivers/unisoc_platform/sprdwcn/platform/wcn_boot.c`，
`btwifi_download_firmware()` 在非安全封装路径直接使用 `firmware->data/size`，
然后从文件开头逐块发送；没有对应的 XPE getter 和拼接文件选择步骤。
已有 WCNM 容器判断属于另外的 partition 下载路径，不能覆盖此 request_firmware 路径。

## 其他延迟线索核对

- 本机板级 ini 的 `power_save_switch=2` 来自原厂；其固件内部语义未证实，未改为 0。
- 旧日志在客户端接入时有 `CMD_POWER_SAVE`，但事件处理会调用
  `sc2355_work_host_wakeup_fw()`，对应子命令 `SPRD_HOST_WAKEUP_FW=7`。
  不能仅凭命令名把它解释为“接入后开启睡眠”。
- TX 数据入队后直接唤醒 TX 线程；所查路径未找到“固定等待约 26 ms 凑包”的逻辑。
  SDIO credit 的显式轮询预算是 15 次、每次 10 微秒量级，不等于 26 ms 定时发送。
- TCP ACK 过滤器先判断 IPPROTO_TCP，不适用于 ICMP；不能用改 ACK 合并参数解释 ping。
- 旧内网 iperf3 38 秒平均约 299 Mbit/s，前期出现 300 次 TCP 重传，后段没有新增。
  这说明吞吐基本可用，但不能证明空闲小包时延正常，也不能定位重传原因。
- 用户报告手机到热点约 26 ms；此前热点反向 ping 手机平均约 98 ms。
  两方向包含不同的客户端响应和休眠影响，不能直接混为同一个延迟指标。
- 定时更新 beacon 的旧日志不能单独证明信标抖动或客户端断线；不据此关闭标准功能。

## 后续修正边界

优先按原厂运行时判据补齐公共 WCN 下载路径中的选段逻辑，并覆盖长度、边界、
安全封装与错误返回；保留完整本机固件文件，不通过替换为其他机型固件或硬编码
T512N 固定截取来掩盖驱动缺口。其他型号也使用公共下载器，但必须核对其固件格式、
芯片及 XPE 判据，不将本机偏移与长度无条件用于所有文件。

实际验证首先核对运行版本是否恢复为本机 Android 的 lite_abX，再对照手机到热点的
空闲/负载 ICMP、UDP 小包与吞吐。固件版本一致仍不是低延迟验证通过。
不以关闭无线/SDIO/CPU 休眠、提高常驻频率或修改射频功率代替原因分析。

以上为第一阶段静态分析，当时未修改生产源码、打包产物或部署实机。

## 用户要求修复后的实施结果

新增 `devices/common/wcn-firmware.py` / `wcn-firmware.h`，接入 E5、T551M、
M8 的 prepare-kernel 及 upstream 容器/原生构建入口；T512N 经现有 T551M
公共准备入口取得同一修复。

- 仅识别已核验的 Marlin3Lite 原始 3 MiB 拼接布局；读取原厂同组 eFuse 准备寄存器，
  从 `0x40859030` 提取 XPE 字段，值为 1 时选取 `0x180000/0xe73b0`。
- 其他芯片、普通单镜像与非 XPE 标志值保持原来的加载结果。
- eFuse 成功读取后缓存，不增加运行时轮询；读取失败返回错误，不猜测应该加载哪段。
  只执行原厂读取准备的 RMW，没有写入 eFuse 数据或编程寄存器。
- 选择在已有安全封装解包之后进行，保存原始分配指针供释放；检查头部长度、
  有效载荷范围，下载/eFuse 失败路径释放缓冲区。没有覆盖或裁切本机固件文件。
- 这次只修正常使用的 request_firmware 路径；已有分区回退入口保持不变。
  没有将修改称为全格式固件解析器，也没有改动未知 WCNM/其他芯片格式。

离线验证命令：

```sh
python3 devices/common/test_wcn_firmware.py /path/to/linux-lts-e5 -v
```

3 项测试通过，其中实际生成的下载函数使用 ASan/UBSan 执行：全部四种 XPE 值、
其他芯片、单镜像及相邻大小、安全封装、512 种截短长度、长度溢出、
四组寄存器的每一步读写失败、分块发送失败、分配失败、成功缓存与失败后重试。
检查写入字节/长度/地址、寄存器 RMW 和内存所有权；原下载函数在 XPE 镜像
字节匹配断言处可复现失败。另验证重复应用、未知源码拒绝及构建入口覆盖。

E5、T551M、M8、T512N 的 ARM64 WCN 模块均编译通过，保留 BTF，vermagic
分别对应原有四个内核 release。完整模块依赖校验通过，没有跳过 modpost 未定义符号。
产物和构建日志位于 `work/t512n-wifi-static-20261019/build/`。

| 机型 | 新 wcn_bsp.ko SHA-256 |
| --- | --- |
| T512N | `aea1e04a9a20b37c31629eff5f00d9b386e253511d4d5c2784190c930d7782c4` |
| E5 | `49564379a2c49331dc2fa39d6228c55c9d1b1adb72223b0ee3cfb329c8091f24` |
| T551M | `a046f818d64a87ae515d3c5a5eb75c16de172d544d8c741f47f50942b0298b1d` |
| M8 | `31f2f12a6cf2a29a2b67cfd9e7ed2143da912320d43c09ecdbbbe9c9fac794b1` |

**源码和编译已完成，未刷入设备或替换之前的发布包。固件版本恢复及延迟改善仍待实机验证。**
