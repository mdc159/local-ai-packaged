# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a self-hosted AI development environment that combines multiple AI services into a unified Docker Compose stack. The project extends the original n8n starter kit with Supabase, Open WebUI, Flowise, Neo4j, Langfuse, SearXNG, and Caddy to create a comprehensive local AI development platform.

## Key Commands

### Starting the Environment
```bash
# Start with CPU profile (default)
python start_services.py --profile cpu

# Start with Nvidia GPU support
python start_services.py --profile gpu-nvidia

# Start with AMD GPU support  
python start_services.py --profile gpu-amd

# Start without Ollama (for Mac users running Ollama locally)
python start_services.py --profile none

# Start for production deployment
python start_services.py --profile gpu-nvidia --environment public
```

### Managing Services
```bash
# Stop all services
docker compose -p localai -f docker-compose.yml --profile <profile> down

# Update all containers to latest versions
docker compose -p localai -f docker-compose.yml --profile <profile> pull

# View logs for debugging
docker compose -p localai logs
docker compose -p localai logs <service-name>
```

### Environment Setup
```bash
# Setup environment file
cp .env.example .env

# Generate secure secrets (Linux/Mac)
openssl rand -hex 32

# Generate secure secrets (Windows)
python -c "import secrets; print(secrets.token_hex(32))"
```

## Architecture

### Service Stack
The project uses a unified Docker Compose project named "localai" that includes:

- **n8n**: Low-code workflow automation (port 5678)
- **Supabase**: Database service with PostgreSQL + additional tools
- **Ollama**: Local LLM runtime with multi-GPU profile support
- **Open WebUI**: ChatGPT-like interface (port 3000)
- **Flowise**: No-code AI agent builder (port 3001)
- **Qdrant**: Vector database (port 6333)
- **Neo4j**: Knowledge graph database (port 7474)
- **SearXNG**: Privacy-focused search engine (port 8080)
- **Langfuse**: LLM observability (port 3002)
- **Caddy**: Reverse proxy with automatic HTTPS

### Key Files
- `start_services.py`: Main orchestration script that handles Supabase + AI service startup
- `docker-compose.yml`: Main service definitions with GPU profiles
- `n8n_pipe.py`: Open WebUI integration function for n8n workflows
- `Caddyfile`: Reverse proxy configuration for production deployments
- `.env.example`: Template for required environment variables

### GPU Support Profiles
The Docker Compose configuration supports multiple GPU profiles:
- `cpu`: CPU-only execution
- `gpu-nvidia`: NVIDIA GPU support with CUDA
- `gpu-amd`: AMD GPU support with ROCm
- `none`: No Ollama container (for external Ollama instances)

### Environment Modes
- `private`: Development mode with exposed ports (default)
- `public`: Production mode with only ports 80/443 exposed

## Development Guidelines

### Configuration Management
- Always copy `.env.example` to `.env` before starting
- Generate secure random values for all secrets in production
- Never commit the `.env` file to version control
- Use `POOLER_DB_POOL_SIZE=5` in .env for Supabase compatibility

### Service Dependencies
- Supabase must start first, then local AI services
- The `start_services.py` script handles proper startup sequencing
- n8n depends on successful database initialization
- SearXNG requires special permission handling on first run

### Integration Points
- n8n workflows are pre-imported from `n8n/backup/workflows/`
- Open WebUI connects to n8n via the `n8n_pipe.py` function
- Shared data volumes allow file exchange between services
- All services use the unified "localai" Docker project namespace

## Troubleshooting

### Common Issues
- **Supabase pooler restarting**: Ensure `POOLER_DB_POOL_SIZE=5` is set in .env
- **SearXNG permission errors**: Run `chmod 755 searxng` to fix directory permissions
- **GPU not detected**: Verify Docker GPU setup matches your profile selection
- **Mac GPU issues**: Use `--profile none` and run Ollama locally, set `OLLAMA_HOST=host.docker.internal:11434` in n8n

### Service Health Checks
- Check container status: `docker ps`
- View service logs: `docker compose -p localai logs <service>`
- Test endpoints at their respective localhost URLs
- Verify database connectivity through Supabase dashboard

### Data Persistence
- All services use named Docker volumes for data persistence
- Shared files are mounted at `/data/shared` within n8n container
- Neo4j data persists in `./neo4j/` directories
- SearXNG settings persist in `./searxng/` directory