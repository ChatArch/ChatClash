# chatclash 文档

`chatclash` 第一阶段提供 Clash/Yacd compose 目录生成、subconverter 订阅转换、状态摘要和 shell 代理环境变量输出。

## 常用命令

```bash
chatclash setup clash /tmp/clash -y
chatclash status /tmp/clash
chatclash proxy env

chatclash sub status
chatclash sub url
chatclash sub generate -o /tmp/clash/config.yaml --dry-run
```

详细 CLI 设计见：[cli-design.md](cli-design.md)。

## 本地预览

```bash
pip install -e ".[docs]"
mkdocs serve
```

英文版见：[index.en.md](index.en.md)。
