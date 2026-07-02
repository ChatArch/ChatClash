<div align="center">
    <a href="https://pypi.python.org/pypi/chatclash">
        <img src="https://img.shields.io/pypi/v/chatclash.svg" alt="PyPI version" />
    </a>
    <a href="https://github.com/OWNER/REPO/actions/workflows/ci.yml">
        <img src="https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg" alt="Tests" />
    </a>
    <a href="https://OWNER.github.io/REPO">
        <img src="https://img.shields.io/badge/docs-mkdocs-blue.svg" alt="Documentation" />
    </a>
</div>

<div align="center">

[English](README.en.md) | [简体中文](README.md)
</div>

# chatclash

ChatArch proxy toolkit for Clash, subconverter, and proxy service operations.

## 快速开始

```bash
pip install -e ".[dev]"
chatclash init
chatclash subscription set -i
chatclash mihomo install --daemon
chatclash subscription update
chatclash mihomo start
chatclash status
chatclash check proxy
chatclash check ip
```

常用维护命令：

```bash
chatclash subscription status
chatclash subscription update
chatclash mihomo update
chatclash mihomo restart
chatclash mihomo logs
chatclash proxy show
eval "$(chatclash proxy env)"
python -m pytest -q
```

## CLI 规范

项目依赖 `chatstyle>=0.1.0` 和 `chatenv>=0.1.1`，命令输入优先使用：

- `CommandSchema` / `CommandField` 描述输入。
- `add_interactive_option()` 提供统一 `-i/-I`。
- `resolve_command_inputs()` 统一缺参补问、默认值、TTY 与校验。

## 目录结构

- `src/`：包源码
- `tests/code-tests/`：代码测试和历史测试迁移
- `tests/cli-tests/`：真实 CLI 测试，doc-first
- `tests/mock-cli-tests/`：mock/fake CLI 测试，doc-first
- `docs/`：长期维护文档，由 mkdocs 构建

## 开发说明

扩展脚手架前，先阅读 `DEVELOP.md` 和 `AGENTS.md`。
