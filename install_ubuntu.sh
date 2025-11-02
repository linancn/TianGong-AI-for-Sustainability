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
if [ "$INSTALL_MODE" != "minimal" ]; then
    if [ "$INSTALL_MODE" = "interactive" ]; then
        if ask_yes_no "Install Node.js 22+ for AntV chart visualization?"; then
            INSTALL_CHARTS=true
        fi
    fi
fi

if [ "$INSTALL_CHARTS" = true ]; then
    print_header "Step 3a: Installing Node.js 22+"
    if ! command -v node &> /dev/null || [[ $(node --version | grep -oE '[0-9]+' | head -1) -lt 22 ]]; then
        print_warning "Installing Node.js 22 from NodeSource repository..."
        curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
        sudo apt install -y nodejs
        print_success "Node.js installed: $(node --version)"
    else
        print_success "Node.js already installed: $(node --version)"
    fi
fi

# Optional: Pandoc & LaTeX (for PDF/DOCX)
if [ "$INSTALL_MODE" != "minimal" ]; then
    if [ "$INSTALL_MODE" = "interactive" ]; then
        if ask_yes_no "Install Pandoc + LaTeX for PDF/DOCX report export?"; then
            INSTALL_PDF=true
        fi
    fi
fi

if [ "$INSTALL_PDF" = true ]; then
    print_header "Step 3b: Installing Pandoc & LaTeX"
    
    # Pandoc
    if ! command -v pandoc &> /dev/null; then
        print_warning "Installing Pandoc..."
        sudo apt install -y pandoc
        print_success "Pandoc installed"
    else
        print_success "Pandoc already installed: $(pandoc --version | head -1)"
    fi
    
    # LaTeX
    if ! command -v pdflatex &> /dev/null; then
        print_warning "LaTeX not found. Installing TeX Live..."
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
    else
        print_success "LaTeX already installed: $(pdflatex --version 2>&1 | head -1)"
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
if uv run tiangong-research --version &> /dev/null; then
    print_success "TianGong CLI: $(uv run tiangong-research --version)"
else
    print_error "TianGong CLI not accessible"
fi

# Check optional components
if [ "$INSTALL_CHARTS" = true ]; then
    if node --version &> /dev/null; then
        print_success "Node.js: $(node --version)"
    else
        print_error "Node.js not found"
    fi
fi

if [ "$INSTALL_PDF" = true ]; then
    if pandoc --version &> /dev/null; then
        print_success "Pandoc: $(pandoc --version | head -1)"
    else
        print_error "Pandoc not found"
    fi
    
    if pdflatex --version &> /dev/null; then
        print_success "LaTeX: installed"
    else
        print_error "LaTeX not found"
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
echo "   ${BLUE}uv run tiangong-research --help${NC}"
echo ""
echo "2. List available data sources:"
echo "   ${BLUE}uv run tiangong-research sources list${NC}"
echo ""
echo "3. Run a simple workflow:"
echo "   ${BLUE}uv run tiangong-research research workflow simple --topic \"life cycle assessment\"${NC}"
echo ""
echo "4. For more details, read:"
echo "   ${BLUE}README.md${NC} - User guide"
echo "   ${BLUE}SETUP_GUIDE.md${NC} - Detailed installation guide"
echo "   ${BLUE}specs/architecture.md${NC} - Technical architecture"
echo ""

if [ "$INSTALL_MODE" = "interactive" ]; then
    if ask_yes_no "Would you like to run the CLI help now?"; then
        uv run tiangong-research --help
    fi
fi
