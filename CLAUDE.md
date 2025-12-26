# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a self-hosted AI package that combines multiple AI/LLM services using Docker Compose. It's a fork of n8n's self-hosted AI starter kit with added services including Supabase, Open WebUI, Flowise, Neo4j, Langfuse, SearXNG, and Caddy.

The package provides a complete local AI development environment for building AI agents and workflows without relying on external cloud services.

## Architecture

### Service Organization

The project uses a unified Docker Compose setup with two main layers:

1. **Supabase Stack** (`supabase/docker/docker-compose.yml`): Database and backend services including PostgreSQL, Kong API gateway, Supabase Studio, and pooler services
2. **AI Services Stack** (`docker-compose.yml`): All AI and application services

Both stacks share the same Docker Compose project name (`localai`) so they appear together in Docker Desktop.

### Key Services

Private mode port mappings (localhost only) are shown in parentheses. In public mode, all services are accessed via Caddy (ports 80/443).

- **n8n**: Low-code workflow automation platform (5678) - primary orchestration tool for AI agents
- **n8n-mcp**: n8n Model Context Protocol server (3002) - allows Claude Desktop to interact with n8n workflows
- **Docling**: Advanced document parser (5001) - converts PDFs, DOCX, PPTX, XLSX, images to Markdown/JSON for RAG
- **Graphiti**: Temporal knowledge graph service (5002) - builds episodic memory and entity relationships with Neo4j
- **Ollama**: Local LLM runtime (11434) - runs models like qwen2.5:7b-instruct-q4_K_M
- **Open WebUI**: ChatGPT-like interface (8080) - interacts with n8n agents via `n8n_pipe.py`
- **Supabase**: Database, vector store, and auth (Kong API on port 8000)
- **Flowise**: No-code AI agent builder (3001)
- **Qdrant**: Vector database (6333/6334) - alternative to Supabase for vector storage
- **Neo4j**: Graph database (7474/7687) - for GraphRAG, LightRAG, Graphiti
- **Langfuse**: LLM observability platform (web: 3000, worker: 3030, minio: 9010/9011, clickhouse: 8123/9000/9009)
- **SearXNG**: Privacy-focused metasearch engine (8081)
- **Postgres**: Dedicated Postgres for Langfuse (5433) - separate from Supabase's Postgres
- **Redis/Valkey**: Cache for n8n and Langfuse (6379)
- **Caddy**: Reverse proxy with automatic HTTPS (80/443)

### Docker Profiles

The project supports GPU acceleration via Docker Compose profiles:
- `cpu`: CPU-only mode
- `gpu-nvidia`: Nvidia GPU support
- `gpu-amd`: AMD GPU (ROCm) support
- `none`: No Ollama container (for running Ollama natively on Mac)

### Environment Modes

Two deployment modes controlled by `start_services.py --environment`:

- `private` (default): All service ports exposed on localhost for development
  - Uses `docker-compose.override.private.yml` to map all ports to `0.0.0.0` (binds to all interfaces)
  - **WSL2 Compatibility**: Ports are bound to `0.0.0.0` instead of `127.0.0.1` to avoid WSL2 port forwarding bug that causes "500 Internal Server Error"
  - Security is maintained by Windows Firewall which blocks external access by default
  - Direct access to all services without going through Caddy
  - Best for local development and debugging
- `public`: Only ports 80/443 exposed, Caddy handles routing with HTTPS
  - Uses `docker-compose.override.public.yml` to close most ports
  - All services accessed through Caddy reverse proxy
  - Required for production deployments with custom domains

## Common Commands

### Platform Notes

- **Windows**: Use PowerShell for all commands and scripts
- **Linux/macOS**: The `start_services.py` script works cross-platform
- **WSL2**: Recommended for Windows GPU support with Docker Desktop

### Starting Services

```bash
# Start with specific GPU profile (cpu, gpu-nvidia, gpu-amd, none)
python start_services.py --profile gpu-nvidia

# Start in public mode (production)
python start_services.py --profile gpu-nvidia --environment public
```

The startup script:
1. Clones/updates Supabase repo (sparse checkout of `docker/` folder)
2. Copies `.env` to `supabase/docker/.env`
3. Generates SearXNG secret key
4. Stops existing containers
5. Starts Supabase stack
6. **Actively polls Supabase health** (max 180s, checking every 10s via Kong API gateway)
7. Starts AI services stack with **automatic retry logic** (up to 3 attempts with 15s delays)

### Stopping Services

```bash
# Stop all services for a profile
docker compose -p localai -f docker-compose.yml --profile <profile> down
```

### Upgrading Containers

```bash
# Pull latest images and restart
docker compose -p localai -f docker-compose.yml --profile <profile> down
docker compose -p localai -f docker-compose.yml --profile <profile> pull
python start_services.py --profile <profile>
```

### Direct Docker Compose Commands

```bash
# View logs for specific service
docker compose -p localai logs -f n8n

# Restart a single service
docker compose -p localai restart open-webui

# View running containers
docker compose -p localai ps
```

## Configuration

### Environment Variables

Required secrets in `.env` (see `.env.example`):
- **N8N**: `N8N_ENCRYPTION_KEY`, `N8N_USER_MANAGEMENT_JWT_SECRET` (generate with `openssl rand -hex 32`)
- **N8N MCP**: `N8N_API_KEY` (create in n8n Settings → API), `N8N_MCP_AUTH_TOKEN` (generate with `openssl rand -base64 32`)
- **Supabase**: `POSTGRES_PASSWORD`, `JWT_SECRET`, `ANON_KEY`, `SERVICE_ROLE_KEY`, `DASHBOARD_USERNAME`, `DASHBOARD_PASSWORD`, `POOLER_TENANT_ID`
- **Neo4j**: `NEO4J_AUTH` (format: `username/password`)
- **Langfuse**: `CLICKHOUSE_PASSWORD`, `MINIO_ROOT_PASSWORD`, `LANGFUSE_SALT`, `NEXTAUTH_SECRET`, `ENCRYPTION_KEY`

Optional production Caddy config:
- `N8N_HOSTNAME`, `WEBUI_HOSTNAME`, `FLOWISE_HOSTNAME`, `SUPABASE_HOSTNAME`, `LANGFUSE_HOSTNAME`, `N8N_MCP_HOSTNAME`, `NEO4J_HOSTNAME`, `DOCLING_HOSTNAME`, `GRAPHITI_HOSTNAME`
- `LETSENCRYPT_EMAIL`

### Service Connections

When configuring credentials in n8n:
- **Ollama**: `http://ollama:11434` (or `http://host.docker.internal:11434` if running Ollama natively on Mac)
- **Docling**: `http://docling:5001` (API endpoint: `/v1/convert`)
- **Graphiti**: `http://graphiti:5002` (API endpoints: `/v1/episodes`, `/v1/search`, `/v1/entities/search`)
- **Postgres (Supabase)**: Host is `db` (not localhost), use credentials from `.env`
- **Qdrant**: `http://qdrant:6333`
- **Neo4j**: `bolt://neo4j:7687` or `http://neo4j:7474`

## Important Implementation Details

### N8N and Open WebUI Integration

The `n8n_pipe.py` file is an Open WebUI function/pipe that:
1. Extracts the last message from Open WebUI chat
2. Sends it to an n8n webhook URL with session ID
3. Returns n8n's response to the chat

Setup requires:
1. Creating a workflow in n8n with a webhook trigger (copy the "Production" webhook URL)
2. Installing the function in Open WebUI (Workspace → Functions → Add Function)
3. Setting the `n8n_url` in the function's gear icon settings
4. Toggling the function on to use it as a model

### Pre-configured Workflows

Three n8n workflows are auto-imported from `n8n/backup/workflows/`:

- `V1_Local_RAG_AI_Agent.json`: Basic RAG agent
- `V2_Local_Supabase_RAG_AI_Agent.json`: RAG with Supabase vector store
- `V3_Local_Agentic_RAG_AI_Agent.json`: Advanced agentic RAG

The `n8n-import` service runs these imports before the main n8n service starts.

**Testing workflows:**

1. Open n8n at <http://localhost:5678> (or your configured domain)
2. Navigate to the workflow you want to test
3. Set up credentials for any required services (Ollama, Supabase/Postgres, Qdrant)
4. Use the "Test workflow" button to execute manually
5. Toggle the workflow to "Active" to enable webhook triggers
6. Copy the "Production" webhook URL for integration with Open WebUI

### Shared Volume

The `./shared` directory is mounted to `/data/shared` inside the n8n container for accessing local files. Use this path in n8n nodes like Read/Write Files from Disk, Local File Trigger, or Execute Command.

### Supabase Repository Management

The Supabase repo is cloned using sparse checkout to only get the `docker/` directory, reducing download size. The `start_services.py` script handles this automatically.

**Note:** The Supabase directory may appear as a modified submodule in git status (`m supabase`). This is expected as the `start_services.py` script manages it independently from git.

### SearXNG Secret Key

On first run, `start_services.py` copies `searxng/settings-base.yml` to `searxng/settings.yml` and replaces `ultrasecretkey` with a generated random value. The script handles platform differences (Windows PowerShell, macOS, Linux).

### Caddy Reverse Proxy

Caddy configuration in `Caddyfile`:
- Uses environment variables for hostnames (default to `:800X` ports for local dev)
- Automatically provisions Let's Encrypt certificates when domain names are provided
- Falls back to HTTP for localhost/port-based addresses
- Imports additional config from `caddy-addon/*.conf`

### Ollama Model Loading

The init containers (`ollama-pull-llama-*`) automatically pull:
- `qwen2.5:7b-instruct-q4_K_M` (default LLM)
- `nomic-embed-text` (embeddings)

These run after the Ollama service starts and complete before n8n becomes available.

### Password Special Characters

Avoid using `@` symbols in `POSTGRES_PASSWORD` as they can cause connection issues with Supabase Kong. If using special characters, remember to percent-encode them in connection strings.

### N8N MCP Server Integration

The n8n-mcp service allows Claude Desktop to interact with n8n workflows via the Model Context Protocol (MCP).

**Setup steps:**

1. Generate required credentials in `.env`:
   - `N8N_API_KEY`: Create in n8n at Settings → API
   - `N8N_MCP_AUTH_TOKEN`: Generate with `openssl rand -base64 32`

2. Configure Claude Desktop:
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`

   Add this configuration:

   ```json
   {
     "mcpServers": {
       "n8n-mcp": {
         "command": "docker",
         "args": ["exec", "-i", "n8n-mcp", "node", "dist/mcp/index.js"]
       }
     }
   }
   ```

3. Restart Claude Desktop to load the configuration

**Access:**

- Health endpoint: <http://localhost:3002/health>
- MCP endpoint: <http://localhost:3002/mcp>
- Caddy (production): Port 8009 or custom hostname via `N8N_MCP_HOSTNAME`

**Important:** The n8n-mcp container (internal port 3000, external port 3002) depends on the n8n service being started first. It automatically starts when you run `python start_services.py`.

### Docling Document Parser Integration

Docling is an advanced document parser that converts complex documents into structured formats for RAG systems.

**Supported formats:**
- PDFs (with advanced table/image extraction)
- Microsoft Office: DOCX, PPTX, XLSX
- Images: PNG, TIFF, JPEG
- HTML, Audio (WAV, MP3), Subtitles (VTT)

**Access:**
- API endpoint: <http://localhost:5001> (private mode)
- Documentation: <http://localhost:5001/docs>
- Web UI: <http://localhost:5001/ui>
- Caddy (production): Port 8010 or custom hostname via `DOCLING_HOSTNAME`

**Using Docling in n8n workflows:**

In HTTP Request nodes, use:
- **URL**: `http://docling:5001/v1/convert`
- **Method**: POST
- **Body**: JSON with document URL or file upload
- **Headers**: `Content-Type: application/json`

Example JSON payload for URL-based conversion:
```json
{
  "source": {
    "type": "url",
    "url": "https://example.com/document.pdf"
  },
  "output": {
    "format": "markdown"
  }
}
```

For local files in the `./shared` folder, first upload the file to a temporary web-accessible location or use multipart form upload.

**Benefits for RAG:**
- Superior PDF parsing with table structure preservation
- Image and diagram extraction from documents
- Markdown output ideal for vector embeddings
- JSON structured output for precise data extraction
- Handles complex layouts better than basic text extraction

**Troubleshooting:**

- Check container health: `docker ps | grep docling`
- View logs: `docker logs docling --tail 50`
- Test health: `curl http://localhost:5001/health`

For detailed documentation, see:
- [CLAUDE_DESKTOP_SETUP.md](CLAUDE_DESKTOP_SETUP.md) - Step-by-step Claude Desktop setup guide
- `n8n-mcp/README.md` - n8n-mcp server documentation
- `n8n-mcp/CLAUDE_DESKTOP_CONFIG.md` - Additional configuration details

### Graphiti Knowledge Graph Integration

Graphiti provides temporal knowledge graph capabilities for building AI agents with episodic memory.

**Access:**
- API endpoint: <http://localhost:5002> (private mode)
- Documentation: <http://localhost:5002/docs>
- Health check: <http://localhost:5002/health>
- Caddy (production): Port 8011 or custom hostname via `GRAPHITI_HOSTNAME`

**Key Features:**
- **Episodic Memory**: Track discrete interactions, conversations, or events as episodes
- **Temporal Awareness**: Bi-temporal tracking (when facts were valid vs. when they were recorded)
- **Entity Extraction**: Automatically extract entities and relationships from unstructured text
- **Hybrid Search**: Semantic embeddings + BM25 + graph traversal (P95 latency ~300ms)
- **Real-time Updates**: Incrementally processes data without batch recomputation

**Using Graphiti in n8n workflows:**

In HTTP Request nodes, use:
- **Add Episode**: `POST http://graphiti:5002/v1/episodes`
  ```json
  {
    "name": "Customer Meeting",
    "content": "Met with John from Acme Corp. He needs reporting features.",
    "source": "crm",
    "reference_time": "2025-10-22T10:30:00Z"
  }
  ```

- **Search Knowledge**: `POST http://graphiti:5002/v1/search`
  ```json
  {
    "query": "What did John from Acme Corp need?",
    "num_results": 5
  }
  ```

- **Find Entities**: `POST http://graphiti:5002/v1/entities/search`
  ```json
  {
    "entity_name": "John"
  }
  ```

**Configuration:**

Graphiti uses Neo4j for storage and requires an LLM for entity extraction:
- **Default (Ollama)**: Uses local `qwen2.5:7b-instruct-q4_K_M` model, no API key needed
- **OpenAI**: Set `GRAPHITI_LLM_PROVIDER=openai` and `OPENAI_API_KEY` in `.env`
- **Anthropic**: Set `GRAPHITI_LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY` in `.env`

Graphiti automatically creates a `graphiti` database in Neo4j on first run.

**Use Cases:**
- **Agent Memory**: Build AI agents that remember past conversations and learn from interactions
- **CRM Integration**: Track customer interactions over time with automatic relationship discovery
- **Document Understanding**: Build temporal knowledge graphs from documents with entity linking
- **Multi-source Intelligence**: Combine data from conversations, documents, and business systems

**Example Workflows:**

Three pre-built n8n workflows demonstrate Graphiti:
- `Example_Graphiti_Memory_Agent.json` - Chat agent with episodic memory
- `Example_Graphiti_CRM_Tracker.json` - Automatic CRM interaction tracking
- `Example_Graphiti_Knowledge_Query.json` - Natural language knowledge base queries

**Troubleshooting:**

- **Startup Time**: Graphiti takes ~80 seconds to initialize on first run as it builds Neo4j indices and constraints
- **API Version**: The service uses graphiti-core v0.3.5 with `OpenAIClient` which works with Ollama's OpenAI-compatible API
- Check container health: `docker ps | grep graphiti`
- View logs: `docker logs graphiti --tail 50`
- Test health: `curl http://localhost:5002/health` (should return `{"status":"ok","neo4j_connected":true,"llm_provider":"ollama","database":"graphiti"}`)
- Verify Neo4j connection: `docker exec localai-neo4j-1 cypher-shell -u neo4j -p your-password`
- If you see import errors like `ModuleNotFoundError: No module named 'graphiti_core.embedder'`, the API code has been updated to work with the current graphiti-core library version

For detailed documentation, see:
- `graphiti-service/README.md` - Complete API documentation and examples
- [Graphiti GitHub](https://github.com/getzep/graphiti) - Official documentation

## Troubleshooting Notes

### Startup Issues

- **Docker Compose Startup Failures**: If you see "dependency failed to start: 500 Internal Server Error" during startup, this is usually a transient health check failure (typically from Clickhouse during initialization). The `start_services.py` script includes automatic retry logic (up to 3 attempts with 15-second delays) to handle this. Health check `start_period` grace periods have been added to postgres (30s), redis (15s), and clickhouse (60s) to prevent premature health check failures during cold starts.

- **WSL2 Port Forwarding Bug (Windows)**: If you encounter `ports are not available: exposing port TCP 127.0.0.1:XXXX -> 127.0.0.1:0: /forwards/expose returned unexpected status: 500`, this is a known WSL2/Docker Desktop bug. The `docker-compose.override.private.yml` file now binds ports to `0.0.0.0` instead of `127.0.0.1` to work around this issue. Windows Firewall provides security by blocking external access by default.

- **Supabase Wait Time**: The startup script now uses active health polling (max 180s, checking every 10s) instead of a fixed 20-second sleep. Supabase services typically take 50-100+ seconds to fully initialize on first run.

- **n8n Workflow Import Issues**: If you see UNIQUE constraint violations during n8n-import, all workflow files have been cleaned to set `versionId: null` and the import command now processes workflows individually, skipping any that already exist. This ensures idempotent imports on restarts.

### Service-Specific Issues

- **Supabase Pooler Restarting**: See GitHub issue #30210 in supabase/supabase repo
- **Supabase Analytics Startup Failure**: Delete `supabase/docker/volumes/db/data` folder after changing Postgres password
- **Docker Desktop**: Enable "Expose daemon on tcp://localhost:2375 without TLS" in settings
- **Windows GPU Support**: Enable WSL 2 backend in Docker Desktop settings
- **Missing Supabase Files**: Delete entire `supabase/` folder and re-run `start_services.py`
- **SearXNG First Run**: The script temporarily removes `cap_drop: - ALL` from docker-compose.yml on first run, then re-adds it for security
- **Redis Authentication Warnings**: If you see "Redis connection error: ERR AUTH" in Langfuse logs, this was fixed in recent versions by removing `REDIS_AUTH` from the configuration since Redis/Valkey runs without authentication

## Common Debugging Tasks

### Checking Service Status

```bash
# View all running containers for the localai project
docker compose -p localai ps

# Check logs for a specific service
docker compose -p localai logs -f <service-name>

# Check logs for multiple services
docker compose -p localai logs -f n8n ollama open-webui
```

### Restarting Individual Services

```bash
# Restart a single service without affecting others
docker compose -p localai restart <service-name>

# Example: Restart n8n after config changes
docker compose -p localai restart n8n
```

### Accessing Service Health Endpoints

- n8n: <http://localhost:5678/healthz>
- n8n-mcp: <http://localhost:3002/health>
- Docling: <http://localhost:5001/health>
- Graphiti: <http://localhost:5002/health>
- Ollama: <http://localhost:11434/api/tags>
- Qdrant: <http://localhost:6333/dashboard>
- Neo4j: <http://localhost:7474>
- Langfuse: <http://localhost:3000>
- Supabase Studio: <http://localhost:8000>

### Verifying Ollama Models

```bash
# List downloaded models
docker exec ollama ollama list

# Pull a specific model manually
docker exec ollama ollama pull qwen2.5:7b-instruct-q4_K_M

# Test Ollama is responding
curl http://localhost:11434/api/generate -d '{"model": "qwen2.5:7b-instruct-q4_K_M", "prompt": "Hello", "stream": false}'
```

### Debugging n8n Workflows

- Check n8n logs: `docker compose -p localai logs -f n8n`
- Access n8n container shell: `docker exec -it n8n sh`
- Check shared volume mount: `ls -la ./shared` (host) or `ls -la /data/shared` (inside container)
- Verify database connection: Check `DB_POSTGRESDB_HOST` points to `db` service

### Resetting Services

```bash
# Remove all containers and volumes (DESTRUCTIVE - loses all data)
docker compose -p localai -f docker-compose.yml --profile <profile> down -v

# Remove only containers (keeps volumes/data)
docker compose -p localai -f docker-compose.yml --profile <profile> down

# Reset Supabase only
docker compose -p localai -f supabase/docker/docker-compose.yml down -v
```

## File Structure Highlights

- `docker-compose.yml`: Main services definition with x-templates for Ollama variants
- `docker-compose.override.private.yml`: Port mappings for private/dev environment
- `docker-compose.override.public.yml`: Removes unnecessary port exposures for production
- `start_services.py`: Orchestration script for starting both stacks in correct order
- `n8n_pipe.py`: Open WebUI function for n8n integration
- `.env.example`: Template for all required environment variables
- `Caddyfile`: Reverse proxy configuration
- `n8n/backup/`: Workflows and credentials for auto-import
- `n8n-mcp/`: n8n MCP server standalone configuration and documentation
- `docling-service/`: Docling document parser service and API
- `graphiti-service/`: Graphiti knowledge graph service and API
- `flowise/`: Pre-built Flowise custom tools
- `n8n-tool-workflows/`: N8N workflows used as tools by Flowise agents
- `searxng/settings-base.yml`: Base SearXNG configuration

## Backup and Restoration

The project includes automated scripts for backing up and restoring your entire setup:

- **Backup Script**: `backup_docker_volumes.ps1` - Backs up all Docker volumes and critical data
- **Restore Script**: `restore_docker_volumes.ps1` - Restores from backup after reimaging

See detailed guides:
- `BACKUP_GUIDE.md` - Complete backup procedures and manual commands
- `RESTORATION_GUIDE.md` - Step-by-step restoration after reimaging

### Critical Data to Backup

The backup script automatically handles:
- Docker volumes: n8n_storage, open-webui, qdrant_storage, db-config, langfuse_*
- Project directories: supabase/docker/volumes, neo4j/data, shared/
- Configuration: .env, docker-compose files, Caddyfile
- User data: ~/.flowise directory

### Quick Backup

**Windows (PowerShell):**
```powershell
.\backup_docker_volumes.ps1
```

Backups are saved to `J:\My Backups\local-ai-backup_<timestamp>\` by default.

### Quick Restore

**Windows (PowerShell):**
```powershell
.\restore_docker_volumes.ps1 -BackupLocation "J:\My Backups\local-ai-backup_<timestamp>"
```

The restore script will:
- Validate backup integrity
- Show backup manifest
- Prompt for confirmation
- Restore all Docker volumes
- Restore project files
- Restore Flowise directory
