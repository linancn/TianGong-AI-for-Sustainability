# TianGong 可持续发展研究 CLI

欢迎使用 TianGong 可持续发展研究命令行工具。本说明面向第一次接触本项目的用户，帮助您快速完成安装、验证环境并运行首个工作流。

## 一键启动

1. 打开终端，进入项目目录：
   ```bash
   cd /path/to/TianGong-AI-for-Sustainability
   ```
2. 根据操作系统执行安装脚本。

### macOS

```bash
bash install_macos.sh
```

### Ubuntu / Debian

```bash
bash install_ubuntu.sh
```

脚本会提供交互式提示，可直接回车接受默认配置，也可以按需选择可选功能。如果想跳过提问：

- 全量安装：`bash install_<os>.sh --full`
- 仅核心组件：`bash install_<os>.sh --minimal`
- 指定功能：`bash install_<os>.sh --with-charts --with-pdf --with-carbon`

## 脚本会检查什么？

- Python 3.12+ 与 [uv](https://docs.astral.sh/uv/) 包管理器
- Git 以及项目依赖（`uv sync`）
- 按需安装的可选工具：
  - AntV 图表流程所需的 Node.js 22+（脚本会检测已有版本并给出安装/升级建议）
  - PDF/DOCX 导出所需的 Pandoc 3+ 与 LaTeX
  - 碳强度查询所需的 `grid-intensity` CLI

安装结束后会给出总结，告诉您哪些组件已就绪、哪些仍需处理。

## 安装完成后

推荐始终通过 `uv run` 在受管环境中运行 CLI：

```bash
uv run tiangong-research --help
uv run tiangong-research sources list
uv run tiangong-research sources verify un_sdg_api
uv run tiangong-research research workflow simple --topic "生命周期评估"
```

需要图表输出时，请先启动 AntV MCP 图表服务器，再在工作流命令中加上 `--chart-output visuals/snapshot.png`。

### 可选功能自检

- 图表：`node --version`，以及 `npx -y @antv/mcp-server-chart --transport streamable --version`
- PDF 导出：`pandoc --version`，`pdflatex --version`
- 碳强度：`uv run grid-intensity --help`

如缺少任何命令，可携带对应 `--with-*` 选项重新运行安装脚本，或参考脚本输出的指引手动安装。

## 手动安装（可选）

如果您倾向自己配置环境：

1. 安装 Python 3.12+、Git 与 uv。
2. （推荐）使用 Python 3.12 创建虚拟环境。
3. 在项目根目录执行：
   ```bash
   uv sync
   ```
4. 使用 `uv run tiangong-research ...` 运行 CLI。

macOS 与 Ubuntu 的详细排障说明见 `SETUP_GUIDE_CN.md`（中文）与 `SETUP_GUIDE.md`（英文）。

## 常用命令速查

- `uv run tiangong-research sources list` — 查看数据源注册表。
- `uv run tiangong-research sources verify <id>` — 检查特定数据源的连通性与配置。
- `uv run tiangong-research research find-code "<主题>" --limit 5 --json` — 搜索可持续性相关的开源代码仓库。
- `uv run tiangong-research research map-sdg <文件>` — 调用 OSDG API 将文本映射到 SDG 目标（需配置可用的 OSDG 端点或令牌）。
- `uv run tiangong-research research get-carbon-intensity <地区>` — 通过 `uv sync --group 3rd` 安装的 `grid-intensity` CLI 获取碳强度指标。
- `uv run tiangong-research research visuals verify` — 检查 AntV MCP 图表服务器是否可连通。

## 获取更多帮助

- **详细安装指南**：`SETUP_GUIDE_CN.md`、`SETUP_GUIDE.md`
- **技术架构说明**：`specs/architecture.md`
- **自动化代理手册**：`AGENTS_CN.md`
- **提示模版**：`specs/prompts/`

当可选依赖暂不可用时，CLI 会自动降级（例如缺少图表时输出文本结果）。如需外部 API，请确保在环境变量或 `.secrets/secrets.toml` 中配置好相关密钥。
