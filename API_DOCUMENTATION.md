# API Documentation

## Purpose and Scope
This document describes the API endpoints, data flow, and usage patterns for the RAG-KG Customer Service QA System. Includes REST API specifications, CLI interface, and integration examples.

## API Architecture

### System Overview
```
Client Request → FastAPI Server → Query Processor → Retrieval System → Answer Generator → Response
                                      ↓
                            ┌─────────────────┐
                            │   Knowledge     │
                            │     Graph       │
                            │   (Neo4j)       │
                            └─────────────────┘
                                      ↓
                            ┌─────────────────┐
                            │   Vector DB     │
                            │   (Qdrant)      │
                            └─────────────────┘
```

### Core Components
- **FastAPI Server**: REST API endpoint handling
- **Query Processor**: Entity extraction and intent detection
- **Retrieval System**: Graph traversal and vector similarity search
- **Answer Generator**: OLLAMA-based response synthesis

## REST API Endpoints

### Query Endpoint

#### POST /api/v1/query
Process a customer service question and return an answer with sources.

**Request Body:**
```json
{
  "question": "How do I reset my password on the mobile app?",
  "context": {
    "user_id": "user123",
    "product": "mobile_app",
    "priority": "normal"
  },
  "options": {
    "max_sources": 5,
    "include_similar": true,
    "confidence_threshold": 0.7
  }
}
```

**Response:**
```json
{
  "answer": "To reset your password on the mobile app, go to Settings > Account > Reset Password. You'll receive an email with reset instructions.",
  "confidence": 0.89,
  "sources": [
    {
      "ticket_id": "CS-001",
      "type": "resolution",
      "text": "Password reset process for mobile app",
      "similarity": 0.92
    },
    {
      "ticket_id": "CS-045",
      "type": "comment",
      "text": "User confirmed password reset worked",
      "similarity": 0.78
    }
  ],
  "processing_time": 1.2,
  "model_used": "llama2:7b-chat-q4_0"
}
```

**Error Responses:**
```json
{
  "error": "Query processing failed",
  "code": "PROCESSING_ERROR",
  "details": "OLLAMA model not available"
}
```

### Health Check Endpoint

#### GET /health
Check system health and component status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "components": {
    "ollama": "healthy",
    "neo4j": "healthy",
    "qdrant": "healthy",
    "api": "healthy"
  },
  "memory_usage": {
    "total": "12.5GB",
    "available": "3.5GB",
    "used_percent": 78.1
  }
}
```

### Metrics Endpoint

#### GET /metrics
Get system performance metrics.

**Response:**
```json
{
  "queries_processed": 1250,
  "average_response_time": 1.8,
  "cache_hit_rate": 0.65,
  "model_inference_time": 1.2,
  "database_query_time": 0.3,
  "vector_search_time": 0.3,
  "uptime_seconds": 86400
}
```

## CLI Interface

### Command Line Usage
```bash
# Query the system
python -m rag_kg query "How do I reset my password?"

# Batch processing
python -m rag_kg batch --input questions.txt --output answers.json

# System status
python -m rag_kg status

# Data management
python -m rag_kg data --refresh
```

### CLI Commands

#### query Command
```
Usage: rag_kg query [OPTIONS] QUESTION

Options:
  --context TEXT     Additional context (JSON)
  --format TEXT      Output format (json/text)
  --verbose          Show detailed processing info
  --max-sources INT  Maximum sources to include

Examples:
  rag_kg query "login issues" --verbose
  rag_kg query "payment problems" --context '{"product": "web"}' --format json
```

#### batch Command
```
Usage: rag_kg batch [OPTIONS]

Options:
  --input FILE       Input file with questions
  --output FILE      Output file for answers
  --concurrency INT  Number of parallel requests
  --delay FLOAT      Delay between requests

Example:
  rag_kg batch --input customer_questions.txt --output responses.json --concurrency 2
```

## Sequence Diagrams

### Query Processing Flow
```
1. User Query → 2. FastAPI Endpoint
                    ↓
3. Entity Extraction (OLLAMA) → 4. Intent Detection
                    ↓
5. Graph Traversal (Cypher) → 6. Vector Search (Qdrant)
                    ↓
7. Context Assembly → 8. Answer Generation (OLLAMA)
                    ↓
9. Response Formatting → 10. Return to User
```

### Detailed Processing Steps

#### Step 1: Entity Extraction
```
Input: "I can't login to the mobile app after the update"
OLLAMA Prompt: "Extract key entities from this customer query"
Output: ["mobile app", "login", "update"]
```

#### Step 2: Intent Detection
```
Input: Query + Entities
Classification: "troubleshooting" (confidence: 0.85)
```

#### Step 3: Subgraph Retrieval
```
Cypher Query:
MATCH (i:Issue)-[:MENTIONS_ENTITY]->(e:Entity)
WHERE e.value IN ["mobile app", "login"]
RETURN i, e
LIMIT 10

Vector Search:
Query: "mobile app login issues"
Top-K: 5 similar nodes
```

#### Step 4: Answer Generation
```
Context: Retrieved tickets + similar issues
OLLAMA Prompt: "Generate helpful answer based on this context"
Output: Structured response with sources
```

## Data Flow Documentation

### Input Processing
1. **Query Validation**: Check query length, format, rate limits
2. **Preprocessing**: Clean text, extract keywords
3. **Context Enrichment**: Add user/product context if available

### Retrieval Pipeline
1. **Entity-based Retrieval**: Find relevant graph nodes
2. **Similarity Search**: Vector-based candidate retrieval
3. **Graph Traversal**: Explore connected nodes (2-hop neighbors)
4. **Score Combination**: Weighted combination of retrieval methods

### Answer Synthesis
1. **Context Assembly**: Combine retrieved information
2. **Prompt Engineering**: Create effective prompts for OLLAMA
3. **Generation**: Produce natural language response
4. **Post-processing**: Add sources, confidence scores

## Integration Examples

### Python Client
```python
import requests

class RAGKGClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url

    def query(self, question, context=None, options=None):
        payload = {
            "question": question,
            "context": context or {},
            "options": options or {}
        }

        response = requests.post(f"{self.base_url}/api/v1/query", json=payload)
        return response.json()

# Usage
client = RAGKGClient()
result = client.query("How do I reset my password?")
print(result["answer"])
```

### JavaScript Client
```javascript
async function queryRAGKG(question, context = {}) {
    const response = await fetch('http://localhost:8000/api/v1/query', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            question: question,
            context: context,
            options: { max_sources: 3 }
        })
    });

    return await response.json();
}

// Usage
const result = await queryRAGKG("login issues", { product: "mobile" });
console.log(result.answer);
```

### cURL Examples
```bash
# Simple query
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I update my profile?"}'

# Query with context
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Payment not processing",
    "context": {"product": "web_app", "user_id": "12345"},
    "options": {"max_sources": 5}
  }'

# Health check
curl http://localhost:8000/health

# Metrics
curl http://localhost:8000/metrics
```

## Error Handling

### Common Error Codes
- `INVALID_QUERY`: Query too short or malformed
- `MODEL_UNAVAILABLE`: OLLAMA model not responding
- `DATABASE_ERROR`: Neo4j/Qdrant connection issues
- `RATE_LIMITED`: Too many requests
- `PROCESSING_TIMEOUT`: Query took too long

### Retry Logic
```python
def query_with_retry(question, max_retries=3):
    for attempt in range(max_retries):
        try:
            result = client.query(question)
            return result
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(2 ** attempt)  # Exponential backoff
```

## Performance Characteristics

### Response Times
- **Average**: 1.5-2.5 seconds
- **P95**: <5 seconds
- **P99**: <10 seconds

### Throughput
- **Concurrent Users**: 10-20
- **Requests/Minute**: 60 (rate limited)
- **Batch Processing**: 5-10 queries/minute

### Memory Usage
- **Base Load**: 6-8GB
- **Peak Load**: 12-14GB
- **Per Query**: ~500MB temporary

## Monitoring and Logging

### Structured Logs
```json
{
  "timestamp": "2024-01-15T10:30:15Z",
  "level": "INFO",
  "component": "query_processor",
  "query_id": "q_12345",
  "user_id": "user_678",
  "processing_time": 1.8,
  "model_used": "llama2:7b-chat-q4_0",
  "sources_found": 3,
  "confidence": 0.87
}
```

### Metrics Collection
- Query latency percentiles
- Model inference times
- Cache hit rates
- Error rates by component
- Memory usage trends

## Testing

### API Testing
```bash
# Install testing dependencies
pip install pytest httpx

# Run API tests
pytest tests/test_api.py -v

# Load testing
python -m locust -f tests/load_test.py
```

### Sample Test Queries
```python
test_queries = [
    "How do I reset my password?",
    "The app crashes when I try to login",
    "Payment failed but money was charged",
    "Can't upload files larger than 10MB",
    "Two-factor authentication not working",
    "Account suspended without reason"
]
```

## Deployment

### Local Development
```bash
# Start API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# With Gunicorn (production)
gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker Deployment
```dockerfile
FROM python:3.9-slim

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Systemd Service
```ini
[Unit]
Description=RAG-KG API Service
After=network.target

[Service]
User=raguser
WorkingDirectory=/opt/rag-kg
ExecStart=/opt/rag-kg/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

## Security Considerations

### Input Validation
- Query length limits (max 1000 characters)
- Sanitize inputs to prevent injection
- Rate limiting per IP/user

### Authentication
- API key authentication for production
- Request signing for sensitive operations
- Audit logging for all queries

### Data Privacy
- No persistent storage of queries
- Anonymize user identifiers in logs
- Encrypt sensitive context data

## Troubleshooting

### Common Issues

#### Slow Responses
```
Check: ollama list (model loaded?)
Check: Monitor Neo4j heap usage
Check: Qdrant collection size
Solution: Restart services, check memory
```

#### Model Errors
```
Check: ollama serve status
Check: Model disk space
Solution: Restart OLLAMA, verify model files
```

#### Database Connection Issues
```
Check: Neo4j browser at http://localhost:7474
Check: Qdrant at http://localhost:6333/health
Solution: Restart databases, check credentials
```

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Verbose API responses
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "test", "options": {"debug": true}}'
```