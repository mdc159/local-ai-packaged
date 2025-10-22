# Docling Integration Guide

## What Was Done

Successfully integrated Docling document parser into the local AI stack:

1. **Docling Service**: Running at `http://localhost:5001` (or `http://docling:5001` inside Docker)
2. **V4 Workflow**: Enhanced Agentic RAG workflow with Docling for superior document parsing
3. **Example Workflows**: Three practical examples demonstrating Docling capabilities

## Docling Service Status

- **Health**: http://localhost:5001/health
- **API Endpoints**:
  - `POST /v1/convert` - Convert document from path or URL
  - `POST /v1/convert/upload` - Upload and convert document
- **Supported Formats**: PDF, DOCX, PPTX, XLSX, HTML, PNG, JPEG, TIFF
- **Output Formats**: Markdown, JSON, Text

## Testing Docling

Your PDF from `X:\GitHub\local-ai-packaged\shared\data\12.pdf` was successfully tested:
- **Status**: Success
- **Pages**: 21 pages
- **Format**: Clean markdown with proper structure

```bash
# Test health
curl http://localhost:5001/health

# Convert a PDF
curl -X POST http://localhost:5001/v1/convert \
  -H "Content-Type: application/json" \
  -d '{"source": {"type": "path", "path": "X:/GitHub/local-ai-packaged/shared/data/12.pdf"}, "output": {"format": "markdown"}}'
```

## Importing Workflows into n8n

The V4 workflow and examples are in `X:\GitHub\local-ai-packaged\n8n\backup\workflows\`:
- `V4_Local_Agentic_RAG_Docling.json`
- `Example_Batch_PDF_Converter.json`
- `Example_Document_Structure_Analyzer.json`
- `Example_Multi_Format_Document_Converter.json`

### Method 1: Web UI Import (Recommended)

1. Open n8n: http://localhost:5678
2. Click **"+"** → **"Import from File"**
3. Select the workflow JSON file
4. Click **"Import"**

### Method 2: Copy from V3 and Modify

Since the CLI import is having path issues, you can:

1. Open **V3 Local Agentic RAG AI Agent** in n8n
2. Click the **three dots** → **"Duplicate"**
3. Rename it to "V4 Local Agentic RAG with Docling"
4. Replace the **"Extract PDF Text"** node with an **HTTP Request** node:
   - **Method**: POST
   - **URL**: `http://docling:5001/v1/convert`
   - **Body**: JSON
   ```json
   {
     "source": {
       "type": "path",
       "path": "={{ $('Set File ID').item.json.file_id }}"
     },
     "output": {
       "format": "markdown"
     }
   }
   ```
5. Add a **Code** node after the HTTP Request to extract content:
   ```javascript
   const item = items[0].json;
   const markdown = item.content || '';

   return {
     json: {
       data: markdown
     }
   };
   ```
6. Connect: `Docling HTTP Request` → `Extract Content Code` → `Postgres PGVector Store`
7. Update the **Switch** node to route DOCX/PPTX files to Docling as well

## V4 Workflow Features

Enhancements over V3:

- **Superior PDF Parsing**: Better table detection, layout analysis, text extraction
- **Multi-Format Support**: PDF, DOCX, PPTX with structure preservation
- **OCR Capabilities**: Handles scanned documents
- **Structured Output**: Clean markdown for better RAG retrieval

### File Type Routing

- **PDF, DOCX, PPTX** → Docling (enhanced parsing)
- **XLSX** → Standard Excel extraction
- **CSV, TXT** → Standard text extraction

## Example Workflows

### 1. Batch PDF Converter

**Purpose**: Automatically convert PDFs to markdown

**Setup**:
1. Create folders:
   ```bash
   mkdir -p X:/GitHub/local-ai-packaged/shared/pdf_input
   mkdir -p X:/GitHub/local-ai-packaged/shared/pdf_output
   ```
2. Import and activate the workflow
3. Drop PDFs into `shared/pdf_input`
4. Find markdown files in `shared/pdf_output`

### 2. Document Structure Analyzer

**Purpose**: Analyze document structure and extract metadata

**Usage**:
```bash
curl -X POST http://localhost:5678/webhook/analyze-document \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/data/shared/document.pdf"}'
```

**Returns**:
- Total pages, tables, figures
- Document headings hierarchy
- Element counts

### 3. Multi-Format Converter

**Purpose**: Upload any document and convert to markdown

**Setup**:
```bash
mkdir -p X:/GitHub/local-ai-packaged/shared/temp
```

**Usage**:
```bash
curl -X POST http://localhost:5678/webhook/convert-document \
  -F "file=@document.pdf"
```

## Testing the V4 Workflow

Once imported:

1. **Activate the workflow** (toggle switch in n8n)
2. **Upload a test PDF** to `/data/shared/` (maps to `X:\GitHub\local-ai-packaged\shared\`)
3. **Check n8n execution** - should see Docling being called
4. **Query the RAG agent** via chat or webhook about the document content

Example chat query:
```bash
curl -X POST http://localhost:5678/webhook/bf4dd093-bb02-472c-9454-7ab9af97bd1d \
  -H "Content-Type: application/json" \
  -d '{
    "chatInput": "What documents do you have about game theory?",
    "sessionId": "test-session-1"
  }'
```

## Troubleshooting

### Docling Service Not Running

```bash
cd X:\GitHub\local-ai-packaged\docling-service
python docling_api.py
```

### Check Docling Logs

Look at the background bash output for any errors during document parsing.

### Path Issues

Remember:
- Inside n8n container: `/data/shared/`
- On Windows host: `X:\GitHub\local-ai-packaged\shared\`
- For Docling API: Use either format (Python handles both)

### Workflow Import Fails

Use the Web UI method instead of CLI due to Git Bash path translation issues on Windows.

## Benefits of Docling Integration

1. **Better PDF parsing** - Handles complex layouts, tables, multi-column text
2. **Multi-format support** - One API for PDF, DOCX, PPTX, XLSX
3. **Structure preservation** - Maintains headings, lists, formatting
4. **OCR built-in** - Processes scanned documents automatically
5. **Clean markdown** - Better for RAG chunking and retrieval

## Next Steps

1. Import the V4 workflow via n8n Web UI
2. Test with your PDFs in `shared/data/`
3. Compare results with V3 workflow
4. Customize system prompts for your use case
5. Try the example workflows for specific document processing tasks
