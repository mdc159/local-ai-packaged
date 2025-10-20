# n8n MCP Server

This directory contains the Docker Compose configuration for the n8n MCP (Model Context Protocol) server.

## Setup

1. **Copy environment file**:
   ```bash
   cp .env.docker .env
   ```

2. **Update your n8n API key** in `.env`:
   - Go to your n8n instance (http://localhost:5678)
   - Navigate to Settings → API
   - Create or copy your API key
   - Update `N8N_API_KEY` in `.env`

3. **Generate authentication token** (optional, or keep the existing one):
   ```bash
   openssl rand -base64 32
   ```
   Update `AUTH_TOKEN` in `.env`

## Starting the Service

### Option 1: Start with main stack (Recommended)

The n8n-mcp service is now part of the main docker-compose.yml and will start automatically when you run:

```bash
python start_services.py --profile gpu-nvidia
```

### Option 2: Start standalone

```bash
cd n8n-mcp
docker compose up -d
```

## Accessing the Service

- **Health check**: http://localhost:3002/health
- **MCP endpoint**: http://localhost:3002/mcp

## Claude Desktop Configuration

Update your Claude Desktop MCP settings to connect to the running container:

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

Or use HTTP mode:

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

## Configuration

### Environment Variables

- `MCP_MODE`: Set to `http` for HTTP mode
- `PORT`: Internal port (default: 3000)
- `AUTH_TOKEN`: Authentication token for MCP server
- `N8N_API_URL`: URL to your n8n instance
- `N8N_API_KEY`: Your n8n API key
- `WEBHOOK_SECURITY_MODE`: Security mode for webhooks (strict, moderate, permissive)

### Port Mapping

- External: `127.0.0.1:3002` (localhost only)
- Internal: `3000`

This avoids conflicts with langfuse-web which uses port 3000 externally.

## Troubleshooting

### Container is unhealthy

Check logs:
```bash
docker logs n8n-mcp
```

Test health endpoint:
```bash
curl http://localhost:3002/health
```

### Can't connect from Claude Desktop

1. Ensure container is running: `docker ps | grep n8n-mcp`
2. Check container logs: `docker logs n8n-mcp --tail 50`
3. Verify n8n API key is correct
4. Test MCP endpoint: `curl http://localhost:3002/mcp`

### Multiple containers running

If you see multiple n8n-mcp containers, stop and remove them:

```bash
docker ps -a | grep n8n-mcp
docker stop $(docker ps -a --filter "ancestor=ghcr.io/czlonkowski/n8n-mcp:latest" --format "{{.Names}}" | grep -v "^n8n-mcp$")
docker rm $(docker ps -a --filter "ancestor=ghcr.io/czlonkowski/n8n-mcp:latest" --format "{{.Names}}" | grep -v "^n8n-mcp$")
```

This happens when using `docker run --rm -i` in Claude Desktop config instead of `docker exec`.
