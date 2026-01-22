#!/usr/bin/env python3
"""
Knowledge Graph Construction Script for RAG-KG Customer Service QA System

Builds dual-level knowledge graph: intra-issue trees + inter-issue connections
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple
import argparse
from neo4j import GraphDatabase
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GraphBuilder:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def clear_database(self):
        """Clear all nodes and relationships."""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            logger.info("Database cleared")

    def create_intra_issue_tree(self, ticket_data: Dict[str, Any]) -> None:
        """Create hierarchical tree structure for a single ticket."""

        ticket_id = ticket_data['ticket_id']

        with self.driver.session() as session:
            # Create root issue node
            session.run("""
                CREATE (i:Issue {
                    id: $id,
                    title: $title,
                    description: $description,
                    status: $status,
                    priority: $priority,
                    created_date: $created_date,
                    product: $product
                })
                """,
                id=ticket_id,
                title=ticket_data.get('title', ''),
                description=ticket_data.get('description', ''),
                status=ticket_data.get('status', ''),
                priority=ticket_data.get('priority', ''),
                created_date=ticket_data.get('created_date', ''),
                product=ticket_data.get('product', '')
            )

            # Create description node
            if ticket_data.get('description'):
                session.run("""
                    MATCH (i:Issue {id: $ticket_id})
                    CREATE (i)-[:HAS_DESCRIPTION]->(d:Description {
                        text: $text,
                        type: 'description'
                    })
                    """,
                    ticket_id=ticket_id,
                    text=ticket_data['description']
                )

            # Create comment nodes
            for idx, comment in enumerate(ticket_data.get('comments', [])):
                session.run("""
                    MATCH (i:Issue {id: $ticket_id})
                    CREATE (i)-[:HAS_COMMENT]->(c:Comment {
                        id: $comment_id,
                        author: $author,
                        text: $text,
                        timestamp: $timestamp
                    })
                    """,
                    ticket_id=ticket_id,
                    comment_id=f"{ticket_id}_comment_{idx}",
                    author=comment.get('author', ''),
                    text=comment.get('text', ''),
                    timestamp=comment.get('timestamp', '')
                )

            # Create resolution node
            if ticket_data.get('resolution'):
                session.run("""
                    MATCH (i:Issue {id: $ticket_id})
                    CREATE (i)-[:HAS_RESOLUTION]->(r:Resolution {
                        text: $text,
                        type: 'resolution'
                    })
                    """,
                    ticket_id=ticket_id,
                    text=ticket_data['resolution']
                )

            # Create entity nodes
            entities = ticket_data.get('entities', {})
            for entity_type, entity_list in entities.items():
                for entity in entity_list:
                    session.run("""
                        MATCH (i:Issue {id: $ticket_id})
                        MERGE (e:Entity {
                            type: $entity_type,
                            value: $value
                        })
                        CREATE (i)-[:MENTIONS_ENTITY]->(e)
                        """,
                        ticket_id=ticket_id,
                        entity_type=entity_type,
                        value=entity.lower()
                    )

            # Create tag nodes
            for tag in ticket_data.get('tags', []):
                session.run("""
                    MATCH (i:Issue {id: $ticket_id})
                    MERGE (t:Tag {name: $tag})
                    CREATE (i)-[:HAS_TAG]->(t)
                    """,
                    ticket_id=ticket_id,
                    tag=tag
                )

    def create_inter_issue_connections(self, all_tickets: List[Dict[str, Any]], threshold: float = 0.85) -> None:
        """
        Create connections between different tickets.
        Implements SIGIR '24 Implicit Connections (Eimp) and Explicit Links (Eexp).
        """

        logger.info("Creating inter-issue connections...")

        # 1. Generate embeddings for all ticket titles for Eimp (Implicit connections)
        titles = [t.get('title', '') for t in all_tickets]
        logger.info(f"Generating embeddings for {len(titles)} titles...")
        
        embeddings = []
        for title in titles:
            try:
                emb = ollama.embeddings(
                    model=os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
                    prompt=title
                )['embedding']
                embeddings.append(emb)
            except Exception as e:
                logger.error(f"Failed to generate title embedding: {str(e)}")
                embeddings.append(None)

        with self.driver.session() as session:
            # 2. SIGIR '24: Implicit Connections (Eimp) based on title similarity
            import numpy as np
            def cosine_sim(a, b):
                if a is None or b is None: return 0
                return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

            for i in range(len(all_tickets)):
                for j in range(i + 1, len(all_tickets)):
                    sim = cosine_sim(embeddings[i], embeddings[j])
                    if sim >= threshold:
                        session.run("""
                            MATCH (i1:Issue {id: $id1}), (i2:Issue {id: $id2})
                            MERGE (i1)-[:SIMILAR_TO {weight: $weight, type: 'semantic_title'}]-(i2)
                            """,
                            id1=all_tickets[i]['ticket_id'],
                            id2=all_tickets[j]['ticket_id'],
                            weight=float(sim)
                        )

            # 3. SIGIR '24: Explicit Connections (Eexp) 
            # (Handled by REFERENCES and existing tag logic below)

            # Create REFERENCES relationships based on explicit mentions
            for ticket in all_tickets:
                ticket_id = ticket['ticket_id']
                references = ticket.get('entities', {}).get('references', [])

                for ref in references:
                    # Check if referenced ticket exists
                    result = session.run("""
                        MATCH (i:Issue {id: $ref_id})
                        RETURN count(i) as exists
                        """,
                        ref_id=ref
                    ).single()

                    if result and result['exists'] > 0:
                        session.run("""
                            MATCH (i1:Issue {id: $ticket_id}), (i2:Issue {id: $ref_id})
                            CREATE (i1)-[:REFERENCES]->(i2)
                            """,
                            ticket_id=ticket_id,
                            ref_id=ref
                        )

            # Create DEPENDS_ON relationships based on resolution patterns
            # This is a simplified version - in practice, you'd use more sophisticated logic
            resolution_keywords = {
                'prerequisite': ['depends', 'requires', 'before', 'first'],
                'blocking': ['blocks', 'prevents', 'stops'],
                'related': ['related', 'similar', 'same']
            }

            for ticket in all_tickets:
                ticket_id = ticket['ticket_id']
                resolution_text = (ticket.get('resolution') or '').lower()

                for rel_type, keywords in resolution_keywords.items():
                    if any(keyword in resolution_text for keyword in keywords):
                        # Find tickets with similar issues
                        similar_tickets = session.run("""
                            MATCH (i1:Issue {id: $ticket_id})-[:SIMILAR_TO]-(i2:Issue)
                            WHERE i1 <> i2
                            RETURN i2.id as similar_id
                            LIMIT 3
                            """,
                            ticket_id=ticket_id
                        )

                        for record in similar_tickets:
                            session.run("""
                                MATCH (i1:Issue {id: $ticket_id}), (i2:Issue {id: $similar_id})
                                CREATE (i1)-[:DEPENDS_ON {type: $rel_type}]->(i2)
                                """,
                                ticket_id=ticket_id,
                                similar_id=record['similar_id'],
                                rel_type=rel_type
                            )

    def get_graph_stats(self) -> Dict[str, int]:
        """Get basic graph statistics."""

        with self.driver.session() as session:
            node_count = session.run("MATCH (n) RETURN count(n) as count").single()['count']
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()['count']

            issue_count = session.run("MATCH (n:Issue) RETURN count(n) as count").single()['count']
            entity_count = session.run("MATCH (n:Entity) RETURN count(n) as count").single()['count']

            return {
                'total_nodes': node_count,
                'total_relationships': rel_count,
                'issues': issue_count,
                'entities': entity_count
            }

def process_ticket_batch(tickets: List[Dict[str, Any]], builder: GraphBuilder, phase: str) -> int:
    """Process a batch of tickets for graph construction."""

    processed = 0
    for ticket in tickets:
        try:
            if phase == 'intra_issue':
                builder.create_intra_issue_tree(ticket)
            processed += 1
        except Exception as e:
            logger.error(f"Failed to process ticket {ticket['ticket_id']}: {str(e)}")

    return processed

def main():
    parser = argparse.ArgumentParser(description="Build knowledge graph")
    parser.add_argument("--phase", choices=['intra_issue', 'inter_issue', 'full'],
                       default='full', help="Graph construction phase")
    parser.add_argument("--input_dir", type=str, default="data/processed",
                       help="Input directory with parsed tickets")
    parser.add_argument("--neo4j_uri", type=str, default="bolt://localhost:7687",
                       help="Neo4j database URI")
    parser.add_argument("--neo4j_user", type=str, default="neo4j",
                       help="Neo4j username")
    parser.add_argument("--neo4j_password", type=str, default="password",
                       help="Neo4j password")
    parser.add_argument("--batch_size", type=int, default=10,
                       help="Batch size for processing")
    parser.add_argument("--clear_db", action='store_true',
                       help="Clear database before building")
    args = parser.parse_args()

    # Load all processed tickets
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

    # Initialize graph builder
    builder = GraphBuilder(args.neo4j_uri, args.neo4j_user, args.neo4j_password)

    try:
        if args.clear_db:
            logger.info("Clearing database...")
            builder.clear_database()

        start_time = time.time()

        if args.phase in ['intra_issue', 'full']:
            logger.info("Building intra-issue trees...")

            # Process in batches
            batch_size = args.batch_size
            total_processed = 0

            for i in range(0, len(all_tickets), batch_size):
                batch = all_tickets[i:i + batch_size]
                processed = process_ticket_batch(batch, builder, 'intra_issue')
                total_processed += processed

                logger.info(f"Processed {total_processed}/{len(all_tickets)} tickets")

            logger.info("Intra-issue tree construction complete")

        if args.phase in ['inter_issue', 'full']:
            logger.info("Building inter-issue connections...")
            builder.create_inter_issue_connections(all_tickets)
            logger.info("Inter-issue connection construction complete")

        # Get final statistics
        stats = builder.get_graph_stats()
        elapsed = time.time() - start_time

        logger.info("Graph construction complete!")
        logger.info(f"Time elapsed: {elapsed:.2f} seconds")
        logger.info("Graph Statistics:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")

    finally:
        builder.close()

if __name__ == "__main__":
    main()