# Claude Desktop Setup for n8n-mcp

This guide will help you connect Claude Desktop to your running n8n-mcp server.

## Prerequisites

- n8n-mcp container is running (started via `python start_services.py`)
- n8n API key created in n8n at Settings → API
- Claude Desktop installed

## Configuration

### Step 1: Locate Claude Desktop Config File

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Linux:** `~/.config/Claude/claude_desktop_config.json`

### Step 2: Choose Your Connection Method

#### Option 1: Connect to Running Container (Recommended)

This connects to the n8n-mcp container that's already running as part of your docker-compose stack.

**Configuration:**
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

**Advantages:**
- ✅ Uses the existing container from your stack
- ✅ Automatically shares network with n8n and other services
- ✅ No need to specify API keys (reads from environment)
- ✅ Container persists across Claude Desktop restarts

**When to use:** This is the recommended approach for most users.

---

#### Option 2: Run Separate Container

This creates a new container each time Claude Desktop connects.

**Configuration:**
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
        "--network", "localai_default",
        "-e", "MCP_MODE=stdio",
        "-e", "AUTH_TOKEN=YOUR_AUTH_TOKEN_HERE",
        "-e", "N8N_API_URL=http://n8n:5678",
        "-e", "N8N_API_KEY=YOUR_N8N_API_KEY_HERE",
        "-e", "WEBHOOK_SECURITY_MODE=moderate",
        "ghcr.io/czlonkowski/n8n-mcp:latest"
      ]
    }
  }
}
```

**Replace these values:**
- `YOUR_AUTH_TOKEN_HERE` - Generate with: `openssl rand -base64 32`
- `YOUR_N8N_API_KEY_HERE` - Your n8n API key from Settings → API

**Important notes:**
- Must use `--network localai_default` to access n8n
- Use `http://n8n:5678` (not `host.docker.internal`) when on the same network
- Must use `MCP_MODE=stdio` for Claude Desktop (not http)

**Advantages:**
- ✅ Isolated from main stack
- ✅ Different API keys if needed
- ✅ Can run when main stack is down

**Disadvantages:**
- ❌ Creates/destroys container on each connection
- ❌ Requires manual API key management
- ❌ More complex configuration

**When to use:** Only if you need isolation or different credentials.

---

## Step 3: Apply Configuration

### For Your Current Setup

Based on your API key, here's your ready-to-use configuration:

**Option 1 (Recommended):**
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

**Option 2 (Standalone):**
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
        "--network", "localai_default",
        "-e", "MCP_MODE=stdio",
        "-e", "AUTH_TOKEN=zN9ngtXSNyNXlUB3gC2iO6fu/x32RtGMghzoWg0bdEM=",
        "-e", "N8N_API_URL=http://n8n:5678",
        "-e", "N8N_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmMjFiZDk2Yi0xOWVlLTQ1N2QtYWJjZS0xNmM3ZDBkYzY2OGIiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzYwMTU3Nzc4fQ.TdXSFN8LwtIbRs80rIUkNGo7dVft_HZlc_T0eh3mAVo",
        "-e", "WEBHOOK_SECURITY_MODE=moderate",
        "ghcr.io/czlonkowski/n8n-mcp:latest"
      ]
    }
  }
}
```

### Step 4: Restart Claude Desktop

After saving your configuration, completely quit and restart Claude Desktop for the changes to take effect.

## Verification

Once Claude Desktop restarts, you should see the n8n-mcp server available. You can test it by asking Claude Desktop to:

- "List my n8n workflows"
- "Show me my active workflows"
- "What integrations do I have in n8n?"

## Troubleshooting

### "Cannot connect to n8n-mcp"

1. **Check container is running:**
   ```bash
   docker ps | grep n8n-mcp
   ```

2. **Test container accessibility:**
   ```bash
   docker exec n8n-mcp node dist/mcp/index.js --help
   ```

3. **Check n8n API access:**
   ```bash
   curl http://localhost:5678/api/v1/workflows \
     -H "X-N8N-API-KEY: YOUR_API_KEY"
   ```

### "Container not found" (Option 1)

Make sure the n8n-mcp container is running:
```bash
docker ps --filter "name=n8n-mcp"
```

If not running, start your stack:
```bash
python start_services.py --profile gpu-nvidia
```

### "Network error" (Option 2)

Make sure you're using:
- `--network localai_default` flag
- `http://n8n:5678` (not `host.docker.internal`)
- `MCP_MODE=stdio` (not `http`)

## Security Notes

- Keep your `N8N_API_KEY` secure - it provides full access to n8n
- The `AUTH_TOKEN` is optional when using `docker exec` (Option 1)
- For production use, rotate API keys regularly

## Additional Resources

- [n8n MCP Documentation](https://github.com/czlonkowski/n8n-mcp)
- [Claude Desktop MCP Guide](https://docs.anthropic.com/claude/docs/model-context-protocol)
- Main project documentation: [README.md](./README.md)
