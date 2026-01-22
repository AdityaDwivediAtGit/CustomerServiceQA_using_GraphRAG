# bundle_migration.ps1
# This script prepares the project for offline migration by bundling all dependencies and images.

$ManifestDir = "manifest"
$InstallersDir = "$ManifestDir/installers"
$WheelsDir = "$ManifestDir/wheels"
$ImagesDir = "$ManifestDir/images"
$DataDir = "$ManifestDir/data"

# Create directories
New-Item -ItemType Directory -Force -Path $InstallersDir, $WheelsDir, $ImagesDir, $DataDir

Write-Host "--- Starting Bundling for Offline Migration ---" -ForegroundColor Cyan

# 1. Download Python Dependencies
Write-Host "[1/4] Downloading Python wheels..." -ForegroundColor Yellow
& ".\rag-kg-env\Scripts\pip.exe" download -r requirements.txt -d $WheelsDir

# 2. Save Docker Images
Write-Host "[2/4] Saving Docker images (this may take several minutes)..." -ForegroundColor Yellow
docker save -o "$ImagesDir/neo4j.tar" neo4j:5.18
docker save -o "$ImagesDir/ollama.tar" ollama/ollama
docker save -o "$ImagesDir/qdrant.tar" qdrant/qdrant

# 3. Export Data (Basic Copy)
Write-Host "[3/4] Exporting processed data..." -ForegroundColor Yellow
Copy-Item -Path "data/processed" -Destination "$DataDir/processed" -Recurse -Force
Copy-Item -Path "data/embeddings" -Destination "$DataDir/embeddings" -Recurse -Force

# 4. Ollama Models (Optional but recommended)
$OllamaModelsPath = "$HOME/.ollama/models"
if (Test-Path $OllamaModelsPath) {
    Write-Host "[4/4] Copying Ollama models from user profile..." -ForegroundColor Yellow
    Copy-Item -Path $OllamaModelsPath -Destination "$DataDir/ollama_models" -Recurse -Force
} else {
    Write-Host "[4/4] Ollama models folder not found in default location. Skipping copy..." -ForegroundColor Gray
}

Write-Host "`nBundling Complete!" -ForegroundColor Green
Write-Host "Please copy the following to your hard drive:" -ForegroundColor Cyan
Write-Host "1. The entire project folder"
Write-Host "2. The '$ManifestDir' folder"
Write-Host "3. (Don't forget to download the installers mentioned in the plan!)"
