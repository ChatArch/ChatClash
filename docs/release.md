# 发版

## 本地验收

在目标 Python 版本的隔离环境中执行：

```bash
python -m pytest -q
python -m pip check
chatclash --version
chatclash --tree
chatclash --tree-brief
python -m build
python -m twine check dist/*
mkdocs build --strict
git diff --check
```

构建的 wheel 必须在全新环境中安装，并回读 `--version`、`--tree`、`--tree-brief` 与 ChatEnv provider 发现。不要把源码 editable 环境当作公开安装验证。

## 发布顺序

1. 根据 PyPI、远程标签和默认分支源码选择下一个前进版本。
2. 更新版本、变更日志、测试和用户文档；先完成本地验收和独立审查。
3. 推送分支并创建 PR，只在该 PR 的精确提交检查全绿后合并。
4. 同步默认分支，确认发布标签指向合并后的默认分支提交，而非功能分支提交。
5. 按仓库既有风格创建并推送 `v<version>` 标签，等待 tag 触发的发布工作流成功。
6. 回读 PyPI 精确版本、wheel 和 sdist；从公开 PyPI 用无缓存隔离环境安装精确版本。
7. 同步 canonical checkout、确认干净状态，并在需要时用标准 ChatArch venv 安装该精确发布版本。

## 服务边界

发布 Python 包不会自动替换引擎、刷新订阅或重启 `chatclash-mihomo.service`。生产迁移要单独安排：先安装已发布版本、重新生成/校验配置，再在授权的维护窗口内显式重载或重启并验证代理。禁止把订阅、认证或生成 YAML 写入提交和发布产物。
