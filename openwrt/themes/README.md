# 额外 LuCI 主题（随固件构建一并安装）

这里放**不在 OpenWrt 官方 feed 里、又希望每次构建都带上**的 LuCI 主题包。
`openwrt/build-rootfs.sh` 会把这些 `.apk` 复制进构建工作区，并在安装 Argon 的同一批
`apk add --allow-untrusted` 里装进镜像（构建日志会打印 `themes: ...` 一行）。

**E5 全新安装默认使用 Vantage**，由 `93-e5-luci` 在首次启动设置。已有设备保配置更新时，
保留原先选择的主题。装上的主题在 LuCI 的「系统 → 系统 → 语言和样式 → 设计」里切换，或用：

```sh
uci set luci.main.mediaurlbase='/luci-static/footstrap'
uci commit luci
/etc/init.d/uhttpd restart
```

## Vantage 1.1.1-r1

预装主题、仪表盘和两者的简体中文包。四个 APK 原样取自
[Vantage v1.1.1 上游发行版及对应源码](https://github.com/anothaDev/luci-theme-vantage/releases/tag/v1.1.1)
（GPL-3.0），构建前按 `VANTAGE-SHA256SUMS` 校验。更新时一起替换四个 APK 和校验清单。

## luci-theme-footstrap 0.14.20-r1

| 项 | 值 |
| --- | --- |
| 上游 | https://github.com/VizzleTF/luci-theme-footstrap |
| 版本 | v0.14.20（2026-11-02） |
| 资产 | `luci-theme-footstrap-0.14.20-r1.apk`（Release 原样，62,906 字节） |
| SHA-256 | `0001e17083aacc589da195453602ae99c965c8c2c42cc4283dd37c6004494486` |
| 许可 | Apache-2.0 |
| 要求 | OpenWrt 24.10.3+（本仓库为 25.12.6） |

升级方式：从上游新 Release 取同名 `.apk`，替换本目录文件，并同步更新上面的版本与
SHA-256；Footstrap 的哈希用于手动核对，替换后建议在构建日志里核对
`Themes` 一行与镜像内 `apk list --installed | grep footstrap` 的版本。

上游同时提供 `.ipk`（供 OpenWrt 24.10 及更早的 opkg）；本仓库只用 `.apk`。
