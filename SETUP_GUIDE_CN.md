# 系统配置指南 — macOS、Ubuntu 与 Windows

> **适用对象提示：** 本指南适合需要手动管理依赖或在定制环境部署的专业用户。如果只想快速使用 CLI，请直接运行项目根目录的 `install_macos.sh`、`install_ubuntu.sh` 或 `install_windows.ps1`，并按照 README 的简单步骤操作。

## 目录

- [快速开始](#快速开始)
- [macOS 配置](#macos-配置)
- [Ubuntu 配置](#ubuntu-配置)
- [Windows 配置](#windows-配置)
- [验证](#验证)
- [故障排除](#故障排除)

---

## 快速开始

| 组件 | 用途 | 必需？ | 说明 |
|------|------|--------|------|
| Python 3.12+ | 核心运行时 | ✅ 必需 | 由 `uv` 管理 |
| `uv` | 包管理器 | ✅ 必需 | 现代 Python 包管理工具 |
| Chocolatey | Windows 包管理器 | ⭐ 可选 | `install_windows.ps1` 会自动安装；手动配置 Windows 时推荐 |
| Node.js 22+ | 图表可视化 | ⭐ 可选 | 仅用于 AntV MCP 图表 |
| Pandoc 3.0+ | 报告导出 | ⭐ 可选 | 用于 PDF/DOCX 输出 |
| LaTeX (TeX Live) | PDF 生成 | ⭐ 可选 | 仅当需要 Pandoc + PDF |
| `uk-grid-intensity` CLI | 碳排指标 | ⭐ 可选 | 建议执行 `uv sync --group 3rd` 安装；如需自定义可设置 `GRID_INTENSITY_CLI` |

---

## macOS 配置

### 1. 核心依赖

#### 安装 Homebrew（如果未安装）

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### 安装 Python 3.12+

```bash
brew install python@3.12
```

验证安装：

```bash
python3 --version  # 应显示 3.12 或更高版本
```

#### 安装 `uv`

```bash
brew install uv
```

或者通过 pip：

```bash
pip3 install uv
```

验证安装：

```bash
uv --version
```

### 2. 可选：Node.js（用于图表可视化）

如果计划通过 AntV MCP 图表服务器生成图表：

```bash
brew install node@22
```

验证安装：

```bash
node --version
npm --version
```

测试 AntV 服务器：

```bash
npx -y @antv/mcp-server-chart --transport streamable
# 按 Ctrl+C 停止；如果启动无误则表示配置正确
```

### 3. 可选：Pandoc 和 LaTeX（用于 PDF/DOCX 导出）

#### 安装 Pandoc

```bash
brew install pandoc
```

验证安装：

```bash
pandoc --version
```

#### 安装 LaTeX 以支持 PDF

选择以下其中一个选项：

**选项 A：完整 TeX Live（≈ 7 GB，功能完整）**

```bash
brew install --cask mactex
```

**选项 B：轻量级 BasicTeX（≈ 100 MB，最小化）**

```bash
brew install basictex
```

安装后，如果使用 BasicTeX，需添加到 PATH：

```bash
export PATH="/Library/TeX/texbin:$PATH"
```

添加到 shell 配置文件（`~/.zshrc` 或 `~/.bash_profile`）：

```bash
echo 'export PATH="/Library/TeX/texbin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

验证 LaTeX 安装：

```bash
pdflatex --version  # 应显示版本信息
```

### 4. 可选：uk-grid-intensity CLI（用于碳排指标）

推荐使用 uv 依赖组安装：

```bash
uv sync --group 3rd
```

验证 CLI：

```bash
uv run --group 3rd uk-grid-intensity --help
```

如需手动放置可执行文件，可安装上游 CLI 并设置 `GRID_INTENSITY_CLI` 环境变量指向实际命令。

### 5. 项目配置

克隆并初始化项目：

```bash
git clone https://github.com/linancn/TianGong-AI-for-Sustainability.git
cd TianGong-AI-for-Sustainability
uv sync
```

测试 CLI：

```bash
uv run tiangong-research --help
```

---

## Ubuntu 配置

### 1. 核心依赖

#### 更新包管理器

```bash
sudo apt update && sudo apt upgrade -y
```

#### 安装 Python 3.12+（如果默认仓库中无此版本）

**对于 Ubuntu 24.04 LTS (Noble) 或更新版本：**

```bash
sudo apt install -y python3.12 python3.12-venv python3.12-dev
```

**对于较旧的 Ubuntu 版本，使用 deadsnakes PPA：**

```bash
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev
```

验证安装：

```bash
python3.12 --version  # 应显示 3.12 或更高版本
```

#### 安装 `uv`

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

如果 `uv` 未自动添加到 PATH，需手动添加：

```bash
export PATH="$HOME/.cargo/bin:$PATH"
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

验证安装：

```bash
uv --version
```

### 2. 可选：Node.js 22+（用于图表可视化）

**方法 1：NodeSource 仓库（推荐）**

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
```

**方法 2：使用 `nvm`（Node 版本管理器）**

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 22
nvm use 22
```

验证安装：

```bash
node --version
npm --version
```

测试 AntV 服务器：

```bash
npx -y @antv/mcp-server-chart --transport streamable
# 按 Ctrl+C 停止；如果启动无误则表示配置正确
```

### 3. 可选：Pandoc 和 LaTeX（用于 PDF/DOCX 导出）

#### 安装 Pandoc

```bash
sudo apt install -y pandoc
```

验证安装：

```bash
pandoc --version
```

#### 安装 LaTeX 以支持 PDF

**选项 A：完整 TeX Live（≈ 1 GB）**

```bash
sudo apt install -y texlive-full
```

**选项 B：最小化安装（≈ 300 MB）**

```bash
sudo apt install -y texlive-latex-base texlive-latex-extra texlive-fonts-recommended texlive-fonts-extra
```

验证 LaTeX 安装：

```bash
pdflatex --version  # 应显示版本信息
```

### 4. 可选：uk-grid-intensity CLI（用于碳排指标）

```bash
uv sync --group 3rd
```

验证安装：

```bash
uv run --group 3rd uk-grid-intensity --help
```

若需使用其他 CLI，可单独安装并设置 `GRID_INTENSITY_CLI` 环境变量。

### 5. 项目配置

克隆并初始化项目：

```bash
git clone https://github.com/linancn/TianGong-AI-for-Sustainability.git
cd TianGong-AI-for-Sustainability
uv sync
```

测试 CLI：

```bash
uv run tiangong-research --help
```

---

## Windows 配置

> ⚠️ 安装系统级依赖或运行 `install_windows.ps1` 时，请以管理员身份打开 PowerShell：右键 PowerShell 图标，选择“以管理员身份运行”。

### 1. 核心依赖

#### 安装 Chocolatey（若尚未安装）

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
choco --version
```

#### 安装 Git

```powershell
choco install -y git
git --version
```

#### 安装 Python 3.12+

```powershell
choco install -y python312
python --version  # 期望输出 Python 3.12+
```

若执行 `python` 仍失败，可重启 PowerShell 或使用 `py -3.12`。

#### 安装 `uv`

```powershell
irm https://astral.sh/uv/install.ps1 | iex
uv --version
```

若 `uv` 未立即生效，请重新打开 PowerShell。

### 2. 可选：Node.js 22+（图表可视化）

```powershell
choco install -y nodejs --version=22.0.0
node --version  # 期望输出 v22.x
npx -y @antv/mcp-server-chart --transport streamable --version
```

已经安装旧版本 Node.js 时，请升级到 ≥22 后再启用图表工作流。

### 3. 可选：Pandoc 与 MiKTeX（PDF/DOCX 导出）

```powershell
choco install -y pandoc
choco install -y miktex
pandoc --version
pdflatex --version
```

首次启动 MiKTeX 可能弹出 GUI 并提示按需下载宏包，保持默认选项即可。

### 4. 可选：uk-grid-intensity CLI（碳排指标）

```powershell
uv sync --group 3rd
uv run --group 3rd uk-grid-intensity --help
```

若使用自定义可执行文件，请设置 `GRID_INTENSITY_CLI` 环境变量。

### 5. 项目初始化

```powershell
git clone https://github.com/linancn/TianGong-AI-for-Sustainability.git
Set-Location TianGong-AI-for-Sustainability
uv sync
```

### 6. 安装后检查

```powershell
uv run tiangong-research --help
uv run tiangong-research sources list
```

安装新工具后建议重新打开 PowerShell，以确保 PATH 更新生效。

---

## 验证

运行以下检查以确认所有组件都已正确安装：

### 基本配置

```bash
# 检查 Python
python3 --version

# 检查 uv
uv --version

# 检查项目安装
uv run tiangong-research --version
```

### 可选组件

```bash
# 检查 Node.js（如已安装）
node --version

# 检查 Pandoc（如已安装）
pandoc --version

# 检查 LaTeX（如已安装）
pdflatex --version

# 检查 uk-grid-intensity（如已安装）
uv run --group 3rd uk-grid-intensity --help

# 验证 AntV 图表服务器（如已安装 Node.js）
npx -y @antv/mcp-server-chart --transport streamable &
sleep 2
curl http://127.0.0.1:1122/mcp
kill %1
```

### 测试数据源

```bash
# 列出可用数据源
uv run tiangong-research sources list

# 验证 UN SDG API（无需凭证）
uv run tiangong-research sources verify un_sdg_api

# 验证 Semantic Scholar
uv run tiangong-research sources verify semantic_scholar
```

---

## 故障排除

### macOS

#### 问题：`command not found: uv`

**解决方案：**

```bash
# 确认 Homebrew 已安装
brew --version

# 重新安装 uv
brew reinstall uv

# 验证 PATH
echo $PATH | grep -i brew
```

#### 问题：`pdflatex: command not found`

**解决方案（如使用 BasicTeX）：**

```bash
export PATH="/Library/TeX/texbin:$PATH"
echo 'export PATH="/Library/TeX/texbin:$PATH"' >> ~/.zshrc
source ~/.zshrc
pdflatex --version
```

#### 问题：Node.js 版本不匹配

**解决方案：**

```bash
# 检查当前版本
node --version

# 如需更新
brew upgrade node@22

# 或使用 nvm 管理版本
nvm install 22
nvm use 22
```

#### 问题：导入包时出现 `ModuleNotFoundError`

**解决方案：**

```bash
# 确认 uv 已安装依赖
cd /path/to/TianGong-AI-for-Sustainability
uv sync --upgrade

# 清空缓存的虚拟环境
rm -rf .venv
uv sync
```

### Ubuntu

#### 问题：`command not found: uv`

**解决方案：**

```bash
# 验证安装是否完成
curl -LsSf https://astral.sh/uv/install.sh | sh

# 确保 PATH 已更新
export PATH="$HOME/.cargo/bin:$PATH"
source ~/.bashrc

# 验证
uv --version
```

#### 问题：Python 3.12 不可用

**解决方案（Ubuntu < 24.04）：**

```bash
# 添加 deadsnakes PPA
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev

# 验证
python3.12 --version
```

#### 问题：`pdflatex: command not found`

**解决方案：**

```bash
# 安装 TeX Live
sudo apt install -y texlive-latex-base texlive-latex-extra

# 验证
pdflatex --version
```

#### 问题：`uv sync` 时权限被拒绝

**解决方案：**

```bash
# 确认主目录权限无问题
ls -la ~ | head -n 3

# 使用详细输出重试
uv sync --verbose
```

#### 问题：Node.js 安装冲突

**解决方案：**

```bash
# 检查多个安装
which node
which npm

# 删除冲突版本
sudo apt remove -y nodejs npm

# 通过 NodeSource 清洁安装
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs

# 验证
node --version  # 应为 22.x
```

### 两个平台通用

#### 问题：`uk-grid-intensity` 命令不可用

**解决方案：**

```bash
# 重新安装可选依赖组
uv sync --group 3rd

# 使用 uv 验证命令是否可用
uv run --group 3rd uk-grid-intensity --help

# 如需自定义可执行文件，可设置环境变量
export GRID_INTENSITY_CLI=/path/to/custom/cli
```

#### 问题：运行命令时出现网络错误

**解决方案：**

```bash
# 检查网络连接
ping -c 3 8.8.8.8

# 测试 API 端点
curl -s https://api.semanticscholar.org/ | head -c 100

# 如在企业网络后，验证代理设置
echo $HTTP_PROXY
echo $HTTPS_PROXY
```

#### 问题：AntV 图表服务器无法启动

**解决方案：**

```bash
# 确认 Node.js 已安装
node --version

# 测试 AntV 包安装
npx -y @antv/mcp-server-chart --transport streamable

# 如失败，尝试全局重装
npm install -g @antv/mcp-server-chart
@antv/mcp-server-chart --transport streamable
```

---

## 平台对比

| 功能 | macOS | Ubuntu | 说明 |
|------|-------|--------|------|
| Python 3.12+ | Homebrew | apt/deadsnakes PPA | 两者都容易安装 |
| `uv` | Homebrew | curl 安装器 | macOS 上 Homebrew 更简单 |
| Node.js | Homebrew | apt/NodeSource/nvm | 两者都很直接 |
| Pandoc | Homebrew | apt | 两者官方仓库都有 |
| LaTeX | MacTeX 或 BasicTeX | TeX Live | Linux 上 TeX Live 更小 |
| `uk-grid-intensity` | uv(sync) | uv(sync) | 推荐使用 `uv sync --group 3rd` 安装 |

---

## 下一步

成功配置后：

1. **运行测试套件**：`uv run pytest`
2. **尝试简单工作流**：`uv run tiangong-research research workflow simple --topic "life cycle assessment"`
3. **浏览数据源**：`uv run tiangong-research sources list`
4. **阅读 CLI 参考**：`uv run tiangong-research --help`

如需了解更多高级主题，请参阅：

- `AGENTS_CN.md`（架构蓝图章节）— 技术架构
- `AGENTS.md` — AI 自动化手册
- `tasks/blueprint.yaml` — 开发任务图
