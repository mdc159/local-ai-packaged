# Claude Desktop MCP Configuration for n8n-mcp

## Overview

This guide shows you how to configure Claude Desktop to use the n8n-mcp server running in Docker.

## Configuration File Location

The Claude Desktop MCP configuration file is typically located at:

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

## Recommended Configuration (Docker Exec)

This approach connects to the persistent n8n-mcp container:

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

### Advantages:
- ✅ Uses the existing persistent container
- ✅ No duplicate containers created
- ✅ Shares configuration with docker-compose
- ✅ Container managed by Docker Compose lifecycle

### Requirements:
- The `n8n-mcp` container must be running before starting Claude Desktop
- Start it with: `cd n8n-mcp && docker compose up -d`

## Alternative Configuration (HTTP Mode)

This approach uses HTTP to communicate with the running server:

```json
{
  "mcpServers": {
    "n8n-mcp": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/inspector",
        "http://localhost:3002/mcp"
      ]
    }
  }
}
```

### Advantages:
- ✅ Simpler setup
- ✅ Works even if container restarts
- ✅ Better for debugging

### Requirements:
- Node.js and npx must be installed on your system
- The `n8n-mcp` container must be running and accessible at http://localhost:3002

## What NOT to Do

❌ **DO NOT use this configuration:**

```json
{
  "mcpServers": {
    "n8n-mcp": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--init",
        "ghcr.io/czlonkowski/n8n-mcp:latest"
      ]
    }
  }
}
```

**Problems with this approach:**
- Creates a new ephemeral container every time Claude Desktop connects
- Containers don't get cleaned up properly (despite `--rm` flag)
- Leads to dozens of duplicate containers consuming resources
- Each container has separate configuration and state

## Verifying Configuration

After updating your Claude Desktop configuration:

1. **Ensure container is running:**
   ```bash
   docker ps | grep n8n-mcp
   ```

   You should see:
   ```
   n8n-mcp   Up X minutes (healthy)   127.0.0.1:3002->3000/tcp
   ```

2. **Test health endpoint:**
   ```bash
   curl http://localhost:3002/health
   ```

3. **Restart Claude Desktop** to load the new configuration

4. **Test MCP connection** by asking Claude to list your n8n workflows

## Troubleshooting

### "Container n8n-mcp is not running"

Start the container:
```bash
cd n8n-mcp
docker compose up -d
```

### Multiple containers running

Clean up duplicate containers:
```bash
docker ps -a | grep n8n-mcp
docker stop $(docker ps -a --filter "ancestor=ghcr.io/czlonkowski/n8n-mcp:latest" --format "{{.Names}}" | grep -v "^n8n-mcp$")
docker rm $(docker ps -a --filter "ancestor=ghcr.io/czlonkowski/n8n-mcp:latest" --format "{{.Names}}" | grep -v "^n8n-mcp$")
```

### Claude Desktop can't connect

1. Check logs: `docker logs n8n-mcp --tail 50`
2. Verify AUTH_TOKEN matches between `.env` and any Claude config
3. Ensure n8n is accessible at http://localhost:5678
4. Verify N8N_API_KEY is valid

### Container is unhealthy

The healthcheck tests `http://127.0.0.1:3000/health` inside the container. If failing:

1. Check if server is listening on port 3000 internally:
   ```bash
   docker exec n8n-mcp netstat -tlnp | grep 3000
   ```

2. Test health endpoint from inside container:
   ```bash
   docker exec n8n-mcp curl http://localhost:3000/health
   ```

3. Check environment variables:
   ```bash
   docker exec n8n-mcp env | grep PORT
   ```

## Integration with Main Stack

To integrate n8n-mcp with the main local-ai-packaged stack, add this service to the main `docker-compose.yml`:

```yaml
services:
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
      - WEBHOOK_SECURITY_MODE=moderate
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

Then add these variables to your main `.env`:
```env
N8N_MCP_AUTH_TOKEN=zN9ngtXSNyNXlUB3gC2iO6fu/x32RtGMghzoWg0bdEM=
N8N_API_KEY=your_n8n_api_key_here
```
