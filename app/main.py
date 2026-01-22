#!/usr/bin/env python3
"""
FastAPI Server for RAG-KG Customer Service QA System

Provides REST API endpoints for querying the knowledge graph and vector database.
"""

import os
import sys
import logging
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv

# Fix for Windows asyncio
if sys.platform == 'win32':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Import our custom modules
from app.query_processor import QueryProcessor
from app.retrieval_system import RetrievalSystem
from app.answer_generator import AnswerGenerator

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="RAG-KG Customer Service QA API",
    description="Retrieval-Augmented Generation with Knowledge Graphs for customer service",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components (lazy initialization)
query_processor = None
retrieval_system = None
answer_generator = None

# Pydantic models for request/response
class QueryRequest(BaseModel):
    question: str = Field(..., description="The customer's question")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    options: Optional[Dict[str, Any]] = Field(default=None, description="Query options")

    class Config:
        json_schema_extra = {
            "example": {
                "question": "How do I reset my password on the mobile app?",
                "context": {
                    "user_id": "user123",
                    "product": "mobile_app",
                    "priority": "normal"
                },
                "options": {
                    "max_sources": 5,
                    "include_similar": True,
                    "confidence_threshold": 0.7
                }
            }
        }

class SourceInfo(BaseModel):
    ticket_id: str
    node_type: str
    text: str
    score: float
    metadata: Optional[Dict[str, Any]] = None

class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceInfo]
    confidence: float
    processing_time: float
    metadata: Optional[Dict[str, Any]] = None

class HealthResponse(BaseModel):
    status: str
    version: str
    services: Dict[str, str]

@app.get("/test")
async def test_endpoint():
    """Simple test endpoint"""
    return {"status": "ok", "message": "Test endpoint working"}
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        services={"test": "ok"}
    )

@app.post("/api/v1/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Process a customer service question"""
    import time
    start_time = time.time()

    try:
        logger.info(f"Processing query: {request.question[:100]}...")

        # Step 1: Process query (entity extraction, intent detection)
        processed_query = query_processor.process(request.question, request.context)

        # Step 2: Retrieve relevant information
        sources = retrieval_system.retrieve(
            processed_query,
            options=request.options or {}
        )

        # Step 3: Generate answer
        answer, confidence = answer_generator.generate(
            request.question,
            sources,
            processed_query
        )

        processing_time = time.time() - start_time

        # Format sources for response
        formatted_sources = [
            SourceInfo(
                ticket_id=source.get('ticket_id', ''),
                node_type=source.get('node_type', ''),
                text=source.get('text', ''),
                score=source.get('score', 0.0),
                metadata=source.get('metadata')
            )
            for source in sources
        ]

        logger.info(".2f")

        return QueryResponse(
            answer=answer,
            sources=formatted_sources,
            confidence=confidence,
            processing_time=processing_time,
            metadata={
                "query_entities": processed_query.get('entities', []),
                "intent": processed_query.get('intent'),
                "sources_count": len(sources)
            }
        )

    except Exception as e:
        logger.error(f"Query processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")

@app.get("/api/v1/stats")
async def get_stats():
    """Get system statistics"""
    try:
        stats = retrieval_system.get_stats()
        return {
            "graph_nodes": stats.get("nodes", 0),
            "graph_relationships": stats.get("relationships", 0),
            "vector_count": stats.get("vectors", 0),
            "total_tickets": stats.get("tickets", 0)
        }
    except Exception as e:
        logger.error(f"Stats retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Stats retrieval failed")

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    global query_processor, retrieval_system, answer_generator
    logger.info("Starting RAG-KG API server...")
    try:
        # Initialize components
        logger.info("Initializing query processor...")
        query_processor = QueryProcessor()
        logger.info("Query processor initialized")

        logger.info("Initializing retrieval system...")
        retrieval_system = RetrievalSystem()
        retrieval_system.initialize()
        logger.info("Retrieval system initialized")

        logger.info("Initializing answer generator...")
        answer_generator = AnswerGenerator()
        logger.info("Answer generator initialized")

        logger.info("All components initialized successfully")
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}", exc_info=True)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down RAG-KG API server...")
    try:
        if retrieval_system:
            retrieval_system.close()
            logger.info("Connections closed")
    except Exception as e:
        logger.error(f"Shutdown error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=False,
        workers=int(os.getenv("API_WORKERS", 1))
    )