# Installation Guide

## Purpose and Scope
This guide provides step-by-step instructions for setting up the complete environment for the RAG-KG Customer Service QA System. All installations are designed for local/offline operation with 16GB RAM constraints. Commands are provided for Windows with WSL support where needed.

## Prerequisites
- Windows 10/11 with WSL2 enabled
- At least 16GB RAM (32GB recommended for optimal performance)
- 50GB free disk space
- Administrator privileges for installations

## Step-by-Step Installation

### 1. OLLAMA Installation and Model Setup

#### Install OLLAMA
```
# COMMAND: Download OLLAMA from https://ollama.ai/download/windows
# PURPOSE: Install OLLAMA runtime for local LLM inference
# EXPECTED OUTPUT: OLLAMA installer executable downloaded
# MEMORY USAGE: Minimal during installation

# Run the installer as administrator
# After installation, verify:
ollama --version
# EXPECTED OUTPUT: ollama version x.x.x
```

#### Pull Required Models
```
# COMMAND: ollama pull llama2:7b-chat-q4_0
# PURPOSE: Download quantized Llama 2 7B chat model (optimized for 16GB RAM)
# EXPECTED OUTPUT: Download progress (100%), model verification
# MEMORY USAGE: ~4GB when loaded, ~8GB during download

# COMMAND: ollama pull nomic-embed-text
# PURPOSE: Download embedding model for text vectorization
# EXPECTED OUTPUT: Download progress, model ready
# MEMORY USAGE: ~200MB when loaded

# COMMAND: ollama pull mistral:7b-instruct-v0.1-q4_0
# PURPOSE: Alternative LLM for parsing tasks (smaller memory footprint)
# EXPECTED OUTPUT: Download progress
# MEMORY USAGE: ~4GB when loaded
```

#### Verify Models
```
ollama list
# EXPECTED OUTPUT: List of installed models including llama2:7b-chat-q4_0, nomic-embed-text, mistral:7b-instruct-v0.1-q4_0
```

### 2. Python Environment Setup

#### Create Virtual Environment
```
# COMMAND: python3 -m venv rag-kg-env
# PURPOSE: Creates isolated Python environment
# EXPECTED OUTPUT: New directory 'rag-kg-env' created
# MEMORY USAGE: Minimal

# COMMAND: rag-kg-env\Scripts\activate
# PURPOSE: Activate virtual environment (Windows)
# EXPECTED OUTPUT: Command prompt shows (rag-kg-env)
```

#### Install Dependencies
```
# COMMAND: pip install -r requirements.txt
# PURPOSE: Install all Python dependencies
# EXPECTED OUTPUT: Successful installation of packages
# MEMORY USAGE: ~2GB during installation

# If pip install fails, upgrade pip first:
python -m pip install --upgrade pip
```

### 3. Neo4j Graph Database Setup

#### Download and Install Neo4j Community Edition
```
# Download from: https://neo4j.com/download/
# Choose: Neo4j Desktop or Server (Community Edition)
# For server: neo4j-community-5.x.x-windows.zip

# Extract to: C:\neo4j
# Set environment variables:
set NEO4J_HOME=C:\neo4j
set PATH=%PATH%;%NEO4J_HOME%\bin
```

#### Configure Neo4j for 16GB RAM
```
# Edit neo4j.conf (located in %NEO4J_HOME%\conf\neo4j.conf)
# Set memory settings:
dbms.memory.heap.initial_size=2G
dbms.memory.heap.max_size=8G
dbms.memory.pagecache.size=4G

# Enable APOC procedures:
dbms.security.procedures.unrestricted=apoc.*
```

#### Start Neo4j
```
# COMMAND: neo4j start
# PURPOSE: Start Neo4j database service
# EXPECTED OUTPUT: Neo4j started successfully
# MEMORY USAGE: ~4-6GB with configured limits

# Verify connection:
# Open browser to http://localhost:7474
# Default credentials: neo4j/neo4j (change on first login)
```

### 4. Qdrant Vector Database Setup

#### Install Docker Desktop (if not already installed)
```
# Download from: https://www.docker.com/products/docker-desktop
# Install and start Docker Desktop
# Enable WSL2 integration
```

#### Run Qdrant Container
```
# COMMAND: docker run -d -p 6333:6333 -p 6334:6334 -v qdrant_data:/qdrant/storage qdrant/qdrant
# PURPOSE: Start Qdrant vector database in Docker container
# EXPECTED OUTPUT: Container ID output
# MEMORY USAGE: ~1-2GB

# Verify Qdrant is running:
curl http://localhost:6333/health
# EXPECTED OUTPUT: {"status":"green","version":"x.x.x"}
```

### 5. Environment Variables Setup

#### Create .env file
```
# Create .env file in project root
OLLAMA_BASE_URL=http://localhost:11434
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here
QDRANT_URL=http://localhost:6333
EMBEDDING_MODEL=nomic-embed-text
LLM_MODEL=llama2:7b-chat-q4_0
PARSING_MODEL=mistral:7b-instruct-v0.1-q4_0
```

#### Load Environment Variables
```
# In Python scripts:
from dotenv import load_dotenv
load_dotenv()
```

### 6. Verify Complete Setup

#### Run System Check Script
```
# Create and run system_check.py (see CONFIGURATION_GUIDE.md)
python system_check.py
# EXPECTED OUTPUT: All components status: OK
```

## Error Handling

### Common Installation Issues

#### OLLAMA Model Download Fails
```
# Check internet connection
# Retry: ollama pull <model_name>
# If persistent, try smaller models or different quantization
```

#### Neo4j Memory Errors
```
# Reduce heap size in neo4j.conf:
dbms.memory.heap.max_size=4G
# Restart Neo4j
```

#### Docker/Qdrant Issues
```
# Restart Docker Desktop
# Check WSL2: wsl --list --running
# Recreate container: docker rm -f qdrant && rerun docker run command
```

#### Python Dependency Conflicts
```
# Create fresh venv
# Install in order: pip install langchain neo4j qdrant-client ollama python-dotenv
```

## Post-Installation Steps
1. Run data preparation scripts (see DATA_PREPARATION.md)
2. Configure models and databases (see CONFIGURATION_GUIDE.md)
3. Test the system with sample queries

## Memory Usage Summary
- OLLAMA models: ~8GB total when loaded
- Neo4j: 4-6GB
- Qdrant: 1-2GB
- Python application: 2-4GB
- Total: ~15-20GB (monitor with system tools)