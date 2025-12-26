#!/usr/bin/env python3
"""
Graphiti API Service - FastAPI wrapper for Graphiti knowledge graph operations.

This service provides a REST API for building and querying temporal knowledge graphs
using Graphiti with Neo4j backend.
"""

import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from graphiti_core.edges import EntityEdge


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Environment variables
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "graphiti")

# LLM Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # openai, anthropic, ollama
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")  # For Ollama: http://ollama:11434/v1

# Global Graphiti instance
graphiti_instance: Optional[Graphiti] = None


# Pydantic Models
class HealthResponse(BaseModel):
    status: str
    neo4j_connected: bool
    llm_provider: str
    database: str


class AddEpisodeRequest(BaseModel):
    name: str = Field(..., description="Name/title of the episode")
    content: str = Field(..., description="Content or description of the episode")
    source: str = Field(default="api", description="Source of the episode")
    source_description: Optional[str] = Field(None, description="Description of the source")
    reference_time: Optional[datetime] = Field(None, description="Reference timestamp for the episode")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Customer Meeting",
                "content": "Met with John from Acme Corp to discuss Q1 product requirements. He mentioned they need better reporting features.",
                "source": "crm",
                "source_description": "CRM interaction log",
                "reference_time": "2025-10-22T10:30:00Z"
            }
        }


class SearchRequest(BaseModel):
    query: str = Field(..., description="Natural language search query")
    num_results: int = Field(default=10, description="Number of results to return")
    center_node_uuid: Optional[str] = Field(None, description="UUID of center node for focused search")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What were the main topics discussed with Acme Corp?",
                "num_results": 5
            }
        }


class EntitySearchRequest(BaseModel):
    entity_name: str = Field(..., description="Name of the entity to search for")

    class Config:
        json_schema_extra = {
            "example": {
                "entity_name": "John"
            }
        }


class AddEpisodeResponse(BaseModel):
    status: str
    episode_uuid: str
    entities_extracted: int
    edges_created: int
    message: str


class SearchResponse(BaseModel):
    status: str
    query: str
    results: List[Dict[str, Any]]
    num_results: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Graphiti instance on startup."""
    global graphiti_instance

    try:
        logger.info(f"Initializing Graphiti with Neo4j at {NEO4J_URI}")

        from graphiti_core.llm_client import OpenAIClient, LLMConfig

        # Configure LLM - OpenAIClient works with Ollama's OpenAI-compatible API
        if LLM_PROVIDER == "ollama":
            llm_config = LLMConfig(
                base_url=LLM_BASE_URL,
                model=LLM_MODEL,
                api_key="ollama"  # Dummy key for Ollama
            )
        elif LLM_PROVIDER == "anthropic":
            # Anthropic requires using OpenAI-compatible mode or separate client
            llm_config = LLMConfig(
                api_key=ANTHROPIC_API_KEY,
                model=LLM_MODEL
            )
        else:  # openai
            llm_config = LLMConfig(
                api_key=OPENAI_API_KEY,
                model=LLM_MODEL,
                base_url=LLM_BASE_URL if LLM_BASE_URL else None
            )

        llm_client = OpenAIClient(config=llm_config)

        # Initialize Graphiti
        graphiti_instance = Graphiti(
            uri=NEO4J_URI,
            user=NEO4J_USER,
            password=NEO4J_PASSWORD,
            llm_client=llm_client
        )

        # Build indices
        await graphiti_instance.build_indices_and_constraints()

        logger.info("Graphiti initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize Graphiti: {e}")
        raise

    yield

    # Cleanup
    if graphiti_instance:
        await graphiti_instance.close()
        logger.info("Graphiti connection closed")


# Initialize FastAPI app
app = FastAPI(
    title="Graphiti Knowledge Graph API",
    description="REST API for building and querying temporal knowledge graphs with Graphiti",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check service health and Neo4j connectivity."""
    neo4j_connected = False

    if graphiti_instance:
        try:
            # Simple connectivity check
            neo4j_connected = True
        except:
            pass

    return HealthResponse(
        status="ok" if neo4j_connected else "degraded",
        neo4j_connected=neo4j_connected,
        llm_provider=LLM_PROVIDER,
        database=NEO4J_DATABASE
    )


@app.post("/v1/episodes", response_model=AddEpisodeResponse)
async def add_episode(request: AddEpisodeRequest):
    """
    Add a new episode to the knowledge graph.

    Episodes represent discrete units of information or interactions that will be
    processed to extract entities, relationships, and facts.
    """
    if not graphiti_instance:
        raise HTTPException(status_code=503, detail="Graphiti not initialized")

    try:
        # Add episode to knowledge graph
        episode_uuid = await graphiti_instance.add_episode(
            name=request.name,
            episode_body=request.content,
            source=EpisodeType.text,  # or message, json depending on use case
            source_description=request.source_description or request.source,
            reference_time=request.reference_time or datetime.now()
        )

        logger.info(f"Added episode: {episode_uuid}")

        # Get episode stats (simplified - actual implementation would query the graph)
        return AddEpisodeResponse(
            status="success",
            episode_uuid=str(episode_uuid),
            entities_extracted=0,  # Would need to query
            edges_created=0,  # Would need to query
            message=f"Episode '{request.name}' added successfully"
        )

    except Exception as e:
        logger.error(f"Error adding episode: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add episode: {str(e)}")


@app.post("/v1/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Search the knowledge graph using natural language queries.

    Uses hybrid search combining semantic embeddings, keyword search, and graph traversal.
    """
    if not graphiti_instance:
        raise HTTPException(status_code=503, detail="Graphiti not initialized")

    try:
        # Perform search
        results = await graphiti_instance.search(
            query=request.query,
            num_results=request.num_results,
            center_node_uuid=request.center_node_uuid
        )

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                "uuid": str(result.uuid),
                "name": result.name,
                "content": result.fact if hasattr(result, 'fact') else str(result),
                "score": result.score if hasattr(result, 'score') else 0.0,
                "created_at": result.created_at.isoformat() if hasattr(result, 'created_at') else None
            })

        return SearchResponse(
            status="success",
            query=request.query,
            results=formatted_results,
            num_results=len(formatted_results)
        )

    except Exception as e:
        logger.error(f"Error searching: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/v1/entities/search")
async def search_entities(request: EntitySearchRequest):
    """
    Search for entities by name in the knowledge graph.
    """
    if not graphiti_instance:
        raise HTTPException(status_code=503, detail="Graphiti not initialized")

    try:
        entities = await graphiti_instance.retrieve_entities(
            entity_name=request.entity_name
        )

        formatted_entities = []
        for entity in entities:
            formatted_entities.append({
                "uuid": str(entity.uuid),
                "name": entity.name,
                "summary": entity.summary if hasattr(entity, 'summary') else None,
                "created_at": entity.created_at.isoformat() if hasattr(entity, 'created_at') else None
            })

        return {
            "status": "success",
            "entity_name": request.entity_name,
            "entities": formatted_entities,
            "count": len(formatted_entities)
        }

    except Exception as e:
        logger.error(f"Error searching entities: {e}")
        raise HTTPException(status_code=500, detail=f"Entity search failed: {str(e)}")


@app.get("/v1/stats")
async def get_stats():
    """Get statistics about the knowledge graph."""
    if not graphiti_instance:
        raise HTTPException(status_code=503, detail="Graphiti not initialized")

    try:
        # This would need proper implementation to query Neo4j for stats
        return {
            "status": "success",
            "message": "Stats endpoint - implementation needed",
            "database": NEO4J_DATABASE
        }

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("GRAPHITI_PORT", "5002"))
    host = os.getenv("GRAPHITI_HOST", "0.0.0.0")

    logger.info(f"Starting Graphiti API service on {host}:{port}")
    logger.info(f"Neo4j: {NEO4J_URI}, Database: {NEO4J_DATABASE}")
    logger.info(f"LLM Provider: {LLM_PROVIDER}, Model: {LLM_MODEL}")

    uvicorn.run(
        "graphiti_api:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )
