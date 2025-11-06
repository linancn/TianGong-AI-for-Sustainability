# TianGong 可持续发展研究 CLI

[English](https://github.com/linancn/TianGong-AI-for-Sustainability/blob/main/README.md) | 中文

本 README 面向所有用户，按照脚本提示一步步完成安装即可。无需手动配置环境，也不需要了解复杂依赖。

## 推荐做法：运行安装脚本

1. 打开终端，克隆仓库：
   ```bash
   git clone https://github.com/linancn/TianGong-AI-for-Sustainability.git
   ```
2. 进入项目目录：
   ```bash
   cd TianGong-AI-for-Sustainability
   ```
3. 根据操作系统执行脚本：

   **macOS**
   ```bash
   bash install_macos.sh
   ```

   **Ubuntu / Debian**
   ```bash
   bash install_ubuntu.sh
   ```

   **Windows（以管理员身份运行 PowerShell）**
   ```powershell
   PowerShell -ExecutionPolicy Bypass -File .\install_windows.ps1
   ```

脚本会自动检查 Python 3.12+、uv、Git 以及项目依赖，并在需要时安装可选组件：图表支持（Node.js 22+）、PDF 导出（Pandoc + LaTeX）、碳强度查询（`uk-grid-intensity`）。只需根据提示回答 **y/n**。

> **想更新或添加功能？** 直接重新运行脚本即可。也可以用 `--full`、`--minimal`、`--with-*` 等参数跳过交互。

## 安装完成后

所有命令都建议通过 `uv run` 调用，确保使用受管环境：

```bash
uv run tiangong-research --help
uv run tiangong-research sources list
uv run tiangong-research sources audit
uv run tiangong-research sources verify un_sdg_api
uv run tiangong-research research workflow simple --topic "生命周期评估"
```

若启用了图表功能，请先启动 AntV MCP 图表服务器，再运行带 `--chart-output` 的工作流。

### 可选功能自检

- 图表：`node --version`、`npx -y @antv/mcp-server-chart --transport streamable --version`
- PDF 导出：`pandoc --version`、`pdflatex --version`
- 碳强度：`uv run --group 3rd uk-grid-intensity --help`

缺少某项功能时，重新运行对应的安装脚本（`install_macos.sh`、`install_ubuntu.sh`、`install_windows.ps1`），并选择合适的 `--with-*` 选项即可。

## Codex Docker 工作流

- 使用默认参数构建镜像即可自动安装 Codex：`docker build -t tiangong-ai-codex .`（若需精简，可传入 `--build-arg INSTALL_CODEX=false`、`INSTALL_NODE=false` 等关闭对应组件）。
- 运行时请挂载仓库目录，确保 Codex 能访问项目与数据：`docker run --rm -v "$(pwd):/workspace" tiangong-ai-codex codex`。
- 自动化任务建议使用 `codex exec --json "<指令>"`；通过 `turn.completed` 事件判断成功，或在捕获 `turn.failed`/`error` 时人工介入，可配合 `--ask-for-approval never` 免去审批提示。
- 如需回到 CLI 环境，可覆盖入口：`docker run --rm --entrypoint uv tiangong-ai-codex run tiangong-research --help`。
- 持久化 Codex 会话数据时，可将卷挂载到 `/workspace/.codex`（示例：`-v codex_state:/workspace/.codex`）。

## 常用命令速查

- `uv run tiangong-research sources list` — 查看数据源注册表。
- `uv run tiangong-research sources verify <id>` — 检查指定数据源的连通性与配置。
- `uv run tiangong-research research find-code "<主题>" --limit 5 --json` — 搜索可持续性相关开源仓库。
- `uv run tiangong-research research map-sdg <文件>` — 调用 OSDG API 将文本映射到 SDG 目标（需配置可用的 OSDG 端点）。
- `uv run tiangong-research research find-papers "<关键词>" --openalex --arxiv --scopus --citation-graph --limit 10 --json` — 聚合 Semantic Scholar 与可选的 OpenAlex、本地 arXiv、Scopus 数据。
- `uv run --group 3rd tiangong-research research get-carbon-intensity <地区>` — 获取碳强度指标（如使用自定义 CLI，可设置 `GRID_INTENSITY_CLI` 环境变量）。
- `uv run tiangong-research research synthesize "<问题>" --output reports/synthesis.md` — 先收集 SDG、代码、文献与碳强度，再由 LLM 生成综合分析。 
- `uv run tiangong-research research visuals verify` — 确认 AntV MCP 图表服务器可达。

## 提示模版与 Deep Research

- CLI 提供全局参数 `--prompt-template`、`--prompt-language`（请使用 `en`）、`--prompt-variable key=value`，用于选择驱动 LLM 综合分析的 Markdown 模版（适用于 Deep Research 与 `research synthesize`）。
- 内置别名包括 `default`、`default-en`、`en`（均指向相同的英文模版）。若未指定 `--prompt-template`，CLI 会默认使用 `default`；也可传入仓库相对或绝对路径以加载自定义模版。
- `specs/prompts/default.md` 是提供给 Codex 的英文提示骨架；`specs/prompts/default_CN.md` 为人工翻译版，勿直接发送给 Codex。
- 遵循 CLI 优先原则：先运行 `uv run tiangong-research …` 子命令，只有在确认缺失对应子命令时才考虑阅读或编写 Python 代码。
- 模版支持 `{{topic}}` 等占位符，可多次使用 `--prompt-variable` 按键值对替换内容。
- 示例：
  ```bash
  uv run tiangong-research --prompt-template default --prompt-variable topic="城市气候韧性" research workflow deep-report --profile lca --years 3
  ```
- 若仅需一次性覆盖，可继续使用 `--deep-prompt` 与 `--deep-instructions`；当未提供指令时，CLI 会自动回退至模版机制。

## 内联提示组合器

- 生成一段单行提示，将 `user_prompts/ai-infra.md` 与分阶段工作流说明拼接在一起：`uv run python scripts/compose_inline_prompt.py`
- 如需自定义输入，可使用以下参数：
  - `--user-prompt path/to/file.md` 指定其他研究简报。
  - `--spec path/to/workflow.md`（`--template` 为别名）选择不同的工作流规范。
- `--output path/to/prompt.txt` 可覆盖输出文件路径（脚本仍会在标准输出回显提示内容）。
- 默认情况下脚本会在当前目录生成 `./inline_prompt.txt`，同时依然在标准输出回显单行提示，方便复制粘贴。
- 脚本会规范化空白字符，并插入过渡语句 “By following the staged workflow strictly”，确保生成的提示简洁且具可重复性。

## 需要更专业的控制？

如果你希望自行管理 Python 环境、在特殊平台部署，或需要详细排障说明，请阅读：

- `SETUP_GUIDE.md`（英文）
- `SETUP_GUIDE_CN.md`（中文）

大多数用户直接运行 `install_macos.sh`、`install_ubuntu.sh` 或 `install_windows.ps1`，即可完成安装、更新与可选功能管理。

## 其他资源

- 技术架构总览 — `AGENTS_CN.md`（架构蓝图）
- 自动化代理手册 — `AGENTS_CN.md`
- 提示模板 — `specs/prompts/default.md`（AI 使用） / `specs/prompts/default_CN.md`（人工参考）

可选组件缺失时，工作流会自动降级（例如无图表时输出纯文本）。如需访问受限数据源，请将所需密钥配置在环境变量或 `.secrets/secrets.toml` 文件中。

## Codex
```bash
# 危险操作：直接执行转换后的内联prompt（请确保已了解风险）
codex exec --dangerously-bypass-approvals-and-sandbox "$(cat specs/prompts/default.md)"
```
