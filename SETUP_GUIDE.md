# System Setup Guide — Ubuntu & macOS

Complete platform-specific setup instructions for TianGong AI for Sustainability.

## Table of Contents

- [Quick Start](#quick-start)
- [macOS Setup](#macos-setup)
- [Ubuntu Setup](#ubuntu-setup)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

| Component | Purpose | Required? | Notes |
|-----------|---------|-----------|-------|
| Python 3.12+ | Core runtime | ✅ Yes | Managed by `uv` |
| `uv` | Package manager | ✅ Yes | Modern Python packaging |
| Node.js 22+ | Chart visualization | ⭐ Optional | Only for AntV MCP charts |
| Pandoc 3.0+ | Report export | ⭐ Optional | For PDF/DOCX output |
| LaTeX (TeX Live) | PDF generation | ⭐ Optional | Only if Pandoc + PDF needed |
| `grid-intensity` CLI | Carbon metrics | ⭐ Optional | For grid carbon queries |

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

### 4. Optional: grid-intensity CLI (for carbon metrics)

```bash
pip3 install grid-intensity
```

Verify installation:

```bash
grid-intensity --help
```

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

### 4. Optional: grid-intensity CLI (for carbon metrics)

```bash
pip3 install grid-intensity
```

Verify installation:

```bash
grid-intensity --help
```

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

# Check grid-intensity (if installed)
grid-intensity --help

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

#### Problem: `grid-intensity` not found in PATH

**Solution:**

```bash
# Ensure installed
pip3 install grid-intensity

# Verify installation location
which grid-intensity

# Add to PATH if needed
export PATH="$HOME/.local/bin:$PATH"
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
| `grid-intensity` | pip3 | pip3 | Same for both |

---

## Next Steps

After successful setup:

1. **Run the test suite**: `uv run pytest`
2. **Try a simple workflow**: `uv run tiangong-research research workflow simple --topic "life cycle assessment"`
3. **Explore data sources**: `uv run tiangong-research sources list`
4. **Read the CLI reference**: `uv run tiangong-research --help`

For advanced topics, see:

- `specs/architecture.md` — Technical architecture
- `AGENTS.md` — AI automation playbook
- `tasks/blueprint.yaml` — Development task graph
