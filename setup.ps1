# =============================================================================
# WiFi Password Recovery Tool - Windows Setup Script
# =============================================================================
# This script installs required dependencies for Windows.
#
# USAGE:
#   .\setup.ps1
#
# Run as Administrator for best results.
#
# =============================================================================

#Requires -Version 5.1

<#
.SYNOPSIS
    Setup script for WiFi Password Recovery Tool on Windows

.DESCRIPTION
    Installs Python, Hashcat, and other dependencies for the tool.
#>

function Show-Banner {
    $banner = @"
╔═══════════════════════════════════════════════════════════════╗
║       WiFi Password Recovery Tool - Windows Setup            ║
║                         v2.0                                  ║
╚═══════════════════════════════════════════════════════════════╝
"@
    Write-Host $banner -ForegroundColor Cyan
}

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Install-Winget {
    Write-Host "`n[*] Checking for winget..." -ForegroundColor Blue
    
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "[✓] winget is installed" -ForegroundColor Green
        return $true
    }
    
    Write-Host "[!] winget not found. Installing App Installer..." -ForegroundColor Yellow
    
    # Try to install winget via Microsoft Store
    try {
        Start-Process "ms-appinstaller:?source=https://aka.ms/getwinget" -Wait
        Write-Host "[✓] winget installation initiated" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "[!] Could not install winget automatically" -ForegroundColor Red
        Write-Host "[*] Please install winget manually from: https://aka.ms/getwinget" -ForegroundColor Yellow
        return $false
    }
}

function Install-Python {
    Write-Host "`n[*] Checking for Python..." -ForegroundColor Blue
    
    try {
        $pythonVersion = python --version 2>&1
        if ($pythonVersion -match "Python 3") {
            Write-Host "[✓] Python is installed: $pythonVersion" -ForegroundColor Green
            return $true
        }
    }
    catch {
        # Python not found
    }
    
    Write-Host "[!] Python not found. Installing..." -ForegroundColor Yellow
    
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
        Write-Host "[✓] Python installed" -ForegroundColor Green
        return $true
    }
    else {
        Write-Host "[*] Please install Python manually from: https://www.python.org/downloads/" -ForegroundColor Yellow
        return $false
    }
}

function Install-Hashcat {
    Write-Host "`n[*] Checking for Hashcat..." -ForegroundColor Blue
    
    # Check if hashcat is in PATH
    if (Get-Command hashcat.exe -ErrorAction SilentlyContinue) {
        Write-Host "[✓] Hashcat is installed" -ForegroundColor Green
        return $true
    }
    
    # Check common install locations
    $hashcatPaths = @(
        "C:\Program Files\hashcat\hashcat.exe",
        "C:\hashcat\hashcat.exe",
        "$env:LOCALAPPDATA\hashcat\hashcat.exe"
    )
    
    foreach ($path in $hashcatPaths) {
        if (Test-Path $path) {
            Write-Host "[✓] Hashcat found at: $path" -ForegroundColor Green
            # Add to PATH if not already there
            $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
            if ($currentPath -notlike "*hashcat*") {
                [Environment]::SetEnvironmentVariable("Path", "$currentPath;$(Split-Path $path)", "User")
                Write-Host "[✓] Added hashcat to PATH" -ForegroundColor Green
            }
            return $true
        }
    }
    
    Write-Host "[!] Hashcat not found. Installing..." -ForegroundColor Yellow
    
    # Try winget
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install -e --id Hashcat.Hashcat --accept-package-agreements --accept-source-agreements
        Write-Host "[✓] Hashcat installed" -ForegroundColor Green
        return $true
    }
    
    # Try chocolatey
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        choco install hashcat -y
        Write-Host "[✓] Hashcat installed via Chocolatey" -ForegroundColor Green
        return $true
    }
    
    Write-Host "[*] Please install hashcat manually from: https://hashcat.net/hashcat/" -ForegroundColor Yellow
    return $false
}

function Install-AdditionalTools {
    Write-Host "`n[*] Installing additional tools..." -ForegroundColor Blue
    
    # Install Git (useful for downloading wordlists)
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-Host "[*] Installing Git..." -ForegroundColor Yellow
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            winget install -e --id Git.Git --accept-package-agreements --accept-source-agreements
        }
    }
    
    # Install curl (usually comes with Windows)
    if (-not (Get-Command curl.exe -ErrorAction SilentlyContinue)) {
        Write-Host "[!] curl not found - Windows should include this by default" -ForegroundColor Yellow
    }
    
    Write-Host "[✓] Additional tools check complete" -ForegroundColor Green
}

function Setup-Directories {
    Write-Host "`n[*] Setting up directories..." -ForegroundColor Blue
    
    $dirs = @("captures", "logs", "wordlists", "rules")
    
    foreach ($dir in $dirs) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-Host "  [+] Created: $dir" -ForegroundColor Cyan
        }
    }
    
    Write-Host "[✓] Directories ready" -ForegroundColor Green
}

function Download-Wordlists {
    Write-Host "`n[*] Setting up wordlists..." -ForegroundColor Blue
    
    $wordlistFile = "wordlists\rockyou.txt"
    
    if (Test-Path $wordlistFile) {
        Write-Host "[✓] Wordlist already exists" -ForegroundColor Green
        return
    }
    
    Write-Host "[*] Downloading rockyou.txt (this may take a while)..." -ForegroundColor Yellow
    
    # Note: rockyou.txt is a large file (~140MB compressed)
    # Users should download manually or use a smaller wordlist
    
    Write-Host "[!] rockyou.txt is ~140MB. Please download manually:" -ForegroundColor Yellow
    Write-Host "    1. Visit: https://github.com/danielmiessler/SecLists/tree/master/Passwords/Leaked-Databases" -ForegroundColor Cyan
    Write-Host "    2. Download rockyou.txt.tar.gz" -ForegroundColor Cyan
    Write-Host "    3. Extract to wordlists\ folder" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "    Or use a smaller wordlist for testing:" -ForegroundColor Yellow
    Write-Host "    curl -o wordlists\common.txt https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/10k-most-common.txt" -ForegroundColor Cyan
}

function Install-PythonDependencies {
    Write-Host "`n[*] Installing Python dependencies..." -ForegroundColor Blue
    
    if (Test-Path "requirements.txt") {
        python -m pip install -r requirements.txt
        Write-Host "[✓] Python dependencies installed" -ForegroundColor Green
    }
    else {
        Write-Host "[!] requirements.txt not found" -ForegroundColor Yellow
    }
}

function Test-Installation {
    Write-Host "`n[*] Testing installation..." -ForegroundColor Blue
    
    $tests = @(
        @{Name="Python"; Command="python --version"},
        @{Name="Pip"; Command="python -m pip --version"},
        @{Name="Hashcat"; Command="hashcat --version"}
    )
    
    $allPassed = $true
    
    foreach ($test in $tests) {
        try {
            $result = Invoke-Expression $test.Command 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  [✓] $($test.Name)" -ForegroundColor Green
            }
            else {
                Write-Host "  [✗] $($test.Name)" -ForegroundColor Red
                $allPassed = $false
            }
        }
        catch {
            Write-Host "  [✗] $($test.Name)" -ForegroundColor Red
            $allPassed = $false
        }
    }
    
    # Test GPU detection
    Write-Host "`n[*] Testing GPU detection..." -ForegroundColor Blue
    python wifi_cracker.py gpu-detect 2>$null
    
    return $allPassed
}

function Show-Usage {
    Write-Host "`n╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║                    SETUP COMPLETE!                          ║" -ForegroundColor Cyan
    Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    
    Write-Host "`nUsage Examples:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  # Detect GPUs" -ForegroundColor Cyan
    Write-Host "  python wifi_cracker.py gpu-detect" -ForegroundColor White
    Write-Host ""
    Write-Host "  # Extract saved WiFi passwords" -ForegroundColor Cyan
    Write-Host "  python wifi_cracker.py windows" -ForegroundColor White
    Write-Host ""
    Write-Host "  # GPU-accelerated cracking (with capture file)" -ForegroundColor Cyan
    Write-Host "  python wifi_cracker.py wpa --capture handshake.cap --parallel --gpu-count 4" -ForegroundColor White
    Write-Host ""
    Write-Host "  # Advanced wordlist generation" -ForegroundColor Cyan
    Write-Host "  python wifi_cracker.py wordlist --input wordlists\common.txt --rules" -ForegroundColor White
    Write-Host ""
}

# ============================================================================
# Main Script
# ============================================================================

Show-Banner

# Check administrator privileges
if (-not (Test-Administrator)) {
    Write-Host "`n[!] Warning: Not running as Administrator" -ForegroundColor Yellow
    Write-Host "[*] Some installations may require Administrator privileges" -ForegroundColor Yellow
    Write-Host "[*] Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne 'y') {
        exit 0
    }
}

# Install dependencies
$hasWinget = Install-Winget
$hasPython = Install-Python
$hasHashcat = Install-Hashcat

Install-AdditionalTools
Setup-Directories
Download-Wordlists
Install-PythonDependencies

# Test installation
$testPassed = Test-Installation

# Show usage
Show-Usage

if ($testPassed) {
    Write-Host "`n[✓] Setup completed successfully!" -ForegroundColor Green
}
else {
    Write-Host "`n[!] Setup completed with warnings. Please check above messages." -ForegroundColor Yellow
}
