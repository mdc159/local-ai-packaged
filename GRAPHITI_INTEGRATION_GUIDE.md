# Graphiti Knowledge Graph Integration Guide

## What Was Done

Successfully integrated Graphiti, a temporal knowledge graph framework, into the local AI stack:

1. **Graphiti Service**: FastAPI wrapper ready to build as Docker image
2. **Neo4j Integration**: Uses existing Neo4j container, creates separate `graphiti` database
3. **Three Example Workflows**: Practical n8n workflows demonstrating key use cases
4. **Complete Documentation**: API docs, usage examples, and troubleshooting

## Graphiti Service Status

The Graphiti service is ready to deploy:

- **API Endpoints**:
  - `POST /v1/episodes` - Add episodic data to knowledge graph
  - `POST /v1/search` - Natural language search with hybrid retrieval
  - `POST /v1/entities/search` - Find specific entities
  - `GET /v1/stats` - Knowledge graph statistics
  - `GET /health` - Health check

- **Configuration**:
  - Neo4j: `bolt://neo4j:7687`, database: `graphiti`
  - LLM Provider: Ollama (default), OpenAI, or Anthropic
  - Port: 5002 (localhost) or via Caddy reverse proxy

## Building and Starting Graphiti

### Build the Docker Image

```bash
cd X:\GitHub\local-ai-packaged
docker compose build graphiti
```

### Start with the Stack

The Graphiti service will start automatically with `start_services.py`:

```bash
python start_services.py --profile gpu-nvidia
```

Or start it manually:

```bash
docker compose up -d graphiti
```

### Verify It's Running

```bash
# Check container status
docker ps | grep graphiti

# Test health endpoint
curl http://localhost:5002/health

# View logs
docker logs graphiti --tail 50
```

## Quick Start Example

### 1. Add an Episode

Store a conversation or interaction:

```bash
curl -X POST http://localhost:5002/v1/episodes \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sales Call - Acme Corp",
    "content": "Spoke with Sarah Johnson, CTO at Acme Corp. They need better reporting features for their 500-person team. Budget is $50k annually. Interested in Q1 2025 rollout.",
    "source": "crm",
    "source_description": "Sales call log",
    "reference_time": "2025-10-22T14:00:00Z"
  }'
```

Response:
```json
{
  "status": "success",
  "episode_uuid": "123e4567-e89b-12d3-a456-426614174000",
  "entities_extracted": 3,
  "edges_created": 5,
  "message": "Episode 'Sales Call - Acme Corp' added successfully"
}
```

### 2. Search the Knowledge Graph

Query what you know:

```bash
curl -X POST http://localhost:5002/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What does Acme Corp need?",
    "num_results": 5
  }'
```

Response:
```json
{
  "status": "success",
  "query": "What does Acme Corp need?",
  "results": [
    {
      "uuid": "...",
      "name": "Acme Corp",
      "content": "Acme Corp needs better reporting features",
      "score": 0.95,
      "created_at": "2025-10-22T14:00:00Z"
    }
  ],
  "num_results": 1
}
```

### 3. Find Entities

```bash
curl -X POST http://localhost:5002/v1/entities/search \
  -H "Content-Type: application/json" \
  -d '{
    "entity_name": "Sarah Johnson"
  }'
```

## Example n8n Workflows

Three workflows have been created in `n8n/backup/workflows/`:

### 1. Example_Graphiti_Memory_Agent.json

**AI agent with episodic memory:**
- User sends chat message
- Agent searches Graphiti for relevant context
- Agent responds with context-aware answer
- Conversation stored as episode

**Test it:**
```bash
curl -X POST http://localhost:5678/webhook/graphiti-chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I met with Sarah from TechCorp today",
    "user_id": "user123"
  }'
```

### 2. Example_Graphiti_CRM_Tracker.json

**Automatic CRM interaction tracking:**
- Watches `/data/shared/crm_interactions/` folder
- Parses interaction logs (JSON format)
- Stores in Graphiti with entity extraction
- Builds relationship graph over time

**Setup:**
```bash
mkdir -p X:/GitHub/local-ai-packaged/shared/crm_interactions
```

**Sample interaction log** (`interaction_001.json`):
```json
{
  "customer_name": "John Doe",
  "company": "Tech Industries",
  "interaction_type": "Demo Call",
  "notes": "Showed product features. Very interested in API integration.",
  "products": ["API Gateway", "Analytics Dashboard"],
  "next_steps": "Send pricing proposal",
  "timestamp": "2025-10-22T15:00:00Z"
}
```

### 3. Example_Graphiti_Knowledge_Query.json

**Simple knowledge base interface:**
- Natural language question via webhook
- Search Graphiti knowledge graph
- Format results with source attribution
- Return structured answer

**Test it:**
```bash
curl -X POST http://localhost:5678/webhook/graphiti-query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What do we know about Acme Corp?"
  }'
```

## Importing Workflows

Use the n8n import container:

```bash
docker start -a n8n-import
```

This will import all workflows including the new Graphiti examples.

## Architecture

```
┌──────────────┐
│ n8n Workflow │
└──────┬───────┘
       │ HTTP POST
       ▼
┌──────────────────┐
│ Graphiti API     │
│ (Port 5002)      │
│ - Episodes       │
│ - Search         │
│ - Entities       │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Graphiti Core    │
│ - LLM Client     │
│ - Entity Extract │
│ - Graph Builder  │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Neo4j Database   │
│ (Port 7687)      │
│ Database:graphiti│
└──────────────────┘
```

## Key Features

### 1. Temporal Awareness

Graphiti tracks **bi-temporal data**:
- **t_created**: When fact was recorded in system
- **t_expired**: When fact was invalidated/updated
- **t_valid**: When fact became true in real world
- **t_invalid**: When fact stopped being true

Example:
```
"John worked at Microsoft"
- t_valid: 2018-01-01
- t_invalid: 2023-06-30
- t_created: 2025-10-22 (when we learned it)
- t_expired: null
```

### 2. Episodic Memory

Store discrete units of information:
- **Conversations**: Chat logs, meeting notes
- **Events**: Transactions, interactions
- **Documents**: Reports, emails, articles

Each episode automatically extracts:
- **Entities**: People, companies, products
- **Relationships**: Works for, needs, mentions
- **Facts**: Assertions with temporal context

### 3. Hybrid Search

Retrieval combines three methods:
- **Semantic**: Vector embeddings for meaning
- **Keyword**: BM25 for exact matches
- **Graph**: Traversal for relationships

Result: **P95 latency ~300ms** without LLM calls during search.

### 4. Real-time Updates

No batch processing needed:
- Add episodes incrementally
- Graph updates automatically
- Relationships discovered dynamically

## Configuration

### LLM Providers

**Option 1: Ollama (Default - No API Key)**
```bash
# In .env
GRAPHITI_LLM_PROVIDER=ollama
GRAPHITI_LLM_MODEL=qwen2.5:7b-instruct-q4_K_M
GRAPHITI_LLM_BASE_URL=http://ollama:11434/v1
```

**Option 2: OpenAI**
```bash
# In .env
GRAPHITI_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
GRAPHITI_LLM_MODEL=gpt-4o-mini
```

**Option 3: Anthropic**
```bash
# In .env
GRAPHITI_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
GRAPHITI_LLM_MODEL=claude-3-5-sonnet-20241022
```

### Neo4j Connection

Graphiti uses your existing Neo4j container:
- **URI**: `bolt://neo4j:7687`
- **User**: From `NEO4J_AUTH` in `.env`
- **Database**: `graphiti` (auto-created)

## Use Cases

### 1. AI Agent Memory

Build agents that remember and learn:

```python
# Store interaction
await graphiti.add_episode(
    name="User Question",
    content="User asked about pricing for enterprise tier. They have 200 employees.",
    source="chat"
)

# Later, recall context
results = await graphiti.search("What did user ask about pricing?")
# Returns: Previous conversation with 200 employee detail
```

### 2. Customer Intelligence

Track relationships over time:

```python
# Log sales call
await graphiti.add_episode(
    name="Discovery Call - TechCorp",
    content="CEO wants integration with Salesforce. Budget approved for Q1.",
    source="crm",
    reference_time=datetime(2025, 10, 22, 10, 0)
)

# Query customer knowledge
results = await graphiti.search("What does TechCorp's CEO want?")
# Returns: Salesforce integration need with temporal context
```

### 3. Document Knowledge Graphs

Build connected understanding from documents:

```python
# Process document sections
for chunk in document.chunks:
    await graphiti.add_episode(
        name=f"Section: {chunk.heading}",
        content=chunk.text,
        source="document",
        source_description=document.title
    )

# Cross-document queries
results = await graphiti.search("How do these systems integrate?")
# Returns: Connected facts across multiple documents
```

## Troubleshooting

### Graphiti Won't Start

**Startup Time:**
Graphiti takes approximately 80 seconds to fully initialize on first run. This is normal as it:
- Connects to Neo4j
- Builds indices and constraints
- Initializes the LLM client (Ollama by default)

Wait for the health check to pass before making API calls.

**API Compatibility:**
The service uses graphiti-core v0.3.5 with `OpenAIClient` which works with Ollama's OpenAI-compatible API. If you see import errors like `ModuleNotFoundError: No module named 'graphiti_core.embedder'`, the API code has been updated to work with the current library version.

**Check Neo4j is running:**
```bash
docker ps | grep neo4j
docker logs localai-neo4j-1 --tail 50
```

**Test Neo4j connection:**
```bash
docker exec localai-neo4j-1 cypher-shell -u neo4j -p your-password
```

### LLM Errors

**Ollama:**
```bash
# Verify Ollama is running
curl http://localhost:11434/api/tags

# Check model is pulled
docker exec ollama ollama list
```

**OpenAI/Anthropic:**
```bash
# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Slow Performance

1. Reduce `num_results` in search requests
2. Use `center_node_uuid` for focused search
3. Check Neo4j indexes (Graphiti creates automatically)

### Empty Search Results

- Episode processing takes time (entity extraction)
- Wait 10-30 seconds after adding episode
- Check logs: `docker logs graphiti --tail 100`

## Performance Tips

1. **Batch Episodes**: Add multiple episodes before searching
2. **Specific Queries**: More specific = better results
3. **Entity Names**: Use consistent naming for better linking
4. **Reference Times**: Provide timestamps for temporal queries

## Advanced Usage

### Point-in-Time Queries

Query knowledge as it existed at specific time:

```python
# "What did we know about TechCorp in January?"
results = await graphiti.search(
    query="TechCorp",
    reference_time=datetime(2025, 1, 31)
)
```

### Entity Relationships

Track how entities connect:

```python
# After multiple episodes, Graphiti automatically discovers:
# - "Sarah Johnson" works_for "Acme Corp"
# - "Acme Corp" needs "Reporting Features"
# - "Reporting Features" costs "$50k annually"
```

### Community Detection

Graphiti builds hierarchical communities:
- **Episodic**: Raw interactions
- **Semantic**: Extracted entities/facts
- **Community**: High-level domain summaries

## Resources

- **Local Documentation**: `graphiti-service/README.md`
- **Graphiti GitHub**: https://github.com/getzep/graphiti
- **Graphiti Docs**: https://help.getzep.com/graphiti/
- **Zep Platform**: https://www.getzep.com/
- **Neo4j**: https://neo4j.com/

## Next Steps

1. **Build the image**: `docker compose build graphiti`
2. **Start the service**: Included in `start_services.py`
3. **Import workflows**: `docker start -a n8n-import`
4. **Test with example**: See "Quick Start Example" above
5. **Build your use case**: Adapt example workflows

Your Neo4j database just got a powerful memory system! 🧠
