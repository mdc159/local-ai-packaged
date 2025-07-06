# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

This is a self-hosted AI package that combines multiple services in a Docker Compose stack:

- **n8n**: Low-code workflow automation platform for AI agents
- **Supabase**: Full-stack backend with PostgreSQL, authentication, and API
- **Ollama**: Local LLM inference server (with GPU profiles: nvidia, amd, cpu, none)
- **Open WebUI**: ChatGPT-like interface for interacting with local models
- **Flowise**: No/low-code AI agent builder
- **Qdrant**: Vector database for embeddings
- **Neo4j**: Knowledge graph database
- **SearXNG**: Privacy-focused metasearch engine
- **Langfuse**: LLM observability and analytics
- **Caddy**: Reverse proxy with automatic HTTPS

## Key Commands

### Starting Services
```bash
# Start with NVIDIA GPU support
python start_services.py --profile gpu-nvidia

# Start with AMD GPU support  
python start_services.py --profile gpu-amd

# Start CPU-only
python start_services.py --profile cpu

# Start without Ollama (for external Ollama)
python start_services.py --profile none

# For production deployment (closes all ports except 80/443)
python start_services.py --profile gpu-nvidia --environment public
```

### Managing Services
```bash
# Stop all services
docker compose -p localai -f docker-compose.yml --profile <profile> down

# Update containers
docker compose -p localai -f docker-compose.yml --profile <profile> pull

# View logs
docker compose -p localai logs -f <service-name>

# View logs for specific service (common services: n8n, open-webui, ollama, supabase-kong)
docker compose -p localai logs -f n8n
docker compose -p localai logs -f open-webui
docker compose -p localai logs -f ollama
```

## Environment Configuration

The system requires a `.env` file with these critical variables:
- `N8N_ENCRYPTION_KEY` and `N8N_USER_MANAGEMENT_JWT_SECRET` for n8n
- `POSTGRES_PASSWORD`, `JWT_SECRET`, `ANON_KEY`, `SERVICE_ROLE_KEY` for Supabase
- `NEO4J_AUTH` for Neo4j access
- `CLICKHOUSE_PASSWORD`, `MINIO_ROOT_PASSWORD`, `LANGFUSE_SALT`, `NEXTAUTH_SECRET`, `ENCRYPTION_KEY` for Langfuse

For production deployments, also configure domain hostnames like `N8N_HOSTNAME`, `WEBUI_HOSTNAME`, etc.

## Architecture Details

### Service Communication
- All services run in a unified Docker Compose project named "localai"
- Services communicate via internal Docker networks
- n8n acts as the orchestration layer, coordinating between services
- Supabase provides the primary database (PostgreSQL) shared across services

### Data Flow
1. **Input**: Users interact via Open WebUI or directly with n8n workflows
2. **Processing**: n8n workflows coordinate between LLMs (Ollama), vector stores (Qdrant/Supabase), and external APIs
3. **Storage**: Data persists in Supabase PostgreSQL, with vectors in Qdrant and knowledge graphs in Neo4j
4. **Monitoring**: Langfuse tracks LLM interactions and performance

### Key Integration Points
- `n8n_pipe.py`: Open WebUI function that bridges chat interface to n8n workflows
- Pre-configured n8n workflows in `n8n/backup/workflows/` for RAG and agent functionality
- Flowise chatflows in `flowise/` for visual AI workflow building
- Caddy configuration for reverse proxy and SSL termination

## Important Files

- `start_services.py`: Main service orchestration script
- `docker-compose.yml`: Core service definitions with GPU profiles
- `n8n_pipe.py`: Open WebUI integration function
- `supabase/docker/docker-compose.yml`: Supabase service definitions (cloned automatically)
- `Caddyfile`: Reverse proxy configuration
- `searxng/settings-base.yml`: SearXNG search engine configuration template
- `n8n/backup/workflows/`: Pre-configured RAG AI Agent workflows (V1, V2, V3)
- `flowise/`: Flowise chatflow definitions and custom tools
- `n8n-tool-workflows/`: Additional n8n tool workflows

## Service URLs (Development)

- n8n: http://localhost:5678/
- Open WebUI: http://localhost:3000/
- Flowise: http://localhost:3001/
- Supabase Studio: http://localhost:8000/
- SearXNG: http://localhost:8080/
- Langfuse: http://localhost:3002/
- Neo4j Browser: http://localhost:7474/

## Troubleshooting

### Common Issues
- **Supabase Pooler Restarting**: Check GitHub issue #30210 for pooler configuration
- **Docker Desktop**: Enable "Expose daemon on tcp://localhost:2375 without TLS"
- **Postgres Password**: Avoid "@" character in `POSTGRES_PASSWORD`
- **SearXNG Permissions**: Run `chmod 755 searxng` if container keeps restarting

### Debugging Commands
```bash
# Check container status
docker compose -p localai ps

# Inspect specific service
docker compose -p localai logs <service-name>

# Enter container for debugging
docker compose -p localai exec <service-name> bash
```

## Development Workflow

### Making Changes to Services
When modifying service configurations or adding new services:

1. **Environment Variables**: Update `.env` file for new service credentials
2. **Docker Compose**: Modify `docker-compose.yml` for service definitions
3. **Caddy Configuration**: Update `Caddyfile` for reverse proxy routing
4. **Restart Services**: Use `python start_services.py --profile <profile>` to apply changes

### Testing Changes
```bash
# Check service status
docker compose -p localai ps

# Monitor service logs during testing
docker compose -p localai logs -f <service-name>

# Test individual service connectivity
curl http://localhost:<port>/health  # if available
```

### Backup and Restore
- **n8n workflows**: Automatically backed up in `n8n/backup/workflows/`
- **n8n credentials**: Automatically backed up in `n8n/backup/credentials/`
- **Flowise chatflows**: Stored in `flowise/` directory
- **Database**: Supabase PostgreSQL data persists in Docker volumes

## Service Integration Patterns

### n8n Integration
- **Open WebUI Integration**: Use `n8n_pipe.py` as a function in Open WebUI
- **Webhook Endpoints**: n8n workflows expose webhook URLs for external integration
- **Database Connection**: n8n connects to Supabase PostgreSQL at `db:5432`
- **LLM Integration**: n8n connects to Ollama at `ollama:11434`

### Cross-Service Communication
- **Internal DNS**: Services communicate using container names (e.g., `db`, `ollama`, `n8n`)
- **Network Isolation**: All services run in the same Docker network for internal communication
- **External Access**: Only Caddy exposes ports externally (80/443) in production mode

### Environment-Specific Configurations
- **Private Environment**: All service ports exposed for development
- **Public Environment**: Only ports 80/443 exposed, all traffic routed through Caddy
- **Profile-Specific**: GPU profiles (nvidia, amd, cpu, none) affect only Ollama service

## Notes

- The system automatically clones Supabase repository on first run using sparse checkout
- SearXNG requires special permissions handling on first run (handled by start script)
- Ollama models are automatically pulled on container startup (qwen2.5:7b-instruct-q4_K_M and nomic-embed-text)
- For Mac users running Ollama locally, update n8n environment to use `host.docker.internal:11434`
- All services use unified Docker Compose project name "localai" for unified management
- The start script handles SearXNG secret key generation and Docker Compose modifications automatically