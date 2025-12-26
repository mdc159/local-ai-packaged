# Docker Volume Backup Script for Local AI Package
# This script backs up all critical Docker volumes and project data before reimaging

param(
    [string]$BackupDestination = "J:\My Backups",
    [switch]$SkipProjectFiles = $false,
    [switch]$SkipFlowise = $false
)

$ErrorActionPreference = "Stop"

# Configuration
$Timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$BackupRoot = Join-Path $BackupDestination "local-ai-backup_$Timestamp"
$VolumesBackupPath = Join-Path $BackupRoot "docker-volumes"
$ProjectBackupPath = Join-Path $BackupRoot "local-ai-packaged"
$FlowiseBackupPath = Join-Path $BackupRoot "flowise"
$ManifestPath = Join-Path $BackupRoot "backup_manifest.txt"

# Docker volumes to backup (excluding ollama_storage as per user preference)
# Note: Volumes are prefixed with the Docker Compose project name 'localai_'
$CriticalVolumes = @(
    "localai_n8n_storage",
    "localai_open-webui",
    "localai_qdrant_storage",
    "localai_langfuse_postgres_data",
    "localai_langfuse_clickhouse_data",
    "localai_langfuse_minio_data",
    "localai_db-config",  # Supabase encryption keys - CRITICAL
    "n8n-mcp_n8n-mcp-data"  # n8n-mcp server data
)

# Optional volumes (cache, can skip if space constrained)
$OptionalVolumes = @(
    "localai_valkey-data"
)

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
        Write-ErrorMsg "Failed to connect to Docker: $($_.Exception.Message)"
        exit 1
    }
}

function Backup-DockerVolume {
    param(
        [string]$VolumeName,
        [string]$BackupPath
    )

    Write-Step "Backing up volume: $VolumeName"

    # Check if volume exists
    $volumeExists = docker volume ls -q | Select-String -Pattern "^${VolumeName}$"
    if (-not $volumeExists) {
        Write-Warning "Volume '$VolumeName' does not exist, skipping..."
        return $false
    }

    $backupFile = Join-Path $BackupPath "${VolumeName}.tar.gz"

    try {
        # Use alpine container to backup volume
        $dockerCmd = "docker run --rm -v ${VolumeName}:/source:ro -v `"${BackupPath}:/backup`" alpine tar czf /backup/${VolumeName}.tar.gz -C /source ."
        Invoke-Expression $dockerCmd

        if ($LASTEXITCODE -eq 0 -and (Test-Path $backupFile)) {
            $fileSize = (Get-Item $backupFile).Length / 1MB
            Write-Success "Backed up $VolumeName (${fileSize:N2} MB)"
            return $true
        }
        else {
            Write-ErrorMsg "Failed to backup $VolumeName"
            return $false
        }
    }
    catch {
        Write-ErrorMsg "Error backing up $VolumeName`: $($_.Exception.Message)"
        return $false
    }
}

function Backup-ProjectDirectory {
    param(
        [string]$SourcePath,
        [string]$DestinationPath
    )

    Write-Step "Backing up project directory..."

    try {
        # Critical directories and files to backup
        $itemsToBackup = @(
            "supabase\docker\volumes\db\data",
            "supabase\docker\volumes\storage",
            "neo4j\data",
            "neo4j\config",
            "neo4j\plugins",
            ".env",
            "docker-compose.yml",
            "docker-compose.override.private.yml",
            "docker-compose.override.public.yml",
            "Caddyfile",
            "caddy-addon",
            "searxng\settings.yml",
            "n8n\backup",
            "shared",
            "start_services.py",
            "README.md",
            "CLAUDE.md"
        )

        foreach ($item in $itemsToBackup) {
            $sourcePath = Join-Path $SourcePath $item
            if (Test-Path $sourcePath) {
                $destPath = Join-Path $DestinationPath $item
                $destDir = Split-Path $destPath -Parent

                if (-not (Test-Path $destDir)) {
                    New-Item -ItemType Directory -Path $destDir -Force | Out-Null
                }

                if (Test-Path $sourcePath -PathType Container) {
                    Write-Step "Copying directory: $item"
                    Copy-Item -Path $sourcePath -Destination $destPath -Recurse -Force
                }
                else {
                    Write-Step "Copying file: $item"
                    Copy-Item -Path $sourcePath -Destination $destPath -Force
                }
                Write-Success "Backed up: $item"
            }
            else {
                Write-Warning "Path not found, skipping: $item"
            }
        }

        return $true
    }
    catch {
        Write-ErrorMsg "Error backing up project directory`: $($_.Exception.Message)"
        return $false
    }
}

function Backup-FlowiseDirectory {
    param([string]$DestinationPath)

    Write-Step "Backing up Flowise directory..."

    $flowiseSource = Join-Path $env:USERPROFILE ".flowise"

    if (Test-Path $flowiseSource) {
        try {
            Copy-Item -Path $flowiseSource -Destination $DestinationPath -Recurse -Force
            Write-Success "Backed up Flowise directory"
            return $true
        }
        catch {
            Write-ErrorMsg "Error backing up Flowise`: $($_.Exception.Message)"
            return $false
        }
    }
    else {
        Write-Warning "Flowise directory not found at: $flowiseSource"
        return $false
    }
}

function Create-BackupManifest {
    param([string]$ManifestPath)

    Write-Step "Creating backup manifest..."

    $manifest = @"
=================================================
Docker Volume Backup Manifest
=================================================
Backup Date: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Backup Location: $BackupRoot
Machine Name: $env:COMPUTERNAME
User: $env:USERNAME

=================================================
BACKED UP DOCKER VOLUMES
=================================================
"@

    Get-ChildItem $VolumesBackupPath -Filter "*.tar.gz" | ForEach-Object {
        $size = $_.Length / 1MB
        $manifest += "`n$($_.Name) - ${size:N2} MB"
    }

    $manifest += @"

=================================================
PROJECT FILES BACKED UP
=================================================
"@

    if (Test-Path $ProjectBackupPath) {
        Get-ChildItem $ProjectBackupPath -Recurse -File | ForEach-Object {
            $relativePath = $_.FullName.Replace($ProjectBackupPath, "").TrimStart('\')
            $manifest += "`n$relativePath"
        }
    }

    $manifest += @"

=================================================
FLOWISE DIRECTORY
=================================================
"@

    if (Test-Path $FlowiseBackupPath) {
        $manifest += "`nFlowise directory backed up successfully"
    }
    else {
        $manifest += "`nFlowise directory not found or skipped"
    }

    $totalSize = (Get-ChildItem $BackupRoot -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1GB

    $manifest += @"

=================================================
BACKUP SUMMARY
=================================================
Total Backup Size: ${totalSize:N2} GB
Backup Completed: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

=================================================
RESTORATION NOTES
=================================================
1. After reimaging, install Docker Desktop
2. Clone the repository to desired location
3. Run restore_docker_volumes.ps1 with this backup location
4. Ollama models will be re-downloaded automatically on first start

=================================================
"@

    $manifest | Out-File -FilePath $ManifestPath -Encoding UTF8
    Write-Success "Manifest created at: $ManifestPath"
}

# ============================================
# MAIN SCRIPT EXECUTION
# ============================================

Write-Header "Docker Volume Backup Script"

Write-Host "Backup Configuration:" -ForegroundColor White
Write-Host "  Destination: $BackupDestination" -ForegroundColor White
Write-Host "  Backup Root: $BackupRoot" -ForegroundColor White
Write-Host "  Timestamp: $Timestamp" -ForegroundColor White
Write-Host ""

# Check prerequisites
Test-DockerRunning

# Check backup destination
Write-Step "Checking backup destination..."
if (-not (Test-Path $BackupDestination)) {
    Write-ErrorMsg "Backup destination does not exist: $BackupDestination"
    Write-Host "Please ensure your external drive is connected and the path is correct."
    exit 1
}
Write-Success "Backup destination is accessible"

# Create backup directories
Write-Step "Creating backup directories..."
New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
New-Item -ItemType Directory -Path $VolumesBackupPath -Force | Out-Null
Write-Success "Backup directories created"

# Backup Docker volumes
Write-Header "Backing Up Docker Volumes"

$successCount = 0
$failCount = 0

foreach ($volume in $CriticalVolumes) {
    if (Backup-DockerVolume -VolumeName $volume -BackupPath $VolumesBackupPath) {
        $successCount++
    }
    else {
        $failCount++
    }
}

Write-Host ""
Write-Host "Docker Volumes: $successCount succeeded, $failCount failed" -ForegroundColor $(if ($failCount -eq 0) { "Green" } else { "Yellow" })

# Backup project files
if (-not $SkipProjectFiles) {
    Write-Header "Backing Up Project Files"
    $projectPath = $PSScriptRoot  # Use the directory where this script is located

    if (Backup-ProjectDirectory -SourcePath $projectPath -DestinationPath $ProjectBackupPath) {
        Write-Success "Project files backed up successfully"
    }
    else {
        Write-Warning "Some project files may not have been backed up"
    }
}

# Backup Flowise directory
if (-not $SkipFlowise) {
    Write-Header "Backing Up Flowise Directory"
    Backup-FlowiseDirectory -DestinationPath $FlowiseBackupPath
}

# Create manifest
Write-Header "Creating Backup Manifest"
Create-BackupManifest -ManifestPath $ManifestPath

# Final summary
Write-Header "Backup Complete"

$totalSize = (Get-ChildItem $BackupRoot -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1GB

Write-Host ""
Write-Host "Backup Summary:" -ForegroundColor White
Write-Host "  Location: $BackupRoot" -ForegroundColor Green
Write-Host "  Total Size: ${totalSize:N2} GB" -ForegroundColor Green
Write-Host "  Manifest: $ManifestPath" -ForegroundColor Green
Write-Host ""
Write-Host "IMPORTANT: Keep this backup safe until you have verified restoration!" -ForegroundColor Yellow
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor White
Write-Host "  1. Verify backup manifest at: $ManifestPath" -ForegroundColor White
Write-Host "  2. Proceed with reimaging your machine" -ForegroundColor White
Write-Host "  3. After reimage, use restore_docker_volumes.ps1 to restore" -ForegroundColor White
Write-Host ""
