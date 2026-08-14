# =============================================================================
# GPU Detection Script for Hashcat (Windows)
# =============================================================================
# This script detects available GPUs and their capabilities for hashcat.
#
# USAGE:
#   .\scripts\gpu_detect.ps1
#
# OUTPUT:
#   - GPU count, vendor, name, memory
#   - Recommended hashcat configuration
#
# =============================================================================

#Requires -Version 5.1

<#
.SYNOPSIS
    Detect GPUs for hashcat acceleration

.DESCRIPTION
    Scans system for NVIDIA/AMD GPUs and outputs configuration for hashcat.
#>

function Show-Banner {
    $banner = @"
╔═══════════════════════════════════════════════════════════════╗
║           GPU Detection Tool for Hashcat                     ║
║                        v1.0                                   ║
╚═══════════════════════════════════════════════════════════════╝
"@
    Write-Host $banner -ForegroundColor Cyan
}

function Get-NvidiaGPUs {
    Write-Host "`n[*] Detecting NVIDIA GPUs..." -ForegroundColor Blue
    
    $gpus = @()
    
    # Try nvidia-smi first
    try {
        $nvidiaSmi = & nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader,nounits 2>$null
        
        if ($nvidiaSmi) {
            foreach ($line in $nvidiaSmi) {
                $parts = $line -split ',\s*'
                $gpus += [PSCustomObject]@{
                    Index = [int]$parts[0]
                    Name = $parts[1]
                    Memory = [int]$parts[2]
                    Vendor = 'NVIDIA'
                }
            }
        }
    }
    catch {
        Write-Host "[!] nvidia-smi not found or failed" -ForegroundColor Yellow
    }
    
    # Fallback: Check WMI
    if ($gpus.Count -eq 0) {
        try {
            $wmiGPUs = Get-WmiObject Win32_VideoController | Where-Object { $_.Name -like "*NVIDIA*" }
            foreach ($gpu in $wmiGPUs) {
                $gpus += [PSCustomObject]@{
                    Index = $gpus.Count
                    Name = $gpu.Name
                    Memory = [math]::Round($gpu.AdapterRAM / 1MB)
                    Vendor = 'NVIDIA'
                }
            }
        }
        catch {
            Write-Host "[!] WMI query failed" -ForegroundColor Yellow
        }
    }
    
    return $gpus
}

function Get-AMDGPUs {
    Write-Host "`n[*] Detecting AMD GPUs..." -ForegroundColor Blue
    
    $gpus = @()
    
    # Check WMI for AMD cards
    try {
        $wmiGPUs = Get-WmiObject Win32_VideoController | Where-Object { $_.Name -like "*AMD*" -or $_.Name -like "*Radeon*" }
        foreach ($gpu in $wmiGPUs) {
            $gpus += [PSCustomObject]@{
                Index = $gpus.Count
                Name = $gpu.Name
                Memory = [math]::Round($gpu.AdapterRAM / 1MB)
                Vendor = 'AMD'
            }
        }
    }
    catch {
        Write-Host "[!] WMI query failed" -ForegroundColor Yellow
    }
    
    return $gpus
}

function Get-IntelGPUs {
    Write-Host "`n[*] Detecting Intel GPUs..." -ForegroundColor Blue
    
    $gpus = @()
    
    try {
        $wmiGPUs = Get-WmiObject Win32_VideoController | Where-Object { $_.Name -like "*Intel*" }
        foreach ($gpu in $wmiGPUs) {
            $gpus += [PSCustomObject]@{
                Index = $gpus.Count
                Name = $gpu.Name
                Memory = [math]::Round($gpu.AdapterRAM / 1MB)
                Vendor = 'Intel'
            }
        }
    }
    catch {
        Write-Host "[!] WMI query failed" -ForegroundColor Yellow
    }
    
    return $gpus
}

function Test-HashcatGPU {
    param([string]$HashcatPath = "hashcat.exe")
    
    Write-Host "`n[*] Testing hashcat GPU detection..." -ForegroundColor Blue
    
    try {
        $output = & $HashcatPath -I 2>&1 | Out-String
        
        $cudaCount = ([regex]::Matches($output, 'CUDA\.\d+')).Count
        $openclCount = ([regex]::Matches($output, 'OpenCL\.\d+')).Count
        
        Write-Host "  CUDA devices: $cudaCount" -ForegroundColor Green
        Write-Host "  OpenCL devices: $openclCount" -ForegroundColor Green
        
        return @{
            CUDA = $cudaCount
            OpenCL = $openclCount
            Output = $output
        }
    }
    catch {
        Write-Host "[!] Hashcat not found or failed" -ForegroundColor Yellow
        return $null
    }
}

function Show-Recommendations {
    param(
        [int]$TotalGPUs,
        [int]$TotalMemory,
        [string]$Vendor
    )
    
    Write-Host "`n╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║                    RECOMMENDATIONS                          ║" -ForegroundColor Cyan
    Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    
    # Workload recommendation
    if ($TotalGPUs -ge 4) {
        Write-Host "  Workload Profile:   -w 3 (High)" -ForegroundColor Green
        Write-Host "  Parallel Workers:   $TotalGPUs" -ForegroundColor Green
    }
    elseif ($TotalGPUs -ge 2) {
        Write-Host "  Workload Profile:   -w 2 (Default)" -ForegroundColor Yellow
        Write-Host "  Parallel Workers:   $TotalGPUs" -ForegroundColor Yellow
    }
    else {
        Write-Host "  Workload Profile:   -w 1 (Low)" -ForegroundColor Red
        Write-Host "  Parallel Workers:   1" -ForegroundColor Red
    }
    
    # Memory optimization
    if ($TotalMemory -gt 16000) {
        Write-Host "  Wordlist Size:      Unlimited" -ForegroundColor Green
    }
    elseif ($TotalMemory -gt 8000) {
        Write-Host "  Wordlist Size:      Max 500MB recommended" -ForegroundColor Yellow
    }
    else {
        Write-Host "  Wordlist Size:      Max 200MB recommended" -ForegroundColor Red
    }
    
    # Hashcat command example
    Write-Host "`n  Example Hashcat Command:" -ForegroundColor Cyan
    if ($TotalGPUs -ge 2) {
        $deviceIds = (0..($TotalGPUs-1)) -join ','
        Write-Host "    hashcat -m 22000 -a 0 -d $deviceIds -w 3 --force capture.hc22000 wordlist.txt" -ForegroundColor White
    }
    else {
        Write-Host "    hashcat -m 22000 -a 0 -w 3 --force capture.hc22000 wordlist.txt" -ForegroundColor White
    }
}

function Export-GPUInfo {
    param(
        [array]$AllGPUs,
        [string]$OutputFile = "gpu_info.json"
    )
    
    $export = @{
        Timestamp = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
        ComputerName = $env:COMPUTERNAME
        TotalGPUs = $AllGPUs.Count
        GPUs = $AllGPUs
    }
    
    $export | ConvertTo-Json -Depth 3 | Out-File -FilePath $OutputFile -Encoding UTF8
    
    Write-Host "`n[✓] GPU info exported to: $OutputFile" -ForegroundColor Green
}

# ============================================================================
# Main Script
# ============================================================================

Show-Banner

# Detect all GPUs
$nvidiaGPUs = Get-NvidiaGPUs
$amdGPUs = Get-AMDGPUs
$intelGPUs = Get-IntelGPUs

$allGPUs = @()
$allGPUs += $nvidiaGPUs
$allGPUs += $amdGPUs
$allGPUs += $intelGPUs

# Display results
Write-Host "`n╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                    DETECTED GPUs                             ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

if ($allGPUs.Count -eq 0) {
    Write-Host "`n[!] No GPUs detected" -ForegroundColor Red
    Write-Host "[*] Hashcat will use CPU only" -ForegroundColor Yellow
}
else {
    Write-Host ""
    $allGPUs | Format-Table -AutoSize
    
    $totalMemory = ($allGPUs | Measure-Object -Property Memory -Sum).Sum
    Write-Host "  Total GPU Memory: ${totalMemory} MB" -ForegroundColor Green
}

# Test hashcat
$hashcatTest = Test-HashcatGPU

# Show recommendations
if ($allGPUs.Count -gt 0) {
    $primaryVendor = $allGPUs[0].Vendor
    Show-Recommendations -TotalGPUs $allGPUs.Count -TotalMemory $totalMemory -Vendor $primaryVendor
}

# Export results
Export-GPUInfo -AllGPUs $allGPUs

Write-Host "`n[*] Detection complete!" -ForegroundColor Green
