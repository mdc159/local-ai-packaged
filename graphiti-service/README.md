# Graphiti Knowledge Graph Service

A FastAPI-based REST API for building and querying temporal knowledge graphs using [Graphiti](https://github.com/getzep/graphiti) with Neo4j backend.

## Overview

Graphiti is a temporally-aware knowledge graph framework that:
- Builds dynamic knowledge graphs from episodic data
- Tracks entities, relationships, and facts over time
- Provides hybrid search (semantic + keyword + graph traversal)
- Maintains historical context with bi-temporal tracking
- Achieves P95 latency of ~300ms for retrieval

## Features

- **Episode Management**: Add discrete units of information (conversations, events, interactions)
- **Entity Extraction**: Automatically extract entities and relationships from episodes
- **Temporal Awareness**: Track when facts were created, when they're valid, and when they expire
- **Hybrid Search**: Semantic embeddings + BM25 + graph traversal
- **REST API**: Simple HTTP endpoints for integration with n8n, Python, or any HTTP client

## Quick Start

### Prerequisites

- Neo4j running on `bolt://neo4j:7687` (or configure `NEO4J_URI`)
- OpenAI API key (or Ollama for local LLM)
- Python 3.10+

### Installation

```bash
cd graphiti-service
pip install -r requirements.txt
```

### Configuration

Set environment variables (or use `.env` file):

```bash
# Neo4j Configuration
export NEO4J_URI=bolt://neo4j:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=your-password
export NEO4J_DATABASE=graphiti

# LLM Configuration (Option 1: OpenAI)
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
export LLM_MODEL=gpt-4o-mini

# LLM Configuration (Option 2: Ollama - Local)
export LLM_PROVIDER=ollama
export LLM_BASE_URL=http://ollama:11434/v1
export LLM_MODEL=qwen2.5:7b-instruct-q4_K_M

# Service Configuration
export GRAPHITI_PORT=5002
export GRAPHITI_HOST=0.0.0.0
```

### Running the Service

```bash
python graphiti_api.py
```

The API will be available at `http://localhost:5002`

## API Endpoints

### Health Check

```bash
GET /health
```

Response:
```json
{
  "status": "ok",
  "neo4j_connected": true,
  "llm_provider": "ollama",
  "database": "graphiti"
}
```

### Add Episode

Add a new episode (conversation, event, interaction) to the knowledge graph:

```bash
POST /v1/episodes
Content-Type: application/json

{
  "name": "Customer Meeting",
  "content": "Met with John from Acme Corp to discuss Q1 product requirements. He mentioned they need better reporting features and wants to integrate with Salesforce.",
  "source": "crm",
  "source_description": "CRM interaction log",
  "reference_time": "2025-10-22T10:30:00Z"
}
```

Response:
```json
{
  "status": "success",
  "episode_uuid": "123e4567-e89b-12d3-a456-426614174000",
  "entities_extracted": 3,
  "edges_created": 5,
  "message": "Episode 'Customer Meeting' added successfully"
}
```

### Search Knowledge Graph

Search using natural language:

```bash
POST /v1/search
Content-Type: application/json

{
  "query": "What did John from Acme Corp want?",
  "num_results": 5
}
```

Response:
```json
{
  "status": "success",
  "query": "What did John from Acme Corp want?",
  "results": [
    {
      "uuid": "...",
      "name": "John",
      "content": "John from Acme Corp wants better reporting features",
      "score": 0.95,
      "created_at": "2025-10-22T10:30:00Z"
    }
  ],
  "num_results": 1
}
```

### Search Entities

Find entities by name:

```bash
POST /v1/entities/search
Content-Type: application/json

{
  "entity_name": "John"
}
```

Response:
```json
{
  "status": "success",
  "entity_name": "John",
  "entities": [
    {
      "uuid": "...",
      "name": "John",
      "summary": "Customer contact at Acme Corp",
      "created_at": "2025-10-22T10:30:00Z"
    }
  ],
  "count": 1
}
```

### Get Statistics

```bash
GET /v1/stats
```

## Use Cases

### 1. Agent Memory

Build AI agents that remember past interactions:

```python
# Add conversation to memory
await graphiti.add_episode(
    name="Chat with User",
    content="User asked about pricing for enterprise plan. They have 500 employees.",
    source="chat"
)

# Later, query what we know about pricing
results = await graphiti.search("What did the user ask about pricing?")
```

### 2. CRM Integration

Track customer interactions over time:

```python
# Log sales call
await graphiti.add_episode(
    name="Sales Call - Acme Corp",
    content="Discussion with CEO about contract renewal. Mentioned budget constraints but interested in premium features.",
    source="crm",
    reference_time=datetime(2025, 10, 22, 14, 0)
)

# Query customer history
results = await graphiti.search("What are Acme Corp's budget concerns?")
```

### 3. Document Understanding

Build knowledge graphs from documents:

```python
# Process document chunks
for chunk in document_chunks:
    await graphiti.add_episode(
        name=f"Document Section: {chunk.title}",
        content=chunk.text,
        source="document",
        source_description=document.filename
    )

# Query across all documents
results = await graphiti.search("What are the key findings?")
```

## Architecture

```
┌─────────────┐
│   n8n       │
│  Workflow   │
└──────┬──────┘
       │ HTTP Request
       ▼
┌─────────────────────┐
│  Graphiti API       │
│  (FastAPI)          │
│  - Episodes         │
│  - Search           │
│  - Entity Retrieval │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│   Graphiti Core     │
│   - LLM Client      │
│   - Embedder        │
│   - Graph Builder   │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│     Neo4j           │
│  (Knowledge Graph)  │
│  - Entities         │
│  - Relationships    │
│  - Episodes         │
└─────────────────────┘
```

## Temporal Model

Graphiti uses a bi-temporal model:

- **t_created**: When the fact was created in the system
- **t_expired**: When the fact was invalidated/updated
- **t_valid**: When the fact became true in the real world
- **t_invalid**: When the fact stopped being true

Example:
```
John worked at Acme Corp from 2020-2023
- t_valid: 2020-01-01
- t_invalid: 2023-12-31
- t_created: 2025-10-22 (when we learned about it)
- t_expired: null (still valid information)
```

## Integration with n8n

See example workflows in `n8n/backup/workflows/`:
- `Example_Graphiti_Memory_Agent.json` - AI agent with episodic memory
- `Example_Graphiti_CRM_Tracker.json` - Customer interaction tracking
- `Example_Graphiti_Document_KB.json` - Document knowledge base

## Performance

- **P95 Latency**: ~300ms for retrieval
- **No LLM calls during search**: Only during episode ingestion
- **Real-time updates**: Incrementally processes data without batch recomputation

## Troubleshooting

### Neo4j Connection Failed

Check Neo4j is running:
```bash
docker ps | grep neo4j
```

Test connection:
```bash
docker exec neo4j cypher-shell -u neo4j -p your-password "RETURN 1;"
```

### LLM Provider Errors

**OpenAI**: Verify API key is valid
```bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

**Ollama**: Verify Ollama is running and model is pulled
```bash
curl http://ollama:11434/api/tags
docker exec ollama ollama list
```

### Slow Performance

1. Reduce `num_results` in search requests
2. Use focused search with `center_node_uuid`
3. Ensure Neo4j has proper indexes (Graphiti creates these automatically)

## Advanced Configuration

### Custom LLM Models

For better structured output support:
- OpenAI: `gpt-4o`, `gpt-4o-mini` (recommended)
- Anthropic: `claude-3-5-sonnet-20241022`
- Ollama: Models that support function calling

### Concurrency

Control concurrent LLM calls to avoid rate limiting:
```bash
export SEMAPHORE_LIMIT=5  # Default: 10
```

### Database Selection

Use different Neo4j databases for different knowledge domains:
```bash
export NEO4J_DATABASE=sales_kb
export NEO4J_DATABASE=support_kb
export NEO4J_DATABASE=personal_memory
```

## Resources

- [Graphiti GitHub](https://github.com/getzep/graphiti)
- [Graphiti Documentation](https://help.getzep.com/graphiti/)
- [Zep Platform](https://www.getzep.com/)
- [Neo4j Graph Database](https://neo4j.com/)

## License

This service wrapper is part of the local-ai-packaged project. Graphiti is licensed under Apache 2.0.
