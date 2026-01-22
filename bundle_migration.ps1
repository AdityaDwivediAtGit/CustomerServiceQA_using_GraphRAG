param (
    [Parameter(Mandatory = $true)]
    [ValidateSet("Export", "Restore")]
    [string]$Mode
)

$ManifestDir = "manifest"
$WheelsDir = "$ManifestDir/wheels"
$ImagesDir = "$ManifestDir/images"
$VolumesDir = "$ManifestDir/volumes"
$DataDir = "$ManifestDir/data"

function New-MigrationDirectories {
    New-Item -ItemType Directory -Force -Path $ManifestDir, $WheelsDir, $ImagesDir, $VolumesDir, $DataDir
}

if ($Mode -eq "Export") {
    Write-Host "=== Starting Migration EXPORT ===" -ForegroundColor Cyan
    New-MigrationDirectories

    # 0. Pull Ollama Models
    Write-Host "[1/5] Ensuring Ollama models are pulled..." -ForegroundColor Yellow
    $Models = @("llama2:7b-chat-q4_0", "mistral:7b-instruct-q4_0", "nomic-embed-text", "llama3.2:1b", "llama3.2:3b", "codellama:7b", "qwen2.5:7b")
    foreach ($m in $Models) {
        Write-Host "Pulling $m..." -ForegroundColor Gray
        docker exec ollama ollama pull $m
    }

    # 1. Download Python Wheels
    Write-Host "[2/5] Downloading Python dependencies (wheels)..." -ForegroundColor Yellow
    pip download -r requirements.txt -d $WheelsDir

    # 2. Save Docker Images
    Write-Host "[3/5] Saving Docker images to .tar files..." -ForegroundColor Yellow
    docker save -o "$ImagesDir/neo4j.tar" neo4j:5.18
    docker save -o "$ImagesDir/ollama.tar" ollama/ollama
    docker save -o "$ImagesDir/qdrant.tar" qdrant/qdrant

    # 3. Export Docker Volumes
    Write-Host "[4/5] Exporting Docker volumes..." -ForegroundColor Yellow
    # Note: We use a small alpine image to tar the volumes
    docker pull alpine
    docker save -o "$ImagesDir/alpine.tar" alpine
    
    Write-Host "Backing up Neo4j volume..." -ForegroundColor Gray
    docker run --rm -v neo4j_data:/data -v "${PWD}/$VolumesDir":/backup alpine tar cvf /backup/neo4j_data.tar /data
    
    Write-Host "Backing up Ollama volume..." -ForegroundColor Gray
    docker run --rm -v ollama:/root/.ollama -v "${PWD}/$VolumesDir":/backup alpine tar cvf /backup/ollama.tar /root/.ollama
    
    Write-Host "Backing up Qdrant volume..." -ForegroundColor Gray
    docker run --rm -v qdrant_storage:/qdrant/storage -v "${PWD}/$VolumesDir":/backup alpine tar cvf /backup/qdrant_storage.tar /qdrant/storage

    # 4. Copy Processed Data
    Write-Host "[5/5] Copying local data folders..." -ForegroundColor Yellow
    if (Test-Path "data") {
        Copy-Item -Path "data" -Destination "$DataDir" -Recurse -Force
    }

    Write-Host "`nExport Complete! Copy the entire project folder to your hard drive." -ForegroundColor Green
}
elseif ($Mode -eq "Restore") {
    Write-Host "=== Starting Migration RESTORE ===" -ForegroundColor Cyan

    if (-not (Test-Path $ManifestDir)) {
        Write-Error "Manifest directory not found! Ensure you are running this in the project folder copied from the export."
        return
    }

    # 1. Load Docker Images
    Write-Host "[1/4] Loading Docker images..." -ForegroundColor Yellow
    Get-ChildItem "$ImagesDir/*.tar" | ForEach-Object {
        Write-Host "Loading $($_.Name)..." -ForegroundColor Gray
        docker load -i $_.FullName
    }

    # 2. Restore Docker Volumes
    Write-Host "[2/4] Restoring Docker volumes..." -ForegroundColor Yellow
    
    Write-Host "Restoring Neo4j volume..." -ForegroundColor Gray
    docker volume create neo4j_data
    docker run --rm -v neo4j_data:/data -v "${PWD}/$VolumesDir":/backup alpine sh -c "cd / && tar xvf /backup/neo4j_data.tar"
    
    Write-Host "Restoring Ollama volume..." -ForegroundColor Gray
    docker volume create ollama
    docker run --rm -v ollama:/root/.ollama -v "${PWD}/$VolumesDir":/backup alpine sh -c "cd / && tar xvf /backup/ollama.tar"
    
    Write-Host "Restoring Qdrant volume..." -ForegroundColor Gray
    docker volume create qdrant_storage
    docker run --rm -v qdrant_storage:/qdrant/storage -v "${PWD}/$VolumesDir":/backup alpine sh -c "cd / && tar xvf /backup/qdrant_storage.tar"

    # 3. Start Containers (using your specific commands)
    Write-Host "[3/4] Starting Service Containers..." -ForegroundColor Yellow
    
    # Ollama
    docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
    
    # Neo4j
    docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -v neo4j_data:/data -e NEO4J_AUTH=neo4j/password neo4j:5.18
    
    # Qdrant
    docker run -d --name qdrant -p 6333:6333 -p 6334:6334 -v qdrant_storage:/qdrant/storage qdrant/qdrant

    # 4. Setup Python Environment
    Write-Host "[4/4] Setting up Python virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    .\venv\Scripts\activate
    python -m pip install --upgrade pip
    pip install --no-index --find-links=$WheelsDir -r requirements.txt

    Write-Host "`nRestore Complete! You can now run the application." -ForegroundColor Green
    Write-Host "Try: python scripts/system_check.py" -ForegroundColor Cyan
}
