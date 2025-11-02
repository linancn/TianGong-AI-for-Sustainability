#!/bin/bash

# TianGong AI for Sustainability - One-Click Setup Script for Ubuntu
# 
# This script automates the installation of all dependencies and project setup
# on Ubuntu. It guides you through optional components with prompts.
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

# Parse command line arguments
INSTALL_MODE="interactive"
INSTALL_PDF=false
INSTALL_CHARTS=false
INSTALL_CARBON=false
PDF_INSTALL_PERFORMED=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --full)
            INSTALL_MODE="full"
            INSTALL_PDF=true
            INSTALL_CHARTS=true
            INSTALL_CARBON=true
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
            INSTALL_CARBON=true
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
echo "This script will install all necessary dependencies for Ubuntu."
echo ""
echo "Installation mode: $INSTALL_MODE"
echo ""

# Check if running as root for sudo operations
if [[ $EUID -ne 0 ]]; then
    print_warning "This script will use sudo to install packages. You may be prompted for your password."
fi

# Update package manager
print_header "Step 1: Updating Package Manager"
sudo apt update
sudo apt upgrade -y
print_success "Package manager updated"

# Install core dependencies
print_header "Step 2: Installing Core Dependencies"

# Python 3.12+
print_warning "Checking Python 3.12+ installation..."
if ! command -v python3.12 &> /dev/null; then
    print_warning "Python 3.12 not found. Detecting Ubuntu version..."
    
    UBUNTU_VERSION=$(lsb_release -rs)
    if (( $(echo "$UBUNTU_VERSION >= 24.04" | bc -l) )); then
        print_warning "Installing Python 3.12 from default repository..."
        sudo apt install -y python3.12 python3.12-venv python3.12-dev
    else
        print_warning "Installing Python 3.12 from deadsnakes PPA..."
        sudo add-apt-repository -y ppa:deadsnakes/ppa
        sudo apt update
        sudo apt install -y python3.12 python3.12-venv python3.12-dev
    fi
    print_success "Python 3.12 installed"
else
    print_success "Python 3.12 already installed: $(python3.12 --version)"
fi

# uv
if ! command -v uv &> /dev/null; then
    print_warning "uv not found. Installing via curl..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Add to PATH
    export PATH="$HOME/.cargo/bin:$PATH"
    echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
    
    print_success "uv installed"
    print_warning "Please run: source ~/.bashrc"
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
        print_warning "Installing Node.js 22 from NodeSource repository..."
        curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
        sudo apt install -y nodejs
        NODE_VERSION=$(node --version)
        NODE_MAJOR=$(echo "$NODE_VERSION" | sed 's/^v//' | cut -d. -f1)
        if [ "$NODE_MAJOR" -ge 22 ]; then
            print_success "Node.js installed: $NODE_VERSION"
        else
            print_error "Node.js installation did not reach version 22+. Please review the NodeSource output."
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
            sudo apt install -y pandoc
            PANDOC_PRESENT=true
            PANDOC_VERSION_STR=$(pandoc --version | head -1)
            PANDOC_OK=true
            print_success "Pandoc ready: $PANDOC_VERSION_STR"
        fi

        if [ "$PDFLATEX_PRESENT" != true ]; then
            print_warning "Installing TeX Live..."
            echo ""
            echo "Choose installation size:"
            echo "1) Full TeX Live (≈1 GB, feature-complete) - recommended"
            echo "2) Minimal TeX Live (≈300 MB, lightweight)"
            echo ""
            read -p "Enter choice (1 or 2): " latex_choice

            if [ "$latex_choice" = "2" ]; then
                print_warning "Installing minimal TeX Live packages..."
                sudo apt install -y texlive-latex-base texlive-latex-extra texlive-fonts-recommended texlive-fonts-extra
            else
                print_warning "Installing full TeX Live (this may take a few minutes)..."
                sudo apt install -y texlive-full
            fi

            print_success "LaTeX installed"
            PDFLATEX_PRESENT=true
            PDFLATEX_VERSION_STR=$(pdflatex --version 2>&1 | head -1)
        fi
    fi
fi

# Optional: grid-intensity CLI (for carbon metrics)
if [ "$INSTALL_MODE" != "minimal" ]; then
    if [ "$INSTALL_MODE" = "interactive" ]; then
        if ask_yes_no "Install grid-intensity CLI for carbon intensity metrics?"; then
            INSTALL_CARBON=true
        fi
    fi
fi

if [ "$INSTALL_CARBON" = true ]; then
    print_header "Step 3c: Installing grid-intensity CLI"
    if ! pip3 list 2>/dev/null | grep -q grid-intensity; then
        print_warning "Installing grid-intensity..."
        pip3 install grid-intensity
        print_success "grid-intensity installed"
    else
        print_success "grid-intensity already installed"
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

# Source bashrc if uv was just installed
if [ -f ~/.bashrc ]; then
    source ~/.bashrc
fi

# Run uv sync
print_warning "Running 'uv sync' to install project dependencies..."
uv sync
print_success "Project dependencies installed"

# Verification
print_header "Step 5: Verification"

echo "Checking installations..."
echo ""

# Check Python
if python3.12 --version &> /dev/null; then
    print_success "Python: $(python3.12 --version)"
else
    print_error "Python 3.12 not found"
fi

# Check uv
if uv --version &> /dev/null; then
    print_success "uv: $(uv --version)"
else
    print_error "uv not found. Try: source ~/.bashrc"
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
        print_error "LaTeX not found"
    else
        print_warning "LaTeX: not found (PDF/DOCX export disabled)"
    fi
fi

if [ "$INSTALL_CARBON" = true ]; then
    if grid-intensity --help &> /dev/null 2>&1; then
        print_success "grid-intensity: installed"
    else
        print_error "grid-intensity not accessible"
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
