# Data Preparation Guide

## Purpose and Scope
This guide covers the data preparation pipeline for constructing the knowledge graph from customer service tickets. Includes sample data generation, parsing scripts, graph construction, and embedding generation. All scripts are optimized for 16GB RAM with batch processing.

## Directory Structure
```
data/
├── raw/           # Raw ticket data
├── processed/     # Parsed ticket data
└── embeddings/    # Generated embeddings
scripts/
├── generate_sample_data.py
├── parse_tickets.py
├── build_graph.py
└── generate_embeddings.py
```

## Step-by-Step Data Preparation

### 1. Generate Sample Ticket Data

#### Run Sample Data Generator
```
# COMMAND: python scripts/generate_sample_data.py --num_tickets 100
# PURPOSE: Generate synthetic Jira-like ticket data for testing
# EXPECTED OUTPUT: 100 JSON files in data/raw/
# MEMORY USAGE: <1GB

# Sample ticket structure:
{
  "ticket_id": "CS-001",
  "title": "Login issues with mobile app",
  "description": "Users unable to login via mobile app after update",
  "status": "resolved",
  "priority": "high",
  "created_date": "2024-01-01",
  "comments": [
    {"author": "user", "text": "App crashes on login", "timestamp": "2024-01-01T10:00:00Z"},
    {"author": "agent", "text": "Please try clearing cache", "timestamp": "2024-01-01T11:00:00Z"}
  ],
  "resolution": "Clear app cache and restart",
  "tags": ["mobile", "login", "crash"]
}
```

### 2. Parse Ticket Data

#### Rule-Based Parsing
```
# COMMAND: python scripts/parse_tickets.py --method rule_based --input_dir data/raw --output_dir data/processed
# PURPOSE: Extract structured information using regex patterns
# EXPECTED OUTPUT: Processed JSON files with extracted entities
# MEMORY USAGE: <2GB

# Extracts:
# - Entities: product names, error codes, user actions
# - Relationships: references to other tickets, dependencies
# - Metadata: timestamps, priorities, statuses
```

#### LLM-Based Parsing
```
# COMMAND: python scripts/parse_tickets.py --method llm --input_dir data/raw --output_dir data/processed --model mistral:7b-instruct-v0.1-q4_0
# PURPOSE: Use OLLAMA LLM for semantic parsing of unstructured text
# EXPECTED OUTPUT: Enhanced JSON with semantic entities and relationships
# MEMORY USAGE: ~6GB (LLM + processing)

# LLM prompts extract:
# - Implicit relationships between issues
# - Root cause analysis
# - Solution patterns
```

### 3. Build Knowledge Graph

#### Intra-Issue Tree Construction
```
# COMMAND: python scripts/build_graph.py --phase intra_issue --input_dir data/processed --neo4j_uri bolt://localhost:7687
# PURPOSE: Create hierarchical trees for individual tickets
# EXPECTED OUTPUT: Neo4j nodes and relationships created
# MEMORY USAGE: <4GB

# Creates nodes:
# - Issue (root)
# - Description, Comments, Resolution (children)
# - Entities, Actions, Solutions (leaves)
```

#### Inter-Issue Graph Construction
```
# COMMAND: python scripts/build_graph.py --phase inter_issue --input_dir data/processed --neo4j_uri bolt://localhost:7687
# PURPOSE: Create connections between different tickets
# EXPECTED OUTPUT: Cross-ticket relationships added
# MEMORY USAGE: <6GB

# Creates relationships:
# - SIMILAR_TO: semantic similarity
# - REFERENCES: explicit mentions
# - DEPENDS_ON: prerequisite issues
# - SOLVED_BY: solution patterns
```

#### Verify Graph Structure
```
# Cypher query to check graph:
MATCH (n) RETURN count(n) as node_count
# EXPECTED: ~5000+ nodes for 100 tickets

MATCH ()-[r]->() RETURN count(r) as relationship_count
# EXPECTED: ~10000+ relationships
```

### 4. Generate Node Embeddings

#### Embedding Generation
```
# COMMAND: python scripts/generate_embeddings.py --input_dir data/processed --qdrant_url http://localhost:6333 --collection tickets --model nomic-embed-text --batch_size 10
# PURPOSE: Generate vector embeddings for all graph nodes
# EXPECTED OUTPUT: Embeddings stored in Qdrant collection
# MEMORY USAGE: ~8GB (embedding model + batch processing)

# Process in batches to manage memory:
# - Batch size: 10 nodes
# - Dimension: 768 (nomic-embed-text)
# - Total vectors: ~5000
```

#### Verify Embeddings
```
# Check Qdrant collection:
curl http://localhost:6333/collections/tickets
# EXPECTED: Collection info with vector count
```

## Data Quality Validation

### Run Validation Script
```
# COMMAND: python scripts/validate_data.py --graph_uri bolt://localhost:7687 --vector_url http://localhost:6333
# PURPOSE: Validate graph structure and embedding completeness
# EXPECTED OUTPUT: Validation report with statistics
# MEMORY USAGE: <2GB

# Checks:
# - Node completeness
# - Relationship validity
# - Embedding coverage
# - Data consistency
```

## Performance Optimization

### Memory Management
- Process tickets in batches of 20
- Clear intermediate data after each phase
- Use streaming for large datasets

### Processing Times (Approximate)
- Data generation: 1 minute for 100 tickets
- Rule-based parsing: 5 minutes
- LLM parsing: 30 minutes
- Graph construction: 10 minutes
- Embedding generation: 15 minutes
- Total: ~1 hour

## Error Handling

### Common Data Issues

#### Parsing Failures
```
# Check input data format
# Verify OLLAMA model availability: ollama list
# Retry with smaller batch size
```

#### Graph Construction Errors
```
# Clear Neo4j database: MATCH (n) DETACH DELETE n
# Check Neo4j logs in %NEO4J_HOME%\logs
# Verify connection: python -c "from neo4j import GraphDatabase; GraphDatabase.driver('bolt://localhost:7687')"
```

#### Embedding Generation Issues
```
# Check Qdrant health: curl http://localhost:6333/health
# Verify model: ollama show nomic-embed-text
# Reduce batch size if memory errors
```

## Sample Data Statistics

For 100 sample tickets:
- Total nodes: ~5,000
- Total relationships: ~10,000
- Embedding vectors: ~5,000 (768 dimensions each)
- Storage size: ~500MB (graph) + ~200MB (vectors)

## Next Steps
After data preparation:
1. Configure query processing (see CONFIGURATION_GUIDE.md)
2. Test the QA system (see API_DOCUMENTATION.md)
3. Run performance benchmarks (see PERFORMANCE_OPTIMIZATION.md)