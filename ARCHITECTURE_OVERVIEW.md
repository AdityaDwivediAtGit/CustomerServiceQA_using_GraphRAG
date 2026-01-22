# Architecture Overview

## Purpose and Scope
This document provides a high-level overview of the Retrieval-Augmented Generation with Knowledge Graphs (RAG-KG) Customer Service QA System architecture. The system is designed to answer customer service questions by leveraging a dual-level knowledge graph constructed from historical support tickets, combined with vector-based retrieval and local OLLAMA models for generation. The architecture emphasizes offline operation, local models, and optimization for 16GB RAM constraints.

## System Components (SIGIR '24 Alignment)

### 1. Dual-Level Knowledge Graph
- **Intra-issue Trees ($T_i$):** Hierarchical representation of individual ticket sections (status, priority, root cause, etc).
- **Inter-issue Graph ($G$):** 
    - **Explicit Connections ($E_{exp}$):** Reference links or clones.
    - **Implicit Connections ($E_{imp}$):** Semantic title similarity using cosine distance.

### 2. Retrieval & Question Answering
- **Entity Extraction:** LLM-based mapping of query segments to graph sections (Section -> Value).
- **$S_{T_i}$ Scoring Logic:** Accurate ranking by summing node-level similarities for a given ticket.
- **LLM-driven Subgraph Extraction:** Translating natural language queries into Cypher for retrieved subgraphs.

### 3. Data Storage Layer
- **Graph Database:** Neo4j (Stores $T_i$ and $G$).
- **Vector Database:** Qdrant (Stores embeddings for node-level lookup).

### 4. Model Layer
- **LLM/Embedding:** OLLAMA-hosted local models (e.g., Mistral, Llama 2).

## Data Flow

1. **Ingestion Phase**:
   - Raw ticket data → Parsing → Graph construction → Embedding generation → Storage

2. **Query Phase**:
   - User query → Entity extraction → Intent detection → Subgraph retrieval → Answer synthesis → Response

## Memory Optimization Strategies
- Model quantization (Q4_0 for LLMs, FP16 for embeddings)
- Batch processing with small batch sizes (2-4)
- Graph database memory tuning (heap size limits)
- Vector database in-memory caching with disk persistence
- Lazy loading of embeddings and graph nodes

## Scalability Considerations
- Horizontal scaling via multiple Neo4j instances (future)
- Embedding sharding in Qdrant
- Query result caching
- Asynchronous processing for heavy computations

## Security and Privacy
- All data stored locally
- No external API calls
- Encrypted storage for sensitive ticket data (optional)
- Access controls via local authentication

## Monitoring and Logging
- Structured logging for all components
- Resource usage monitoring (CPU, RAM, disk)
- Query performance metrics
- Error tracking and alerting
- **Automated Migration**: Unified bundling for offline deployment and disaster recovery

## Expected Performance Baselines
- Query response time: <5 seconds
- Memory usage: <12GB peak during processing
- Graph construction time: <30 minutes for 1000 tickets
- Embedding generation: <10 minutes for 1000 nodes