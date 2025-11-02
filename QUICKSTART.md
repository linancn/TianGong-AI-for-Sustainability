# Quick Start Guide — One-Click Setup

Get TianGong AI for Sustainability running in minutes!

## For Complete Beginners 👶

### macOS

1. **Open Terminal** and navigate to the project folder:
   ```bash
   cd /path/to/TianGong-AI-for-Sustainability
   ```

2. **Run the setup script:**
   ```bash
   bash install_macos.sh
   ```

3. **Follow the prompts** — the script will ask which optional features you want:
   - Charts (Node.js) ✓
   - PDF/DOCX export (Pandoc + LaTeX) ✓
   - Carbon metrics (grid-intensity) ✓

4. **That's it!** Once complete, test with:
   ```bash
   uv run tiangong-research --help
   ```

### Ubuntu/Debian

1. **Open Terminal** and navigate to the project folder:
   ```bash
   cd /path/to/TianGong-AI-for-Sustainability
   ```

2. **Run the setup script:**
   ```bash
   bash install_ubuntu.sh
   ```

3. **Follow the prompts** — the script will ask which optional features you want.

4. **That's it!** Once complete, test with:
   ```bash
   uv run tiangong-research --help
   ```

## For Advanced Users 🚀

### Pre-configured Setups

**macOS — Full Installation (all features):**
```bash
bash install_macos.sh --full
```

**macOS — Minimal (core only, no optional dependencies):**
```bash
bash install_macos.sh --minimal
```

**macOS — With Specific Features:**
```bash
bash install_macos.sh --with-pdf --with-charts --with-carbon
```

**Ubuntu — Full Installation:**
```bash
bash install_ubuntu.sh --full
```

**Ubuntu — Minimal:**
```bash
bash install_ubuntu.sh --minimal
```

**Ubuntu — With Specific Features:**
```bash
bash install_ubuntu.sh --with-pdf --with-charts --with-carbon
```

## What the Script Does ✓

1. ✅ Installs Python 3.12+ (if needed)
2. ✅ Installs `uv` package manager
3. ✅ Optionally installs Node.js, Pandoc, LaTeX
4. ✅ Clones the repository (if needed)
5. ✅ Runs `uv sync` to install project dependencies
6. ✅ Verifies all components are working
7. ✅ Provides next steps for using the CLI

## What to Do Next

Once setup is complete:

### 1. List Available Data Sources
```bash
uv run tiangong-research sources list
```

### 2. Test a Specific Data Source
```bash
uv run tiangong-research sources verify un_sdg_api
```

### 3. Run Your First Workflow
```bash
uv run tiangong-research research workflow simple --topic "life cycle assessment"
```

### 4. Generate a Report (if PDF support installed)
```bash
# Generate Markdown report
uv run tiangong-research research workflow simple \
  --topic "sustainable energy" \
  --report-output reports/output.md

# Convert to PDF with Pandoc
pandoc reports/output.md -o reports/output.pdf
```

## Troubleshooting

### "Command not found" after installation

**macOS:**
```bash
source ~/.zshrc
```

**Ubuntu:**
```bash
source ~/.bashrc
```

### Script permissions error

```bash
chmod +x install_macos.sh
# or
chmod +x install_ubuntu.sh
```

### Want to see what the script does?

You can review the installation script before running:
- **macOS**: `cat install_macos.sh`
- **Ubuntu**: `cat install_ubuntu.sh`

## Manual Installation

If you prefer not to use the automated script, follow the [detailed setup guide](./SETUP_GUIDE.md).

## Getting Help

- 📖 **User Guide**: [README.md](./README.md)
- 🔧 **Detailed Setup**: [SETUP_GUIDE.md](./SETUP_GUIDE.md)
- 🏗️ **Architecture**: [specs/architecture.md](./specs/architecture.md)
- 🤖 **For AI Agents**: [AGENTS.md](./AGENTS.md)
