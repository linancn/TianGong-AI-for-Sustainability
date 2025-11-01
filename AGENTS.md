# TianGong AI for Sustainability

This repository follows the Tiangong LCA Spec Coding project configuration pattern while providing a clean slate for new automation workflows. Install dependencies with `uv sync` and run development tooling via `uv run` when adding new code.

## 质量保障与自检
- 如果某次的修改涉及 Python 源代码，需在结束后按序执行：
  ```bash
  uv run black .
  uv run ruff check
  uv run python -m compileall src scripts
  uv run pytest
