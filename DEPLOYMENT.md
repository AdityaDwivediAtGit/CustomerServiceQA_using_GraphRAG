# Deployment Guide

## Purpose and Scope
This guide covers deployment strategies for the RAG-KG Customer Service QA System, including local deployment, Docker containerization, production setup, and maintenance procedures. Optimized for 16GB RAM environments with offline operation.

## Deployment Options

### Option 1: Local Development Deployment
Best for development, testing, and small-scale production.

### Option 2: Docker Container Deployment
Recommended for production with isolation and scalability.

### Option 3: Hybrid Deployment
Databases in Docker, application services local.

## Local Deployment

### Directory Structure
```
/opt/rag-kg/
├── app/                 # Application code
├── config/             # Configuration files
├── data/               # Data directories
├── logs/               # Log files
├── scripts/            # Management scripts
├── venv/               # Python virtual environment
└── docker-compose.yml  # For hybrid deployment
```

### Installation Steps

#### 1. Create Application Directory
```
# COMMAND: sudo mkdir -p /opt/rag-kg && sudo chown $USER:$USER /opt/rag-kg
# PURPOSE: Create application directory with proper permissions
# EXPECTED OUTPUT: Directory created
```

#### 2. Clone or Copy Application Code
```
# Copy all project files to /opt/rag-kg/
# Set proper permissions
chmod +x /opt/rag-kg/scripts/*.py
chmod +x /opt/rag-kg/scripts/*.sh
```

#### 3. Setup Python Environment
```
# COMMAND: cd /opt/rag-kg && python3 -m venv venv
# PURPOSE: Create isolated Python environment
# EXPECTED OUTPUT: venv directory created

# COMMAND: source venv/bin/activate && pip install -r requirements.txt
# PURPOSE: Install dependencies
# EXPECTED OUTPUT: All packages installed successfully
```

#### 4. Configure Environment
```
# Copy and edit .env file
cp .env.example .env
# Edit .env with your settings
```

#### 5. Setup Systemd Services

##### OLLAMA Service
```ini
# /etc/systemd/system/ollama.service
[Unit]
Description=OLLAMA AI Model Server
After=network.target

[Service]
Type=simple
User=ollama
Group=ollama
ExecStart=/usr/local/bin/ollama serve
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

##### Neo4j Service
```ini
# /etc/systemd/system/neo4j.service
[Unit]
Description=Neo4j Graph Database
After=network.target

[Service]
Type=simple
User=neo4j
Group=neo4j
Environment=NEO4J_HOME=/opt/neo4j
ExecStart=/opt/neo4j/bin/neo4j start
ExecStop=/opt/neo4j/bin/neo4j stop
Restart=always
LimitNOFILE=60000
LimitMEMLOCK=infinity

[Install]
WantedBy=multi-user.target
```

##### Qdrant Service (Local)
```ini
# /etc/systemd/system/qdrant.service
[Unit]
Description=Qdrant Vector Database
After=network.target

[Service]
Type=simple
User=qdrant
Group=qdrant
WorkingDirectory=/opt/qdrant
ExecStart=/opt/qdrant/qdrant
Restart=always
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

##### RAG-KG API Service
```ini
# /etc/systemd/system/rag-kg-api.service
[Unit]
Description=RAG-KG Customer Service QA API
After=network.target ollama.service neo4j.service qdrant.service
Requires=ollama.service neo4j.service qdrant.service

[Service]
Type=simple
User=raguser
Group=raguser
WorkingDirectory=/opt/rag-kg
Environment=PATH=/opt/rag-kg/venv/bin
ExecStart=/opt/rag-kg/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# Memory limits for 16GB RAM
MemoryLimit=4G
MemoryHigh=3G

[Install]
WantedBy=multi-user.target
```

#### 6. Enable and Start Services
```
# Enable services
sudo systemctl enable ollama neo4j qdrant rag-kg-api

# Start services in order
sudo systemctl start ollama
sleep 10
sudo systemctl start neo4j
sleep 10
sudo systemctl start qdrant
sleep 10
sudo systemctl start rag-kg-api

# Check status
sudo systemctl status ollama neo4j qdrant rag-kg-api
```

## Docker Deployment

### Docker Compose Configuration
```yaml
# docker-compose.yml
version: '3.8'

services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 8G
        reservations:
          memory: 4G

  neo4j:
    image: neo4j:5.16-community
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      NEO4J_AUTH: neo4j/your_password
      NEO4J_PLUGINS: '["graph-data-science"]'
      NEO4J_dbms_memory_heap_initial__size: 2G
      NEO4J_dbms_memory_heap_max__size: 8G
      NEO4J_dbms_memory_pagecache_size: 4G
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
      - ./neo4j.conf:/var/lib/neo4j/conf/neo4j.conf
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 12G
        reservations:
          memory: 8G

  qdrant:
    image: qdrant/qdrant:v1.7.4
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G

  rag-kg-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - NEO4J_URI=bolt://neo4j:7687
      - QDRANT_URL=http://qdrant:6333
    depends_on:
      - ollama
      - neo4j
      - qdrant
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G

volumes:
  ollama_data:
  neo4j_data:
  neo4j_logs:
  qdrant_data:
```

### Docker Build and Deploy
```
# Build application image
docker build -t rag-kg-api .

# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f

# Scale API service if needed
docker-compose up -d --scale rag-kg-api=3
```

### Dockerfile
```dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash raguser

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data logs && \
    chown -R raguser:raguser /app

# Switch to non-root user
USER raguser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

## Hybrid Deployment

### Recommended Setup
- **OLLAMA**: Local service (better performance)
- **Neo4j**: Docker container (easier management)
- **Qdrant**: Docker container (memory efficient)
- **API**: Local Python application (direct access to models)

### docker-compose.override.yml
```yaml
version: '3.8'

services:
  # Only databases in Docker
  neo4j:
    # ... same as above

  qdrant:
    # ... same as above

  # API runs locally, connect to Docker databases
  # rag-kg-api service commented out
```

## Resource Limits and Optimization

### Memory Configuration

#### For 16GB RAM Systems
```yaml
# Total allocation
ollama: 8GB (models loaded)
neo4j: 8GB (heap + page cache)
qdrant: 2GB
api: 2GB
system: 2GB reserved
# Total: ~22GB required (with some overlap)
```

#### Neo4j Memory Tuning
```properties
# neo4j.conf
dbms.memory.heap.initial_size=2G
dbms.memory.heap.max_size=6G
dbms.memory.pagecache.size=4G
dbms.tx_state.memory_allocation=ON_HEAP
```

#### System Memory Limits
```bash
# Set system-wide limits
echo "vm.overcommit_memory=1" >> /etc/sysctl.conf
echo "vm.max_map_count=262144" >> /etc/sysctl.conf
sysctl -p
```

### CPU Optimization
```yaml
# docker-compose.yml deploy section
deploy:
  resources:
    limits:
      cpus: '2.0'
    reservations:
      cpus: '1.0'
```

### Storage Optimization
```yaml
# Volume mounts for persistence
volumes:
  - type: bind
    source: /opt/rag-kg/data
    target: /app/data
  - type: bind
    source: /opt/rag-kg/logs
    target: /app/logs
```

## Backup and Recovery

### Automated Backup Scripts

#### Neo4j Backup
```bash
#!/bin/bash
# scripts/backup_neo4j.sh

BACKUP_DIR="/opt/rag-kg/backups/neo4j"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Stop Neo4j for consistent backup
sudo systemctl stop neo4j

# Create backup
/opt/neo4j/bin/neo4j-admin database dump neo4j --to-path=$BACKUP_DIR/neo4j_$TIMESTAMP.dump

# Restart Neo4j
sudo systemctl start neo4j

# Cleanup old backups (keep last 7 days)
find $BACKUP_DIR -name "neo4j_*.dump" -mtime +7 -delete

echo "Neo4j backup completed: neo4j_$TIMESTAMP.dump"
```

#### Qdrant Backup
```bash
#!/bin/bash
# scripts/backup_qdrant.sh

BACKUP_DIR="/opt/rag-kg/backups/qdrant"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Create snapshot
curl -X POST http://localhost:6333/snapshots/create \
  -H "Content-Type: application/json" \
  -d '{"collection_name": "tickets"}' \
  -o $BACKUP_DIR/qdrant_tickets_$TIMESTAMP.snapshot

# Cleanup old backups
find $BACKUP_DIR -name "qdrant_*.snapshot" -mtime +7 -delete

echo "Qdrant backup completed: qdrant_tickets_$TIMESTAMP.snapshot"
```

#### Application Data Backup
```bash
#!/bin/bash
# scripts/backup_app.sh

BACKUP_DIR="/opt/rag-kg/backups/app"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup configuration and data
tar -czf $BACKUP_DIR/app_backup_$TIMESTAMP.tar.gz \
  -C /opt/rag-kg \
  config/ \
  data/ \
  logs/ \
  .env

# Cleanup old backups
find $BACKUP_DIR -name "app_backup_*.tar.gz" -mtime +30 -delete

echo "Application backup completed: app_backup_$TIMESTAMP.tar.gz"
```

### Scheduled Backups
```bash
# Add to crontab (crontab -e)
# Daily backups at 2 AM
0 2 * * * /opt/rag-kg/scripts/backup_neo4j.sh
30 2 * * * /opt/rag-kg/scripts/backup_qdrant.sh
0 3 * * * /opt/rag-kg/scripts/backup_app.sh
```

### Recovery Procedures

#### Neo4j Recovery
```bash
# Stop Neo4j
sudo systemctl stop neo4j

# Restore from backup
/opt/neo4j/bin/neo4j-admin database load neo4j --from-path=/opt/rag-kg/backups/neo4j/neo4j_20240115_020000.dump --overwrite-destination=true

# Start Neo4j
sudo systemctl start neo4j
```

#### Qdrant Recovery
```bash
# Restore from snapshot
curl -X POST http://localhost:6333/snapshots/restore \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "tickets",
    "snapshot_path": "/opt/rag-kg/backups/qdrant/qdrant_tickets_20240115_020000.snapshot"
  }'
```

## Monitoring and Alerting

### System Monitoring
```bash
# Install monitoring tools
sudo apt install htop iotop sysstat

# Monitor memory usage
watch -n 5 'free -h && echo "---" && ps aux --sort=-%mem | head -10'
```

### Log Monitoring
```bash
# View application logs
journalctl -u rag-kg-api -f

# Monitor all services
journalctl -u ollama -u neo4j -u qdrant -u rag-kg-api --since "1 hour ago"
```

### Health Check Monitoring
```bash
#!/bin/bash
# scripts/health_monitor.sh

# Check all services
services=("ollama" "neo4j" "qdrant" "rag-kg-api")
for service in "${services[@]}"; do
    if ! systemctl is-active --quiet $service; then
        echo "$(date): $service is down" >> /opt/rag-kg/logs/health_alerts.log
        # Send alert (email, slack, etc.)
    fi
done

# Check API health
if ! curl -f -s http://localhost:8000/health > /dev/null; then
    echo "$(date): API health check failed" >> /opt/rag-kg/logs/health_alerts.log
fi
```

### Performance Monitoring
```bash
# Add to crontab for regular monitoring
*/5 * * * * /opt/rag-kg/scripts/health_monitor.sh
0 * * * * /opt/rag-kg/scripts/performance_report.sh
```

## Scaling Considerations

### Vertical Scaling
```yaml
# Increase resources as available
deploy:
  resources:
    limits:
      memory: 32G  # If upgrading RAM
      cpus: '4.0'
```

### Horizontal Scaling
```yaml
# Multiple API instances
services:
  rag-kg-api-1:
    # ...
  rag-kg-api-2:
    ports:
      - "8001:8000"
  load-balancer:
    image: nginx
    ports:
      - "80:80"
```

### Database Scaling
- **Neo4j**: Cluster setup for high availability
- **Qdrant**: Distributed deployment
- **OLLAMA**: Multiple model servers

## Security Hardening

### Service Isolation
```bash
# Create separate users
sudo useradd -r -s /bin/false ollama
sudo useradd -r -s /bin/false neo4j
sudo useradd -r -s /bin/false qdrant
sudo useradd -m raguser
```

### Firewall Configuration
```bash
# UFW rules
sudo ufw allow 8000/tcp  # API
sudo ufw allow 11434/tcp # OLLAMA
sudo ufw allow 7474/tcp  # Neo4j browser
sudo ufw allow 7687/tcp  # Neo4j bolt
sudo ufw allow 6333/tcp  # Qdrant
sudo ufw --force enable
```

### SSL/TLS Configuration
```nginx
# nginx.conf for SSL termination
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Troubleshooting Deployment

### Common Issues

#### Service Startup Failures
```
# Check logs
journalctl -u <service> -n 50

# Check resource usage
htop
df -h

# Validate configuration
python scripts/system_check.py
```

#### Memory Issues
```
# Monitor memory
free -h
ps aux --sort=-%mem | head -10

# Adjust limits in systemd service files
MemoryLimit=6G
MemoryHigh=4G
```

#### Network Connectivity
```
# Test connections
curl http://localhost:11434/api/tags
curl http://localhost:7687
curl http://localhost:6333/health

# Check firewall
sudo ufw status
```

#### Performance Degradation
```
# Profile application
python -m cProfile -s time app/main.py

# Database performance
# Neo4j: :sysinfo in browser
# Qdrant: Check collection stats
```

### Emergency Procedures
```bash
# Quick restart all services
sudo systemctl restart ollama neo4j qdrant rag-kg-api

# Emergency stop
sudo systemctl stop rag-kg-api  # Stop API first
sudo systemctl stop ollama neo4j qdrant

# Full system reset
sudo systemctl isolate rescue.target
# Then reboot
```

## Maintenance Procedures

### Regular Maintenance
```bash
# Weekly tasks
sudo apt update && sudo apt upgrade -y
docker system prune -f
find /opt/rag-kg/logs -name "*.log" -mtime +30 -delete

# Monthly tasks
sudo systemctl restart ollama neo4j qdrant rag-kg-api
# Verify backups are working
ls -la /opt/rag-kg/backups/
```

### Update Procedures
```bash
# Update application
cd /opt/rag-kg
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart rag-kg-api

# Update Docker services
docker-compose pull
docker-compose up -d
```

### Log Rotation
```bash
# /etc/logrotate.d/rag-kg
/opt/rag-kg/logs/*.log {
    daily
    rotate 30
    compress
    missingok
    notifempty
    create 644 raguser raguser
    postrotate
        systemctl reload rag-kg-api
    endscript
}
```