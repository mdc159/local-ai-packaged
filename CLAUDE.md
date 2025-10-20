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
  - Uses `docker-compose.override.private.yml` to map all ports to 127.0.0.1
  - Direct access to all services without going through Caddy
  - Best for local development and debugging
- `public`: Only ports 80/443 exposed, Caddy handles routing with HTTPS
  - Uses `docker-compose.override.public.yml` to close most ports
  - All services accessed through Caddy reverse proxy
  - Required for production deployments with custom domains

## Common Commands

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
6. Waits 10 seconds
7. Starts AI services stack

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
- `N8N_HOSTNAME`, `WEBUI_HOSTNAME`, `FLOWISE_HOSTNAME`, `SUPABASE_HOSTNAME`, `LANGFUSE_HOSTNAME`, `N8N_MCP_HOSTNAME`, `NEO4J_HOSTNAME`
- `LETSENCRYPT_EMAIL`

### Service Connections

When configuring credentials in n8n:
- **Ollama**: `http://ollama:11434` (or `http://host.docker.internal:11434` if running Ollama natively on Mac)
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

**Troubleshooting:**

- Check container health: `docker ps | grep n8n-mcp`
- View logs: `docker logs n8n-mcp --tail 50`
- Test health: `curl http://localhost:3002/health`

For detailed documentation, see `n8n-mcp/README.md` and `n8n-mcp/CLAUDE_DESKTOP_CONFIG.md`.

## Troubleshooting Notes

- **Docker Compose Startup Failures**: If you see "dependency failed to start: 500 Internal Server Error" during startup, this is usually a transient health check failure (typically from Clickhouse during initialization). The `start_services.py` script includes automatic retry logic (up to 3 attempts with 15-second delays) to handle this. If it persists after 3 attempts, check individual service logs with `docker compose -p localai logs <service-name>`.
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
- `flowise/`: Pre-built Flowise custom tools
- `n8n-tool-workflows/`: N8N workflows used as tools by Flowise agents
- `searxng/settings-base.yml`: Base SearXNG configuration
