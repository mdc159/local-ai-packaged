# Docker Volume Restoration Guide

Complete guide for restoring your Local AI Package after reimaging your machine.

## Overview

This guide walks you through:
1. Reinstalling required software
2. Restoring Docker volumes
3. Restoring project files
4. Starting services
5. Verifying everything works

**Estimated Time:** 1-2 hours (including Ollama model downloads)

## Prerequisites

Before starting restoration, ensure you have:

- [ ] Backup drive connected with your backup (e.g., `J:\My Backups\local-ai-backup_<timestamp>`)
- [ ] Fresh Windows installation completed
- [ ] Administrator access to the machine
- [ ] Internet connection (for downloading Docker, Python, and Ollama models)

## Phase 1: Install Required Software

### 1.1 Install Docker Desktop

1. Download Docker Desktop for Windows:
   - Visit: https://www.docker.com/products/docker-desktop
   - Download the Windows installer

2. Install Docker Desktop:
   - Run the installer
   - Enable WSL 2 backend when prompted
   - Enable Hyper-V if required
   - Restart computer if prompted

3. Configure Docker Desktop:
   - Open Docker Desktop
   - Go to Settings → General
   - Enable "Expose daemon on tcp://localhost:2375 without TLS"
   - Go to Settings → Resources
   - Allocate at least 8 GB RAM (16 GB recommended)
   - Allocate at least 4 CPU cores

4. Verify Docker is running:
   ```powershell
   docker info
   docker version
   ```

### 1.2 Install Python

1. Download Python 3.11 or later:
   - Visit: https://www.python.org/downloads/
   - Download Windows installer

2. Install Python:
   - **IMPORTANT:** Check "Add Python to PATH"
   - Choose "Install Now"

3. Verify installation:
   ```powershell
   python --version
   pip --version
   ```

### 1.3 Install Git (if not already installed)

1. Download Git for Windows:
   - Visit: https://git-scm.com/download/win

2. Install with default settings

3. Verify:
   ```powershell
   git --version
   ```

## Phase 2: Restore Project Files

### 2.1 Clone Repository (or Restore from Backup)

**Option A: Clone from Git (if you have a remote repository)**

```powershell
cd X:\GitHub
git clone <your-repo-url> local-ai-packaged
cd local-ai-packaged
```

**Option B: Restore from Backup**

```powershell
# Use the automated restoration script
$BackupLocation = "J:\My Backups\local-ai-backup_<timestamp>"
cd <path-to-where-you-have-the-restore-script>

# If you backed up the scripts to external drive:
.\restore_docker_volumes.ps1 -BackupLocation $BackupLocation -ProjectDestination "X:\GitHub\local-ai-packaged"
```

**Option C: Manual Restoration**

If you prefer manual restoration, continue with the steps below.

### 2.2 Manual Project Files Restoration

```powershell
# Set variables
$BackupPath = "J:\My Backups\local-ai-backup_<timestamp>\project"
$ProjectPath = "X:\GitHub\local-ai-packaged"

# Create project directory
New-Item -ItemType Directory -Path $ProjectPath -Force

# Restore all project files
Copy-Item -Path "$BackupPath\*" -Destination $ProjectPath -Recurse -Force

# Verify critical files exist
Test-Path "$ProjectPath\.env"  # Should return True
Test-Path "$ProjectPath\docker-compose.yml"  # Should return True
```

### 2.3 Restore Flowise Directory

```powershell
$BackupPath = "J:\My Backups\local-ai-backup_<timestamp>\flowise"

# Restore to user home directory
Copy-Item -Path $BackupPath -Destination "$env:USERPROFILE\.flowise" -Recurse -Force
```

## Phase 3: Restore Docker Volumes

### 3.1 Using Automated Restoration Script

```powershell
cd X:\GitHub\local-ai-packaged
.\restore_docker_volumes.ps1 -BackupLocation "J:\My Backups\local-ai-backup_<timestamp>"
```

The script will:
- Validate backup location
- Show backup manifest
- Prompt for confirmation
- Restore all Docker volumes
- Restore project files (if not already done)
- Restore Flowise directory
- Show next steps

### 3.2 Manual Docker Volume Restoration

If you prefer manual restoration:

```powershell
$BackupPath = "J:\My Backups\local-ai-backup_<timestamp>\docker-volumes"

# Restore each volume
$volumes = @("n8n_storage", "open-webui", "qdrant_storage", "db-config", "langfuse_postgres_data", "langfuse_clickhouse_data", "langfuse_minio_data")

foreach ($vol in $volumes) {
    Write-Host "Restoring $vol..."

    # Create volume
    docker volume create $vol

    # Restore data
    docker run --rm -v "${vol}:/target" -v "${BackupPath}:/backup" alpine tar xzf "/backup/${vol}.tar.gz" -C /target

    Write-Host "✓ Restored $vol"
}
```

### 3.3 Verify Volume Restoration

```powershell
# List all volumes
docker volume ls

# Check specific volume
docker volume inspect n8n_storage
```

## Phase 4: Start Services

### 4.1 Navigate to Project Directory

```powershell
cd X:\GitHub\local-ai-packaged
```

### 4.2 Verify Configuration

```powershell
# Check .env file exists and has correct values
Get-Content .env | Select-String "N8N_ENCRYPTION_KEY"
Get-Content .env | Select-String "POSTGRES_PASSWORD"
```

### 4.3 Start Services

**For GPU (Nvidia) systems:**
```powershell
python start_services.py --profile gpu-nvidia
```

**For CPU-only systems:**
```powershell
python start_services.py --profile cpu
```

**For AMD GPU systems:**
```powershell
python start_services.py --profile gpu-amd
```

**For Mac with native Ollama:**
```powershell
python start_services.py --profile none
```

### 4.4 Wait for Startup

The startup script will:
1. Clone/update Supabase repo
2. Stop existing containers (if any)
3. Start Supabase stack
4. Wait 10 seconds
5. Start AI services stack

**Expected startup time:** 2-3 minutes

### 4.5 Monitor Startup

Open a new terminal and watch the logs:

```powershell
# Watch all services
docker compose -p localai logs -f

# Watch specific service
docker compose -p localai logs -f n8n
docker compose -p localai logs -f ollama
```

## Phase 5: Ollama Model Downloads

### 5.1 Automatic Model Pulls

The `ollama-pull-*` init containers will automatically download:
- `qwen2.5:7b-instruct-q4_K_M` (LLM - ~4.7 GB)
- `nomic-embed-text` (Embeddings - ~274 MB)

**Expected download time:** 30-60 minutes depending on internet speed

### 5.2 Monitor Model Downloads

```powershell
# Check Ollama logs
docker compose -p localai logs -f ollama-pull-llama-cpu
# OR
docker compose -p localai logs -f ollama-pull-llama-gpu

# Check downloaded models
docker exec ollama ollama list
```

### 5.3 Verify Models

Once downloaded, you should see:

```
NAME                              ID              SIZE      MODIFIED
qwen2.5:7b-instruct-q4_K_M        <id>           4.7 GB    X minutes ago
nomic-embed-text:latest           <id>           274 MB    X minutes ago
```

## Phase 6: Verify Services

### 6.1 Check Container Status

```powershell
docker compose -p localai ps
```

All containers should show "Up" or "healthy" status.

### 6.2 Access Web Interfaces

Open your browser and verify these services are accessible:

- **n8n**: http://localhost:5678
  - Should show login page
  - Login with your credentials
  - Verify workflows are present

- **Open WebUI**: http://localhost:8080
  - Should show chat interface
  - Verify chat history is restored

- **Supabase Studio**: http://localhost:8000
  - Should show Supabase dashboard
  - Login with credentials from .env

- **Flowise**: http://localhost:3001
  - Should show Flowise interface
  - Verify chatflows are present

- **Neo4j Browser**: http://localhost:7474
  - Login with credentials from .env (NEO4J_AUTH)
  - Verify graph data is present

- **Langfuse**: http://localhost:3000
  - Should show Langfuse dashboard

- **Qdrant Dashboard**: http://localhost:6333/dashboard
  - Should show collections

### 6.3 Test n8n Workflows

1. Open n8n at http://localhost:5678
2. Open a workflow
3. Click "Test workflow"
4. Verify it executes successfully

### 6.4 Test Ollama

```powershell
# Test Ollama is responding
curl http://localhost:11434/api/generate -Method Post -Body '{"model": "qwen2.5:7b-instruct-q4_K_M", "prompt": "Hello", "stream": false}' -ContentType "application/json"
```

### 6.5 Test Database Connections

```powershell
# Test Supabase PostgreSQL
docker exec supabase-db psql -U postgres -c "\l"

# Test Neo4j
docker exec neo4j cypher-shell -u neo4j -p <your-password> "MATCH (n) RETURN count(n);"
```

## Phase 7: Troubleshooting

### Common Issues

#### Services Not Starting

**Symptom:** Containers keep restarting

**Solution:**
```powershell
# Check logs for specific service
docker compose -p localai logs <service-name>

# Common issues:
# - Check .env file has correct values
# - Ensure ports are not already in use
# - Verify Docker has enough resources allocated
```

#### n8n Shows No Workflows

**Symptom:** n8n interface is empty

**Solution:**
1. Check n8n_storage volume was restored:
   ```powershell
   docker volume inspect n8n_storage
   ```

2. Check n8n can access the volume:
   ```powershell
   docker compose -p localai logs n8n | Select-String "error"
   ```

3. If needed, restore workflows from JSON backup in `n8n/backup/` directory

#### Supabase Database Errors

**Symptom:** Connection errors or empty database

**Solution:**
1. Verify db-config volume was restored (contains encryption keys):
   ```powershell
   docker volume inspect db-config
   ```

2. Check PostgreSQL data directory:
   ```powershell
   Test-Path "X:\GitHub\local-ai-packaged\supabase\docker\volumes\db\data"
   ```

3. Check PostgreSQL logs:
   ```powershell
   docker compose -p localai logs db
   ```

#### Ollama Models Not Downloading

**Symptom:** Ollama pull containers fail or timeout

**Solution:**
1. Check Ollama service is running:
   ```powershell
   docker compose -p localai ps ollama
   ```

2. Pull models manually:
   ```powershell
   docker exec ollama ollama pull qwen2.5:7b-instruct-q4_K_M
   docker exec ollama ollama pull nomic-embed-text
   ```

3. Check available disk space (need ~5 GB free)

#### Neo4j Connection Errors

**Symptom:** Cannot connect to Neo4j

**Solution:**
1. Verify neo4j/data was restored
2. Check NEO4J_AUTH in .env matches your backup
3. Check Neo4j logs:
   ```powershell
   docker compose -p localai logs neo4j
   ```

#### Qdrant No Collections

**Symptom:** Qdrant dashboard shows no collections

**Solution:**
1. Verify qdrant_storage volume was restored:
   ```powershell
   docker volume inspect qdrant_storage
   ```

2. Collections will appear if volume was properly restored

#### Open WebUI No Chat History

**Symptom:** Open WebUI is empty

**Solution:**
1. Verify open-webui volume was restored:
   ```powershell
   docker volume inspect open-webui
   ```

2. Check Open WebUI logs:
   ```powershell
   docker compose -p localai logs open-webui
   ```

### Nuclear Option: Full Reset

If nothing works, you can reset and try again:

```powershell
# Stop all services
docker compose -p localai down -v

# Remove all volumes (DESTRUCTIVE)
docker volume prune -f

# Restore volumes again using the script
.\restore_docker_volumes.ps1 -BackupLocation "J:\My Backups\local-ai-backup_<timestamp>"

# Start services
python start_services.py --profile gpu-nvidia
```

## Phase 8: Post-Restoration Tasks

### 8.1 Update Docker Images (Optional)

After verifying everything works, you may want to update to latest images:

```powershell
docker compose -p localai down
docker compose -p localai pull
python start_services.py --profile gpu-nvidia
```

### 8.2 Update n8n-mcp Configuration

If using Claude Desktop integration:

1. Update Claude Desktop config with new container name
2. Restart Claude Desktop
3. Test MCP connection

### 8.3 Verify Backups Are Working

Set up regular backups going forward:

```powershell
# Schedule weekly backups (optional)
# Use Windows Task Scheduler to run backup script weekly
```

### 8.4 Test Critical Workflows

Go through your important n8n workflows and test them:
- Verify database connections work
- Verify Ollama LLM calls work
- Verify vector search works (Qdrant/Supabase)
- Verify external API integrations work

## Success Checklist

You've successfully restored everything if:

- [ ] Docker Desktop is running
- [ ] All containers show "Up" or "healthy" status
- [ ] n8n shows all your workflows
- [ ] Open WebUI shows chat history
- [ ] Supabase Studio is accessible with data
- [ ] Flowise shows your chatflows
- [ ] Neo4j contains your graph data
- [ ] Qdrant shows your collections
- [ ] Ollama has downloaded models
- [ ] Test workflows execute successfully
- [ ] All web interfaces are accessible

## Getting Help

If you encounter issues:

1. **Check logs first:**
   ```powershell
   docker compose -p localai logs -f <service-name>
   ```

2. **Check container status:**
   ```powershell
   docker compose -p localai ps
   ```

3. **Check volume status:**
   ```powershell
   docker volume ls
   docker volume inspect <volume-name>
   ```

4. **Review the manifest:**
   Check `backup_manifest.txt` in your backup directory to see what was backed up

5. **Consult project documentation:**
   - README.md
   - CLAUDE.md
   - Individual service documentation

## Cleanup

Once you've verified everything works, you can:

1. Keep the backup on the external drive for safety (recommended)
2. Create a new backup from the restored system
3. Remove old backup after verifying new one works

## Maintenance

Going forward:

- Run backups regularly (weekly recommended)
- Keep external backup drive in safe location
- Document any configuration changes
- Update .env.example if you add new secrets

---

**Congratulations!** Your Local AI Package has been successfully restored. You can now continue using all your AI services with your data intact.
