# Option Comparison Tool API

A comprehensive REST API for comparing multiple options with structured analysis.

## Quick Start

### Installation

```bash
pip install -e .
```

### Starting the API Server

```bash
# Using the entry point
option-compare-api

# Or directly with Python
python -m option_comparison_tool.api_server

# With custom configuration
option-compare-api --host 0.0.0.0 --port 8080 --reload
```

### API Documentation

Once the server is running, visit:
- **Interactive API docs**: http://localhost:8000/docs
- **ReDoc documentation**: http://localhost:8000/redoc

## API Endpoints

### Health Check
- `GET /health` - Service health status

### Sessions
- `POST /sessions` - Create a new comparison session
- `GET /sessions` - List all sessions
- `GET /sessions/{session_id}` - Get session details
- `PUT /sessions/{session_id}` - Update session constraints
- `DELETE /sessions/{session_id}` - Delete a session
- `POST /sessions/{session_id}/options` - Add option to session

### Analysis
- `POST /sessions/{session_id}/analyze` - Run analysis on session
- `POST /sessions/{session_id}/adjust-weights` - Adjust constraint weights
- `POST /sessions/{session_id}/what-if` - Create what-if scenario
- `POST /sessions/{session_id}/sensitivity` - Analyze constraint sensitivity
- `GET /sessions/{session_id}/critical-constraints` - Get critical constraints

### Export
- `POST /sessions/{session_id}/export` - Export session results

### Templates
- `GET /templates` - List available templates
- `GET /templates/{template_id}` - Get template details
- `POST /templates/{template_id}/apply` - Apply template to create session

## Example Usage

### Create a Comparison Session

```bash
curl -X POST "http://localhost:8000/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "options": [
      {
        "name": "Option A",
        "description": "First option",
        "attributes": {"cost": 100, "performance": 8}
      },
      {
        "name": "Option B", 
        "description": "Second option",
        "attributes": {"cost": 150, "performance": 9}
      }
    ],
    "constraints": [
      {
        "name": "Cost",
        "description": "Total cost consideration",
        "weight": 0.6,
        "type": "numeric",
        "priority": "required"
      },
      {
        "name": "Performance",
        "description": "Performance rating",
        "weight": 0.4,
        "type": "numeric", 
        "priority": "preferred"
      }
    ]
  }'
```

### Run Analysis

```bash
curl -X POST "http://localhost:8000/sessions/{session_id}/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "weighted_scoring"
  }'
```

### Export Results

```bash
curl -X POST "http://localhost:8000/sessions/{session_id}/export" \
  -H "Content-Type: application/json" \
  -d '{
    "formats": ["json", "markdown"]
  }'
```

## Development

### Running in Development Mode

```bash
option-compare-api --reload --log-level debug
```

### API Testing

The API includes comprehensive request/response validation using Pydantic models and automatic OpenAPI documentation generation.

### CORS Configuration

The API includes CORS middleware configured to allow all origins for development. Configure appropriately for production use.

## Production Deployment

### Using Uvicorn

```bash
uvicorn option_comparison_tool.api:app --host 0.0.0.0 --port 8000 --workers 4
```

### Using Gunicorn

```bash
gunicorn option_comparison_tool.api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Environment Variables

- `HOST`: Server host (default: 127.0.0.1)
- `PORT`: Server port (default: 8000)
- `LOG_LEVEL`: Logging level (default: info)
- `WORKERS`: Number of worker processes (default: 1)

## Error Handling

The API provides comprehensive error handling with appropriate HTTP status codes:

- `400 Bad Request`: Invalid input data or validation errors
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Unexpected server errors
- `503 Service Unavailable`: Service not initialized

All error responses follow a consistent format with error type, message, and optional details.