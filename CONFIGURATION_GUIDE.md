# Configuration Guide

## Purpose and Scope
This guide covers the configuration of all system components including model parameters, database settings, and performance tuning for the 16GB RAM constraint. Includes YAML configuration templates and environment setup.

## Directory Structure
```
config/
├── models.yaml          # OLLAMA model configurations
├── database.yaml        # Neo4j and Qdrant settings
├── processing.yaml      # Data processing parameters
├── api.yaml            # API server configuration
└── logging.yaml        # Logging configuration
scripts/
└── system_check.py     # System validation script
```

## Model Configuration

### OLLAMA Model Settings
```yaml
# config/models.yaml
ollama:
  base_url: "http://localhost:11434"

  # LLM for answer generation
  llm_model: "llama2:7b-chat-q4_0"
  llm_params:
    temperature: 0.1
    top_p: 0.9
    max_tokens: 512
    context_window: 4096

  # LLM for parsing tasks
  parsing_model: "mistral:7b-instruct-v0.1-q4_0"
  parsing_params:
    temperature: 0.0
    top_p: 0.95
    max_tokens: 256

  # Embedding model
  embedding_model: "nomic-embed-text"
  embedding_params:
    dimensions: 768
    normalize: true

# Memory optimization settings
memory:
  max_batch_size: 4
  embedding_batch_size: 8
  clear_cache_after_batch: true
  preload_models: false
```

### Memory Usage Estimates
- **llama2:7b-chat-q4_0**: ~4GB RAM when loaded
- **mistral:7b-instruct-v0.1-q4_0**: ~4GB RAM when loaded
- **nomic-embed-text**: ~200MB RAM when loaded
- **Concurrent loading**: Avoid loading multiple LLMs simultaneously

## Database Configuration

### Neo4j Settings
```yaml
# config/database.yaml
neo4j:
  uri: "bolt://localhost:7687"
  user: "neo4j"
  password: "your_secure_password"

  # Memory settings for 16GB RAM
  memory:
    heap_initial: "2G"
    heap_max: "8G"
    pagecache: "4G"

  # Performance settings
  performance:
    query_cache_size: "100M"
    string_block_size: "100M"
    array_block_size: "100M"

  # Indexing for performance
  indexes:
    - "CREATE INDEX issue_id IF NOT EXISTS FOR (i:Issue) ON (i.id)"
    - "CREATE INDEX entity_value IF NOT EXISTS FOR (e:Entity) ON (e.value)"
    - "CREATE INDEX tag_name IF NOT EXISTS FOR (t:Tag) ON (t.name)"

# Apply settings in neo4j.conf:
# dbms.memory.heap.initial_size=2G
# dbms.memory.heap.max_size=8G
# dbms.memory.pagecache.size=4G
```

### Qdrant Settings
```yaml
# config/database.yaml
qdrant:
  url: "http://localhost:6333"
  collection: "tickets"

  # Vector configuration
  vectors:
    size: 768
    distance: "Cosine"

  # Performance settings
  performance:
    max_threads: 4
    memmap_threshold: "100MB"

  # Persistence settings
  persistence:
    snapshots_interval: "3600"  # 1 hour
    wal_capacity: "32MB"
```

## Data Processing Configuration

### Parsing Parameters
```yaml
# config/processing.yaml
parsing:
  # Rule-based parsing
  rule_based:
    enabled: true
    patterns:
      products:
        - "\\b(mobile app|web portal|api|desktop client)\\b"
      errors:
        - "\\b(error|exception|failed|crash)\\b"
        - "\\b(404|500|403|401)\\b"
      actions:
        - "\\b(login|logout|click|submit|upload)\\b"

  # LLM-based parsing
  llm_based:
    enabled: true
    prompt_template: |
      Analyze this customer service ticket and extract:
      1. Key entities (products, features, error types)
      2. Root cause analysis
      3. Solution approach
      4. Related concepts

      Ticket: {ticket_content}

      Return JSON format only.

  # Hybrid processing
  hybrid:
    rule_based_first: true
    llm_fallback: true
    confidence_threshold: 0.7
```

### Graph Construction Settings
```yaml
# config/processing.yaml
graph_construction:
  # Intra-issue trees
  intra_issue:
    max_comments_per_issue: 20
    max_entities_per_issue: 10
    create_resolution_nodes: true

  # Inter-issue connections
  inter_issue:
    similarity_threshold: 0.3
    max_connections_per_issue: 5
    connection_types:
      - "SIMILAR_TO"
      - "RELATED_TO"
      - "REFERENCES"
      - "DEPENDS_ON"

  # Batch processing
  batch_processing:
    ticket_batch_size: 10
    node_batch_size: 50
    commit_interval: 100
```

### Embedding Generation
```yaml
# config/processing.yaml
embeddings:
  # Generation settings
  generation:
    model: "nomic-embed-text"
    batch_size: 8
    max_text_length: 512
    truncate_strategy: "end"

  # Storage settings
  storage:
    collection_name: "tickets"
    upload_batch_size: 50
    retry_attempts: 3
    retry_delay: 1.0

  # Node text templates
  text_templates:
    issue: "Title: {title}. Description: {description}. Status: {status}"
    comment: "Comment by {author}: {text}"
    entity: "Entity ({type}): {value}"
    tag: "Tag: {name}"
```

## API Configuration

### FastAPI Server Settings
```yaml
# config/api.yaml
api:
  host: "0.0.0.0"
  port: 8000
  workers: 2

  # CORS settings
  cors:
    allow_origins: ["*"]
    allow_methods: ["GET", "POST"]
    allow_headers: ["*"]

  # Rate limiting
  rate_limit:
    requests_per_minute: 60
    burst_limit: 10

  # Endpoints
  endpoints:
    query: "/api/v1/query"
    health: "/health"
    metrics: "/metrics"
```

### Query Processing
```yaml
# config/api.yaml
query_processing:
  # Entity extraction
  entity_extraction:
    model: "mistral:7b-instruct-v0.1-q4_0"
    max_entities: 5
    confidence_threshold: 0.6

  # Intent detection
  intent_detection:
    enabled: true
    intents:
      - "troubleshooting"
      - "feature_request"
      - "bug_report"
      - "general_inquiry"

  # Retrieval settings
  retrieval:
    max_candidates: 10
    similarity_threshold: 0.7
    graph_hops: 2
    combine_scores: true

  # Answer generation
  answer_generation:
    model: "llama2:7b-chat-q4_0"
    max_length: 300
    include_sources: true
    fallback_responses:
      - "I couldn't find specific information about your issue."
      - "Please provide more details about the problem."
```

## Logging Configuration

### Structured Logging
```yaml
# config/logging.yaml
logging:
  version: 1
  disable_existing_loggers: false

  formatters:
    detailed:
      format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    json:
      class: "pythonjsonlogger.jsonlogger.JsonFormatter"
      format: "%(asctime)s %(name)s %(levelname)s %(levelname)s %(message)s"

  handlers:
    console:
      class: "logging.StreamHandler"
      level: "INFO"
      formatter: "detailed"

    file:
      class: "logging.FileHandler"
      level: "DEBUG"
      filename: "logs/rag_kg_system.log"
      formatter: "json"

  root:
    level: "INFO"
    handlers: ["console", "file"]

  loggers:
    neo4j: {level: "WARNING"}
    qdrant: {level: "WARNING"}
    ollama: {level: "WARNING"}
```

## Environment Variables

### Required Environment Variables
```bash
# .env file
OLLAMA_BASE_URL=http://localhost:11434
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password
QDRANT_URL=http://localhost:6333
COLLECTION_NAME=tickets

# Model settings
LLM_MODEL=llama2:7b-chat-q4_0
PARSING_MODEL=mistral:7b-instruct-v0.1-q4_0
EMBEDDING_MODEL=nomic-embed-text

# API settings
API_HOST=0.0.0.0
API_PORT=8000

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/rag_kg_system.log
```

## System Check Script

### Validation Commands
```python
# scripts/system_check.py - See separate file
```

### Running System Check
```
# COMMAND: python scripts/system_check.py
# PURPOSE: Validate all system components are running and accessible
# EXPECTED OUTPUT: All components show ✓ and Overall Status: PASS
# MEMORY USAGE: Minimal
```

## Performance Tuning

### Memory Optimization
- Set `PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512` for GPU memory (if available)
- Use `numexpr.set_num_threads(4)` to limit CPU threads
- Configure garbage collection: `gc.set_threshold(700, 10, 10)`

### Database Tuning
- Neo4j: Monitor heap usage with `dbms.memory.heap.used` metric
- Qdrant: Set `memmap_threshold` based on available RAM
- Enable connection pooling with appropriate pool sizes

### Model Optimization
- Load models on-demand rather than preloading
- Clear CUDA cache between operations: `torch.cuda.empty_cache()`
- Use model quantization for reduced memory footprint

## Configuration Validation

### Validate Configuration Files
```
# COMMAND: python -c "import yaml; yaml.safe_load(open('config/models.yaml')); print('models.yaml: OK')"
# PURPOSE: Validate YAML syntax in configuration files
# EXPECTED OUTPUT: OK for each config file
```

### Test Configuration Loading
```
# COMMAND: python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('OLLAMA_BASE_URL:', os.getenv('OLLAMA_BASE_URL'))"
# PURPOSE: Verify environment variables are loaded correctly
# EXPECTED OUTPUT: Correct values for all required variables
```

## Next Steps
After configuration:
1. Run system check to validate setup
2. Test data processing pipeline (see DATA_PREPARATION.md)
3. Deploy API server (see API_DOCUMENTATION.md)
4. Monitor performance (see PERFORMANCE_OPTIMIZATION.md)