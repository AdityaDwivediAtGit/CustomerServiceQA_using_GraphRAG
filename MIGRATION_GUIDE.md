# Offline Migration Guide

This guide describes how to migrate the RAG-KG Customer Service QA system to a Windows machine with **no internet connectivity**.

## Overview

The migration process uses a unified PowerShell script `bundle_migration.ps1` to handle:
1. **Export**: Bundling all models, dependencies, Docker images, and database volumes from your connected machine.
2. **Restore**: Automating the entire setup on the offline machine.

## Prerequisites (Connected Machine)

1. Create a `manifest/installers` folder in the project root.
2. Download and save the following installers into that folder:
   - [Python 3.12.x Installer](https://www.python.org/downloads/windows/)
   - [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
   - [WSL2 Linux Kernel Update Package](https://learn.microsoft.com/en-us/windows/wsl/install-manual#step-4---download-the-linux-kernel-update-package)

## Phase 1: Export (Source Machine)

Run the migration script in **Export** mode. This will pull all required models (Llama 2, Mistral, etc.), bundle Python wheels (including LangChain, LangGraph, etc.), and export Docker volumes:

```powershell
.\bundle_migration.ps1 -Mode Export
```

Once complete, copy the **entire project folder** (including the newly created `manifest` folder) to your portable hard drive.

## Phase 2: Setup (Clean Offline Machine)

1. **Enable Windows Features**: Enable "Virtual Machine Platform" and "Windows Subsystem for Linux" in "Turn Windows features on or off".
2. **Install Software**:
   - Install the WSL2 Update package.
   - Install Docker Desktop (requires restart).
   - Install Python 3.12 (ensure "Add Python to PATH" is checked).

## Phase 3: Restore (Destination Machine)

Copy the project folder from your hard drive to the local disk. Open a terminal (PowerShell) inside the project folder and run:

```powershell
.\bundle_migration.ps1 -Mode Restore
```

This script will:
- Load all Docker images.
- Recreate and restore Neo4j, Qdrant, and Ollama volumes.
- Start all service containers.
- Create a virtual environment and install all dependencies offline.

## Verification

After the restore is complete, verify the system:

```powershell
.\venv\Scripts\activate
python scripts/system_check.py
```

## Management Commands

- **Start/Stop Ollama**: `docker start ollama` / `docker stop ollama`
- **Interact with Models**: `docker exec -it ollama ollama run mistral`
- **API Health**: Visit `http://localhost:8000/health`

---
**Note**: LangSmith functionality may be limited in a strictly offline environment. Focus on LangChain and LangGraph for core logic.
