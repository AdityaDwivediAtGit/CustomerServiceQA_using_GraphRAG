#!/usr/bin/env python3
"""
Embedding Generation Script for RAG-KG Customer Service QA System

Generates vector embeddings for graph nodes using OLLAMA models and stores in Qdrant
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple
import argparse
import ollama
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    def __init__(self, model_name: str, qdrant_client: QdrantClient, collection_name: str):
        self.model_name = model_name
        self.qdrant = qdrant_client
        self.collection_name = collection_name

    def create_collection(self, vector_size: int = 768):
        """Create Qdrant collection if it doesn't exist."""

        try:
            self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
            )
            logger.info(f"Created collection '{self.collection_name}' with vector size {vector_size}")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info(f"Collection '{self.collection_name}' already exists")
            else:
                raise e

    def generate_text_embedding(self, text: str) -> List[float]:
        """Generate embedding for a text string using OLLAMA."""

        try:
            response = ollama.embeddings(
                model=self.model_name,
                prompt=text
            )
            return response['embedding']
        except Exception as e:
            logger.error(f"Failed to generate embedding for text: {text[:50]}...: {str(e)}")
            return None

    def create_node_text(self, ticket_data: Dict[str, Any], node_type: str, node_id: str) -> str:
        """Create text representation for a graph node."""

        if node_type == 'Issue':
            return f"Title: {ticket_data.get('title', '')}. Description: {ticket_data.get('description', '')}. Status: {ticket_data.get('status', '')}. Priority: {ticket_data.get('priority', '')}"

        elif node_type == 'Comment':
            # Find the specific comment
            comment_id = node_id.split('_comment_')[-1]
            comments = ticket_data.get('comments', [])
            if comment_id.isdigit():
                idx = int(comment_id)
                if idx < len(comments):
                    comment = comments[idx]
                    return f"Comment by {comment.get('author', '')}: {comment.get('text', '')}"
            return f"Comment: {node_id}"

        elif node_type == 'Description':
            return f"Description: {ticket_data.get('description', '')}"

        elif node_type == 'Resolution':
            return f"Resolution: {ticket_data.get('resolution', '')}"

        elif node_type == 'Entity':
            # Extract entity info from node_id or use generic
            return f"Entity: {node_id}"

        elif node_type == 'Tag':
            return f"Tag: {node_id}"

        else:
            return f"{node_type}: {node_id}"

    def process_ticket_embeddings(self, ticket_data: Dict[str, Any]) -> List[PointStruct]:
        """Generate embeddings for all nodes in a ticket."""

        ticket_id = ticket_data['ticket_id']
        points = []

        # Issue node
        issue_text = self.create_node_text(ticket_data, 'Issue', ticket_id)
        issue_embedding = self.generate_text_embedding(issue_text)
        if issue_embedding:
            points.append(PointStruct(
                id=hash(f"{ticket_id}_issue") % 2**63,  # Convert to positive integer
                vector=issue_embedding,
                payload={
                    'ticket_id': ticket_id,
                    'node_type': 'Issue',
                    'node_id': ticket_id,
                    'text': issue_text
                }
            ))

        # Description node
        if ticket_data.get('description'):
            desc_text = self.create_node_text(ticket_data, 'Description', f"{ticket_id}_desc")
            desc_embedding = self.generate_text_embedding(desc_text)
            if desc_embedding:
                points.append(PointStruct(
                    id=hash(f"{ticket_id}_desc") % 2**63,
                    vector=desc_embedding,
                    payload={
                        'ticket_id': ticket_id,
                        'node_type': 'Description',
                        'node_id': f"{ticket_id}_desc",
                        'text': desc_text
                    }
                ))

        # Comment nodes
        for idx, comment in enumerate(ticket_data.get('comments', [])):
            comment_text = self.create_node_text(ticket_data, 'Comment', f"{ticket_id}_comment_{idx}")
            comment_embedding = self.generate_text_embedding(comment_text)
            if comment_embedding:
                points.append(PointStruct(
                    id=hash(f"{ticket_id}_comment_{idx}") % 2**63,
                    vector=comment_embedding,
                    payload={
                        'ticket_id': ticket_id,
                        'node_type': 'Comment',
                        'node_id': f"{ticket_id}_comment_{idx}",
                        'text': comment_text,
                        'author': comment.get('author', ''),
                        'timestamp': comment.get('timestamp', '')
                    }
                ))

        # Resolution node
        if ticket_data.get('resolution'):
            res_text = self.create_node_text(ticket_data, 'Resolution', f"{ticket_id}_res")
            res_embedding = self.generate_text_embedding(res_text)
            if res_embedding:
                points.append(PointStruct(
                    id=hash(f"{ticket_id}_res") % 2**63,
                    vector=res_embedding,
                    payload={
                        'ticket_id': ticket_id,
                        'node_type': 'Resolution',
                        'node_id': f"{ticket_id}_res",
                        'text': res_text
                    }
                ))

        # Entity nodes
        entities = ticket_data.get('entities', {})
        for entity_type, entity_list in entities.items():
            for entity in entity_list:
                entity_id = f"{ticket_id}_entity_{entity_type}_{entity}".replace(' ', '_').lower()
                entity_text = self.create_node_text(ticket_data, 'Entity', entity)
                entity_embedding = self.generate_text_embedding(entity_text)
                if entity_embedding:
                    points.append(PointStruct(
                        id=hash(entity_id) % 2**63,
                        vector=entity_embedding,
                        payload={
                            'ticket_id': ticket_id,
                            'node_type': 'Entity',
                            'node_id': entity_id,
                            'entity_type': entity_type,
                            'entity_value': entity,
                            'text': entity_text
                        }
                    ))

        # Tag nodes
        for tag in ticket_data.get('tags', []):
            tag_id = f"{ticket_id}_tag_{tag}".replace(' ', '_').lower()
            tag_text = self.create_node_text(ticket_data, 'Tag', tag)
            tag_embedding = self.generate_text_embedding(tag_text)
            if tag_embedding:
                points.append(PointStruct(
                    id=hash(tag_id) % 2**63,
                    vector=tag_embedding,
                    payload={
                        'ticket_id': ticket_id,
                        'node_type': 'Tag',
                        'node_id': tag_id,
                        'tag_name': tag,
                        'text': tag_text
                    }
                ))

        return points

def process_ticket_batch(tickets: List[Dict[str, Any]], generator: EmbeddingGenerator,
                        batch_size: int) -> Tuple[int, int]:
    """Process a batch of tickets for embedding generation."""

    all_points = []
    processed_tickets = 0
    total_embeddings = 0

    for ticket in tickets:
        try:
            points = generator.process_ticket_embeddings(ticket)
            all_points.extend(points)
            processed_tickets += 1
            total_embeddings += len(points)

            # Upload batch to Qdrant
            if len(all_points) >= batch_size:
                generator.qdrant.upsert(
                    collection_name=generator.collection_name,
                    points=all_points
                )
                logger.info(f"Uploaded {len(all_points)} embeddings to Qdrant")
                all_points = []

        except Exception as e:
            logger.error(f"Failed to process ticket {ticket['ticket_id']}: {str(e)}")

    # Upload remaining points
    if all_points:
        generator.qdrant.upsert(
            collection_name=generator.collection_name,
            points=all_points
        )
        logger.info(f"Uploaded final {len(all_points)} embeddings to Qdrant")

    return processed_tickets, total_embeddings

def main():
    parser = argparse.ArgumentParser(description="Generate embeddings for graph nodes")
    parser.add_argument("--input_dir", type=str, default="data/processed",
                       help="Input directory with parsed tickets")
    parser.add_argument("--qdrant_url", type=str, default="http://localhost:6333",
                       help="Qdrant server URL")
    parser.add_argument("--collection", type=str, default="tickets",
                       help="Qdrant collection name")
    parser.add_argument("--model", type=str, default="nomic-embed-text",
                       help="OLLAMA embedding model name")
    parser.add_argument("--batch_size", type=int, default=10,
                       help="Batch size for processing and uploading")
    parser.add_argument("--max_workers", type=int, default=2,
                       help="Maximum parallel workers")
    args = parser.parse_args()

    # Load processed tickets
    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        logger.error(f"Input directory {input_dir} does not exist")
        return

    ticket_files = list(input_dir.glob("*.json"))
    if not ticket_files:
        logger.error(f"No JSON files found in {input_dir}")
        return

    logger.info(f"Loading {len(ticket_files)} processed tickets...")

    all_tickets = []
    for filepath in ticket_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                ticket = json.load(f)
                all_tickets.append(ticket)
        except Exception as e:
            logger.error(f"Failed to load {filepath}: {str(e)}")

    if not all_tickets:
        logger.error("No valid tickets loaded")
        return

    logger.info(f"Loaded {len(all_tickets)} tickets")

    # Initialize Qdrant client with longer timeout
    qdrant_client = QdrantClient(url=args.qdrant_url, timeout=60)

    # Initialize embedding generator
    generator = EmbeddingGenerator(args.model, qdrant_client, args.collection)

    # Create collection
    generator.create_collection()

    start_time = time.time()
    total_processed = 0
    total_embeddings = 0

    # Process in batches
    batch_size = args.batch_size
    for i in range(0, len(all_tickets), batch_size):
        batch = all_tickets[i:i + batch_size]
        processed, embeddings = process_ticket_batch(batch, generator, args.batch_size)
        total_processed += processed
        total_embeddings += embeddings

        logger.info(f"Processed {total_processed}/{len(all_tickets)} tickets, {total_embeddings} embeddings generated")

    elapsed = time.time() - start_time

    # Get final collection stats
    try:
        collection_info = qdrant_client.get_collection(args.collection)
        vector_count = collection_info.vectors_count
        logger.info(f"Final collection stats: {vector_count} vectors")
    except Exception as e:
        logger.error(f"Failed to get collection stats: {str(e)}")

    logger.info("Embedding generation complete!")
    logger.info(f"Time elapsed: {elapsed:.2f} seconds")
    logger.info(f"Tickets processed: {total_processed}")
    logger.info(f"Embeddings generated: {total_embeddings}")

if __name__ == "__main__":
    main()