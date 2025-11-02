# TianGong AI for Sustainability - One-Click Setup Script for Windows
# 
# This script automates the installation of all dependencies and project setup
# on Windows. It guides you through optional components with prompts.
#
# Usage: 
#   PowerShell -ExecutionPolicy Bypass -File install_windows.ps1 [options]
#
# Options:
#   -Full          Install all components (PDF, charts, carbon metrics)
#   -Minimal       Install only core dependencies
#   -WithPdf       Include Pandoc & MiKTeX for PDF/DOCX export
#   -WithCharts    Include Node.js 22+ for chart workflows
#   -WithCarbon    Include third-party research libraries
#

param(
    [switch]$Full,
    [switch]$Minimal,
    [switch]$WithPdf,
    [switch]$WithCharts,
    [switch]$WithCarbon
)

# Require Administrator privileges
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "This script requires Administrator privileges." -ForegroundColor Red
    Write-Host "Please run PowerShell as Administrator and try again." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Cyan
    exit 1
}

# Color functions
function Print-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Blue
    Write-Host $Message -ForegroundColor Blue
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Blue
    Write-Host ""
}

function Print-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Print-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Print-Warning {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

function Ask-YesNo {
    param([string]$Prompt)
    $response = Read-Host "$Prompt (y/n)"
    return $response -match '^[Yy]$'
}

# Global variables
$UV_OPTIONAL_GROUPS_SELECTED = @()
$INSTALL_MODE = "interactive"
$INSTALL_PDF = $false
$INSTALL_CHARTS = $false
$PDF_INSTALL_PERFORMED = $false

function Add-UvGroup {
    param([string]$Group)
    if ($UV_OPTIONAL_GROUPS_SELECTED -notcontains $Group) {
        $script:UV_OPTIONAL_GROUPS_SELECTED += $Group
    }
}

function Get-GroupDescription {
    param([string]$Group)
    switch ($Group) {
        "3rd" { return "Third-party research libraries (uk-grid-intensity CLI for carbon metrics)" }
        default { return "Optional dependency group '$Group'" }
    }
}

function Test-GroupSelected {
    param([string]$Group)
    return $UV_OPTIONAL_GROUPS_SELECTED -contains $Group
}

# Parse command line arguments
if ($Full) {
    $INSTALL_MODE = "full"
    $INSTALL_PDF = $true
    $INSTALL_CHARTS = $true
    Add-UvGroup "3rd"
}
elseif ($Minimal) {
    $INSTALL_MODE = "minimal"
}

if ($WithPdf) { $INSTALL_PDF = $true }
if ($WithCharts) { $INSTALL_CHARTS = $true }
if ($WithCarbon) { Add-UvGroup "3rd" }

# Welcome message
Print-Header "Welcome to TianGong AI for Sustainability Setup"
Write-Host "This script will install all necessary dependencies for Windows."
Write-Host ""
Write-Host "Installation mode: $INSTALL_MODE"
Write-Host ""

# Check if Chocolatey is installed
Print-Header "Step 1: Checking Chocolatey Installation"
try {
    $chocoVersion = choco --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Print-Success "Chocolatey is already installed: v$chocoVersion"
    }
    else {
        throw "Chocolatey not found"
    }
}
catch {
    Print-Warning "Chocolatey not found. Installing..."
    Write-Host ""
    Write-Host "Installing Chocolatey package manager..." -ForegroundColor Cyan
    
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    try {
        Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
        
        # Refresh environment variables
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        
        Print-Success "Chocolatey installed successfully"
    }
    catch {
        Print-Error "Failed to install Chocolatey: $_"
        Write-Host "Please install Chocolatey manually from: https://chocolatey.org/install" -ForegroundColor Yellow
        exit 1
    }
}

# Install core dependencies
Print-Header "Step 2: Installing Core Dependencies"

# Git
Write-Host "Checking Git installation..."
try {
    $gitVersion = git --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Print-Success "Git already installed: $gitVersion"
    }
    else {
        throw "Git not found"
    }
}
catch {
    Print-Warning "Installing Git..."
    choco install git -y
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    Print-Success "Git installed"
}

# Python 3.12+
Write-Host "Checking Python 3.12+ installation..."
$pythonFound = $false
$pythonVersion = ""

try {
    $pythonVersion = python --version 2>$null
    if ($pythonVersion -match "Python (\d+)\.(\d+)") {
        $major = [int]$matches[1]
        $minor = [int]$matches[2]
        if ($major -eq 3 -and $minor -ge 12) {
            $pythonFound = $true
            Print-Success "Python already installed: $pythonVersion"
        }
        else {
            Print-Warning "Found $pythonVersion, but need Python 3.12+"
        }
    }
}
catch {
    Print-Warning "Python not found"
}

if (-not $pythonFound) {
    Print-Warning "Installing Python 3.12..."
    choco install python312 -y
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    Print-Success "Python 3.12 installed"
}

# uv
Write-Host "Checking uv installation..."
try {
    $uvVersion = uv --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Print-Success "uv already installed: $uvVersion"
    }
    else {
        throw "uv not found"
    }
}
catch {
    Print-Warning "Installing uv..."
    Write-Host "Downloading uv installer..." -ForegroundColor Cyan
    
    try {
        # Install uv using the official PowerShell installer
        powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
        
        # Add to PATH for current session
        $uvPath = "$env:USERPROFILE\.cargo\bin"
        $env:Path = "$uvPath;$env:Path"
        
        Print-Success "uv installed"
    }
    catch {
        Print-Error "Failed to install uv: $_"
        Write-Host "Please install uv manually from: https://docs.astral.sh/uv/" -ForegroundColor Yellow
        exit 1
    }
}

# Optional: Node.js 22+ (for charts)
$NODE_VERSION = ""
$NODE_MAJOR = 0

try {
    $NODE_VERSION = node --version 2>$null
    if ($NODE_VERSION -match "v(\d+)") {
        $NODE_MAJOR = [int]$matches[1]
    }
}
catch {
    # Node not found
}

Print-Header "Step 3a: Node.js for Chart Workflows"
if ($NODE_MAJOR -ge 22) {
    Print-Success "Node.js already installed: $NODE_VERSION"
}
else {
    if ($NODE_VERSION) {
        Print-Warning "Detected Node.js $NODE_VERSION (<22). Chart workflows require Node.js 22+"
    }
    else {
        Print-Warning "Node.js not found. Chart workflows require Node.js 22+"
    }

    if ($INSTALL_MODE -eq "full" -and -not $INSTALL_CHARTS) {
        $INSTALL_CHARTS = $true
    }

    if ($INSTALL_MODE -eq "interactive" -and -not $INSTALL_CHARTS) {
        if (Ask-YesNo "Install or upgrade Node.js to version 22+ now?") {
            $INSTALL_CHARTS = $true
        }
        else {
            Print-Warning "Skipping Node.js installation. AntV chart features will remain disabled until Node.js 22+ is available."
        }
    }
}

if ($INSTALL_CHARTS) {
    if ($NODE_MAJOR -ge 22) {
        Print-Success "Node.js already meets the requirement. No installation needed."
    }
    else {
        Print-Warning "Installing Node.js 22..."
        choco install nodejs --version=22.0.0 -y
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        
        try {
            $NODE_VERSION = node --version 2>$null
            if ($NODE_VERSION -match "v(\d+)") {
                $NODE_MAJOR = [int]$matches[1]
            }
            if ($NODE_MAJOR -ge 22) {
                Print-Success "Node.js installed: $NODE_VERSION"
            }
            else {
                Print-Error "Node.js installation did not reach version 22+. Please check Chocolatey output."
            }
        }
        catch {
            Print-Error "Failed to verify Node.js installation"
        }
    }
}

# Optional: Pandoc & MiKTeX (for PDF/DOCX)
if ($INSTALL_MODE -ne "minimal" -or $INSTALL_PDF) {
    $PANDOC_PRESENT = $false
    $PANDOC_OK = $false
    $PANDOC_VERSION_STR = ""
    
    try {
        $pandocOutput = pandoc --version 2>$null
        if ($pandocOutput -match "pandoc (\d+)\.(\d+)") {
            $PANDOC_PRESENT = $true
            $PANDOC_VERSION_STR = $matches[0]
            $pandocMajor = [int]$matches[1]
            if ($pandocMajor -ge 3) {
                $PANDOC_OK = $true
            }
        }
    }
    catch {
        # Pandoc not found
    }

    $PDFLATEX_PRESENT = $false
    $PDFLATEX_VERSION_STR = ""
    
    try {
        $pdflatexOutput = pdflatex --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            $PDFLATEX_PRESENT = $true
            $PDFLATEX_VERSION_STR = ($pdflatexOutput | Select-Object -First 1)
        }
    }
    catch {
        # pdflatex not found
    }

    $PDF_READY = $PANDOC_OK -and $PDFLATEX_PRESENT

    Print-Header "Step 3b: Pandoc & LaTeX"

    if ($PANDOC_PRESENT) {
        if ($PANDOC_OK) {
            Print-Success "Pandoc already installed: $PANDOC_VERSION_STR"
        }
        else {
            Print-Warning "Pandoc detected but version < 3.0: $PANDOC_VERSION_STR"
        }
    }
    else {
        Print-Warning "Pandoc not found."
    }

    if ($PDFLATEX_PRESENT) {
        Print-Success "LaTeX already installed: $PDFLATEX_VERSION_STR"
    }
    else {
        Print-Warning "LaTeX not found."
    }

    if ($PDF_READY -and -not $INSTALL_PDF) {
        Print-Success "PDF/DOCX export requirements already satisfied."
    }
    else {
        if ($INSTALL_MODE -eq "interactive" -and -not $INSTALL_PDF) {
            if (Ask-YesNo "Install Pandoc + MiKTeX for PDF/DOCX report export?") {
                $INSTALL_PDF = $true
            }
            else {
                Print-Warning "Skipping Pandoc/MiKTeX installation. PDF export will remain disabled."
            }
        }
    }

    if ($INSTALL_PDF) {
        $PDF_INSTALL_PERFORMED = $true

        if (-not $PANDOC_OK) {
            Print-Warning "Installing or upgrading Pandoc..."
            choco install pandoc -y
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
            Print-Success "Pandoc installed"
        }

        if (-not $PDFLATEX_PRESENT) {
            Print-Warning "Installing MiKTeX (LaTeX distribution for Windows)..."
            Write-Host ""
            Write-Host "Note: MiKTeX installation may take several minutes and requires ~1 GB of disk space." -ForegroundColor Cyan
            Write-Host "      The installer may show a GUI window - please follow the prompts." -ForegroundColor Cyan
            Write-Host ""
            
            choco install miktex -y
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
            
            Print-Success "MiKTeX installed"
            Print-Warning "You may need to restart your terminal for LaTeX commands to be available."
        }
    }
}

# Optional: third-party research libraries (uv groups)
if ($INSTALL_MODE -ne "minimal" -or (Test-GroupSelected "3rd")) {
    $GROUP_DESC = Get-GroupDescription "3rd"
    Print-Header "Step 3c: Third-Party Research Libraries"
    
    if ($INSTALL_MODE -eq "interactive" -and -not (Test-GroupSelected "3rd")) {
        if (Ask-YesNo "Install optional third-party packages via uv? ($GROUP_DESC)") {
            Add-UvGroup "3rd"
        }
        else {
            Print-Warning "Skipping optional third-party packages. You can install them later with: uv sync --group 3rd"
        }
    }

    if (Test-GroupSelected "3rd") {
        Print-Success "uv dependency group '3rd' scheduled ($GROUP_DESC)."
    }
}

# Project setup
Print-Header "Step 4: Setting up TianGong Project"

# Check if we're in the project directory
if (-not (Test-Path "pyproject.toml")) {
    Print-Warning "pyproject.toml not found. Cloning repository..."
    git clone https://github.com/linancn/TianGong-AI-for-Sustainability.git
    Set-Location TianGong-AI-for-Sustainability
}

# Refresh environment variables before running uv
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

# Run uv sync (include optional groups if selected)
$uvSyncArgs = @("sync")
if ($UV_OPTIONAL_GROUPS_SELECTED.Count -gt 0) {
    foreach ($group in $UV_OPTIONAL_GROUPS_SELECTED) {
        $uvSyncArgs += "--group"
        $uvSyncArgs += $group
    }
    $cmdDisplay = "uv " + ($uvSyncArgs -join " ")
    Print-Warning "Running '$cmdDisplay' to install project dependencies..."
}
else {
    Print-Warning "Running 'uv sync' to install project dependencies..."
}

try {
    & uv @uvSyncArgs
    if ($LASTEXITCODE -eq 0) {
        Print-Success "Project dependencies installed"
    }
    else {
        throw "uv sync failed with exit code $LASTEXITCODE"
    }
}
catch {
    Print-Error "Failed to install project dependencies: $_"
    Write-Host "Please check the error messages above and try again." -ForegroundColor Yellow
    exit 1
}

if ($UV_OPTIONAL_GROUPS_SELECTED.Count -gt 0) {
    $groupDir = ".tiangong"
    if (-not (Test-Path $groupDir)) {
        New-Item -ItemType Directory -Path $groupDir | Out-Null
    }
    $groupFile = Join-Path $groupDir "uv-groups.selected"
    $UV_OPTIONAL_GROUPS_SELECTED | Sort-Object -Unique | Set-Content $groupFile
    Print-Success "Optional uv groups recorded in $groupFile (reapply with 'uv sync --group <name>')."
}

# Verification
Print-Header "Step 5: Verification"

Write-Host "Checking installations..."
Write-Host ""

# Check Python
try {
    $pyVersion = python --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Print-Success "Python: $pyVersion"
    }
    else {
        Print-Error "Python not found"
    }
}
catch {
    Print-Error "Python not found"
}

# Check uv
try {
    $uvVersion = uv --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Print-Success "uv: $uvVersion"
    }
    else {
        Print-Error "uv not found"
    }
}
catch {
    Print-Error "uv not found. Try restarting your terminal."
}

# Check CLI
try {
    $cliTest = uv run tiangong-research --help 2>$null
    if ($LASTEXITCODE -eq 0) {
        Print-Success "TianGong CLI: accessible (run 'uv run tiangong-research --help')"
    }
    else {
        Print-Error "TianGong CLI not accessible"
    }
}
catch {
    Print-Error "TianGong CLI not accessible"
}

# Check optional components
try {
    $nodeVer = node --version 2>$null
    if ($nodeVer -match "v(\d+)") {
        $nodeMajor = [int]$matches[1]
        if ($nodeMajor -ge 22) {
            Print-Success "Node.js: $nodeVer"
        }
        else {
            Print-Warning "Node.js: $nodeVer (upgrade to >=22 for chart workflows)"
        }
    }
}
catch {
    Print-Warning "Node.js: not found (chart workflows disabled)"
}

try {
    $pandocVer = pandoc --version 2>$null | Select-Object -First 1
    if ($LASTEXITCODE -eq 0) {
        Print-Success "Pandoc: $pandocVer"
    }
    else {
        if ($PDF_INSTALL_PERFORMED) {
            Print-Error "Pandoc not found (installation may have failed)"
        }
        else {
            Print-Warning "Pandoc: not found (PDF/DOCX export disabled)"
        }
    }
}
catch {
    if ($PDF_INSTALL_PERFORMED) {
        Print-Error "Pandoc not found (installation may have failed)"
    }
    else {
        Print-Warning "Pandoc: not found (PDF/DOCX export disabled)"
    }
}

try {
    $latexVer = pdflatex --version 2>$null | Select-Object -First 1
    if ($LASTEXITCODE -eq 0) {
        Print-Success "LaTeX: $latexVer"
    }
    else {
        if ($PDF_INSTALL_PERFORMED) {
            Print-Warning "LaTeX not in PATH. Try restarting your terminal."
        }
        else {
            Print-Warning "LaTeX: not found (PDF/DOCX export disabled)"
        }
    }
}
catch {
    if ($PDF_INSTALL_PERFORMED) {
        Print-Warning "LaTeX not in PATH. Try restarting your terminal."
    }
    else {
        Print-Warning "LaTeX: not found (PDF/DOCX export disabled)"
    }
}

if (Test-GroupSelected "3rd") {
    try {
        $gridTest = uv run --group 3rd uk-grid-intensity --help 2>$null
        if ($LASTEXITCODE -eq 0) {
            Print-Success "uk-grid-intensity CLI (via uv run): available"
        }
        else {
            Print-Error "uk-grid-intensity not accessible via uv run. Re-run 'uv sync --group 3rd' or check installation."
        }
    }
    catch {
        Print-Error "uk-grid-intensity not accessible via uv run. Re-run 'uv sync --group 3rd' or check installation."
    }
}

Write-Host ""

# Final summary
Print-Header "Setup Complete! 🎉"

Write-Host "Next steps:"
Write-Host ""
Write-Host "1. Test the CLI:" -ForegroundColor Cyan
Write-Host "   uv run tiangong-research --help" -ForegroundColor Blue
Write-Host ""
Write-Host "2. List available data sources:" -ForegroundColor Cyan
Write-Host "   uv run tiangong-research sources list" -ForegroundColor Blue
Write-Host ""
Write-Host "3. Run a simple workflow:" -ForegroundColor Cyan
Write-Host "   uv run tiangong-research research workflow simple --topic `"life cycle assessment`"" -ForegroundColor Blue
Write-Host ""
Write-Host "4. For more details, read:" -ForegroundColor Cyan
Write-Host "   README.md - User guide" -ForegroundColor Blue
Write-Host "   SETUP_GUIDE.md - Detailed installation guide" -ForegroundColor Blue
Write-Host "   AGENTS.md - Architecture Blueprint" -ForegroundColor Blue
Write-Host ""

if ($INSTALL_MODE -eq "interactive") {
    if (Ask-YesNo "Would you like to run the CLI help now?") {
        uv run tiangong-research --help
    }
}

Write-Host ""
Write-Host "Note: If you installed new tools (Node.js, LaTeX, etc.), you may need to" -ForegroundColor Yellow
Write-Host "      restart your terminal for PATH changes to take effect." -ForegroundColor Yellow
Write-Host ""
