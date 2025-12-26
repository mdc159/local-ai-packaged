# Docker Volume Restoration Script for Local AI Package
# This script restores all Docker volumes and project data after reimaging

param(
    [Parameter(Mandatory=$true)]
    [string]$BackupLocation,
    [string]$ProjectDestination = "X:\GitHub\local-ai-packaged",
    [switch]$SkipProjectFiles = $false,
    [switch]$SkipFlowise = $false,
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"

# Configuration
$VolumesBackupPath = Join-Path $BackupLocation "docker-volumes"
$ProjectBackupPath = Join-Path $BackupLocation "local-ai-packaged"
$FlowiseBackupPath = Join-Path $BackupLocation "flowise"
$ManifestPath = Join-Path $BackupLocation "backup_manifest.txt"

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host $Message -ForegroundColor Cyan
    Write-Host "============================================" -ForegroundColor Cyan
}

function Write-Step {
    param([string]$Message)
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Message" -ForegroundColor Yellow
}

function Write-Success {
    param([string]$Message)
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ✓ $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ⚠ $Message" -ForegroundColor Magenta
}

function Write-ErrorMsg {
    param([string]$Message)
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ✗ $Message" -ForegroundColor Red
}

function Test-DockerRunning {
    Write-Step "Checking if Docker is running..."
    try {
        $result = docker info 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-ErrorMsg "Docker is not running. Please start Docker Desktop and try again."
            exit 1
        }
        Write-Success "Docker is running"
        return $true
    }
    catch {
        Write-ErrorMsg "Failed to connect to Docker`: $($_.Exception.Message)"
        exit 1
    }
}

function Test-BackupLocation {
    Write-Step "Validating backup location..."

    if (-not (Test-Path $BackupLocation)) {
        Write-ErrorMsg "Backup location does not exist: $BackupLocation"
        exit 1
    }

    if (-not (Test-Path $VolumesBackupPath)) {
        Write-ErrorMsg "Docker volumes backup not found at: $VolumesBackupPath"
        exit 1
    }

    if (Test-Path $ManifestPath) {
        Write-Success "Found backup manifest"
        Write-Host ""
        Write-Host "Backup Manifest Preview:" -ForegroundColor Cyan
        Get-Content $ManifestPath | Select-Object -First 15 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
        Write-Host ""
    }
    else {
        Write-Warning "Backup manifest not found"
    }

    Write-Success "Backup location validated"
}

function Restore-DockerVolume {
    param(
        [string]$VolumeName,
        [string]$BackupPath,
        [switch]$Force = $false
    )

    Write-Step "Restoring volume: $VolumeName"

    $backupFile = Join-Path $BackupPath "${VolumeName}.tar.gz"

    if (-not (Test-Path $backupFile)) {
        Write-Warning "Backup file not found for $VolumeName, skipping..."
        return $false
    }

    try {
        # Check if volume already exists
        $volumeExists = docker volume ls -q | Select-String -Pattern "^${VolumeName}$"
        if ($volumeExists) {
            Write-Warning "Volume '$VolumeName' already exists"
            if (-not $Force) {
                $response = Read-Host "Do you want to overwrite it? (yes/no)"
                if ($response -ne "yes") {
                    Write-Warning "Skipping $VolumeName"
                    return $false
                }
            } else {
                Write-Host "Force mode: overwriting existing volume" -ForegroundColor Cyan
            }
            # Remove existing volume
            Write-Step "Removing existing volume: $VolumeName"
            docker volume rm $VolumeName | Out-Null
        }

        # Create new volume
        Write-Step "Creating volume: $VolumeName"
        docker volume create $VolumeName | Out-Null

        # Restore data to volume
        $dockerCmd = "docker run --rm -v ${VolumeName}:/target -v `"${BackupPath}:/backup`" alpine tar xzf /backup/${VolumeName}.tar.gz -C /target"
        Invoke-Expression $dockerCmd

        if ($LASTEXITCODE -eq 0) {
            $fileSize = (Get-Item $backupFile).Length / 1MB
            Write-Success "Restored $VolumeName (${fileSize:N2} MB)"
            return $true
        }
        else {
            Write-ErrorMsg "Failed to restore $VolumeName"
            return $false
        }
    }
    catch {
        Write-ErrorMsg "Error restoring $VolumeName`: $($_.Exception.Message)"
        return $false
    }
}

function Restore-ProjectDirectory {
    param(
        [string]$SourcePath,
        [string]$DestinationPath,
        [switch]$Force = $false
    )

    Write-Step "Restoring project directory..."

    if (-not (Test-Path $SourcePath)) {
        Write-Warning "Project backup not found at: $SourcePath"
        return $false
    }

    try {
        # Check if destination exists
        if (Test-Path $DestinationPath) {
            Write-Warning "Project directory already exists at: $DestinationPath"
            if (-not $Force) {
                $response = Read-Host "Do you want to merge/overwrite? (yes/no)"
                if ($response -ne "yes") {
                    Write-Warning "Skipping project directory restore"
                    return $false
                }
            } else {
                Write-Host "Force mode: merging/overwriting existing directory" -ForegroundColor Cyan
            }
        }
        else {
            New-Item -ItemType Directory -Path $DestinationPath -Force | Out-Null
        }

        # Copy all backed up files
        Write-Step "Copying project files..."
        Copy-Item -Path "$SourcePath\*" -Destination $DestinationPath -Recurse -Force

        Write-Success "Project directory restored to: $DestinationPath"
        return $true
    }
    catch {
        Write-ErrorMsg "Error restoring project directory`: $($_.Exception.Message)"
        return $false
    }
}

function Restore-FlowiseDirectory {
    param(
        [string]$SourcePath,
        [switch]$Force = $false
    )

    Write-Step "Restoring Flowise directory..."

    if (-not (Test-Path $SourcePath)) {
        Write-Warning "Flowise backup not found at: $SourcePath"
        return $false
    }

    $flowiseDest = Join-Path $env:USERPROFILE ".flowise"

    try {
        if (Test-Path $flowiseDest) {
            Write-Warning "Flowise directory already exists"
            if (-not $Force) {
                $response = Read-Host "Do you want to overwrite it? (yes/no)"
                if ($response -ne "yes") {
                    Write-Warning "Skipping Flowise restore"
                    return $false
                }
            } else {
                Write-Host "Force mode: overwriting existing Flowise directory" -ForegroundColor Cyan
            }
        }

        Copy-Item -Path $SourcePath -Destination $flowiseDest -Recurse -Force
        Write-Success "Flowise directory restored to: $flowiseDest"
        return $true
    }
    catch {
        Write-ErrorMsg "Error restoring Flowise`: $($_.Exception.Message)"
        return $false
    }
}

function Show-PostRestoreInstructions {
    Write-Header "Post-Restoration Instructions"

    Write-Host ""
    Write-Host "Next Steps to Complete Setup:" -ForegroundColor White
    Write-Host ""
    Write-Host "1. Navigate to project directory:" -ForegroundColor Yellow
    Write-Host "   cd `"$ProjectDestination`"" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Start the services (with your preferred GPU profile):" -ForegroundColor Yellow
    Write-Host "   python start_services.py --profile gpu-nvidia" -ForegroundColor Gray
    Write-Host "   OR" -ForegroundColor Gray
    Write-Host "   python start_services.py --profile cpu" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. Wait for services to start (~2-3 minutes)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "4. Ollama will automatically download models on first run:" -ForegroundColor Yellow
    Write-Host "   - qwen2.5:7b-instruct-q4_K_M (LLM)" -ForegroundColor Gray
    Write-Host "   - nomic-embed-text (embeddings)" -ForegroundColor Gray
    Write-Host "   This may take 30-60 minutes depending on your connection." -ForegroundColor Gray
    Write-Host ""
    Write-Host "5. Verify services are running:" -ForegroundColor Yellow
    Write-Host "   - n8n:       http://localhost:5678" -ForegroundColor Gray
    Write-Host "   - Open WebUI: http://localhost:8080" -ForegroundColor Gray
    Write-Host "   - Supabase:  http://localhost:8000" -ForegroundColor Gray
    Write-Host "   - Flowise:   http://localhost:3001" -ForegroundColor Gray
    Write-Host "   - Neo4j:     http://localhost:7474" -ForegroundColor Gray
    Write-Host ""
    Write-Host "6. Check container status:" -ForegroundColor Yellow
    Write-Host "   docker compose -p localai ps" -ForegroundColor Gray
    Write-Host ""
    Write-Host "7. If you encounter issues:" -ForegroundColor Yellow
    Write-Host "   - Check logs: docker compose -p localai logs -f <service-name>" -ForegroundColor Gray
    Write-Host "   - Restart service: docker compose -p localai restart <service-name>" -ForegroundColor Gray
    Write-Host ""
}

# ============================================
# MAIN SCRIPT EXECUTION
# ============================================

Write-Header "Docker Volume Restoration Script"

Write-Host "Restoration Configuration:" -ForegroundColor White
Write-Host "  Backup Location: $BackupLocation" -ForegroundColor White
Write-Host "  Project Destination: $ProjectDestination" -ForegroundColor White
Write-Host ""

# Check prerequisites
Test-DockerRunning
Test-BackupLocation

# Confirm before proceeding
Write-Host ""
Write-Host "IMPORTANT: This will restore Docker volumes and project files." -ForegroundColor Yellow
Write-Host "Any existing volumes with the same names will be prompted for overwrite." -ForegroundColor Yellow
Write-Host ""
if (-not $Force) {
    $confirm = Read-Host "Do you want to proceed with restoration? (yes/no)"
    if ($confirm -ne "yes") {
        Write-Host "Restoration cancelled by user." -ForegroundColor Red
        exit 0
    }
} else {
    Write-Host "Force mode enabled - proceeding without confirmation" -ForegroundColor Cyan
}

# Restore Docker volumes
Write-Header "Restoring Docker Volumes"

$volumeFiles = Get-ChildItem $VolumesBackupPath -Filter "*.tar.gz"
$successCount = 0
$failCount = 0

foreach ($volumeFile in $volumeFiles) {
    # Extract volume name by removing .tar.gz extension
    # BaseName only removes last extension, so we need to handle .tar.gz specially
    $volumeName = $volumeFile.Name -replace '\.tar\.gz$', ''
    if (Restore-DockerVolume -VolumeName $volumeName -BackupPath $VolumesBackupPath -Force:$Force) {
        $successCount++
    }
    else {
        $failCount++
    }
}

Write-Host ""
Write-Host "Docker Volumes: $successCount succeeded, $failCount failed/skipped" -ForegroundColor $(if ($failCount -eq 0) { "Green" } else { "Yellow" })

# Restore project files
if (-not $SkipProjectFiles) {
    Write-Header "Restoring Project Files"

    if (Restore-ProjectDirectory -SourcePath $ProjectBackupPath -DestinationPath $ProjectDestination -Force:$Force) {
        Write-Success "Project files restored successfully"
    }
    else {
        Write-Warning "Project files were not restored"
    }
}

# Restore Flowise directory
if (-not $SkipFlowise) {
    Write-Header "Restoring Flowise Directory"
    Restore-FlowiseDirectory -SourcePath $FlowiseBackupPath -Force:$Force
}

# Show next steps
Show-PostRestoreInstructions

# Final summary
Write-Header "Restoration Complete"

Write-Host ""
Write-Host "Restoration Summary:" -ForegroundColor White
Write-Host "  Volumes Restored: $successCount" -ForegroundColor Green
Write-Host "  Volumes Failed/Skipped: $failCount" -ForegroundColor $(if ($failCount -eq 0) { "Green" } else { "Yellow" })
Write-Host "  Project Location: $ProjectDestination" -ForegroundColor Green
Write-Host ""
Write-Host "You can now start the services with: python start_services.py --profile <cpu|gpu-nvidia|gpu-amd>" -ForegroundColor Cyan
Write-Host ""
