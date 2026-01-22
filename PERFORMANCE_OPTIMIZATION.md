# Performance Optimization Guide

## Purpose and Scope
This guide provides comprehensive performance optimization strategies for the RAG-KG Customer Service QA System. Focuses on 16GB RAM constraints, includes benchmarking scripts, memory management techniques, and scaling recommendations.

## Performance Baselines

### Target Metrics (16GB RAM)
- **Query Response Time**: <2 seconds average, <5 seconds P95
- **Memory Usage**: <12GB peak during operation
- **Concurrent Users**: 5-10 simultaneous queries
- **Data Processing**: 1000 tickets in <30 minutes
- **Model Inference**: <1 second per query
- **Database Queries**: <500ms average

### Benchmarking Scripts

#### System Benchmark
```python
#!/usr/bin/env python3
# scripts/benchmark_system.py

import time
import psutil
import requests
from concurrent.futures import ThreadPoolExecutor
import statistics

def benchmark_query(question, api_url="http://localhost:8000"):
    """Benchmark single query performance."""
    start_time = time.time()

    try:
        response = requests.post(
            f"{api_url}/api/v1/query",
            json={"question": question},
            timeout=30
        )
        response.raise_for_status()
        result = response.json()

        end_time = time.time()
        latency = end_time - start_time

        return {
            'success': True,
            'latency': latency,
            'response_length': len(result.get('answer', '')),
            'sources_count': len(result.get('sources', []))
        }
    except Exception as e:
        end_time = time.time()
        return {
            'success': False,
            'latency': end_time - start_time,
            'error': str(e)
        }

def benchmark_concurrent_queries(num_queries=50, concurrency=5):
    """Benchmark concurrent query performance."""

    questions = [
        "How do I reset my password?",
        "The app crashes when I login",
        "Payment failed but money charged",
        "Can't upload large files",
        "Two-factor authentication issues",
        "Account recovery process",
        "Mobile app update problems",
        "Email notification settings",
        "Data synchronization issues",
        "Browser compatibility problems"
    ] * 5  # Repeat for more queries

    results = []

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(benchmark_query, q)
            for q in questions[:num_queries]
        ]

        for future in futures:
            results.append(future.result())

    # Calculate statistics
    successful = [r for r in results if r['success']]
    latencies = [r['latency'] for r in successful]

    return {
        'total_queries': len(results),
        'successful_queries': len(successful),
        'success_rate': len(successful) / len(results),
        'avg_latency': statistics.mean(latencies) if latencies else 0,
        'p50_latency': statistics.median(latencies) if latencies else 0,
        'p95_latency': statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies) if latencies else 0,
        'min_latency': min(latencies) if latencies else 0,
        'max_latency': max(latencies) if latencies else 0
    }

def monitor_resources(duration=60):
    """Monitor system resources during benchmarking."""

    cpu_usage = []
    memory_usage = []
    start_time = time.time()

    while time.time() - start_time < duration:
        cpu_usage.append(psutil.cpu_percent(interval=1))
        memory = psutil.virtual_memory()
        memory_usage.append(memory.percent)

    return {
        'avg_cpu': statistics.mean(cpu_usage),
        'max_cpu': max(cpu_usage),
        'avg_memory': statistics.mean(memory_usage),
        'max_memory': max(memory_usage)
    }

def main():
    print("=== RAG-KG System Benchmark ===\n")

    # Single query benchmark
    print("1. Single Query Performance:")
    single_result = benchmark_query("How do I reset my password?")
    print(".3f")
    print(f"   Response length: {single_result['response_length']} chars")
    print(f"   Sources found: {single_result['sources_count']}")

    # Concurrent queries benchmark
    print("\n2. Concurrent Query Performance:")
    concurrent_result = benchmark_concurrent_queries(num_queries=20, concurrency=3)
    print(f"   Total queries: {concurrent_result['total_queries']}")
    print(".1f")
    print(".3f")
    print(".3f")
    print(".3f")
    print(".3f")

    # Resource monitoring
    print("\n3. Resource Usage During Load Test:")
    print("   Monitoring for 30 seconds...")
    resources = monitor_resources(duration=30)
    print(".1f")
    print(f"   Peak CPU: {resources['max_cpu']:.1f}%")
    print(".1f")
    print(f"   Peak Memory: {resources['max_memory']:.1f}%")

    # Performance assessment
    print("\n4. Performance Assessment:")
    if concurrent_result['p95_latency'] < 5.0:
        print("   ✓ Query latency within acceptable range")
    else:
        print("   ✗ Query latency too high - optimization needed")

    if resources['max_memory'] < 90:
        print("   ✓ Memory usage acceptable")
    else:
        print("   ✗ Memory usage too high - optimization needed")

    if concurrent_result['success_rate'] > 0.95:
        print("   ✓ Success rate acceptable")
    else:
        print("   ✗ Success rate too low - investigate failures")

if __name__ == "__main__":
    main()
```

#### Data Processing Benchmark
```python
#!/usr/bin/env python3
# scripts/benchmark_data_processing.py

import time
import psutil
from pathlib import Path
import subprocess
import json

def benchmark_data_generation(num_tickets=100):
    """Benchmark sample data generation."""
    start_time = time.time()
    start_memory = psutil.virtual_memory().used

    cmd = ["python", "scripts/generate_sample_data.py",
           "--num_tickets", str(num_tickets)]
    result = subprocess.run(cmd, capture_output=True, text=True)

    end_time = time.time()
    end_memory = psutil.virtual_memory().used

    return {
        'success': result.returncode == 0,
        'duration': end_time - start_time,
        'memory_delta': (end_memory - start_memory) / 1024 / 1024,  # MB
        'output_lines': len(result.stdout.split('\n'))
    }

def benchmark_parsing(input_dir="data/raw"):
    """Benchmark ticket parsing."""
    start_time = time.time()

    cmd = ["python", "scripts/parse_tickets.py",
           "--method", "hybrid", "--input_dir", input_dir]
    result = subprocess.run(cmd, capture_output=True, text=True)

    end_time = time.time()

    return {
        'success': result.returncode == 0,
        'duration': end_time - start_time
    }

def benchmark_graph_construction():
    """Benchmark graph construction."""
    start_time = time.time()

    cmd = ["python", "scripts/build_graph.py", "--phase", "full"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    end_time = time.time()

    return {
        'success': result.returncode == 0,
        'duration': end_time - start_time
    }

def benchmark_embedding_generation():
    """Benchmark embedding generation."""
    start_time = time.time()

    cmd = ["python", "scripts/generate_embeddings.py"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    end_time = time.time()

    return {
        'success': result.returncode == 0,
        'duration': end_time - start_time
    }

def main():
    print("=== Data Processing Benchmark ===\n")

    # Data generation
    print("1. Sample Data Generation (100 tickets):")
    gen_result = benchmark_data_generation(100)
    print(".2f")
    print(".1f")
    print(f"   Success: {gen_result['success']}")

    # Parsing
    print("\n2. Ticket Parsing:")
    parse_result = benchmark_parsing()
    print(".2f")
    print(f"   Success: {parse_result['success']}")

    # Graph construction
    print("\n3. Graph Construction:")
    graph_result = benchmark_graph_construction()
    print(".2f")
    print(f"   Success: {graph_result['success']}")

    # Embedding generation
    print("\n4. Embedding Generation:")
    embed_result = benchmark_embedding_generation()
    print(".2f")
    print(f"   Success: {embed_result['success']}")

    # Total time
    total_time = (gen_result['duration'] + parse_result['duration'] +
                 graph_result['duration'] + embed_result['duration'])
    print(".2f")

    # Assessment
    print("\n5. Performance Assessment:")
    if total_time < 1800:  # 30 minutes
        print("   ✓ Data processing within acceptable time")
    else:
        print("   ✗ Data processing too slow - optimization needed")

    success_rate = sum([gen_result['success'], parse_result['success'],
                       graph_result['success'], embed_result['success']]) / 4
    if success_rate == 1.0:
        print("   ✓ All processing steps successful")
    else:
        print(".0%")

if __name__ == "__main__":
    main()
```

## Memory Optimization Strategies

### Model Memory Management
```python
# Memory-efficient model loading
import ollama
import gc

class ModelManager:
    def __init__(self):
        self.loaded_models = set()
        self.max_memory_gb = 12

    def load_model(self, model_name):
        """Load model only if memory allows."""
        if model_name in self.loaded_models:
            return True

        # Check current memory usage
        memory_gb = psutil.virtual_memory().used / 1024 / 1024 / 1024

        if memory_gb > self.max_memory_gb:
            # Unload least recently used model
            self.unload_model()

        try:
            # Check if model exists
            ollama.show(model_name)
            self.loaded_models.add(model_name)
            return True
        except:
            return False

    def unload_model(self):
        """Unload a model to free memory."""
        if self.loaded_models:
            model_to_unload = next(iter(self.loaded_models))
            # Note: OLLAMA doesn't have explicit unload, but we can track
            self.loaded_models.remove(model_to_unload)
            gc.collect()

    def get_loaded_models(self):
        return list(self.loaded_models)
```

### Batch Processing Optimization
```python
# Optimized batch processing with memory monitoring
def process_with_memory_limits(items, process_func, batch_size=10, max_memory_gb=12):
    results = []

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]

        # Check memory before processing
        memory_gb = psutil.virtual_memory().used / 1024 / 1024 / 1024
        if memory_gb > max_memory_gb:
            gc.collect()  # Force garbage collection
            time.sleep(1)  # Brief pause

        # Process batch
        batch_results = process_func(batch)
        results.extend(batch_results)

        # Memory cleanup
        del batch
        gc.collect()

    return results
```

### Database Memory Tuning

#### Neo4j Optimization
```properties
# neo4j.conf optimizations
# Memory settings
dbms.memory.heap.initial_size=2G
dbms.memory.heap.max_size=6G
dbms.memory.pagecache.size=4G

# Query optimization
dbms.cypher.hints.error=false
dbms.cypher.statistics_divergence_threshold=0.1

# Transaction settings
dbms.tx_state.memory_allocation=ON_HEAP
dbms.tx_state.max_off_heap_memory=2G

# Indexing
dbms.index.default_schema_provider=native-btree-1.0
```

#### Qdrant Optimization
```yaml
# Performance settings
max_threads: 4
memmap_threshold: 100MB
payload_mmap_threshold: 10MB

# Search optimization
search_cache_size: 100MB
```

## Query Optimization Techniques

### Cypher Query Optimization
```python
# Optimized graph queries
class OptimizedGraphQueries:
    def __init__(self, driver):
        self.driver = driver

    def find_similar_issues(self, entity_list, limit=10):
        """Optimized similarity search."""
        with self.driver.session() as session:
            # Use parameterized query to avoid recompilation
            result = session.run("""
                MATCH (i:Issue)-[:MENTIONS_ENTITY]->(e:Entity)
                WHERE e.value IN $entities
                WITH i, count(e) as entity_matches
                ORDER BY entity_matches DESC
                LIMIT $limit
                RETURN i.id, i.title, entity_matches
                """,
                entities=entity_list,
                limit=limit
            )
            return [record for record in result]

    def get_issue_subgraph(self, issue_id, hops=2):
        """Efficient subgraph retrieval."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH path = (start:Issue {id: $issue_id})-[*1..2]-(connected)
                WHERE ALL(node IN nodes(path) WHERE node:Issue OR node:Entity OR node:Tag)
                RETURN path
                LIMIT 50
                """,
                issue_id=issue_id
            )
            return [record for record in result]
```

### Vector Search Optimization
```python
# Optimized vector retrieval
class OptimizedVectorSearch:
    def __init__(self, qdrant_client, collection_name):
        self.client = qdrant_client
        self.collection = collection_name

    def hybrid_search(self, query_vector, text_query=None, limit=10):
        """Combine vector similarity with text filtering."""
        search_request = {
            "vector": query_vector,
            "limit": limit,
            "with_payload": True,
            "score_threshold": 0.3
        }

        if text_query:
            # Add text-based filtering
            search_request["filter"] = {
                "must": [
                    {
                        "key": "text",
                        "match": {
                            "text": text_query
                        }
                    }
                ]
            }

        return self.client.search(
            collection_name=self.collection,
            **search_request
        )

    def batch_search(self, query_vectors, batch_size=5):
        """Batch multiple vector searches."""
        results = []

        for i in range(0, len(query_vectors), batch_size):
            batch = query_vectors[i:i + batch_size]

            # Execute batch search
            batch_results = self.client.search_batch(
                collection_name=self.collection,
                requests=[
                    {"vector": vec, "limit": 5} for vec in batch
                ]
            )
            results.extend(batch_results)

        return results
```

## Caching Strategies

### Multi-Level Caching
```python
import redis
from cachetools import TTLCache
import hashlib

class MultiLevelCache:
    def __init__(self):
        # L1: In-memory cache (fast, limited size)
        self.l1_cache = TTLCache(maxsize=1000, ttl=300)  # 5 minutes

        # L2: Redis cache (persistent, larger)
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)

        # L3: File-based cache for embeddings
        self.embedding_cache_dir = Path("cache/embeddings")

    def get(self, key):
        """Get from cache hierarchy."""
        # Check L1
        if key in self.l1_cache:
            return self.l1_cache[key]

        # Check L2
        cached = self.redis_client.get(key)
        if cached:
            # Promote to L1
            self.l1_cache[key] = cached
            return cached

        return None

    def set(self, key, value, ttl=300):
        """Set in all cache levels."""
        # L1
        self.l1_cache[key] = value

        # L2
        self.redis_client.setex(key, ttl, value)

    def get_embedding(self, text):
        """Get cached embedding."""
        key = hashlib.md5(text.encode()).hexdigest()
        cache_file = self.embedding_cache_dir / f"{key}.json"

        if cache_file.exists():
            with open(cache_file, 'r') as f:
                return json.load(f)

        return None

    def set_embedding(self, text, embedding):
        """Cache embedding to file."""
        self.embedding_cache_dir.mkdir(parents=True, exist_ok=True)

        key = hashlib.md5(text.encode()).hexdigest()
        cache_file = self.embedding_cache_dir / f"{key}.json"

        with open(cache_file, 'w') as f:
            json.dump(embedding, f)
```

### Query Result Caching
```python
class QueryCache:
    def __init__(self, cache_manager):
        self.cache = cache_manager

    def get_cached_query(self, question, context=None):
        """Get cached query result."""
        cache_key = self._generate_cache_key(question, context)

        cached_result = self.cache.get(cache_key)
        if cached_result:
            cached_result['cached'] = True
            return cached_result

        return None

    def cache_query_result(self, question, context, result):
        """Cache query result."""
        cache_key = self._generate_cache_key(question, context)

        # Don't cache errors or empty results
        if not result.get('success', True) or not result.get('answer'):
            return

        # Cache for 1 hour
        self.cache.set(cache_key, result, ttl=3600)

    def _generate_cache_key(self, question, context=None):
        """Generate consistent cache key."""
        key_parts = [question.strip().lower()]

        if context:
            # Include relevant context in key
            context_str = json.dumps(context, sort_keys=True)
            key_parts.append(context_str)

        return hashlib.md5('|'.join(key_parts).encode()).hexdigest()
```

## Scaling Strategies

### Horizontal Scaling
```yaml
# Docker Compose for multiple API instances
version: '3.8'

services:
  api-1:
    build: .
    environment:
      - API_PORT=8001
    deploy:
      replicas: 1

  api-2:
    build: .
    environment:
      - API_PORT=8002
    deploy:
      replicas: 1

  load-balancer:
    image: nginx
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - api-1
      - api-2
```

### Database Scaling
```yaml
# Neo4j cluster configuration
neo4j:
  image: neo4j:5.16-enterprise
  environment:
    NEO4J_dbms_cluster_discovery_endpoints: neo4j-seed:5000,neo4j-core-1:5000,neo4j-core-2:5000
    NEO4J_dbms_mode:CORE
  volumes:
    - neo4j_data:/data

# Qdrant cluster
qdrant:
  image: qdrant/qdrant
  environment:
    QDRANT__CLUSTER__ENABLED: true
    QDRANT__CLUSTER__PEERS: qdrant-1:6335,qdrant-2:6335
```

### Model Scaling
```python
# Model sharding for large deployments
class ModelShardManager:
    def __init__(self, model_configs):
        self.shards = {}
        for config in model_configs:
            shard_id = config['shard_id']
            self.shards[shard_id] = {
                'url': config['ollama_url'],
                'models': config['models'],
                'capacity': config['capacity']
            }

    def get_optimal_shard(self, model_name, load_factor=0.8):
        """Find best shard for model inference."""
        available_shards = [
            shard for shard in self.shards.values()
            if model_name in shard['models'] and shard['capacity'] < load_factor
        ]

        if not available_shards:
            return None

        # Return shard with lowest capacity
        return min(available_shards, key=lambda x: x['capacity'])
```

## Monitoring and Alerting

### Performance Metrics Collection
```python
import prometheus_client as prom

# Define metrics
query_latency = prom.Histogram(
    'rag_query_latency_seconds',
    'Query processing latency',
    ['model', 'status']
)

memory_usage = prom.Gauge(
    'rag_memory_usage_bytes',
    'Current memory usage'
)

active_queries = prom.Gauge(
    'rag_active_queries',
    'Number of active queries'
)

def record_query_metrics(question, start_time, success, model_used):
    """Record query performance metrics."""
    latency = time.time() - start_time

    query_latency.labels(
        model=model_used,
        status='success' if success else 'error'
    ).observe(latency)

    active_queries.dec()  # Decrement active queries

def update_resource_metrics():
    """Update system resource metrics."""
    memory = psutil.virtual_memory()
    memory_usage.set(memory.used)
```

### Alerting Rules
```yaml
# Prometheus alerting rules
groups:
  - name: rag_kg_alerts
    rules:
      - alert: HighQueryLatency
        expr: histogram_quantile(0.95, rate(rag_query_latency_seconds_bucket[5m])) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High query latency detected"

      - alert: HighMemoryUsage
        expr: rag_memory_usage_bytes / 1024 / 1024 / 1024 > 14
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High memory usage detected"

      - alert: ServiceDown
        expr: up{job="rag-kg-api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "RAG-KG API service is down"
```

## Resource Usage Profiles

### Development Profile
```yaml
# Low resource usage for development
ollama_memory: 4GB
neo4j_heap: 2GB
qdrant_memory: 512MB
api_workers: 1
batch_size: 5
```

### Production Profile (16GB)
```yaml
# Optimized for 16GB systems
ollama_memory: 8GB
neo4j_heap: 6GB
qdrant_memory: 1GB
api_workers: 2
batch_size: 8
cache_size: 500MB
```

### High-Performance Profile (32GB+)
```yaml
# For systems with more resources
ollama_memory: 12GB
neo4j_heap: 12GB
qdrant_memory: 4GB
api_workers: 4
batch_size: 16
cache_size: 2GB
```

## Continuous Optimization

### Automated Performance Testing
```bash
# Add to CI/CD pipeline
#!/bin/bash
# scripts/ci_performance_test.sh

echo "Running performance tests..."

# Run benchmarks
python scripts/benchmark_system.py > benchmark_results.json

# Check thresholds
python -c "
import json
with open('benchmark_results.json') as f:
    results = json.load(f)

if results['p95_latency'] > 5.0:
    print('FAIL: Latency too high')
    exit(1)
else:
    print('PASS: Performance acceptable')
"
```

### Performance Regression Detection
```python
# Performance regression monitoring
class PerformanceMonitor:
    def __init__(self):
        self.baseline_metrics = self.load_baseline()

    def load_baseline(self):
        """Load performance baseline."""
        try:
            with open('performance_baseline.json', 'r') as f:
                return json.load(f)
        except:
            return {}

    def check_regression(self, current_metrics):
        """Check for performance regression."""
        regressions = []

        for metric, current_value in current_metrics.items():
            baseline = self.baseline_metrics.get(metric)
            if baseline:
                degradation = (current_value - baseline) / baseline
                if degradation > 0.1:  # 10% degradation
                    regressions.append({
                        'metric': metric,
                        'baseline': baseline,
                        'current': current_value,
                        'degradation': degradation
                    })

        return regressions

    def update_baseline(self, metrics):
        """Update performance baseline."""
        with open('performance_baseline.json', 'w') as f:
            json.dump(metrics, f, indent=2)
```

## Cost Optimization

### Resource Right-Sizing
- **Monitor utilization**: Use tools like `htop`, `iotop`
- **Auto-scaling**: Scale based on load patterns
- **Spot instances**: Use preemptible resources for non-critical workloads
- **Storage optimization**: Compress old logs and backups

### Efficiency Improvements
- **Batch processing**: Process multiple items together
- **Lazy loading**: Load resources only when needed
- **Connection pooling**: Reuse database connections
- **Query optimization**: Use efficient algorithms and data structures

### Power Management
```bash
# CPU frequency scaling
sudo cpupower frequency-set -g powersave  # For low-power mode
sudo cpupower frequency-set -g performance  # For high-performance mode

# Disable hyper-threading if not needed
echo off > /sys/devices/system/cpu/smt/control
```

This comprehensive optimization guide ensures the RAG-KG system performs efficiently within 16GB RAM constraints while maintaining response quality and system reliability.