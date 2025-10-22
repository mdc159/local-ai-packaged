# Docling API Service

Lightweight document parsing service using Docling for the local AI stack.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start the service
python docling_api.py
```

The service will be available at `http://localhost:5001`

## API Endpoints

- `GET /health` - Health check
- `GET /docs` - Interactive API documentation
- `POST /v1/convert` - Convert document from URL or path
- `POST /v1/convert/upload` - Upload and convert a document

## Example Usage

### Convert from local path:

```bash
curl -X POST http://localhost:5001/v1/convert \
  -H "Content-Type: application/json" \
  -d '{
    "source": {"type": "path", "path": "/path/to/document.pdf"},
    "output": {"format": "markdown"}
  }'
```

### Upload a file:

```bash
curl -X POST http://localhost:5001/v1/convert/upload \
  -F "file=@document.pdf" \
  -F "output_format=markdown"
```

## Integration with n8n

Use the HTTP Request node in n8n workflows:

- **URL**: `http://localhost:5001/v1/convert`
- **Method**: POST
- **Body**: JSON with source and output format
- **Headers**: `Content-Type: application/json`

## Supported Formats

**Input**: PDF, DOCX, PPTX, XLSX, HTML, images (PNG, JPEG, TIFF)

**Output**:
- `markdown` - Markdown with preserved structure
- `json` - Structured JSON with metadata
- `text` - Plain text extraction
