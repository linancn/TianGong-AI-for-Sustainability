#!/bin/bash

# TianGong AI for Sustainability - One-Click Setup Script for macOS
# 
# This script automates the installation of all dependencies and project setup
# on macOS. It guides you through optional components with prompts.
#
# Usage: bash install.sh [--full] [--minimal] [--with-pdf] [--with-charts] [--with-carbon]
#

set -e

# Color definitions for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

ask_yes_no() {
    local prompt="$1"
    local response
    read -p "$(echo -e ${YELLOW}$prompt${NC}) (y/n): " response
    [[ "$response" =~ ^[Yy]$ ]]
}

UV_OPTIONAL_GROUPS_SELECTED=()

add_uv_group() {
    local group="$1"
    for existing in "${UV_OPTIONAL_GROUPS_SELECTED[@]}"; do
        if [ "$existing" = "$group" ]; then
            return
        fi
    done
    UV_OPTIONAL_GROUPS_SELECTED+=("$group")
}

describe_uv_group() {
    case "$1" in
        "3rd")
            echo "Third-party research libraries (uk-grid-intensity CLI for carbon metrics)"
            ;;
        *)
            echo "Optional dependency group '$1'"
            ;;
    esac
}

group_selected() {
    local target="$1"
    for existing in "${UV_OPTIONAL_GROUPS_SELECTED[@]}"; do
        if [ "$existing" = "$target" ]; then
            return 0
        fi
    done
    return 1
}

# Parse command line arguments
INSTALL_MODE="interactive"
INSTALL_PDF=false
INSTALL_CHARTS=false
PDF_INSTALL_PERFORMED=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --full)
            INSTALL_MODE="full"
            INSTALL_PDF=true
            INSTALL_CHARTS=true
            add_uv_group "3rd"
            shift
            ;;
        --minimal)
            INSTALL_MODE="minimal"
            shift
            ;;
        --with-pdf)
            INSTALL_PDF=true
            shift
            ;;
        --with-charts)
            INSTALL_CHARTS=true
            shift
            ;;
        --with-carbon)
            add_uv_group "3rd"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Welcome message
print_header "Welcome to TianGong AI for Sustainability Setup"
echo "This script will install all necessary dependencies for macOS."
echo ""
echo "Installation mode: $INSTALL_MODE"
echo ""

# Check if Homebrew is installed
print_header "Step 1: Checking Homebrew Installation"
if ! command -v brew &> /dev/null; then
    print_warning "Homebrew not found. Installing..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    print_success "Homebrew installed"
else
    print_success "Homebrew is already installed"
fi

# Install core dependencies
print_header "Step 2: Installing Core Dependencies"

# Python 3.12+
if ! command -v python3 &> /dev/null || [[ $(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1) < "3.12" ]]; then
    print_warning "Python 3.12+ not found. Installing..."
    brew install python@3.12
    print_success "Python 3.12 installed"
else
    print_success "Python 3.12+ already installed: $(python3 --version)"
fi

# uv
if ! command -v uv &> /dev/null; then
    print_warning "uv not found. Installing..."
    brew install uv
    print_success "uv installed"
else
    print_success "uv already installed: $(uv --version)"
fi

# Optional: Node.js 22+ (for charts)
NODE_VERSION=""
NODE_MAJOR=0
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    NODE_MAJOR=$(echo "$NODE_VERSION" | sed 's/^v//' | cut -d. -f1)
fi

print_header "Step 3a: Node.js for Chart Workflows"
if [ "$NODE_MAJOR" -ge 22 ]; then
    print_success "Node.js already installed: $NODE_VERSION"
else
    if [ -n "$NODE_VERSION" ]; then
        print_warning "Detected Node.js $NODE_VERSION (<22). Chart workflows require Node.js 22+."
    else
        print_warning "Node.js not found. Chart workflows require Node.js 22+."
    fi

    if [ "$INSTALL_MODE" = "full" ] && [ "$INSTALL_CHARTS" != true ]; then
        INSTALL_CHARTS=true
    fi

    if [ "$INSTALL_MODE" = "interactive" ] && [ "$INSTALL_CHARTS" != true ]; then
        if ask_yes_no "Install or upgrade Node.js to version 22+ now?"; then
            INSTALL_CHARTS=true
        else
            print_warning "Skipping Node.js installation. AntV chart features will remain disabled until Node.js 22+ is available."
        fi
    fi
fi

if [ "$INSTALL_CHARTS" = true ]; then
    if [ "$NODE_MAJOR" -ge 22 ]; then
        print_success "Node.js already meets the requirement. No installation needed."
    else
        print_warning "Installing Node.js 22+ via Homebrew..."
        brew install node@22
        NODE_VERSION=$(node --version)
        NODE_MAJOR=$(echo "$NODE_VERSION" | sed 's/^v//' | cut -d. -f1)
        if [ "$NODE_MAJOR" -ge 22 ]; then
            print_success "Node.js installed: $NODE_VERSION"
        else
            print_error "Node.js installation did not reach version 22+. Please check Homebrew logs."
        fi
    fi
fi

# Optional: Pandoc & LaTeX (for PDF/DOCX)
if [ "$INSTALL_MODE" != "minimal" ] || [ "$INSTALL_PDF" = true ]; then
    PANDOC_PRESENT=false
    PANDOC_OK=false
    PANDOC_VERSION_STR=""
    PANDOC_VERSION_NUM=""
    if command -v pandoc &> /dev/null; then
        PANDOC_PRESENT=true
        PANDOC_VERSION_STR=$(pandoc --version | head -1)
        PANDOC_VERSION_NUM=$(echo "$PANDOC_VERSION_STR" | grep -Eo '[0-9]+\.[0-9]+(\.[0-9]+)?' | head -1)
        PANDOC_MAJOR=$(echo "$PANDOC_VERSION_NUM" | cut -d. -f1)
        if [ "${PANDOC_MAJOR:-0}" -ge 3 ]; then
            PANDOC_OK=true
        fi
    fi

    PDFLATEX_PRESENT=false
    PDFLATEX_VERSION_STR=""
    if command -v pdflatex &> /dev/null; then
        PDFLATEX_PRESENT=true
        PDFLATEX_VERSION_STR=$(pdflatex --version 2>&1 | head -1)
    fi

    PDF_READY=false
    if [ "$PANDOC_OK" = true ] && [ "$PDFLATEX_PRESENT" = true ]; then
        PDF_READY=true
    fi

    print_header "Step 3b: Pandoc & LaTeX"

    if [ "$PANDOC_PRESENT" = true ]; then
        if [ "$PANDOC_OK" = true ]; then
            print_success "Pandoc already installed: $PANDOC_VERSION_STR"
        else
            print_warning "Pandoc detected but version < 3.0: $PANDOC_VERSION_STR"
        fi
    else
        print_warning "Pandoc not found."
    fi

    if [ "$PDFLATEX_PRESENT" = true ]; then
        print_success "LaTeX already installed: $PDFLATEX_VERSION_STR"
    else
        print_warning "LaTeX not found."
    fi

    if [ "$PDF_READY" = true ] && [ "$INSTALL_PDF" != true ]; then
        print_success "PDF/DOCX export requirements already satisfied."
    else
        if [ "$INSTALL_MODE" = "interactive" ] && [ "$INSTALL_PDF" != true ]; then
            if ask_yes_no "Install Pandoc + LaTeX for PDF/DOCX report export?"; then
                INSTALL_PDF=true
            else
                print_warning "Skipping Pandoc/LaTeX installation. PDF export will remain disabled."
            fi
        fi
    fi

    if [ "$INSTALL_PDF" = true ]; then
        PDF_INSTALL_PERFORMED=true

        if [ "$PANDOC_OK" != true ]; then
            print_warning "Installing or upgrading Pandoc..."
            brew install pandoc
            PANDOC_PRESENT=true
            PANDOC_VERSION_STR=$(pandoc --version | head -1)
            PANDOC_OK=true
            print_success "Pandoc ready: $PANDOC_VERSION_STR"
        fi

        if [ "$PDFLATEX_PRESENT" != true ]; then
            print_warning "Installing BasicTeX (lightweight LaTeX)..."
            echo ""
            echo "⚠  Note: Installation may take a few minutes..."
            echo ""
            brew install basictex
            export PATH="/Library/TeX/texbin:$PATH"
            if ! grep -q '/Library/TeX/texbin' ~/.zshrc 2>/dev/null; then
                echo 'export PATH="/Library/TeX/texbin:$PATH"' >> ~/.zshrc
            fi
            print_success "BasicTeX installed"
            print_warning "Run 'source ~/.zshrc' or restart your terminal to refresh PATH."
            PDFLATEX_PRESENT=true
            PDFLATEX_VERSION_STR=$(pdflatex --version 2>&1 | head -1)
        fi
    fi
fi

# Optional: third-party research libraries (uv groups)
if [ "$INSTALL_MODE" != "minimal" ] || group_selected "3rd"; then
    GROUP_DESC="$(describe_uv_group "3rd")"
    print_header "Step 3c: Third-Party Research Libraries"
    if [ "$INSTALL_MODE" = "interactive" ] && ! group_selected "3rd"; then
        if ask_yes_no "Install optional third-party packages via uv? (${GROUP_DESC})"; then
            add_uv_group "3rd"
        else
            print_warning "Skipping optional third-party packages. You can install them later with: uv sync --group 3rd"
        fi
    fi

    if group_selected "3rd"; then
        print_success "uv dependency group '3rd' scheduled (${GROUP_DESC})."
    fi
fi

# Project setup
print_header "Step 4: Setting up TianGong Project"

# Check if we're in the project directory
if [ ! -f "pyproject.toml" ]; then
    print_warning "pyproject.toml not found. Cloning repository..."
    git clone https://github.com/linancn/TianGong-AI-for-Sustainability.git
    cd TianGong-AI-for-Sustainability
fi

# Run uv sync (include optional groups if selected)
UV_SYNC_CMD=("uv" "sync")
if [ "${#UV_OPTIONAL_GROUPS_SELECTED[@]}" -gt 0 ]; then
    for group in "${UV_OPTIONAL_GROUPS_SELECTED[@]}"; do
        UV_SYNC_CMD+=("--group" "$group")
    done
    CMD_DISPLAY=$(printf "%q " "${UV_SYNC_CMD[@]}")
    print_warning "Running '${CMD_DISPLAY}' to install project dependencies..."
else
    print_warning "Running 'uv sync' to install project dependencies..."
fi
"${UV_SYNC_CMD[@]}"
print_success "Project dependencies installed"

if [ "${#UV_OPTIONAL_GROUPS_SELECTED[@]}" -gt 0 ]; then
    mkdir -p .tiangong
    GROUP_FILE=".tiangong/uv-groups.selected"
    printf "%s\n" "${UV_OPTIONAL_GROUPS_SELECTED[@]}" | sort -u > "$GROUP_FILE"
    print_success "Optional uv groups recorded in $GROUP_FILE (reapply with 'uv sync --group <name>')."
fi

# Verification
print_header "Step 5: Verification"

echo "Checking installations..."
echo ""

# Check Python
if python3 --version &> /dev/null; then
    print_success "Python: $(python3 --version)"
else
    print_error "Python not found"
fi

# Check uv
if uv --version &> /dev/null; then
    print_success "uv: $(uv --version)"
else
    print_error "uv not found"
fi

# Check CLI
if uv run tiangong-research --help &> /dev/null; then
    print_success "TianGong CLI: accessible (run 'uv run tiangong-research --help')"
else
    print_error "TianGong CLI not accessible"
fi

# Check optional components
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    NODE_MAJOR=$(echo "$NODE_VERSION" | sed 's/^v//' | cut -d. -f1)
    if [ "$NODE_MAJOR" -ge 22 ]; then
        print_success "Node.js: $NODE_VERSION"
    else
        print_warning "Node.js: $NODE_VERSION (upgrade to >=22 for chart workflows)"
    fi
else
    print_warning "Node.js: not found (chart workflows disabled)"
fi

if pandoc --version &> /dev/null; then
    print_success "Pandoc: $(pandoc --version | head -1)"
else
    if [ "$PDF_INSTALL_PERFORMED" = true ]; then
        print_error "Pandoc not found (installation may have failed)"
    else
        print_warning "Pandoc: not found (PDF/DOCX export disabled)"
    fi
fi

if pdflatex --version &> /dev/null; then
    print_success "LaTeX: $(pdflatex --version 2>&1 | head -1)"
else
    if [ "$PDF_INSTALL_PERFORMED" = true ]; then
        print_warning "LaTeX not in PATH. Run: source ~/.zshrc"
    else
        print_warning "LaTeX: not found (PDF/DOCX export disabled)"
    fi
fi

if group_selected "3rd"; then
    if uv run --group 3rd uk-grid-intensity --help &> /dev/null; then
        print_success "uk-grid-intensity CLI (via uv run): available"
    else
        print_error "uk-grid-intensity not accessible via uv run. Re-run 'uv sync --group 3rd' or check installation."
    fi
fi

echo ""

# Final summary
print_header "Setup Complete! 🎉"

echo "Next steps:"
echo ""
echo "1. Test the CLI:"
printf "   %buv run tiangong-research --help%b\n" "$BLUE" "$NC"
echo ""
echo "2. List available data sources:"
printf "   %buv run tiangong-research sources list%b\n" "$BLUE" "$NC"
echo ""
echo "3. Run a simple workflow:"
printf "   %buv run tiangong-research research workflow simple --topic \"life cycle assessment\"%b\n" "$BLUE" "$NC"
echo ""
echo "4. For more details, read:"
printf "   %bREADME.md%b - User guide\n" "$BLUE" "$NC"
printf "   %bSETUP_GUIDE.md%b - Detailed installation guide\n" "$BLUE" "$NC"
printf "   %bspecs/architecture.md%b - Technical architecture\n" "$BLUE" "$NC"
echo ""

if [ "$INSTALL_MODE" = "interactive" ]; then
    if ask_yes_no "Would you like to run the CLI help now?"; then
        uv run tiangong-research --help
    fi
fi
