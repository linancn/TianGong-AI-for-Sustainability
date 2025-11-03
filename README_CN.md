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
uv run tiangong-research sources verify un_sdg_api
uv run tiangong-research research workflow simple --topic "生命周期评估"
```

若启用了图表功能，请先启动 AntV MCP 图表服务器，再运行带 `--chart-output` 的工作流。

### 可选功能自检

- 图表：`node --version`、`npx -y @antv/mcp-server-chart --transport streamable --version`
- PDF 导出：`pandoc --version`、`pdflatex --version`
- 碳强度：`uv run --group 3rd uk-grid-intensity --help`

缺少某项功能时，重新运行对应的安装脚本（`install_macos.sh`、`install_ubuntu.sh`、`install_windows.ps1`），并选择合适的 `--with-*` 选项即可。

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

- CLI 提供全局参数 `--prompt-template`、`--prompt-language`、`--prompt-variable key=value`，用于选择驱动 LLM 综合分析的 Markdown 模版（适用于 Deep Research 与 `research synthesize`）。
- 内置别名包括 `default`（英文）与 `default-cn`（中文），也可传入仓库相对或绝对路径以加载自定义模版。
- 模版支持 `{{topic}}` 等占位符，可多次使用 `--prompt-variable` 按键值对替换内容。
- 示例：
  ```bash
  uv run tiangong-research --prompt-template default-cn --prompt-variable topic="城市气候韧性" research workflow lca-deep-report --years 3
  ```
- 若仅需一次性覆盖，可继续使用 `--deep-prompt` 与 `--deep-instructions`；当未提供指令时，CLI 会自动回退至模版机制。

## 需要更专业的控制？

如果你希望自行管理 Python 环境、在特殊平台部署，或需要详细排障说明，请阅读：

- `SETUP_GUIDE.md`（英文）
- `SETUP_GUIDE_CN.md`（中文）

大多数用户直接运行 `install_macos.sh`、`install_ubuntu.sh` 或 `install_windows.ps1`，即可完成安装、更新与可选功能管理。

## 其他资源

- 技术架构总览 — `AGENTS_CN.md`（架构蓝图）
- 自动化代理手册 — `AGENTS_CN.md`
- 提示模板 — `specs/prompts/`

可选组件缺失时，工作流会自动降级（例如无图表时输出纯文本）。如需访问受限数据源，请将所需密钥配置在环境变量或 `.secrets/secrets.toml` 文件中。
