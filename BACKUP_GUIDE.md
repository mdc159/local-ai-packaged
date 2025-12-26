# Manual Docker Volume Backup Guide

This guide provides step-by-step manual commands for backing up your Docker volumes before reimaging your machine.

## Prerequisites

- Docker Desktop is running
- External backup drive is connected (e.g., `J:\My Backups`)
- PowerShell or Command Prompt with administrator privileges

## Quick Start (Automated)

**Recommended:** Use the automated backup script:

```powershell
cd X:\GitHub\local-ai-packaged
.\backup_docker_volumes.ps1
```

The script will automatically backup everything to `J:\My Backups\local-ai-backup_<timestamp>\`

## Manual Backup Instructions

If you prefer to backup manually or need to backup specific volumes, follow these steps:

### Step 1: Create Backup Directory

```powershell
$BackupRoot = "J:\My Backups\manual-backup-$(Get-Date -Format 'yyyy-MM-dd')"
New-Item -ItemType Directory -Path "$BackupRoot\docker-volumes" -Force
```

### Step 2: Backup Docker Named Volumes

#### Critical Volumes (MUST BACKUP)

**IMPORTANT:** Docker volumes are prefixed with the project name `localai_`. Use these exact names:

**1. localai_n8n_storage** (Workflows & Credentials)
```powershell
docker run --rm -v localai_n8n_storage:/source:ro -v "J:\My Backups\manual-backup-$(Get-Date -Format 'yyyy-MM-dd')\docker-volumes:/backup" alpine tar czf /backup/localai_n8n_storage.tar.gz -C /source .
```

**2. localai_open-webui** (Chat History)
```powershell
docker run --rm -v localai_open-webui:/source:ro -v "J:\My Backups\manual-backup-$(Get-Date -Format 'yyyy-MM-dd')\docker-volumes:/backup" alpine tar czf /backup/localai_open-webui.tar.gz -C /source .
```

**3. localai_qdrant_storage** (Vector Embeddings)
```powershell
docker run --rm -v localai_qdrant_storage:/source:ro -v "J:\My Backups\manual-backup-$(Get-Date -Format 'yyyy-MM-dd')\docker-volumes:/backup" alpine tar czf /backup/localai_qdrant_storage.tar.gz -C /source .
```

**4. localai_db-config** (Supabase Encryption Keys - CRITICAL!)
```powershell
docker run --rm -v localai_db-config:/source:ro -v "J:\My Backups\manual-backup-$(Get-Date -Format 'yyyy-MM-dd')\docker-volumes:/backup" alpine tar czf /backup/localai_db-config.tar.gz -C /source .
```

**5. localai_langfuse_postgres_data** (Observability Data)
```powershell
docker run --rm -v localai_langfuse_postgres_data:/source:ro -v "J:\My Backups\manual-backup-$(Get-Date -Format 'yyyy-MM-dd')\docker-volumes:/backup" alpine tar czf /backup/localai_langfuse_postgres_data.tar.gz -C /source .
```

**6. localai_langfuse_clickhouse_data** (Analytics)
```powershell
docker run --rm -v localai_langfuse_clickhouse_data:/source:ro -v "J:\My Backups\manual-backup-$(Get-Date -Format 'yyyy-MM-dd')\docker-volumes:/backup" alpine tar czf /backup/localai_langfuse_clickhouse_data.tar.gz -C /source .
```

**7. localai_langfuse_minio_data** (Event Logs)
```powershell
docker run --rm -v localai_langfuse_minio_data:/source:ro -v "J:\My Backups\manual-backup-$(Get-Date -Format 'yyyy-MM-dd')\docker-volumes:/backup" alpine tar czf /backup/localai_langfuse_minio_data.tar.gz -C /source .
```

**8. n8n-mcp_n8n-mcp-data** (n8n MCP Server Data)
```powershell
docker run --rm -v n8n-mcp_n8n-mcp-data:/source:ro -v "J:\My Backups\manual-backup-$(Get-Date -Format 'yyyy-MM-dd')\docker-volumes:/backup" alpine tar czf /backup/n8n-mcp_n8n-mcp-data.tar.gz -C /source .
```

#### Optional: Ollama Models (4-20 GB, can re-download)

**Only backup if you want to save download time:**

```powershell
docker run --rm -v localai_ollama_storage:/source:ro -v "J:\My Backups\manual-backup-$(Get-Date -Format 'yyyy-MM-dd')\docker-volumes:/backup" alpine tar czf /backup/localai_ollama_storage.tar.gz -C /source .
```

### Step 3: Backup Project Directory

**Critical directories and files:**

```powershell
# Set variables
$ProjectPath = "X:\GitHub\local-ai-packaged"
$BackupPath = "J:\My Backups\manual-backup-$(Get-Date -Format 'yyyy-MM-dd')\project"

# Backup Supabase PostgreSQL data (CRITICAL!)
Copy-Item "$ProjectPath\supabase\docker\volumes\db\data" -Destination "$BackupPath\supabase\docker\volumes\db\data" -Recurse -Force

# Backup Supabase storage (user files)
Copy-Item "$ProjectPath\supabase\docker\volumes\storage" -Destination "$BackupPath\supabase\docker\volumes\storage" -Recurse -Force

# Backup Neo4j data
Copy-Item "$ProjectPath\neo4j\data" -Destination "$BackupPath\neo4j\data" -Recurse -Force

# Backup Neo4j config
Copy-Item "$ProjectPath\neo4j\config" -Destination "$BackupPath\neo4j\config" -Recurse -Force

# Backup .env file (ALL SECRETS!)
Copy-Item "$ProjectPath\.env" -Destination "$BackupPath\.env" -Force

# Backup docker-compose files
Copy-Item "$ProjectPath\docker-compose.yml" -Destination "$BackupPath\docker-compose.yml" -Force
Copy-Item "$ProjectPath\docker-compose.override.private.yml" -Destination "$BackupPath\docker-compose.override.private.yml" -Force
Copy-Item "$ProjectPath\docker-compose.override.public.yml" -Destination "$BackupPath\docker-compose.override.public.yml" -Force

# Backup Caddyfile
Copy-Item "$ProjectPath\Caddyfile" -Destination "$BackupPath\Caddyfile" -Force

# Backup SearXNG settings
Copy-Item "$ProjectPath\searxng\settings.yml" -Destination "$BackupPath\searxng\settings.yml" -Force

# Backup n8n workflows (if exported)
Copy-Item "$ProjectPath\n8n\backup" -Destination "$BackupPath\n8n\backup" -Recurse -Force

# Backup shared directory
Copy-Item "$ProjectPath\shared" -Destination "$BackupPath\shared" -Recurse -Force
```

### Step 4: Backup Flowise Directory

```powershell
Copy-Item "$env:USERPROFILE\.flowise" -Destination "J:\My Backups\manual-backup-$(Get-Date -Format 'yyyy-MM-dd')\flowise" -Recurse -Force
```

### Step 5: Verify Backup

```powershell
# Check backed up volumes
Get-ChildItem "J:\My Backups\manual-backup-$(Get-Date -Format 'yyyy-MM-dd')\docker-volumes"

# Check project files
Get-ChildItem "J:\My Backups\manual-backup-$(Get-Date -Format 'yyyy-MM-dd')\project" -Recurse

# Check total backup size
$totalSize = (Get-ChildItem "J:\My Backups\manual-backup-$(Get-Date -Format 'yyyy-MM-dd')" -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1GB
Write-Host "Total backup size: $([math]::Round($totalSize, 2)) GB"
```

## Alternative: PostgreSQL Database Dump

For additional safety, you can also create a SQL dump of the Supabase database:

```powershell
# Dump all databases
docker exec supabase-db pg_dumpall -U postgres > "J:\My Backups\manual-backup-$(Get-Date -Format 'yyyy-MM-dd')\postgres_dump.sql"

# Or dump specific database
docker exec supabase-db pg_dump -U postgres -d postgres > "J:\My Backups\manual-backup-$(Get-Date -Format 'yyyy-MM-dd')\supabase_postgres.sql"
```

## Verification Checklist

Before proceeding with reimaging, verify you have:

- [ ] All Docker volume backups (*.tar.gz files)
- [ ] Supabase database data directory
- [ ] Neo4j data directory
- [ ] .env file with all secrets
- [ ] docker-compose.yml and override files
- [ ] Flowise directory from user home
- [ ] (Optional) PostgreSQL SQL dump
- [ ] Total backup size noted for restoration planning

## Troubleshooting

### Volume Not Found Error

If you get "Error: No such volume" when backing up:

```powershell
# List all volumes to find the correct name
docker volume ls

# Check if volume belongs to a specific project
docker volume ls | Select-String "localai"
```

### Permission Denied

If you get permission errors:

1. Stop all containers:
   ```powershell
   docker compose -p localai down
   ```

2. Retry the backup command

3. Restart containers:
   ```powershell
   python start_services.py --profile gpu-nvidia
   ```

### Backup Taking Too Long

If backup is very slow:

- Ollama models are large (4-20 GB). Consider skipping them.
- Vector databases (Qdrant) can be large depending on how many documents you've embedded.
- Neo4j graph database size depends on usage.

### Out of Space on Backup Drive

Priority order (skip lower priority items if needed):

1. **CRITICAL** (Must have):
   - n8n_storage
   - db-config (Supabase encryption keys)
   - .env file
   - supabase/docker/volumes/db/data

2. **HIGH** (Should have):
   - open-webui
   - qdrant_storage
   - neo4j/data
   - Flowise directory

3. **MEDIUM** (Nice to have):
   - langfuse_* volumes
   - Docker configs

4. **OPTIONAL** (Can skip):
   - ollama_storage (can re-download)
   - valkey-data (cache only)

## Next Steps

After completing the backup:

1. Create a backup manifest listing all backed up items
2. Verify backup integrity by checking file sizes
3. Keep the external drive safe during reimaging
4. Follow the `RESTORATION_GUIDE.md` after reimaging

## Quick Reference: All-in-One Backup Command

```powershell
# This backs up all critical volumes in one command
$volumes = @("localai_n8n_storage", "localai_open-webui", "localai_qdrant_storage", "localai_db-config", "localai_langfuse_postgres_data", "localai_langfuse_clickhouse_data", "localai_langfuse_minio_data", "n8n-mcp_n8n-mcp-data")
$backup = "J:\My Backups\manual-backup-$(Get-Date -Format 'yyyy-MM-dd')\docker-volumes"
New-Item -ItemType Directory -Path $backup -Force | Out-Null

foreach ($vol in $volumes) {
    Write-Host "Backing up $vol..."
    docker run --rm -v "${vol}:/source:ro" -v "${backup}:/backup" alpine tar czf "/backup/${vol}.tar.gz" -C /source .
}

Write-Host "All volumes backed up to: $backup"
```

## Support

If you encounter issues:

1. Check Docker is running: `docker info`
2. Check volume exists: `docker volume ls | Select-String "volume-name"`
3. Check backup destination is writable: `Test-Path "J:\My Backups"`
4. Review Docker logs: `docker logs <container-name>`
