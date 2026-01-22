# RAG-KG Customer Service QA System

A comprehensive Retrieval-Augmented Generation with Knowledge Graphs system for customer service question answering, optimized for 16GB RAM and offline operation using OLLAMA models.

## 🚀 Quick Start

### Prerequisites
- Windows 10/11 with WSL2
- 16GB RAM (32GB recommended)
- 50GB free disk space
- Administrator privileges

### Installation
```bash
# 1. Clone repository
git clone <repository-url>
cd CustomerServiceQA_using_GraphRAG

# 2. Setup environment
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your settings

# 4. Run system check
python scripts/system_check.py
```

### Basic Usage
```bash
# Generate sample data
python scripts/generate_sample_data.py --num_tickets 100

# Process data
python scripts/parse_tickets.py --method hybrid
python scripts/build_graph.py --phase full
python scripts/generate_embeddings.py

# Start API server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Query the system
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I reset my password?"}'
```

## 📋 System Architecture

### Components
- **OLLAMA**: Local LLM inference (Llama 2, Mistral)
- **Neo4j**: Graph database for ticket relationships
- **Qdrant**: Vector database for embeddings
- **FastAPI**: REST API server
- **Hybrid Parsing**: Rule-based + LLM-based text processing

### Data Flow
1. **Ingestion**: Raw tickets → Parsing → Graph construction → Embeddings
2. **Query**: User question → Entity extraction → Graph search → Vector retrieval → Answer generation

## 📚 Documentation

### Setup & Installation
- [Installation Guide](INSTALLATION.md) - Complete setup instructions
- [Migration Guide](MIGRATION_GUIDE.md) - Offline transfer instructions
- [Configuration Guide](CONFIGURATION_GUIDE.md) - System configuration
- [Deployment Guide](DEPLOYMENT.md) - Production deployment

### Usage & API
- [API Documentation](API_DOCUMENTATION.md) - REST API reference
- [Data Preparation](DATA_PREPARATION.md) - Data processing pipeline

### Optimization & Troubleshooting
- [Performance Optimization](PERFORMANCE_OPTIMIZATION.md) - Performance tuning
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions

### Architecture
- [Architecture Overview](ARCHITECTURE_OVERVIEW.md) - System design and components

## 🔧 Key Features

### Memory Optimized
- Quantized models (Q4_0) for 16GB RAM operation
- Batch processing with memory monitoring
- Lazy loading and caching strategies

### Offline Operation
- No cloud dependencies
- Local OLLAMA models
- Self-contained databases

### Hybrid Intelligence
- Rule-based parsing for structured data
- LLM-based parsing for semantic understanding
- Graph algorithms for relationship discovery

### Production Ready
- Comprehensive logging and monitoring
- Automated backups and recovery
- Horizontal scaling support
- Security hardening

## 📊 Performance Benchmarks

### System Requirements
- **RAM**: 16GB minimum, 32GB recommended
- **Storage**: 50GB SSD recommended
- **CPU**: 4+ cores with AVX2 support

### Performance Targets
- Query response: <2 seconds average
- Memory usage: <12GB peak
- Concurrent users: 5-10
- Data processing: 1000 tickets in <30 minutes

## 🛠️ Development

### Project Structure
```
├── app/                    # Application code
├── config/                 # Configuration files
├── data/                   # Data directories
│   ├── raw/               # Raw ticket data
│   ├── processed/         # Parsed tickets
│   └── embeddings/        # Vector embeddings
├── scripts/               # Utility scripts
│   ├── generate_sample_data.py
│   ├── parse_tickets.py
│   ├── build_graph.py
│   ├── generate_embeddings.py
│   ├── system_check.py
│   └── validate_data.py
├── logs/                  # Application logs
├── backups/               # Database backups
├── requirements.txt       # Python dependencies
├── .env.example          # Environment template
└── .gitignore           # Git ignore rules
```

### Scripts Overview
- `generate_sample_data.py`: Create synthetic ticket data
- `parse_tickets.py`: Parse tickets with hybrid approach
- `build_graph.py`: Construct knowledge graph
- `generate_embeddings.py`: Generate vector embeddings
- `system_check.py`: Validate system components
- `validate_data.py`: Verify data pipeline integrity

## 🔒 Security

### Best Practices
- Change default passwords
- Use environment variables for secrets
- Enable firewall rules
- Regular security updates
- Monitor access logs

### Data Privacy
- Local data storage only
- No external API calls
- Encrypted backups
- Audit logging

## 📈 Monitoring

### Key Metrics
- Query latency and throughput
- Memory and CPU usage
- Database performance
- Model inference times
- Error rates

### Logging
- Structured JSON logging
- Configurable log levels
- Log rotation and archiving
- Centralized monitoring

## 🚀 Scaling

### Vertical Scaling
- Increase RAM for larger models
- Add CPU cores for parallel processing
- Use faster storage (NVMe SSD)

### Horizontal Scaling
- Multiple API instances with load balancer
- Database clustering
- Model sharding across servers

## 🤝 Contributing

### Development Setup
```bash
# Fork and clone
git clone <your-fork-url>
cd CustomerServiceQA_using_GraphRAG

# Setup development environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Install development dependencies
pip install pytest black flake8 mypy

# Run tests
pytest

# Code formatting
black .
flake8 .
```

#### By me
```pwsh
rag-kg-env/Scripts/activate
python -m app.main
```

### Code Standards
- Type hints for all functions
- Comprehensive docstrings
- Unit tests for core functionality
- Performance benchmarks
- Memory usage monitoring

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- OLLAMA for local LLM inference
- Neo4j Community Edition
- Qdrant for vector search
- FastAPI framework
- LangChain for LLM orchestration

## 📞 Support

For issues and questions:
1. Check [Troubleshooting Guide](TROUBLESHOOTING.md)
2. Review [Performance Optimization](PERFORMANCE_OPTIMIZATION.md)
3. Check existing GitHub issues
4. Create a new issue with diagnostic information

---

**Note**: This system is designed for customer service automation and should be adapted for your specific use case and data privacy requirements.