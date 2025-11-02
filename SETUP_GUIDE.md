# System Setup Guide — macOS, Ubuntu & Windows

> **Who should read this?** Power users who want to manage dependencies manually or adapt the CLI to bespoke environments. If you simply want to get started, run `install_macos.sh`, `install_ubuntu.sh`, or `install_windows.ps1` from the project root and follow the prompts in the README.

## Table of Contents

- [Quick Start](#quick-start)
- [macOS Setup](#macos-setup)
- [Ubuntu Setup](#ubuntu-setup)
- [Windows Setup](#windows-setup)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

| Component | Purpose | Required? | Notes |
|-----------|---------|-----------|-------|
| Python 3.12+ | Core runtime | ✅ Yes | Managed by `uv` |
| `uv` | Package manager | ✅ Yes | Modern Python packaging |
| Chocolatey | Windows package manager | ⭐ Optional | Auto-installed by `install_windows.ps1`; recommended for manual Windows setup |
| Node.js 22+ | Chart visualization | ⭐ Optional | Only for AntV MCP charts |
| Pandoc 3.0+ | Report export | ⭐ Optional | For PDF/DOCX output |
| LaTeX (TeX Live) | PDF generation | ⭐ Optional | Only if Pandoc + PDF needed |
| `uk-grid-intensity` CLI | Carbon metrics | ⭐ Optional | Install via `uv sync --group 3rd`; set `GRID_INTENSITY_CLI` to override executable |

---

## macOS Setup

### 1. Core Dependencies

#### Install Homebrew (if not already installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### Install Python 3.12+

```bash
brew install python@3.12
```

Verify installation:

```bash
python3 --version  # Should print 3.12 or later
```

#### Install `uv`

```bash
brew install uv
```

Or via pip:

```bash
pip3 install uv
```

Verify installation:

```bash
uv --version
```

### 2. Optional: Node.js (for chart visualization)

If you plan to generate charts via the AntV MCP chart server:

```bash
brew install node@22
```

Verify installation:

```bash
node --version
npm --version
```

Test the AntV server:

```bash
npx -y @antv/mcp-server-chart --transport streamable
# Ctrl+C to stop; if it launches without errors, you're good.
```

### 3. Optional: Pandoc & LaTeX (for PDF/DOCX export)

#### Install Pandoc

```bash
brew install pandoc
```

Verify installation:

```bash
pandoc --version
```

#### Install LaTeX for PDF Support

Choose one of the following:

**Option A: Full TeX Live (≈ 7 GB, feature-complete)**

```bash
brew install --cask mactex
```

**Option B: Lightweight BasicTeX (≈ 100 MB, minimal)**

```bash
brew install basictex
```

After installation, add to PATH (if using BasicTeX):

```bash
export PATH="/Library/TeX/texbin:$PATH"
```

Add to your shell profile (`~/.zshrc` or `~/.bash_profile`):

```bash
echo 'export PATH="/Library/TeX/texbin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Verify LaTeX installation:

```bash
pdflatex --version  # Should print version info
```

### 4. Optional: uk-grid-intensity CLI (for carbon metrics)

Recommended install:

```bash
uv sync --group 3rd
```

Verify availability:

```bash
uv run --group 3rd uk-grid-intensity --help
```

Need a different executable? Install it manually and point `GRID_INTENSITY_CLI` to the command path.

### 5. Project Setup

Clone and initialize:

```bash
git clone https://github.com/linancn/TianGong-AI-for-Sustainability.git
cd TianGong-AI-for-Sustainability
uv sync
```

Test CLI:

```bash
uv run tiangong-research --help
```

---

## Ubuntu Setup

### 1. Core Dependencies

#### Update package manager

```bash
sudo apt update && sudo apt upgrade -y
```

#### Install Python 3.12+ (if not available in default repos)

**For Ubuntu 24.04 LTS (Noble) or later:**

```bash
sudo apt install -y python3.12 python3.12-venv python3.12-dev
```

**For older Ubuntu versions, use deadsnakes PPA:**

```bash
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev
```

Verify installation:

```bash
python3.12 --version  # Should print 3.12 or later
```

#### Install `uv`

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Add to PATH (if not automatically added):

```bash
export PATH="$HOME/.cargo/bin:$PATH"
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Verify installation:

```bash
uv --version
```

### 2. Optional: Node.js 22+ (for chart visualization)

**Method 1: NodeSource repository (recommended)**

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
```

**Method 2: Using `nvm` (Node Version Manager)**

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 22
nvm use 22
```

Verify installation:

```bash
node --version
npm --version
```

Test the AntV server:

```bash
npx -y @antv/mcp-server-chart --transport streamable
# Ctrl+C to stop; if it launches without errors, you're good.
```

### 3. Optional: Pandoc & LaTeX (for PDF/DOCX export)

#### Install Pandoc

```bash
sudo apt install -y pandoc
```

Verify installation:

```bash
pandoc --version
```

#### Install LaTeX for PDF Support

**Option A: Full TeX Live (≈ 1 GB)**

```bash
sudo apt install -y texlive-full
```

**Option B: Minimal installation (≈ 300 MB)**

```bash
sudo apt install -y texlive-latex-base texlive-latex-extra texlive-fonts-recommended texlive-fonts-extra
```

Verify LaTeX installation:

```bash
pdflatex --version  # Should print version info
```

### 4. Optional: uk-grid-intensity CLI (for carbon metrics)

```bash
uv sync --group 3rd
```

Verify installation:

```bash
uv run --group 3rd uk-grid-intensity --help
```

If you must use a different CLI wrapper, install it manually and set `GRID_INTENSITY_CLI`.

### 5. Project Setup

Clone and initialize:

```bash
git clone https://github.com/linancn/TianGong-AI-for-Sustainability.git
cd TianGong-AI-for-Sustainability
uv sync
```

Test CLI:

```bash
uv run tiangong-research --help
```

---

## Windows Setup

> ⚠️ Open PowerShell **as Administrator** when installing system packages or running `install_windows.ps1`. Right-click the PowerShell icon and choose “Run as Administrator.”

### 1. Core Dependencies

#### Install Chocolatey (if not present)

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
choco --version
```

#### Install Git

```powershell
choco install -y git
git --version
```

#### Install Python 3.12+

```powershell
choco install -y python312
python --version  # Expect Python 3.12 or later
```

If `python` is not immediately available, restart the shell or use `py -3.12`.

#### Install `uv`

```powershell
irm https://astral.sh/uv/install.ps1 | iex
uv --version
```

Restart PowerShell if `uv` is still missing from PATH.

### 2. Optional: Node.js 22+ (chart visualization)

```powershell
choco install -y nodejs --version=22.0.0
node --version  # Expect v22.x
npx -y @antv/mcp-server-chart --transport streamable --version
```

Upgrade existing Node.js installations to >=22 before enabling chart workflows.

### 3. Optional: Pandoc & MiKTeX (PDF/DOCX export)

```powershell
choco install -y pandoc
choco install -y miktex
pandoc --version
pdflatex --version
```

MiKTeX may open a GUI installer and prompt for package downloads on first use—accept the defaults.

### 4. Optional: uk-grid-intensity CLI (carbon metrics)

```powershell
uv sync --group 3rd
uv run --group 3rd uk-grid-intensity --help
```

Set the `GRID_INTENSITY_CLI` environment variable if you rely on a custom executable.

### 5. Project Setup

```powershell
git clone https://github.com/linancn/TianGong-AI-for-Sustainability.git
Set-Location TianGong-AI-for-Sustainability
uv sync
```

### 6. Post-Install Checks

```powershell
uv run tiangong-research --help
uv run tiangong-research sources list
```

Reopen PowerShell after installing new tools so updated PATH entries apply.

---

## Verification

Run the following checks to confirm all components are properly installed:

### Basic Setup

```bash
# Check Python
python3 --version

# Check uv
uv --version

# Check project installation
uv run tiangong-research --version
```

### Optional Components

```bash
# Check Node.js (if installed)
node --version

# Check Pandoc (if installed)
pandoc --version

# Check LaTeX (if installed)
pdflatex --version

# Check uk-grid-intensity (if installed)
uv run --group 3rd uk-grid-intensity --help

# Verify AntV chart server (if Node.js installed)
npx -y @antv/mcp-server-chart --transport streamable &
sleep 2
curl http://127.0.0.1:1122/mcp
kill %1
```

### Test Data Sources

```bash
# List available data sources
uv run tiangong-research sources list

# Verify UN SDG API (no credentials needed)
uv run tiangong-research sources verify un_sdg_api

# Verify Semantic Scholar
uv run tiangong-research sources verify semantic_scholar
```

---

## Troubleshooting

### macOS

#### Problem: `command not found: uv`

**Solution:**

```bash
# Ensure Homebrew installation
brew --version

# Re-install uv
brew reinstall uv

# Verify PATH
echo $PATH | grep -i brew
```

#### Problem: `pdflatex: command not found`

**Solution (if using BasicTeX):**

```bash
export PATH="/Library/TeX/texbin:$PATH"
echo 'export PATH="/Library/TeX/texbin:$PATH"' >> ~/.zshrc
source ~/.zshrc
pdflatex --version
```

#### Problem: Node.js version mismatch

**Solution:**

```bash
# Check current version
node --version

# Update if needed
brew upgrade node@22

# Or use nvm for version management
nvm install 22
nvm use 22
```

#### Problem: `ModuleNotFoundError` when importing packages

**Solution:**

```bash
# Ensure uv has installed dependencies
cd /path/to/TianGong-AI-for-Sustainability
uv sync --upgrade

# Clear any cached environments
rm -rf .venv
uv sync
```

### Ubuntu

#### Problem: `command not found: uv`

**Solution:**

```bash
# Verify installation completed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Ensure PATH is updated
export PATH="$HOME/.cargo/bin:$PATH"
source ~/.bashrc

# Verify
uv --version
```

#### Problem: Python 3.12 not available

**Solution (Ubuntu < 24.04):**

```bash
# Add deadsnakes PPA
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev

# Verify
python3.12 --version
```

#### Problem: `pdflatex: command not found`

**Solution:**

```bash
# Install TeX Live
sudo apt install -y texlive-latex-base texlive-latex-extra

# Verify
pdflatex --version
```

#### Problem: Permission denied during `uv sync`

**Solution:**

```bash
# Ensure no permission issues with home directory
ls -la ~ | head -n 3

# Try sync again with verbose output
uv sync --verbose
```

#### Problem: Node.js installation conflicts

**Solution:**

```bash
# Check for multiple installations
which node
which npm

# Remove conflicting versions
sudo apt remove -y nodejs npm

# Install cleanly via NodeSource
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs

# Verify
node --version  # Should be 22.x
```

### Common to Both Platforms

#### Problem: `uk-grid-intensity` command unavailable

**Solution:**

```bash
# Reinstall optional dependency group
uv sync --group 3rd

# Verify the CLI via uv
uv run --group 3rd uk-grid-intensity --help

# Override the executable if using a custom binary
export GRID_INTENSITY_CLI=/path/to/custom/cli
```

#### Problem: Network errors when running commands

**Solution:**

```bash
# Check internet connectivity
ping -c 3 8.8.8.8

# Test API endpoints
curl -s https://api.semanticscholar.org/ | head -c 100

# Verify proxy settings if behind corporate network
echo $HTTP_PROXY
echo $HTTPS_PROXY
```

#### Problem: AntV chart server won't start

**Solution:**

```bash
# Ensure Node.js is installed
node --version

# Test installation of AntV package
npx -y @antv/mcp-server-chart --transport streamable

# If it fails, try reinstalling globally
npm install -g @antv/mcp-server-chart
@antv/mcp-server-chart --transport streamable
```

---

## Platform Comparison

| Feature | macOS | Ubuntu | Notes |
|---------|-------|--------|-------|
| Python 3.12+ | Homebrew | apt/deadsnakes PPA | Both easy to install |
| `uv` | Homebrew | curl installer | Homebrew is simpler on macOS |
| Node.js | Homebrew | apt/NodeSource/nvm | Both straightforward |
| Pandoc | Homebrew | apt | Both official repos have it |
| LaTeX | MacTeX or BasicTeX | TeX Live | TeX Live on Linux is smaller |
| `uk-grid-intensity` | uv(sync) | uv(sync) | Install with `uv sync --group 3rd`; use `GRID_INTENSITY_CLI` for overrides |

---

## Next Steps

After successful setup:

1. **Run the test suite**: `uv run pytest`
2. **Try a simple workflow**: `uv run tiangong-research research workflow simple --topic "life cycle assessment"`
3. **Explore data sources**: `uv run tiangong-research sources list`
4. **Read the CLI reference**: `uv run tiangong-research --help`

For advanced topics, see:

- `AGENTS.md` (Architecture Blueprint) — Technical architecture
- `AGENTS.md` — AI automation playbook
- `tasks/blueprint.yaml` — Development task graph
