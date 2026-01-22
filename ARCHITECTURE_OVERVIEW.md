# Architecture Overview

## Purpose and Scope
This document provides a high-level overview of the Retrieval-Augmented Generation with Knowledge Graphs (RAG-KG) Customer Service QA System architecture. The system is designed to answer customer service questions by leveraging a dual-level knowledge graph constructed from historical support tickets, combined with vector-based retrieval and local OLLAMA models for generation. The architecture emphasizes offline operation, local models, and optimization for 16GB RAM constraints.

## System Components

### 1. Knowledge Graph Construction Pipeline
- **Intra-issue Trees**: Hierarchical representation of individual ticket content (e.g., issue description, comments, resolutions)
- **Inter-issue Graph**: Connections between tickets based on explicit (e.g., references) and implicit (e.g., semantic similarity) relationships
- **Hybrid Parsing**: Rule-based extraction for structured data + LLM-based parsing for unstructured content
- **Node Embeddings**: Vector representations of graph nodes for similarity-based retrieval

### 2. Query Processing System
- **Entity Identification**: Extract key entities from user queries using OLLAMA LLM
- **Intent Detection**: Classify query intent (e.g., troubleshooting, feature request)
- **Subgraph Retrieval**: Retrieve relevant graph subgraphs via vector similarity and graph traversal
- **Cypher Query Generation**: Generate graph database queries for precise traversal
- **Answer Generation**: Synthesize responses using retrieved context, with fallback mechanisms

### 3. Data Storage Layer
- **Graph Database**: Neo4j Community Edition for storing ticket trees and connections
- **Vector Database**: Qdrant Community (Docker) for embedding storage and similarity search
- **Document Store**: Local file system or SQLite for raw ticket data

### 4. Model Layer
- **LLM**: OLLAMA-hosted models (e.g., llama2:7b-chat-q4_0 for memory efficiency)
- **Embedding Model**: OLLAMA-hosted embedding models (e.g., nomic-embed-text)
- **Local Processing**: All inference runs locally, no cloud dependencies

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

## Expected Performance Baselines
- Query response time: <5 seconds
- Memory usage: <12GB peak during processing
- Graph construction time: <30 minutes for 1000 tickets
- Embedding generation: <10 minutes for 1000 nodes