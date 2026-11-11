# 额外 LuCI 主题（随固件构建一并安装）

这里放**不在 OpenWrt 官方 feed 里、又希望每次构建都带上**的 LuCI 主题包。
`openwrt/build-rootfs.sh` 会把这些 `.apk` 复制进构建工作区，并在安装 Argon 的同一批
`apk add --allow-untrusted` 里装进镜像（构建日志会打印 `themes: ...` 一行）。

主题只是多一个可选项：**默认主题不变**（本仓库仍由 Argon 主题包自己的 uci-defaults 决定），
装上的主题在 LuCI 的「系统 → 系统 → 语言和样式 → 设计」里切换，或用：

```sh
uci set luci.main.mediaurlbase='/luci-static/footstrap'
uci commit luci
/etc/init.d/uhttpd restart
```

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
SHA-256；`build-rootfs.sh` 不校验这里的哈希，替换后建议在构建日志里核对
`Themes` 一行与镜像内 `apk list --installed | grep footstrap` 的版本。

上游同时提供 `.ipk`（供 OpenWrt 24.10 及更早的 opkg）；本仓库只用 `.apk`。
