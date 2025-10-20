#!/usr/bin/env python3
import json
import requests

# Read the workflow JSON
with open('n8n/backup/workflows/V1_Local_RAG_AI_Agent.json', 'r') as f:
    workflow_data = json.load(f)

# API configuration
api_url = "http://127.0.0.1:5678/api/v1/workflows"
api_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmMjFiZDk2Yi0xOWVlLTQ1N2QtYWJjZS0xNmM3ZDBkYzY2OGIiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzYwODk1Mzc1fQ.X3xeFl1QSA5fZCMhESP2aZoSpCrFvK0DyG9CraVXhb8"

headers = {
    "X-N8N-API-KEY": api_key,
    "Content-Type": "application/json"
}

# Create the workflow
response = requests.post(api_url, headers=headers, json=workflow_data)

if response.status_code == 201:
    result = response.json()
    print(f"✅ Workflow created successfully!")
    print(f"Workflow ID: {result.get('id')}")
    print(f"Workflow Name: {result.get('name')}")
    print(f"Active: {result.get('active')}")
    print(f"\nYou can view it at: http://127.0.0.1:5678/workflow/{result.get('id')}")
else:
    print(f"❌ Error creating workflow: {response.status_code}")
    print(f"Response: {response.text}")
