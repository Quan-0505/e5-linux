# ubuntu:22.04 的 security 索引仍指向已下线的 perl 5.34.0-3ubuntu1.10，apt 拉取 404。
# 宿主只提供 SDK 之外的原生编译工具，升级到 24.04 不改变交叉工具链与产物 ABI。
FROM ubuntu:24.04
RUN apt-get update -o Acquire::Retries=5 \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    build-essential ca-certificates curl file gawk git gettext libncurses-dev \
    libssl-dev patch python3 python3-setuptools rsync unzip wget zstd \
    && rm -rf /var/lib/apt/lists/*
