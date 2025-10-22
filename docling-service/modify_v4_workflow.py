#!/usr/bin/env python3
"""
Script to modify V4 workflow to add Docling integration for PDF/DOCX/PPTX/XLSX parsing.
Replaces the "Extract PDF Text" node with an HTTP Request to Docling service.
"""
import json
import uuid

# Load V4 workflow
with open("X:/GitHub/local-ai-packaged/n8n/backup/workflows/V4_Local_Agentic_RAG_Docling.json", "r") as f:
    workflow = json.load(f)

# Find and modify the "Extract PDF Text" node
for i, node in enumerate(workflow["nodes"]):
    if node["name"] == "Extract PDF Text":
        # Replace with HTTP Request node that calls Docling
        workflow["nodes"][i] = {
            "parameters": {
                "method": "POST",
                "url": "http://docling:5001/v1/convert",
                "authentication": "none",
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": "={{ {\n  \"source\": {\n    \"type\": \"path\",\n    \"path\": $('Set File ID').item.json.file_id\n  },\n  \"output\": {\n    \"format\": \"markdown\"\n  }\n} }}",
                "options": {}
            },
            "id": str(uuid.uuid4()),
            "name": "Docling PDF Parser",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": node["position"]
        }

    # Update sticky note to reflect Docling integration
    if node["id"] == "69bc6648-74a5-4f24-8539-63fdc890bf8e":  # Main sticky note
        node["parameters"]["content"] = """## 🚀 n8n Local AI Agentic RAG Template with Docling

**Author:** [Cole Medin](https://www.youtube.com/@ColeMedin)
**Enhanced with:** Docling Document Parser

## What is this?
This template provides an entirely local implementation of an **Agentic RAG (Retrieval Augmented Generation)** system in n8n enhanced with **Docling** for superior document parsing. Unlike standard RAG which only performs simple lookups, this agent can reason about your knowledge base, self-improve retrieval, and dynamically switch between different tools based on the specific question.

## Why Docling?
Docling provides advanced document understanding with:
- **Superior PDF parsing**: Better table detection, layout analysis, and text extraction
- **Multi-format support**: PDF, DOCX, PPTX, XLSX, HTML, images
- **Structured extraction**: Preserves document structure, headings, and formatting
- **OCR capabilities**: Handles scanned documents and images
- **Markdown output**: Clean, structured markdown for better RAG retrieval

## Why Agentic RAG?
Standard RAG has significant limitations:
- Poor analysis of numerical/tabular data
- Missing context due to document chunking
- Inability to connect information across documents
- No dynamic tool selection based on question type

## What makes this template powerful:
- **Docling Integration**: Advanced document parsing for PDFs, DOCX, PPTX, XLSX
- **Intelligent tool selection**: Switches between RAG lookups, SQL queries, or full document retrieval
- **Complete document context**: Accesses entire documents when needed instead of just chunks
- **Accurate numerical analysis**: Uses SQL for precise calculations on spreadsheet/tabular data
- **Cross-document insights**: Connects information across your entire knowledge base
- **Multi-file processing**: Handles multiple documents in a single workflow loop
- **Efficient storage**: Uses JSONB in Supabase to store tabular data

## Getting Started
1. Ensure Docling service is running: `http://docling:5001`
2. Run the table creation nodes first to set up your database tables
3. Upload your documents to /data/shared (the shared folder in local-ai-packaged)
4. The agent will process them automatically using Docling for enhanced parsing
5. Start asking questions that leverage the agent's multiple reasoning approaches

## Supported Document Types
- **Docling-enhanced**: PDF, DOCX, PPTX, XLSX (better parsing quality)
- **Standard extraction**: CSV, TXT (direct extraction)

## Customization
This template provides a solid foundation that you can extend by:
- Tuning the system prompt for your specific use case
- Adding document metadata like summaries
- Implementing more advanced RAG techniques
- Optimizing for larger knowledge bases

---

The non-local (\"cloud\") version of this Agentic RAG agent can be [found here](https://github.com/coleam00/ottomator-agents/tree/main/n8n-agentic-rag-agent)."""

# Update Switch node to route PDFs to Docling
for node in workflow["nodes"]:
    if node["name"] == "Switch":
        # The first rule (pdf) should stay, but we'll also add rules for docx, pptx, xlsx to use Docling
        rules = node["parameters"]["rules"]["values"]

        # Add DOCX rule
        rules.append({
            "conditions": {
                "options": {
                    "caseSensitive": "true",
                    "leftValue": "",
                    "typeValidation": "strict",
                    "version": 1
                },
                "conditions": [{
                    "leftValue": "={{ $('Set File ID').item.json.file_type }}",
                    "rightValue": "docx",
                    "operator": {
                        "type": "string",
                        "operation": "equals"
                    }
                }],
                "combinator": "and"
            }
        })

        # Add PPTX rule
        rules.append({
            "conditions": {
                "options": {
                    "caseSensitive": "true",
                    "leftValue": "",
                    "typeValidation": "strict",
                    "version": 1
                },
                "conditions": [{
                    "leftValue": "={{ $('Set File ID').item.json.file_type }}",
                    "rightValue": "pptx",
                    "operator": {
                        "type": "string",
                        "operation": "equals"
                    }
                }],
                "combinator": "and"
            }
        })

# Update connections to use Docling for PDFs/DOCX/PPTX
# The Switch node outputs to different parsers based on file type
# Output 0 (PDF) -> Docling
# Output 1 (XLSX) -> Extract from Excel
# Output 2 (CSV) -> Extract from CSV
# Output 3 (TXT/default) -> Extract Document Text
# Output 4 (DOCX) -> Docling
# Output 5 (PPTX) -> Docling

for node_name, connections in workflow["connections"].items():
    if node_name == "Switch":
        # Add connections for DOCX and PPTX to Docling
        main_connections = connections["main"]
        # Ensure we have enough output slots
        while len(main_connections) < 6:
            main_connections.append([])

        # DOCX (output 4) and PPTX (output 5) should connect to Docling
        main_connections[4] = [{
            "node": "Docling PDF Parser",
            "type": "main",
            "index": 0
        }]
        main_connections[5] = [{
            "node": "Docling PDF Parser",
            "type": "main",
            "index": 0
        }]

# Find Docling Parser node and add connection to vector store
if "Extract PDF Text" in workflow["connections"]:
    # Rename the connection key from "Extract PDF Text" to "Docling PDF Parser"
    workflow["connections"]["Docling PDF Parser"] = workflow["connections"].pop("Extract PDF Text")

# Add a Code node to extract markdown content from Docling response
docling_extract_node = {
    "parameters": {
        "mode": "runOnceForAllItems",
        "jsCode": "// Extract markdown content from Docling API response\nconst item = items[0].json;\nconst markdown = item.content || '';\n\nreturn {\n  json: {\n    data: markdown\n  }\n};"
    },
    "id": str(uuid.uuid4()),
    "name": "Extract Docling Content",
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [380, 580]
}

# Insert the node after Docling Parser
workflow["nodes"].append(docling_extract_node)

# Update connections: Docling PDF Parser -> Extract Docling Content -> Postgres PGVector Store
workflow["connections"]["Docling PDF Parser"] = {
    "main": [[{
        "node": "Extract Docling Content",
        "type": "main",
        "index": 0
    }]]
}

workflow["connections"]["Extract Docling Content"] = {
    "main": [[{
        "node": "Postgres PGVector Store",
        "type": "main",
        "index": 0
    }]]
}

# Save the modified workflow
with open("X:/GitHub/local-ai-packaged/n8n/backup/workflows/V4_Local_Agentic_RAG_Docling.json", "w") as f:
    json.dump(workflow, f, indent=2)

print("[OK] Successfully created V4 workflow with Docling integration")
print("  - PDF files will be parsed by Docling for superior extraction")
print("  - DOCX files will be parsed by Docling")
print("  - PPTX files will be parsed by Docling")
print("  - XLSX files will use standard Excel extraction")
print("  - CSV/TXT files will use standard text extraction")
