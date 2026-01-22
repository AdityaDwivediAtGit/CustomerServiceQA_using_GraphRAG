#!/usr/bin/env python3
"""
Ticket Parsing Script for RAG-KG Customer Service QA System

Implements hybrid parsing: rule-based extraction + LLM-based semantic parsing
"""

import json
import re
import os
from pathlib import Path
from typing import Dict, List, Any
import argparse
import ollama
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TicketParser:
    def __init__(self, model_name: str = None):
        self.model_name = model_name

    def parse_ticket_rule_based(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Rule-based parsing using regex patterns and heuristics."""

        parsed = ticket_data.copy()

        # Extract entities using regex
        text_content = f"{ticket_data.get('title', '')} {ticket_data.get('description', '')}"
        for comment in ticket_data.get('comments', []):
            text_content += f" {comment.get('text', '')}"

        # Product mentions
        products = []
        product_patterns = [
            r'\b(mobile app|web portal|api|desktop client|mobile website)\b',
            r'\b(ios|android|windows|mac|linux)\b',
            r'\b(browser|chrome|firefox|safari|edge)\b'
        ]
        for pattern in product_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            products.extend(matches)

        # Error codes and technical terms
        error_patterns = [
            r'\b(error|exception|failed|crash|bug)\b',
            r'\b(404|500|403|401|502)\b',
            r'\b(null|undefined|timeout|connection)\b'
        ]
        errors = []
        for pattern in error_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            errors.extend(matches)

        # User actions
        actions = []
        action_patterns = [
            r'\b(login|logout|click|submit|upload|download|search|refresh)\b',
            r'\b(clear cache|restart|update|install|uninstall)\b'
        ]
        for pattern in action_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            actions.extend(matches)

        # Extract ticket references
        references = re.findall(r'\b[A-Z]+-\d+\b', text_content)

        parsed['entities'] = {
            'products': list(set(products)),
            'errors': list(set(errors)),
            'actions': list(set(actions)),
            'references': list(set(references))
        }

        # Classify issue type
        issue_types = []
        if any(word in text_content.lower() for word in ['login', 'password', 'auth']):
            issue_types.append('authentication')
        if any(word in text_content.lower() for word in ['payment', 'billing', 'charge']):
            issue_types.append('payment')
        if any(word in text_content.lower() for word in ['slow', 'performance', 'hang']):
            issue_types.append('performance')
        if any(word in text_content.lower() for word in ['crash', 'error', 'bug']):
            issue_types.append('bug')

        parsed['issue_types'] = issue_types
        parsed['parsing_method'] = 'rule_based'

        return parsed

    def parse_ticket_llm(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """LLM-based parsing for semantic understanding."""

        if not self.model_name:
            raise ValueError("Model name required for LLM parsing")

        parsed = ticket_data.copy()

        # Prepare context for LLM
        context = f"""
Title: {ticket_data.get('title', '')}
Description: {ticket_data.get('description', '')}
Comments: {' | '.join([c.get('text', '') for c in ticket_data.get('comments', [])])}
Resolution: {ticket_data.get('resolution', '')}
Tags: {', '.join(ticket_data.get('tags', []))}
"""

        prompt = f"""
Analyze this customer service ticket and extract structured information. Return JSON format only.

Ticket Content:
{context}

Extract:
1. Key entities (products, features, error types)
2. Root cause analysis
3. Solution approach
4. Related concepts or similar issues
5. Sentiment (positive/negative/neutral)
6. Urgency level (low/medium/high/critical)

Format as JSON with keys: entities, root_cause, solution, related_concepts, sentiment, urgency
"""

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[{'role': 'user', 'content': prompt}],
                options={'temperature': 0.1, 'num_predict': 500}
            )

            llm_output = response['message']['content']

            # Try to parse JSON from response
            try:
                # Clean up response if it has extra text
                json_start = llm_output.find('{')
                json_end = llm_output.rfind('}') + 1
                if json_start != -1 and json_end != -1:
                    json_str = llm_output[json_start:json_end]
                    llm_data = json.loads(json_str)
                else:
                    llm_data = {}

                parsed['llm_analysis'] = llm_data
                parsed['parsing_method'] = 'llm'

            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM response as JSON for ticket {ticket_data['ticket_id']}")
                parsed['llm_analysis'] = {'error': 'JSON parsing failed'}
                parsed['parsing_method'] = 'llm_failed'

        except Exception as e:
            logger.error(f"LLM parsing failed for ticket {ticket_data['ticket_id']}: {str(e)}")
            parsed['llm_analysis'] = {'error': str(e)}
            parsed['parsing_method'] = 'llm_error'

        return parsed

def process_ticket_file(filepath: Path, method: str, model_name: str = None) -> Dict[str, Any]:
    """Process a single ticket file."""

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            ticket_data = json.load(f)

        parser = TicketParser(model_name)

        if method == 'rule_based':
            parsed_ticket = parser.parse_ticket_rule_based(ticket_data)
        elif method == 'llm':
            parsed_ticket = parser.parse_ticket_llm(ticket_data)
        else:
            # Hybrid: rule-based first, then LLM
            parsed_ticket = parser.parse_ticket_rule_based(ticket_data)
            if model_name:
                parsed_ticket = parser.parse_ticket_llm(parsed_ticket)

        return parsed_ticket

    except Exception as e:
        logger.error(f"Failed to process {filepath}: {str(e)}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Parse ticket data")
    parser.add_argument("--method", choices=['rule_based', 'llm', 'hybrid'],
                       default='hybrid', help="Parsing method")
    parser.add_argument("--input_dir", type=str, default="data/raw",
                       help="Input directory with raw tickets")
    parser.add_argument("--output_dir", type=str, default="data/processed",
                       help="Output directory for parsed tickets")
    parser.add_argument("--model", type=str, default="mistral:7b-instruct-v0.1-q4_0",
                       help="OLLAMA model for LLM parsing")
    parser.add_argument("--max_workers", type=int, default=4,
                       help="Maximum parallel workers")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_dir.exists():
        logger.error(f"Input directory {input_dir} does not exist")
        return

    # Get all ticket files
    ticket_files = list(input_dir.glob("*.json"))
    if not ticket_files:
        logger.error(f"No JSON files found in {input_dir}")
        return

    logger.info(f"Found {len(ticket_files)} ticket files to process")
    logger.info(f"Using method: {args.method}")

    # Process tickets
    processed_count = 0
    failed_count = 0

    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        future_to_file = {
            executor.submit(process_ticket_file, filepath, args.method, args.model): filepath
            for filepath in ticket_files
        }

        for future in as_completed(future_to_file):
            filepath = future_to_file[future]
            try:
                parsed_ticket = future.result()
                if parsed_ticket:
                    # Save parsed ticket
                    output_file = output_dir / filepath.name
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(parsed_ticket, f, indent=2, ensure_ascii=False)

                    processed_count += 1
                    if processed_count % 10 == 0:
                        logger.info(f"Processed {processed_count}/{len(ticket_files)} tickets")
                else:
                    failed_count += 1

            except Exception as e:
                logger.error(f"Failed to process {filepath}: {str(e)}")
                failed_count += 1

    logger.info(f"Processing complete!")
    logger.info(f"Successfully processed: {processed_count}")
    logger.info(f"Failed: {failed_count}")
    logger.info(f"Output directory: {output_dir.absolute()}")

if __name__ == "__main__":
    main()