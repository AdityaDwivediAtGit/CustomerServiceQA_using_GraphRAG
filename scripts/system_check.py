#!/usr/bin/env python3
"""
System Check Script for RAG-KG Customer Service QA System

Validates all system components are properly installed and configured.
"""

import os
import sys
import requests
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
import ollama
from dotenv import load_dotenv

def check_ollama():
    """Check if OLLAMA is running and has required models."""
    try:
        models = ollama.list()
        required_models = ['llama2:7b-chat-q4_0', 'nomic-embed-text:latest', 'mistral:7b-instruct-q4_0']
        available = [m['name'] for m in models['models']]
        return all(model in available for model in required_models)
    except Exception as e:
        print(f"OLLAMA check failed: {e}")
        return False

def check_neo4j(uri, user, password):
    """Check if Neo4j is running and accessible."""
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            result = session.run("RETURN 'Hello Neo4j' as message")
            message = result.single()['message']
            return message == 'Hello Neo4j'
    except Exception as e:
        print(f"Neo4j check failed: {e}")
        return False
    finally:
        try:
            driver.close()
        except:
            pass

def check_qdrant(url):
    """Check if Qdrant is running and accessible."""
    try:
        response = requests.get(f"{url}/", timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"Qdrant check failed: {e}")
        return False

def main():
    """Main system check function."""
    load_dotenv()

    print("=== RAG-KG System Check ===\n")

    checks = {
        'OLLAMA': check_ollama(),
        'Neo4j': check_neo4j(
            os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            os.getenv('NEO4J_USER', 'neo4j'),
            os.getenv('NEO4J_PASSWORD', 'password')
        ),
        'Qdrant': check_qdrant(os.getenv('QDRANT_URL', 'http://localhost:6333'))
    }

    print("Component Status:")
    for component, status in checks.items():
        status_icon = "✓" if status else "✗"
        print(f"  {component}: {status_icon}")

    all_pass = all(checks.values())

    print(f"\nOverall Status: {'PASS' if all_pass else 'FAIL'}")

    if not all_pass:
        print("\nFailed components need attention:")
        for component, status in checks.items():
            if not status:
                print(f"  - {component}: Check installation and configuration")

        print("\nSee INSTALLATION.md and TROUBLESHOOTING.md for help")

    sys.exit(0 if all_pass else 1)

if __name__ == "__main__":
    main()