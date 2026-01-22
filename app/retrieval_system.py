#!/usr/bin/env python3
"""
Retrieval System for RAG-KG Customer Service QA System

Handles graph traversal and vector similarity search for retrieving relevant information.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
import ollama
from dotenv import load_dotenv
import os

load_dotenv()
logger = logging.getLogger(__name__)

class RetrievalSystem:
    """Handles retrieval from Neo4j graph and Qdrant vector database"""

    def __init__(self):
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
        self.qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.collection_name = os.getenv("COLLECTION_NAME", "tickets")

        self.neo4j_driver = None
        self.qdrant_client = None

    def initialize(self):
        """Initialize database connections"""
        try:
            self.neo4j_driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )
            logger.info("Neo4j connection initialized")
        except Exception as e:
            logger.error(f"Neo4j connection failed: {str(e)}")
            raise

        try:
            self.qdrant_client = QdrantClient(url=self.qdrant_url)
            logger.info("Qdrant connection initialized")
        except Exception as e:
            logger.error(f"Qdrant connection failed: {str(e)}")
            raise

    def close(self):
        """Close database connections"""
        if self.neo4j_driver:
            self.neo4j_driver.close()
        logger.info("Connections closed")

    def check_neo4j(self) -> bool:
        """Check Neo4j connection"""
        if not self.neo4j_driver:
            return False
        try:
            with self.neo4j_driver.session() as session:
                result = session.run("RETURN 'Neo4j OK' as status")
                return result.single()['status'] == 'Neo4j OK'
        except Exception:
            return False

    def check_qdrant(self) -> bool:
        """Check Qdrant connection"""
        if not self.qdrant_client:
            return False
        try:
            response = self.qdrant_client.get_collections()
            return bool(response.collections)
        except Exception:
            return False

    def retrieve_from_graph(self, entities: Dict[str, List[str]], intent: str,
                          max_hops: int = 2) -> List[Dict[str, Any]]:
        """Retrieve relevant information from knowledge graph"""
        if not self.neo4j_driver:
            return []

        results = []

        try:
            with self.neo4j_driver.session() as session:
                # Build Cypher query based on entities and intent
                query_parts = []
                params = {}

                # Search for issues with matching entities
                if entities.get('product'):
                    products = entities['product']
                    query_parts.append("ANY(product IN $products WHERE product IN i.product)")
                    params['products'] = products

                if entities.get('error'):
                    errors = entities['error']
                    query_parts.append("ANY(error IN $errors WHERE error IN i.tags)")
                    params['errors'] = errors

                # Base query
                where_clause = " AND ".join(query_parts) if query_parts else "true"

                cypher = f"""
                MATCH (i:Issue)
                WHERE {where_clause}
                OPTIONAL MATCH (i)-[r*1..{max_hops}]-(related)
                RETURN i, collect(DISTINCT related) as related_nodes,
                       collect(DISTINCT type(head(r))) as relationship_types
                LIMIT 10
                """

                result = session.run(cypher, params)

                for record in result:
                    issue = record['i']
                    related_nodes = record['related_nodes']

                    # Format issue data
                    issue_data = {
                        'ticket_id': issue.get('id', ''),
                        'title': issue.get('title', ''),
                        'description': issue.get('description', ''),
                        'status': issue.get('status', ''),
                        'priority': issue.get('priority', ''),
                        'node_type': 'Issue',
                        'score': 0.9,  # High confidence for direct matches
                        'source': 'graph'
                    }
                    results.append(issue_data)

                    # Add related nodes
                    for node in related_nodes[:5]:  # Limit related nodes
                        if hasattr(node, 'labels') and node.labels:
                            node_type = list(node.labels)[0]
                            node_data = {
                                'ticket_id': issue.get('id', ''),
                                'node_type': node_type,
                                'text': str(dict(node)) if hasattr(node, 'items') else str(node),
                                'score': 0.7,
                                'source': 'graph_related'
                            }
                            results.append(node_data)

        except Exception as e:
            logger.error(f"Graph retrieval failed: {str(e)}")

        return results

    def retrieve_from_vectors(self, query: str, entities: Dict[str, List[str]],
                            limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve relevant information using vector similarity"""
        if not self.qdrant_client:
            return []

        try:
            # Generate embedding for the query
            embedding = ollama.embeddings(
                model=os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
                prompt=query
            )['embedding']

            # Search for similar vectors
            search_result = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=embedding,
                limit=limit,
                score_threshold=0.3  # Minimum similarity
            )

            results = []
            for hit in search_result:
                result = {
                    'ticket_id': hit.payload.get('ticket_id', ''),
                    'node_type': hit.payload.get('node_type', ''),
                    'text': hit.payload.get('text', ''),
                    'score': hit.score,
                    'source': 'vector',
                    'metadata': {
                        'vector_id': hit.id,
                        'node_id': hit.payload.get('node_id', '')
                    }
                }
                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Vector retrieval failed: {str(e)}")
            return []

    def retrieve(self, processed_query: Dict[str, Any],
                options: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Main retrieval method combining graph and vector search"""
        options = options or {}
        max_sources = options.get('max_sources', 10)
        include_similar = options.get('include_similar', True)
        confidence_threshold = options.get('confidence_threshold', 0.5)

        entities = processed_query.get('entities', {})
        intent = processed_query.get('intent', 'general_inquiry')
        original_query = processed_query.get('original_query', '')

        logger.info(f"Retrieving for intent: {intent}, entities: {len(entities)}")

        # Retrieve from both sources
        graph_results = self.retrieve_from_graph(entities, intent)
        vector_results = self.retrieve_from_vectors(original_query, entities)

        # Combine and deduplicate results
        all_results = graph_results + vector_results

        # Remove duplicates based on ticket_id and node_type
        seen = set()
        unique_results = []
        for result in all_results:
            key = (result.get('ticket_id', ''), result.get('node_type', ''), result.get('text', '')[:100])
            if key not in seen and result.get('score', 0) >= confidence_threshold:
                seen.add(key)
                unique_results.append(result)

        # Sort by score and limit results
        unique_results.sort(key=lambda x: x.get('score', 0), reverse=True)
        final_results = unique_results[:max_sources]

        logger.info(f"Retrieved {len(final_results)} sources from {len(graph_results)} graph + {len(vector_results)} vector results")

        return final_results

    def get_stats(self) -> Dict[str, int]:
        """Get system statistics"""
        stats = {
            'nodes': 0,
            'relationships': 0,
            'vectors': 0,
            'tickets': 0
        }

        # Neo4j stats
        if self.neo4j_driver:
            try:
                with self.neo4j_driver.session() as session:
                    result = session.run("MATCH (n) RETURN count(n) as nodes")
                    stats['nodes'] = result.single()['nodes']

                    result = session.run("MATCH ()-[r]->() RETURN count(r) as relationships")
                    stats['relationships'] = result.single()['relationships']

                    result = session.run("MATCH (i:Issue) RETURN count(i) as tickets")
                    stats['tickets'] = result.single()['tickets']
            except Exception as e:
                logger.error(f"Neo4j stats failed: {str(e)}")

        # Qdrant stats
        if self.qdrant_client:
            try:
                # This might fail due to client version issues, but we'll try
                info = self.qdrant_client.get_collection(self.collection_name)
                stats['vectors'] = getattr(info, 'points_count', 0)
            except Exception:
                # Fallback: try to count via scroll
                try:
                    result = self.qdrant_client.scroll(
                        collection_name=self.collection_name,
                        limit=1000
                    )
                    stats['vectors'] = len(result[0]) if result else 0
                except Exception as e:
                    logger.error(f"Qdrant stats failed: {str(e)}")

        return stats