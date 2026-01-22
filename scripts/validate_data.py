#!/usr/bin/env python3
"""
Data Validation Script for RAG-KG Customer Service QA System

Validates graph structure, embedding completeness, and data consistency
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
import argparse
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataValidator:
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str,
                 qdrant_url: str, collection_name: str):
        self.neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.qdrant_client = QdrantClient(url=qdrant_url)
        self.collection_name = collection_name

    def close(self):
        self.neo4j_driver.close()

    def validate_graph_structure(self) -> Dict[str, Any]:
        """Validate Neo4j graph structure and completeness."""

        results = {
            'node_counts': {},
            'relationship_counts': {},
            'issues': []
        }

        with self.neo4j_driver.session() as session:
            # Count different node types
            node_types = ['Issue', 'Description', 'Comment', 'Resolution', 'Entity', 'Tag']
            for node_type in node_types:
                count = session.run(f"MATCH (n:{node_type}) RETURN count(n) as count").single()['count']
                results['node_counts'][node_type] = count

            # Count relationship types
            rel_types = ['HAS_DESCRIPTION', 'HAS_COMMENT', 'HAS_RESOLUTION',
                        'MENTIONS_ENTITY', 'HAS_TAG', 'SIMILAR_TO', 'RELATED_TO',
                        'REFERENCES', 'DEPENDS_ON']
            for rel_type in rel_types:
                count = session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count").single()['count']
                results['relationship_counts'][rel_type] = count

            # Check for orphaned nodes
            orphaned_issues = session.run("""
                MATCH (i:Issue)
                WHERE NOT (i)--()
                RETURN count(i) as count
                """).single()['count']

            if orphaned_issues > 0:
                results['issues'].append(f"Found {orphaned_issues} orphaned Issue nodes")

            # Check for issues without descriptions
            issues_without_desc = session.run("""
                MATCH (i:Issue)
                WHERE NOT (i)-[:HAS_DESCRIPTION]->()
                RETURN count(i) as count
                """).single()['count']

            if issues_without_desc > 0:
                results['issues'].append(f"Found {issues_without_desc} issues without descriptions")

            # Check relationship consistency
            inconsistent_rels = session.run("""
                MATCH (i:Issue)-[r:HAS_COMMENT]->(c:Comment)
                WITH i, count(c) as comment_count
                WHERE comment_count > 10
                RETURN count(i) as count
                """).single()['count']

            if inconsistent_rels > 0:
                results['issues'].append(f"Found issues with unusually high comment counts")

        return results

    def validate_embeddings(self) -> Dict[str, Any]:
        """Validate Qdrant embeddings completeness."""

        results = {
            'collection_exists': False,
            'vector_count': 0,
            'payload_fields': [],
            'issues': []
        }

        try:
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            results['collection_exists'] = True
            results['vector_count'] = collection_info.points_count

            # Get sample points to check payload structure
            if results['vector_count'] > 0:
                sample_points = self.qdrant_client.scroll(
                    collection_name=self.collection_name,
                    limit=5
                )[0]

                if sample_points:
                    payload = sample_points[0].payload
                    results['payload_fields'] = list(payload.keys())

                    # Check for required fields
                    required_fields = ['ticket_id', 'node_type', 'node_id', 'text']
                    missing_fields = [field for field in required_fields if field not in results['payload_fields']]
                    if missing_fields:
                        results['issues'].append(f"Missing payload fields: {missing_fields}")

        except Exception as e:
            results['issues'].append(f"Qdrant validation error: {str(e)}")

        return results

    def validate_data_consistency(self, processed_dir: Path) -> Dict[str, Any]:
        """Validate consistency between processed data and graph/embeddings."""

        results = {
            'processed_files': 0,
            'graph_coverage': 0,
            'embedding_coverage': 0,
            'issues': []
        }

        # Count processed files
        if processed_dir.exists():
            json_files = list(processed_dir.glob("*.json"))
            results['processed_files'] = len(json_files)

            # Sample a few files to check consistency
            sample_files = json_files[:5] if len(json_files) > 5 else json_files

            with self.neo4j_driver.session() as session:
                graph_ticket_ids = set()
                for record in session.run("MATCH (i:Issue) RETURN i.id as ticket_id"):
                    graph_ticket_ids.add(record['ticket_id'])

                file_ticket_ids = set()
                for filepath in sample_files:
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            ticket = json.load(f)
                            file_ticket_ids.add(ticket['ticket_id'])
                    except Exception as e:
                        results['issues'].append(f"Failed to read {filepath}: {str(e)}")

                # Check coverage
                coverage = len(file_ticket_ids & graph_ticket_ids) / len(file_ticket_ids) if file_ticket_ids else 0
                results['graph_coverage'] = coverage

                if coverage < 1.0:
                    missing = file_ticket_ids - graph_ticket_ids
                    results['issues'].append(f"Tickets missing from graph: {missing}")

        return results

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""

        logger.info("Starting data validation...")

        report = {
            'timestamp': str(Path(__file__).stat().st_mtime),
            'graph_validation': self.validate_graph_structure(),
            'embedding_validation': self.validate_embeddings(),
            'consistency_validation': {},
            'overall_status': 'PASS',
            'summary': {}
        }

        # Calculate summary statistics
        total_nodes = sum(report['graph_validation']['node_counts'].values())
        total_relationships = sum(report['graph_validation']['relationship_counts'].values())

        report['summary'] = {
            'total_nodes': total_nodes,
            'total_relationships': total_relationships,
            'total_vectors': report['embedding_validation']['vector_count'],
            'graph_issues': len(report['graph_validation']['issues']),
            'embedding_issues': len(report['embedding_validation']['issues'])
        }

        # Determine overall status
        all_issues = (report['graph_validation']['issues'] +
                     report['embedding_validation']['issues'])

        if all_issues:
            report['overall_status'] = 'WARN' if len(all_issues) < 5 else 'FAIL'

        logger.info("Validation complete")
        return report

def main():
    parser = argparse.ArgumentParser(description="Validate data pipeline")
    parser.add_argument("--graph_uri", type=str, default="bolt://localhost:7687",
                       help="Neo4j database URI")
    parser.add_argument("--graph_user", type=str, default="neo4j",
                       help="Neo4j username")
    parser.add_argument("--graph_password", type=str, default="password",
                       help="Neo4j password")
    parser.add_argument("--vector_url", type=str, default="http://localhost:6333",
                       help="Qdrant server URL")
    parser.add_argument("--collection", type=str, default="tickets",
                       help="Qdrant collection name")
    parser.add_argument("--processed_dir", type=str, default="data/processed",
                       help="Directory with processed ticket data")
    parser.add_argument("--output_file", type=str, default="validation_report.json",
                       help="Output file for validation report")
    args = parser.parse_args()

    # Initialize validator
    validator = DataValidator(
        args.graph_uri, args.graph_user, args.graph_password,
        args.vector_url, args.collection
    )

    try:
        # Generate validation report
        report = validator.generate_report()

        # Add consistency validation
        processed_dir = Path(args.processed_dir)
        report['consistency_validation'] = validator.validate_data_consistency(processed_dir)

        # Save report
        with open(args.output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        # Print summary
        print("\n=== VALIDATION REPORT ===")
        print(f"Overall Status: {report['overall_status']}")
        print(f"Total Nodes: {report['summary']['total_nodes']}")
        print(f"Total Relationships: {report['summary']['total_relationships']}")
        print(f"Total Vectors: {report['summary']['total_vectors']}")

        if report['graph_validation']['issues']:
            print(f"\nGraph Issues ({len(report['graph_validation']['issues'])}):")
            for issue in report['graph_validation']['issues']:
                print(f"  - {issue}")

        if report['embedding_validation']['issues']:
            print(f"\nEmbedding Issues ({len(report['embedding_validation']['issues'])}):")
            for issue in report['embedding_validation']['issues']:
                print(f"  - {issue}")

        print(f"\nDetailed report saved to: {args.output_file}")

    finally:
        validator.close()

if __name__ == "__main__":
    main()