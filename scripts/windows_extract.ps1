# =============================================================================
# Windows WiFi Profile Extraction Script
# =============================================================================
# This script extracts saved WiFi passwords from Windows using netsh commands.
#
# REQUIREMENTS:
# - Windows 10/11
# - Administrator privileges (for some operations)
#
# USAGE:
#   .\scripts\windows_extract.ps1 [OPTIONS]
#
# OPTIONS:
#   -SSID "NetworkName"    Extract password for specific SSID
#   -Export                 Export all passwords to JSON
#   -List                   List all saved profiles
#   -Help                   Show this help message
#
# =============================================================================

#Requires -Version 5.1

<#
.SYNOPSIS
    WiFi Password Recovery Tool for Windows

.DESCRIPTION
    Extracts saved WiFi passwords from Windows using netsh commands.

.PARAMETER SSID
    Specific WiFi network name to extract password for

.PARAMETER Export
    Export all passwords to a JSON file

.PARAMETER List
    List all saved WiFi profiles

.EXAMPLE
    .\windows_extract.ps1 -List
    Lists all saved WiFi profiles

.EXAMPLE
    .\windows_extract.ps1 -SSID "MyHomeWiFi"
    Extracts password for "MyHomeWiFi"

.EXAMPLE
    .\windows_extract.ps1 -Export
    Exports all saved passwords to wifi_passwords.json
#>

param(
    [string]$SSID,
    [switch]$Export,
    [switch]$List,
    [switch]$Help
)

# ============================================================================
# Functions
# ============================================================================

function Show-Banner {
    $banner = @"
╔═══════════════════════════════════════════════════════════════╗
║         Windows WiFi Profile Extraction Tool                 ║
║                        v1.0                                   ║
╚═══════════════════════════════════════════════════════════════╝
"@
    Write-Host $banner -ForegroundColor Cyan
}

function Show-Help {
    $help = @"

WiFi Password Recovery Tool for Windows

USAGE:
    .\windows_extract.ps1 [OPTIONS]

OPTIONS:
    -SSID "NetworkName"    Extract password for specific SSID
    -Export                Export all passwords to JSON file
    -List                  List all saved WiFi profiles
    -Help                  Show this help message

EXAMPLES:
    .\windows_extract.ps1 -List
    .\windows_extract.ps1 -SSID "MyHomeWiFi"
    .\windows_extract.ps1 -Export

"@
    Write-Host $help -ForegroundColor Yellow
}

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-WiFiProfiles {
    Write-Host "`n[*] Retrieving saved WiFi profiles..." -ForegroundColor Blue
    
    $output = netsh wlan show profiles
    $profiles = @()
    
    foreach ($line in $output) {
        if ($line -match 'All User Profile\s*:\s*(.+)') {
            $profiles += $matches[1].Trim()
        }
        elseif ($line -match 'Profile\s*:\s*(.+)') {
            $profiles += $matches[1].Trim()
        }
    }
    
    return $profiles
}

function Get-WiFiPassword {
    param(
        [string]$ProfileName
    )
    
    Write-Host "`n[*] Extracting password for: $ProfileName" -ForegroundColor Blue
    
    $output = netsh wlan show profile name="$ProfileName" key=clear
    
    $password = $null
    $authType = $null
    $encryption = $null
    
    foreach ($line in $output) {
        if ($line -match 'Key Content\s*:\s*(.+)') {
            $password = $matches[1].Trim()
        }
        elseif ($line -match 'Authentication\s*:\s*(.+)') {
            $authType = $matches[1].Trim()
        }
        elseif ($line -match 'Encryption\s*:\s*(.+)') {
            $encryption = $matches[1].Trim()
        }
    }
    
    return @{
        Profile = $ProfileName
        Password = $password
        AuthType = $authType
        Encryption = $encryption
    }
}

function Export-WiFiPasswords {
    param(
        [array]$Profiles
    )
    
    Write-Host "`n[*] Exporting passwords to JSON..." -ForegroundColor Blue
    
    $results = @()
    
    foreach ($profile in $Profiles) {
        $info = Get-WiFiPassword -ProfileName $profile
        $results += $info
        
        if ($info.Password) {
            Write-Host "  [✓] $($info.Profile): $($info.Password)" -ForegroundColor Green
        }
        else {
            Write-Host "  [!] $($info.Profile): No password found" -ForegroundColor Yellow
        }
    }
    
    $export = @{
        Timestamp = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
        ComputerName = $env:COMPUTERNAME
        Profiles = $results
    }
    
    $jsonFile = "wifi_passwords_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
    $export | ConvertTo-Json -Depth 3 | Out-File -FilePath $jsonFile -Encoding UTF8
    
    Write-Host "`n[✓] Results exported to: $jsonFile" -ForegroundColor Green
    return $export
}

function Show-ProfileDetails {
    param(
        [string]$ProfileName
    )
    
    $info = Get-WiFiPassword -ProfileName $ProfileName
    
    Write-Host "`n╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║ Profile: $($info.Profile)" -ForegroundColor Cyan
    Write-Host "╠═══════════════════════════════════════════════════════════════╣" -ForegroundColor Cyan
    Write-Host "║ Authentication: $($info.AuthType)" -ForegroundColor Cyan
    Write-Host "║ Encryption: $($info.Encryption)" -ForegroundColor Cyan
    
    if ($info.Password) {
        Write-Host "║ Password: $($info.Password)" -ForegroundColor Green
    }
    else {
        Write-Host "║ Password: Not found (open network?)" -ForegroundColor Yellow
    }
    
    Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
}

# ============================================================================
# Main Script
# ============================================================================

# Show banner
Show-Banner

# Show help if requested
if ($Help) {
    Show-Help
    exit 0
}

# Check administrator privileges (optional, but recommended)
if (-not (Test-Administrator)) {
    Write-Host "`n[!] Warning: Not running as Administrator" -ForegroundColor Yellow
    Write-Host "[*] Some operations may require Administrator privileges" -ForegroundColor Yellow
    Write-Host "[*] Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
}

# Get all profiles
$profiles = Get-WiFiProfiles

if ($profiles.Count -eq 0) {
    Write-Host "`n[!] No WiFi profiles found" -ForegroundColor Red
    Write-Host "[*] Make sure you have connected to WiFi networks before" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n[✓] Found $($profiles.Count) profiles:" -ForegroundColor Green
for ($i = 0; $i -lt $profiles.Count; $i++) {
    Write-Host "    $($i + 1). $($profiles[$i])" -ForegroundColor Cyan
}

# Handle different options
if ($List) {
    # Just list profiles (already done above)
    Write-Host "`n[*] Use -SSID to extract specific password" -ForegroundColor Yellow
    Write-Host "[*] Use -Export to export all passwords" -ForegroundColor Yellow
}
elseif ($SSID) {
    # Extract specific SSID
    if ($profiles -contains $SSID) {
        Show-ProfileDetails -ProfileName $SSID
    }
    else {
        Write-Host "`n[!] SSID not found: $SSID" -ForegroundColor Red
        Write-Host "[*] Available profiles:" -ForegroundColor Yellow
        $profiles | ForEach-Object { Write-Host "    - $_" -ForegroundColor Cyan }
    }
}
elseif ($Export) {
    # Export all passwords
    Export-WiFiPasswords -Profiles $profiles
}
else {
    # Default: show all profiles and passwords
    Write-Host "`n[*] Extracting all passwords..." -ForegroundColor Blue
    
    foreach ($profile in $profiles) {
        Show-ProfileDetails -ProfileName $profile
    }
    
    Write-Host "`n[*] Options:" -ForegroundColor Yellow
    Write-Host "    -List          List all profiles" -ForegroundColor Cyan
    Write-Host "    -SSID "name"   Extract specific SSID" -ForegroundColor Cyan
    Write-Host "    -Export        Export to JSON file" -ForegroundColor Cyan
}

Write-Host "`n[*] Done!" -ForegroundColor Green
