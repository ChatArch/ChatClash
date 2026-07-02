# chatclash 文档

`chatclash` 是单机 Clash/Mihomo 管理工具：在哪台机器上运行，就管理这台机器上的代理服务。

## 推荐主流程

```bash
chatclash init
chatclash subscription set -i
chatclash mihomo install --daemon
chatclash subscription update
chatclash mihomo start
chatclash status
chatclash check proxy
chatclash check ip
```

## 常用命令

```bash
chatclash status
chatclash subscription status
chatclash subscription update
chatclash mihomo status
chatclash mihomo logs
chatclash proxy show
eval "$(chatclash proxy env)"
```

详细 CLI 路线见：[cli-design.md](cli-design.md)。

## 本地预览

```bash
pip install -e ".[docs]"
mkdocs serve
```

英文版见：[index.en.md](index.en.md)。
