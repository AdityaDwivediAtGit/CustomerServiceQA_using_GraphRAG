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
        """
        Main retrieval method combining graph and vector search.
        Implements SIGIR '24 Scoring (STi): Sum contributions from nodes matching query categories.
        """
        options = options or {}
        max_sources = options.get('max_sources', 10)
        confidence_threshold = options.get('confidence_threshold', 0.5)

        section_value_map = processed_query.get('entities', {})
        original_query = processed_query.get('original_query', '')
        
        # Determine number of sources from options
        k = options.get('max_sources', 5)

        # 1. EBR-based Ticket Identification (SIGIR '24 Method)
        # Calculate score STi for each ticket by summing similarities of its nodes to query entities
        ticket_scores = {} # Map ticket_id -> score
        # Store all contributing nodes for each ticket
        ticket_contributions = {} # Map ticket_id -> List[node]

        for section, value in section_value_map.items():
            if section == 'context': continue
            
            # Retrieve vector candidates for this specific section-value pair
            node_candidates = self.retrieve_from_vectors(value, {section: [value]}, limit=5)
            
            for node in node_candidates:
                tid = node['ticket_id']
                score = node['score']
                
                # SIGIR '24: STi = sum over (k,v) in P [ sum over n in Ti [ I(n.sec=k) * cos(v,n) ] ]
                ticket_scores[tid] = ticket_scores.get(tid, 0) + score
                if tid not in ticket_contributions:
                    ticket_contributions[tid] = []
                ticket_contributions[tid].append(node)

        # 2. Convert to list and sort by STi score
        ranked_tickets = []
        for tid, score in ticket_scores.items():
            if score >= confidence_threshold:
                # Use the contribution info to build a candidate record
                ranked_tickets.append({
                    'ticket_id': tid,
                    'score': score,
                    'contributions': ticket_contributions[tid]
                })

        ranked_tickets.sort(key=lambda x: x['score'], reverse=True)
        top_k_candidates = ranked_tickets[:k]

        # 3. LLM-driven Subgraph Extraction (SIGIR '24 Step 2.1)
        # For each top candidate, extract most relevant subgraph
        final_results = []
        for candidate in top_k_candidates:
            subgraph = self._extract_subgraph(candidate['ticket_id'], original_query)
            if subgraph:
                # Combine subgraph nodes into results
                for node in subgraph:
                    node['score'] = candidate['score'] # Inherit ticket score
                    node['source'] = 'sigir24_subgraph'
                    final_results.append(node)
            else:
                # Fallback: use the contributions if subgraph extraction fails
                for node in candidate['contributions']:
                    node['source'] = 'sti_contribution_fallback'
                    final_results.append(node)

        logger.info(f"Retrieved {len(final_results)} nodes from {len(top_k_candidates)} tickets using SIGIR '24 pipeline.")
        return final_results

    def _extract_subgraph(self, ticket_id: str, query: str) -> List[Dict[str, Any]]:
        """
        Use LLM to generate a Cypher query to extract a relevant subgraph from an intra-issue tree.
        SIGIR '24 Step 2.1 implementation.
        """
        if not self.neo4j_driver:
            return []

        try:
            # 1. Ask LLM to generate Cypher query
            prompt = f"""You are a Neo4j Cypher expert.
User Query: "{query}"
Target Ticket ID: "{ticket_id}"

The graph structure for this ticket is a tree with the Issue node at the root.
Nodes types: Issue, Description, Comment, Resolution, Entity, Tag.
Relationships: HAS_DESCRIPTION, HAS_COMMENT, HAS_RESOLUTION, MENTIONS_ENTITY, HAS_TAG.

Generate a Cypher query that finds the most relevant nodes to the user query for this specific ticket.
The query MUST start with: MATCH (i:Issue {{id: "{ticket_id}"}})
The query should return nodes: i, and any related nodes (d, c, r, e, t).
Example: MATCH (i:Issue {{id: "{ticket_id}"}})-[:HAS_DESCRIPTION]->(d) RETURN d.text as text, labels(d)[0] as type

Return ONLY the Cypher query. No explanation."""

            response = ollama.chat(
                model=os.getenv("LLM_MODEL", "llama2:7b-chat-q4_0"),
                messages=[{'role': 'user', 'content': prompt}]
            )
            
            cypher = response['message']['content'].strip()
            # Basic sanitization
            cypher = cypher.replace('```cypher', '').replace('```', '').strip()
            
            if not cypher.upper().startswith("MATCH"):
                logger.warning(f"Invalid Cypher generated: {cypher}")
                return []

            # 2. Execute the Cypher query
            results = []
            with self.neo4j_driver.session() as session:
                result = session.run(cypher)
                for record in result:
                    # We expect keys like 'text', 'content', 'type' or whole nodes
                    data = dict(record)
                    # Standardize format for AnswerGenerator
                    node_data = {
                        'ticket_id': ticket_id,
                        'text': data.get('text') or data.get('content') or str(data),
                        'node_type': data.get('type') or 'SubNode'
                    }
                    results.append(node_data)
            
            return results

        except Exception as e:
            logger.error(f"Subgraph extraction failed for {ticket_id}: {str(e)}")
            return []

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