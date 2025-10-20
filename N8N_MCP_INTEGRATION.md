# N8N MCP Integration Guide

## Overview

The n8n-mcp service has been successfully integrated into the local-ai-packaged Docker stack. This service enables Claude Desktop to interact with your n8n workflows through the Model Context Protocol (MCP).

## What Was Changed

### 1. Main Stack Integration

**Files Modified:**
- [docker-compose.yml](docker-compose.yml) - Added n8n-mcp service definition
- [docker-compose.override.private.yml](docker-compose.override.private.yml) - Added port mapping for development
- [.env.example](.env.example) - Added n8n-mcp environment variables and documentation
- [.env](.env) - Added actual n8n-mcp credentials
- [Caddyfile](Caddyfile) - Added reverse proxy configuration for n8n-mcp
- [CLAUDE.md](CLAUDE.md) - Updated documentation with n8n-mcp details

**Files Created:**
- [n8n-mcp/docker-compose.yml](n8n-mcp/docker-compose.yml) - Standalone configuration (optional)
- [n8n-mcp/.env.docker](n8n-mcp/.env.docker) - Standalone environment template
- [n8n-mcp/README.md](n8n-mcp/README.md) - Comprehensive usage guide
- [n8n-mcp/CLAUDE_DESKTOP_CONFIG.md](n8n-mcp/CLAUDE_DESKTOP_CONFIG.md) - Claude Desktop setup guide

### 2. Service Configuration

**Docker Compose Service:**
```yaml
n8n-mcp:
  image: ghcr.io/czlonkowski/n8n-mcp:latest
  container_name: n8n-mcp
  restart: unless-stopped
  expose:
    - 3000/tcp
  environment:
    - MCP_MODE=http
    - PORT=3000
    - AUTH_TOKEN=${N8N_MCP_AUTH_TOKEN}
    - N8N_API_URL=http://n8n:5678
    - N8N_API_KEY=${N8N_API_KEY}
    - WEBHOOK_SECURITY_MODE=${N8N_MCP_WEBHOOK_SECURITY_MODE:-moderate}
  extra_hosts:
    - "host.docker.internal:host-gateway"
  depends_on:
    n8n:
      condition: service_started
  healthcheck:
    test: ["CMD", "curl", "-f", "http://127.0.0.1:3000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
```

**Port Mappings:**
- **Private/Dev Mode**: `127.0.0.1:3002:3000` (localhost only)
- **Public/Prod Mode**: Accessed via Caddy on port 8009 or custom hostname

### 3. Environment Variables

**Required in `.env`:**
```env
# N8N MCP Server Configuration
N8N_API_KEY=your-n8n-api-key-here
N8N_MCP_AUTH_TOKEN=generate-with-openssl-rand-base64-32
```

**Optional:**
```env
N8N_MCP_WEBHOOK_SECURITY_MODE=moderate  # strict, moderate, or permissive
N8N_MCP_HOSTNAME=n8n-mcp.yourdomain.com  # For production with Caddy
```

## Setup Instructions

### 1. Generate Credentials

If you haven't already, add the required credentials to your `.env` file:

```bash
# Generate AUTH_TOKEN
openssl rand -base64 32

# Get N8N_API_KEY from n8n
# 1. Open n8n at http://localhost:5678
# 2. Go to Settings → API
# 3. Create or copy your API key
```

### 2. Update .env File

Your `.env` file should already have these values set:
```env
N8N_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
N8N_MCP_AUTH_TOKEN=K2ZN2Y13K6QcLdeXMPUEx5OdIJgz5XltKr0a5ixBmqE=
```

### 3. Start the Service

The n8n-mcp service automatically starts with the main stack:

```bash
# Start all services (including n8n-mcp)
python start_services.py --profile gpu-nvidia --environment private
```

Or restart just the n8n-mcp service:

```bash
docker compose -p localai -f docker-compose.yml -f docker-compose.override.private.yml restart n8n-mcp
```

### 4. Verify Service is Running

```bash
# Check container status
docker ps | grep n8n-mcp

# Expected output:
# n8n-mcp   Up X minutes (healthy)   127.0.0.1:3002->3000/tcp

# Test health endpoint
curl http://localhost:3002/health
```

### 5. Configure Claude Desktop

Update your Claude Desktop configuration file:

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Linux:** `~/.config/Claude/claude_desktop_config.json`

**Recommended configuration:**
```json
{
  "mcpServers": {
    "n8n-mcp": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "n8n-mcp",
        "node",
        "dist/mcp/index.js"
      ]
    }
  }
}
```

### 6. Restart Claude Desktop

Close and restart Claude Desktop completely to load the new MCP configuration.

## How It Works

### Architecture

```
Claude Desktop
    ↓ (docker exec)
n8n-mcp Container (port 3000 internal, 3002 external)
    ↓ (HTTP API)
n8n Container (port 5678)
    ↓
Your n8n Workflows
```

### Service Dependencies

1. **n8n-import** runs first (imports workflows and credentials)
2. **n8n** starts after import completes
3. **n8n-mcp** starts after n8n is running
4. All services share the `localai_default` Docker network

### Network Configuration

- **Internal Communication**: n8n-mcp connects to n8n at `http://n8n:5678` (Docker network)
- **External Access (dev)**: `http://localhost:3002` (mapped to internal port 3000)
- **External Access (prod)**: Via Caddy at port 8009 or custom hostname
- **No Port Conflicts**: Langfuse uses port 3000 externally, n8n-mcp uses port 3002 externally

## Access Points

### Development Mode (Private)

- **Health Check**: http://localhost:3002/health
- **MCP Endpoint**: http://localhost:3002/mcp
- **Via Caddy**: http://localhost:8009 (if Caddy is configured)

### Production Mode (Public)

- **Via Caddy Only**: Configured via `N8N_MCP_HOSTNAME` environment variable
- Example: https://n8n-mcp.yourdomain.com (with automatic Let's Encrypt certificate)

## Troubleshooting

### Container is Unhealthy

```bash
# Check logs
docker logs n8n-mcp --tail 50

# Common issues:
# 1. N8N_API_KEY is invalid - regenerate in n8n Settings → API
# 2. n8n service not running - check: docker ps | grep " n8n "
# 3. Port conflict - verify port 3002 is not in use
```

### Claude Desktop Can't Connect

```bash
# 1. Verify container is running and healthy
docker ps --filter "name=n8n-mcp"

# 2. Test health endpoint
curl http://localhost:3002/health

# 3. Check Claude Desktop config file location
# Windows: %APPDATA%\Claude\claude_desktop_config.json
# macOS: ~/Library/Application Support/Claude/claude_desktop_config.json

# 4. Restart Claude Desktop completely
```

### Multiple n8n-mcp Containers

If you see multiple containers running:

```bash
# Stop all n8n-mcp containers
docker ps -a | grep n8n-mcp

# Remove extras (keep only the one named "n8n-mcp")
docker stop $(docker ps -a --filter "ancestor=ghcr.io/czlonkowski/n8n-mcp:latest" --format "{{.Names}}" | grep -v "^n8n-mcp$")
docker rm $(docker ps -a --filter "ancestor=ghcr.io/czlonkowski/n8n-mcp:latest" --format "{{.Names}}" | grep -v "^n8n-mcp$")
```

This was caused by the old Claude Desktop config using `docker run --rm -i` instead of `docker exec -i`.

### Port Conflicts

The service uses:
- **Internal**: Port 3000 (inside container)
- **External**: Port 3002 (mapped to host)

If you get a port conflict error:
```bash
# Check what's using port 3002
netstat -ano | findstr :3002  # Windows
lsof -i :3002                 # macOS/Linux

# Stop conflicting service or change port in docker-compose.override.private.yml
```

## Service Management

### View Logs

```bash
# Real-time logs
docker compose -p localai logs -f n8n-mcp

# Last 50 lines
docker logs n8n-mcp --tail 50
```

### Restart Service

```bash
# Restart just n8n-mcp
docker compose -p localai restart n8n-mcp

# Or via docker directly
docker restart n8n-mcp
```

### Stop Service

```bash
# Stop n8n-mcp only
docker compose -p localai stop n8n-mcp

# Stop all services
docker compose -p localai -f docker-compose.yml --profile gpu-nvidia down
```

### Update Container

```bash
# Pull latest image
docker pull ghcr.io/czlonkowski/n8n-mcp:latest

# Restart with new image
docker compose -p localai -f docker-compose.yml -f docker-compose.override.private.yml up -d n8n-mcp
```

## Integration with Other Services

### With n8n Workflows

The MCP server can:
- List all workflows
- Execute workflows via webhook
- Manage workflow credentials
- Access workflow execution history

### With Claude Desktop

You can ask Claude to:
- "List my n8n workflows"
- "Execute the RAG workflow with this input"
- "Show me the last execution of workflow X"
- "Create a new workflow for Y task"

### With Caddy (Production)

For production deployment with custom domain:

1. Set environment variable in `.env`:
   ```env
   N8N_MCP_HOSTNAME=n8n-mcp.yourdomain.com
   LETSENCRYPT_EMAIL=your@email.com
   ```

2. Restart services:
   ```bash
   python start_services.py --profile gpu-nvidia --environment public
   ```

3. Caddy will automatically provision Let's Encrypt certificate

## Best Practices

1. **Security**:
   - Keep `N8N_MCP_AUTH_TOKEN` secret and secure
   - Regenerate tokens periodically
   - Use `WEBHOOK_SECURITY_MODE=strict` in production
   - Only expose via Caddy in production (not direct port 3002)

2. **Performance**:
   - Monitor container resource usage: `docker stats n8n-mcp`
   - Check session limits if experiencing issues
   - Review logs regularly for errors

3. **Maintenance**:
   - Update container image regularly
   - Backup n8n workflows before major updates
   - Test MCP connection after updates

## Additional Resources

- **n8n MCP Server GitHub**: https://github.com/czlonkowski/n8n-mcp
- **MCP Documentation**: https://modelcontextprotocol.io/
- **Local Configuration**: See [n8n-mcp/README.md](n8n-mcp/README.md)
- **Claude Desktop Config**: See [n8n-mcp/CLAUDE_DESKTOP_CONFIG.md](n8n-mcp/CLAUDE_DESKTOP_CONFIG.md)

## Summary

✅ **n8n-mcp is now integrated into your local-ai-packaged stack!**

- Automatically starts with `python start_services.py`
- Accessible at http://localhost:3002
- Ready for Claude Desktop integration
- No port conflicts with other services
- Properly health-checked and monitored
- Production-ready with Caddy support

The service is currently running and healthy. Update your Claude Desktop configuration to start using it!
