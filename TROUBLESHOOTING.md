# Troubleshooting Guide

## Purpose and Scope
This guide provides solutions for common issues encountered during setup, operation, and maintenance of the RAG-KG Customer Service QA System. Includes diagnostic procedures, error resolution, and preventive measures.

## Quick Diagnosis

### System Health Check
```
# COMMAND: python scripts/system_check.py
# PURPOSE: Comprehensive system validation
# EXPECTED OUTPUT: Status of all components
# INTERPRETATION:
# ✓ = Component healthy
# ✗ = Component needs attention
```

### Component Status Check
```bash
# Check all services
sudo systemctl status ollama neo4j qdrant rag-kg-api

# Check Docker containers (if using Docker)
docker ps -a

# Check API health
curl http://localhost:8000/health

# Check database connections
curl http://localhost:6333/health  # Qdrant
# Open Neo4j browser: http://localhost:7474
```

## Common Installation Issues

### OLLAMA Installation Problems

#### Issue: OLLAMA not found after installation
```
SYMPTOMS: ollama command not found
SOLUTION:
# Add to PATH
export PATH=$PATH:/usr/local/bin
echo 'export PATH=$PATH:/usr/local/bin' >> ~/.bashrc

# Or reinstall
curl -fsSL https://ollama.ai/install.sh | sh
```

#### Issue: Model download fails
```
SYMPTOMS: "pull model: context canceled"
SOLUTION:
# Check internet connection
ping 8.8.8.8

# Retry with different model
ollama pull mistral:7b-instruct-v0.1-q4_0

# Check disk space
df -h
```

#### Issue: OLLAMA service won't start
```
SYMPTOMS: systemctl status ollama shows failed
LOGS: journalctl -u ollama -n 50
COMMON CAUSES:
- Port 11434 already in use
- Insufficient permissions
- GPU driver issues (if using GPU)

SOLUTION:
# Kill conflicting process
sudo lsof -ti:11434 | xargs sudo kill -9

# Check permissions
sudo chown ollama:ollama /usr/local/bin/ollama

# Start manually for debugging
sudo -u ollama /usr/local/bin/ollama serve
```

### Database Setup Issues

#### Neo4j Connection Refused
```
SYMPTOMS: Can't connect to bolt://localhost:7687
LOGS: journalctl -u neo4j -f
COMMON CAUSES:
- Neo4j not started
- Wrong credentials
- Firewall blocking port

SOLUTION:
# Check if running
sudo systemctl status neo4j

# Test connection
python -c "from neo4j import GraphDatabase; GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password'))"

# Check firewall
sudo ufw status | grep 7687
```

#### Neo4j Memory Issues
```
SYMPTOMS: Neo4j crashes with OutOfMemoryError
LOGS: /opt/neo4j/logs/neo4j.log
SOLUTION:
# Reduce memory settings in neo4j.conf
dbms.memory.heap.max_size=4G
dbms.memory.pagecache.size=2G

# Restart service
sudo systemctl restart neo4j
```

#### Qdrant Collection Issues
```
SYMPTOMS: Collection creation fails
ERROR: "Collection already exists" or "Vector size mismatch"
SOLUTION:
# Delete existing collection
curl -X DELETE http://localhost:6333/collections/tickets

# Recreate with correct parameters
python scripts/generate_embeddings.py --recreate-collection

#### Pydantic Validation Errors (Qdrant Client)
```
SYMPTOMS: pydantic_core._pydantic_core.ValidationError: 3 validation errors for ParsingModel[InlineResponse2005]
ERROR: extra="forbid" context={} input_type=dict
CAUSE: Incompatibility between Qdrant server version and qdrant-client version.
SOLUTION:
# Upgrade qdrant-client to match server schema
pip install qdrant-client==1.12.0

# Verify with:
python -c "from qdrant_client import QdrantClient; print(QdrantClient(url='http://localhost:6333').get_collection('tickets'))"
```

#### TypeError in validate_data.py
```
SYMPTOMS: TypeError: '>' not supported between instances of 'NoneType' and 'int'
CAUSE: Accessing collection_info.vectors_count which is None in newer client versions.
SOLUTION:
# Update scripts/validate_data.py to use points_count:
results['vector_count'] = collection_info.points_count
```
```

### Python Environment Issues

#### Import Errors
```
SYMPTOMS: ModuleNotFoundError
SOLUTION:
# Activate virtual environment
source venv/bin/activate

# Reinstall requirements
pip install -r requirements.txt

# Check Python path
python -c "import sys; print(sys.path)"
```

#### Dependency Conflicts
```
SYMPTOMS: Package installation fails
SOLUTION:
# Update pip
pip install --upgrade pip

# Install in specific order
pip install langchain neo4j qdrant-client ollama

# Use compatible versions
pip install langchain==0.1.0 langchain-community==0.0.10
```

## Runtime Issues

### API Performance Problems

#### Slow Query Responses
```
SYMPTOMS: Queries taking >5 seconds
DIAGNOSIS:
# Check system resources
htop
free -h

# Check model loading
ollama ps

# Profile query processing
python -c "
import time
start = time.time()
# Run test query
end = time.time()
print(f'Query time: {end-start:.2f}s')
"

CAUSES & SOLUTIONS:
1. Model not loaded: ollama pull llama2:7b-chat-q4_0
2. Memory pressure: Restart services
3. Large graph: Optimize Cypher queries
4. Network latency: Use local connections only
```

#### Memory Usage Spikes
```
SYMPTOMS: System becomes unresponsive
MONITORING:
# Real-time memory monitoring
watch -n 1 'free -h && ps aux --sort=-%mem | head -5'

# Check for memory leaks
python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.1f} MB')
"

SOLUTION:
# Set memory limits in systemd
MemoryLimit=4G
MemoryHigh=3G

# Restart services
sudo systemctl restart rag-kg-api
```

### Data Processing Errors

#### Graph Construction Failures
```
SYMPTOMS: build_graph.py fails with Neo4j errors
LOGS: Check script output and Neo4j logs
COMMON ISSUES:
- Constraint violations
- Memory limits exceeded
- Invalid Cypher syntax

DEBUGGING:
# Test Neo4j connection
python -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password'))
with driver.session() as session:
    result = session.run('RETURN 1 as test')
    print('Connection OK')
"

# Clear and retry
MATCH (n) DETACH DELETE n;
python scripts/build_graph.py --clear-db
```

#### Embedding Generation Issues
```
SYMPTOMS: generate_embeddings.py fails
ERRORS:
- "Model not found"
- "Connection timeout"
- "Out of memory"

SOLUTION:
# Verify model
ollama show nomic-embed-text

# Reduce batch size
python scripts/generate_embeddings.py --batch_size 5

# Check Qdrant status
curl http://localhost:6333/health
```

### Query Processing Errors

#### Entity Extraction Failures
```
SYMPTOMS: Empty entities returned
DEBUGGING:
# Test OLLAMA directly
ollama run mistral:7b-instruct-v0.1-q4_0 "Extract entities from: login issues"

# Check prompt formatting
# Verify model is loaded
ollama ps
```

#### Vector Search Issues
```
SYMPTOMS: No similar documents found
DIAGNOSIS:
# Check collection exists
curl http://localhost:6333/collections

# Verify vector dimensions
curl http://localhost:6333/collections/tickets

# Test search
curl -X POST http://localhost:6333/collections/tickets/points/search \
  -H "Content-Type: application/json" \
  -d '{"vector": [0.1, 0.2, ...], "limit": 5}'
```

## Error Codes and Solutions

### API Error Codes

#### 400 Bad Request
```
CAUSES:
- Invalid query format
- Missing required fields
- Query too long/short

SOLUTION:
# Validate request format
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "test query"}'
```

#### 500 Internal Server Error
```
CAUSES:
- Model inference failed
- Database connection lost
- Memory allocation error

DIAGNOSIS:
# Check API logs
journalctl -u rag-kg-api -n 100

# Test components individually
python scripts/system_check.py
```

#### 503 Service Unavailable
```
CAUSES:
- OLLAMA model not loaded
- Database services down
- Resource exhaustion

SOLUTION:
# Restart all services
sudo systemctl restart ollama neo4j qdrant rag-kg-api

# Check resource usage
free -h && df -h
```

### Database Error Codes

#### Neo4j Errors
```
Neo.ClientError.Statement.SyntaxError:
CAUSE: Invalid Cypher syntax
SOLUTION: Validate query syntax in Neo4j browser

Neo.ClientError.Security.Unauthorized:
CAUSE: Wrong credentials
SOLUTION: Check NEO4J_USER and NEO4J_PASSWORD in .env

Neo.TransientError.General.OutOfMemoryError:
CAUSE: Memory limit exceeded
SOLUTION: Reduce heap size or optimize query
```

#### Qdrant Errors
```
Collection doesn't exist:
SOLUTION: Create collection first
curl -X PUT http://localhost:6333/collections/tickets \
  -H "Content-Type: application/json" \
  -d '{"vectors": {"size": 768, "distance": "Cosine"}}'

Incompatible vector size:
SOLUTION: Check embedding dimensions match collection config
```

## Advanced Debugging

### Log Analysis
```bash
# View recent logs
journalctl -u rag-kg-api --since "1 hour ago" | tail -50

# Search for specific errors
journalctl -u rag-kg-api | grep "ERROR" | tail -10

# Follow logs in real-time
journalctl -u rag-kg-api -f
```

### Performance Profiling
```python
# Profile API endpoints
import cProfile
from app.main import app
cProfile.run('app.test_client().post("/api/v1/query", json={"question": "test"})', 'profile.out')

# Analyze profile
python -m pstats profile.out
sort time
stats 20
```

### Memory Leak Detection
```python
# Monitor memory usage over time
import psutil
import time

process = psutil.Process()
mem_usage = []

for i in range(60):  # Monitor for 1 minute
    mem_usage.append(process.memory_info().rss / 1024 / 1024)  # MB
    time.sleep(1)

print(f"Memory range: {min(mem_usage):.1f} - {max(mem_usage):.1f} MB")
print(f"Average: {sum(mem_usage)/len(mem_usage):.1f} MB")
```

### Network Debugging
```bash
# Test all connections
nc -zv localhost 11434  # OLLAMA
nc -zv localhost 7687   # Neo4j
nc -zv localhost 6333   # Qdrant
nc -zv localhost 8000   # API

# Check network latency
ping -c 5 localhost

# Monitor network usage
sudo iftop -i lo
```

## Preventive Maintenance

### Regular Health Checks
```bash
# Add to crontab
*/15 * * * * /opt/rag-kg/scripts/system_check.py >> /opt/rag-kg/logs/health.log 2>&1
```

### Resource Monitoring
```bash
# Monitor disk usage
df -h | grep -E "(Filesystem|/)"

# Monitor memory trends
free -h && echo "--- Memory usage ---" && ps aux --sort=-%mem | head -10

# Check log sizes
du -sh /opt/rag-kg/logs/*
```

### Backup Verification
```bash
# Test backup integrity
ls -la /opt/rag-kg/backups/

# Verify Neo4j backup
/opt/neo4j/bin/neo4j-admin database info /opt/rag-kg/backups/neo4j/neo4j_latest.dump

# Test Qdrant snapshot
curl http://localhost:6333/snapshots
```

## Emergency Procedures

### Service Recovery
```bash
# Emergency restart sequence
sudo systemctl stop rag-kg-api
sudo systemctl stop qdrant
sudo systemctl stop neo4j
sudo systemctl stop ollama

# Wait for cleanup
sleep 10

# Start in reverse order
sudo systemctl start ollama
sleep 15
sudo systemctl start neo4j
sleep 15
sudo systemctl start qdrant
sleep 15
sudo systemctl start rag-kg-api
```

### Data Recovery
```bash
# Restore from latest backup
# See DEPLOYMENT.md for detailed recovery procedures

# Quick data validation
python scripts/validate_data.py
```

### System Reset
```bash
# Last resort: Full system reset
sudo systemctl isolate rescue.target

# After reset, verify all installations
python scripts/system_check.py

# Reinitialize data if needed
python scripts/generate_sample_data.py --num_tickets 100
python scripts/parse_tickets.py --method hybrid
python scripts/build_graph.py --phase full
python scripts/generate_embeddings.py

## Offline Migration Issues

### Bundle Restoration Fails
```
SYMPTOMS: Manifest directory not found
SOLUTION: Ensure you copied the 'manifest' folder alongside the project root to the destination machine.
```

### Docker Volume Restore Permission Error
```
SYMPTOMS: Permission denied when untarring to volume
SOLUTION: Ensure Docker Desktop is running. Try running PowerShell as Administrator.
```

### OLLAMA Models Missing After Restore
```
SYMPTOMS: ollama list is empty
SOLUTION:
# Check if volume was created: docker volume ls
# Ensure restoring to the correct volume name: ollama
# Verify mount point in bundle_migration.ps1
```
```

## Getting Help

### Diagnostic Information Collection
```bash
# Collect system information
echo "=== System Info ===" > diagnostic.log
uname -a >> diagnostic.log
free -h >> diagnostic.log
df -h >> diagnostic.log

echo "=== Service Status ===" >> diagnostic.log
systemctl status ollama neo4j qdrant rag-kg-api >> diagnostic.log

echo "=== Recent Logs ===" >> diagnostic.log
journalctl -u rag-kg-api --since "1 hour ago" | tail -50 >> diagnostic.log

echo "=== Configuration ===" >> diagnostic.log
cat .env | grep -v PASSWORD >> diagnostic.log
```

### Support Checklist
- [ ] System health check output
- [ ] Error messages and logs
- [ ] Configuration files (redacted)
- [ ] Resource usage statistics
- [ ] Steps to reproduce the issue
- [ ] Expected vs actual behavior

### Community Resources
- Check GitHub issues for similar problems
- Review OLLAMA, Neo4j, Qdrant documentation
- Test with minimal configuration
- Isolate components for testing

## Common Configuration Mistakes

### Environment Variables
```bash
# Wrong: Missing protocol
OLLAMA_BASE_URL=localhost:11434
# Correct:
OLLAMA_BASE_URL=http://localhost:11434

# Wrong: Wrong database URL
NEO4J_URI=localhost:7687
# Correct:
NEO4J_URI=bolt://localhost:7687
```

### Memory Settings
```yaml
# Wrong: Too high for 16GB system
neo4j_memory_heap_max: 16G
# Correct:
neo4j_memory_heap_max: 8G

# Wrong: Missing units
memory_limit: 4
# Correct:
memory_limit: 4G
```

### Path Issues
```bash
# Wrong: Relative paths
OLLAMA_MODELS=./models
# Correct:
OLLAMA_MODELS=/usr/local/share/ollama/models

# Wrong: Wrong permissions
chmod 777 /opt/rag-kg/data
# Correct:
chmod 755 /opt/rag-kg/data
chown raguser:raguser /opt/rag-kg/data
```

## Performance Tuning Checklist

### Quick Wins
- [ ] Ensure models are pre-loaded: `ollama pull <model>`
- [ ] Set appropriate memory limits in systemd
- [ ] Use SSD storage for databases
- [ ] Configure swap space: `sudo fallocate -l 8G /swapfile`
- [ ] Update system: `sudo apt update && sudo apt upgrade`

### Advanced Optimization
- [ ] Profile bottlenecks with cProfile
- [ ] Optimize Cypher queries
- [ ] Implement caching for frequent queries
- [ ] Use connection pooling
- [ ] Monitor and tune garbage collection

### Scaling Considerations
- [ ] Horizontal scaling for API services
- [ ] Database clustering for high availability
- [ ] CDN for static assets (if applicable)
- [ ] Load balancing for multiple instances