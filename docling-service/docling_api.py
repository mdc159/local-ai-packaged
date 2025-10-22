#!/usr/bin/env python3
"""
Lightweight Docling API service for document parsing
Provides a simple HTTP endpoint for converting documents to Markdown/JSON
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Literal
import os
import tempfile
from pathlib import Path

app = FastAPI(
    title="Docling API",
    description="Document parsing service using Docling",
    version="1.0.0"
)

class ConvertRequest(BaseModel):
    source: dict
    output: Optional[dict] = {"format": "markdown"}

class HealthResponse(BaseModel):
    status: str
    version: str
    message: str

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "version": "1.0.0",
        "message": "Docling service is running"
    }

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Docling API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "convert_url": "/v1/convert (POST with JSON)",
            "convert_upload": "/v1/convert/upload (POST with file)",
            "docs": "/docs"
        }
    }

@app.post("/v1/convert")
async def convert_document(request: ConvertRequest):
    """
    Convert a document from URL or local path

    Example request body:
    {
        "source": {
            "type": "path",
            "path": "/path/to/document.pdf"
        },
        "output": {
            "format": "markdown"
        }
    }
    """
    try:
        from docling.document_converter import DocumentConverter

        source_type = request.source.get("type")
        output_format = request.output.get("format", "markdown")

        # Initialize converter
        converter = DocumentConverter()

        # Handle different source types
        if source_type == "path":
            file_path = request.source.get("path")
            if not file_path or not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

            result = converter.convert(file_path)

        elif source_type == "url":
            url = request.source.get("url")
            if not url:
                raise HTTPException(status_code=400, detail="URL not provided")

            result = converter.convert(url)

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported source type: {source_type}")

        # Export to requested format
        if output_format == "markdown":
            content = result.document.export_to_markdown()
        elif output_format == "json":
            content = result.document.export_to_dict()
        elif output_format == "text":
            content = result.document.export_to_text()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported output format: {output_format}")

        return JSONResponse(content={
            "status": "success",
            "format": output_format,
            "content": content,
            "metadata": {
                "source": request.source,
                "pages": len(result.document.pages) if hasattr(result.document, 'pages') else None
            }
        })

    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Docling library not installed. Install with: pip install docling"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion error: {str(e)}")

@app.post("/v1/convert/upload")
async def convert_upload(file: UploadFile = File(...), output_format: Literal["markdown", "json", "text"] = "markdown"):
    """
    Convert an uploaded document file

    Upload a file and get it converted to the specified format
    """
    try:
        from docling.document_converter import DocumentConverter

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name

        try:
            # Convert the document
            converter = DocumentConverter()
            result = converter.convert(tmp_path)

            # Export to requested format
            if output_format == "markdown":
                output_content = result.document.export_to_markdown()
            elif output_format == "json":
                output_content = result.document.export_to_dict()
            elif output_format == "text":
                output_content = result.document.export_to_text()

            return JSONResponse(content={
                "status": "success",
                "filename": file.filename,
                "format": output_format,
                "content": output_content,
                "metadata": {
                    "pages": len(result.document.pages) if hasattr(result.document, 'pages') else None
                }
            })

        finally:
            # Clean up temporary file
            os.unlink(tmp_path)

    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Docling library not installed. Install with: pip install docling"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
